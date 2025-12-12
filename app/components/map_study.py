import streamlit as st
import pandas as pd
import fsspec
import duckdb
import time
import numpy as np
import ast
from dotenv import dotenv_values
from .generate_transformations import generate_transformations
from .transformation_utils import generic_direct_conversion, generic_catagorical_conversion, validate_expression
from .util import split_var_confidence, format_example_data, add_to_session_state, pre_process_recomendations
from .validation import render_validation_widget

fs = fsspec.filesystem("")

results_path = "results"
input_path = "input"
preprocess_path = "preprocess"

mapping_options = ['To do',
        'Successfully mapped',
        'Marked to reconsider',
        'Marked unmappable']

if 'transformation_instructions' not in st.session_state:
    st.session_state.transformation_instructions = {}


# SECURITY: safe parsing helper for list-like values stored in CSVs (used for sorting).
# Kept at module scope so it can be covered by unit tests.
def _safe_first_distance(v):
    try:
        if pd.isna(v):
            return float('inf')
        if isinstance(v, (list, tuple)):
            return v[0] if len(v) > 0 else float('inf')
        if isinstance(v, str):
            parsed = ast.literal_eval(v)
            if isinstance(parsed, (list, tuple)):
                return parsed[0] if len(parsed) > 0 else float('inf')
        return float('inf')
    except Exception:
        return float('inf')


def write_to_results(study, variable_to_map, mapped_variable, notes, avail_idx, results_file, transformation_instructions=None, transformation_type=None, source_dtype=None, target_dtype=None, patient_id=None, date=None):
    """
    Writes the mapping results to a CSV file.

    Args:
        study (str): The study name.
        variable_to_map (str): The variable to map.
        mapped_variable (str): The mapped variable.
        notes (str): Notes about the mapping.
        avail_idx (int): Index of the mapping option.
        results_file (str): Path to the results file.
        transformation_instructions (str, optional): Transformation instructions. Defaults to None.
        transformation_type (str, optional): Type of transformation. Defaults to None.
        source_dtype (str, optional): Source data type. Defaults to None.
        target_dtype (str, optional): Target data type. Defaults to None.
        patient_id (str, optional): Patient ID. Defaults to None.
        date (str, optional): Date. Defaults to None.
    """
    codebook_var, confidence = split_var_confidence(mapped_variable)
    patient_id_var, patient_id_confidence = split_var_confidence(patient_id)
    date_var, date_confidence = split_var_confidence(date)

    mark_options = ['To do',
                    'Successfully mapped',
                    'Marked to reconsider',
                    'Marked unmappable']
    marked = mark_options[avail_idx]
    df_new = pd.DataFrame({
        'study_var': variable_to_map,
        'codebook_var': codebook_var,
        'confidence': confidence,
        'notes': notes,
        'marked': marked,
        'transformation_instructions': transformation_instructions,
        'transformation_type': transformation_type,
        'source_dtype': source_dtype,
        'target_dtype': target_dtype,
        'patient_id_var': patient_id_var,
        'patient_id_confidence': patient_id_confidence,
        'date_var': date_var,
        'date_confidence': date_confidence},
        index=[0])
    st.write('The following has been saved:')
    st.write(df_new)
    df_old = pd.read_csv(results_file)
    df_updated = pd.concat([df_old, df_new], ignore_index=True)
    df_updated = df_updated.drop_duplicates(subset=['study_var'], keep='last')
    df_updated.to_csv(results_file, index=False)
    add_to_session_state(study, patient_id_var, date_var)
    # Success confirmation for completed action
    st.success('Mapping saved successfully.')

def test_transformation(example_data, transformation_type, transformation_instructions, source_dtype, target_dtype):
    """
    Runs the transformation instructions on the example data. And displays the results.

    Args:
        example_data (list): List of example data.
        transformation_type (str): The type of transformation.
        transformation_instructions (str): The transformation instructions.
        source_dtype (str): The source data type.
        target_dtype (str): The target data type.
    """
    if transformation_instructions == '':
        transformed_data = None
    else:
        if transformation_type == 'Direct':
            try:
                transformed_list = [generic_direct_conversion(x, transformation_instructions, source_dtype, target_dtype) for x in example_data]
                transformed_data = format_example_data(transformed_list)
            except Exception as e:
                transformed_data = f'Direct transformation failed with error: {e}'
        elif transformation_type == 'Categorical':
            try:
                transformed_list = [generic_catagorical_conversion(x, transformation_instructions) for x in example_data]
                transformed_data = format_example_data(transformed_list)
            except Exception as e:
                transformed_data = f'Categorical transformation failed with error: {e}'
    st.write('Preview of transformation:')
    st.code(transformed_data)
    # Clearer transformation preview: side-by-side for first 10 samples when available
    try:
        if isinstance(example_data, list) and isinstance(transformation_instructions, str) and transformed_data and 'failed with error' not in str(transformed_data):
            original_list = [x for x in example_data][:10]
            # Recompute a short transformed list for preview if not already present
            if transformation_type == 'Direct':
                preview_transformed = [generic_direct_conversion(x, transformation_instructions, source_dtype, target_dtype) for x in original_list]
            elif transformation_type == 'Categorical':
                preview_transformed = [generic_catagorical_conversion(x, transformation_instructions) for x in original_list]
            else:
                preview_transformed = original_list
            preview_df = pd.DataFrame({'original': original_list, 'transformed': preview_transformed})
            st.dataframe(preview_df, use_container_width=True)
            # UI usability: Add a one-line summary (teaching preview) indicating how many values transformed
            # vs blanks to help users quickly gauge effect of their rule on the sample.
            try:
                if transformation_type == 'Direct':
                    all_transformed = [generic_direct_conversion(x, transformation_instructions, source_dtype, target_dtype) for x in example_data]
                elif transformation_type == 'Categorical':
                    all_transformed = [generic_catagorical_conversion(x, transformation_instructions) for x in example_data]
                else:
                    all_transformed = []
                if isinstance(all_transformed, list) and len(all_transformed) > 0:
                    M = len(example_data)
                    def _is_blank(v):
                        return (v is None) or (isinstance(v, float) and np.isnan(v)) or (isinstance(v, str) and v.strip() == '')
                    K = sum(1 for v in all_transformed if _is_blank(v))
                    N = M - K
                    st.caption(f"Transformed {N}/{M}; {K} blanks")
            except Exception:
                pass
    except Exception:
        pass

def map_study(study, variables_status, show_about, original_order, relational_mode, enable_transformations):
    """
    Main function to map study variables to codebook variables.

    Args:
        study (str): The study name.
        variables_status (str): The status of the variables to map.
        show_about (bool): Whether to show the about section.
        original_order (bool): Whether to sort variables in original order.
        relational_mode (bool): Whether to enable relational mode.
        enable_transformations (bool): Whether to enable transformations.
    """
    config = dotenv_values(".env")

    if 'auto_transform_available' in list(config):
        auto_transform_available = config['auto_transform_available']
    else:
        auto_transform_available = 'no'

    if auto_transform_available == 'yes':
        codebook = pd.read_csv(f'{input_path}/target_variables.csv')
    
    if study == None:
        st.write(':red[No studies available, please initialise the mapping app]')
    else:
        transformation_instruction = None
        fs.mkdirs(results_path, exist_ok=True)
        results_file = f'{results_path}/{study}.csv'
        study_input_path = f"{input_path}/{study}"
        # about data
        if show_about:
            # Clarify header to "Study <name>" for better context in About section
            st.write(f"### Study {study}")
            if fs.exists(f"input/{study}/description.txt"):
                with fs.open(f"{study_input_path}/description.txt", 'r') as of:
                    text = of.read()
                st.write(text)
            st.divider()

        if not fs.exists(f'{input_path}/{study}/dataset_variables_with_PID_date_recommendations.csv'):
            st.write(":red[This study has not had a recommendations file created please initialise the mapping app before proceeding.]")
        else:
            # Render validation panel for codebook and study inputs
            render_validation_widget(study)

            vars_df = pd.read_csv(
                f'{input_path}/{study}/dataset_variables_with_PID_date_recommendations.csv'
                )

            # the below sorts the variables by difficulty to match to a codebook variable
            vars_df['best_dist'] = [_safe_first_distance(x) for x in vars_df['target_distances']]
            # get variables
            vars_unsorted = vars_df['variable_name']
            # get variables sorted
            vars_df = vars_df.sort_values('best_dist')
            all_variables = vars_df['variable_name']

            # get already mapped/init
            if not fs.exists(results_file):
                # write an empty dataframe to file
                empty_df = pd.DataFrame(columns=['study_var',
                                                 'codebook_var',
                                                 'confidence',
                                                 'notes',
                                                 'marked',
                                                 'patient_id',
                                                 'date',
                                                 'time'])
                empty_df['study_var'] = all_variables
                empty_df['marked'] = 'To do'
                empty_df.to_csv(results_file, index=False)

            # --- Progress context: show mapped/total summary for the study ---
            try:
                _full_results = pd.read_csv(results_file)
                _total = len(vars_unsorted)
                _mapped = (_full_results['marked'] == 'Successfully mapped').sum() if 'marked' in _full_results.columns else 0
                st.caption(f"{_mapped}/{_total} variables mapped")
                if _total > 0:
                    st.progress(min(max(_mapped / _total, 0.0), 1.0))
            except Exception:
                pass

            # query results file
            variables = duckdb.sql(f"""SELECT study_var
                                FROM read_csv_auto('{results_file}', delim = ',', header = True)
                                WHERE marked = '{variables_status}'""")
            # coerce db output to list
            variables = list(variables.fetchdf()['study_var'].values)

            # sort in original order if requested
            if original_order:
                variables = [x for x in vars_unsorted if x in variables]

            if len(variables) == 0:
                st.write(f'No variables have been: :red[{variables_status}]')
            else:
                # get var to map
                variable_to_map = st.selectbox('Select Variable To Map', variables)

                # previous info
                if not variables_status == 'To do':
                    st.write('The following information has previously been recorded:')
                    _prev_df = duckdb.sql(f"""SELECT *
                                        FROM read_csv_auto('{results_file}', delim = ',', header = True)
                                        WHERE study_var = '{variable_to_map}'""").fetchdf()
                    # Compact, read-only details for review
                    _display_cols = ['study_var','codebook_var','confidence','marked','patient_id_var','date_var','transformation_type','transformation_instructions','notes']
                    _display_cols = [c for c in _display_cols if c in _prev_df.columns]
                    if _display_cols:
                        st.dataframe(_prev_df[_display_cols], use_container_width=True)
                    else:
                        st.dataframe(_prev_df, use_container_width=True)

                    # Optional: allow reopening for edit (moves item back to To do)
                    if st.button('Reopen for edit'):
                        try:
                            _df_old = pd.read_csv(results_file)
                            _df_old.loc[_df_old['study_var'] == variable_to_map, 'marked'] = 'To do'
                            _df_old.to_csv(results_file, index=False)
                            st.success('Moved to To do. Switch to "To do" view to edit.')
                        except Exception as e:
                            st.error(f'Failed to reopen for edit: {e}')

                    # Read-only mode: do not render mapping UI below
                    return

                example_avail = False
                col1, col2 = st.columns(2)
                with col1:
                    # information about variable
                    st.write('Variable name and description:')
                    to_map_df = vars_df[vars_df['variable_name'] == variable_to_map]
                    df_to_show = to_map_df[['variable_name', 'description']].set_index('variable_name')
                    st.dataframe(df_to_show, use_container_width=True)
                with col2:
                    # show synthetic
                    st.write('Example data:')
                    if fs.exists(f"{study_input_path}/example_data.csv"):
                        synthetic_df = pd.read_csv(f"{study_input_path}/example_data.csv")
                        if variable_to_map in list(synthetic_df.columns):
                            example_data = synthetic_df[variable_to_map]
                            example_data = [str(x) for x in list(example_data.dropna())]
                            st.code(format_example_data(example_data))
                            example_avail = True
                    else:
                        st.warning('No example_data.csv found; transformation preview may be limited for this study.')

                st.write('Please complete the form below:')
                # append confidence to var name
                recommended_keys = pre_process_recomendations(to_map_df, 'target', study)
                # SAFETY: hide codebook variables already mapped for other study variables to reduce accidental duplicates
                try:
                    _res_df = pd.read_csv(results_file)
                    _used = set(
                        # Treat any non-'To do' record as "already used" (e.g., Successfully mapped, Marked to reconsider, Marked unmappable)
                        _res_df.loc[_res_df['marked'] != 'To do', 'codebook_var']
                        .dropna()
                        .astype(str)
                        .str.strip()
                        .tolist()
                    )
                    _used = {u for u in _used if u and u.lower() != 'none'}

                    _prev_row = _res_df.loc[_res_df['study_var'] == variable_to_map]
                    _prev_codebook = None
                    if not _prev_row.empty and 'codebook_var' in _prev_row.columns:
                        try:
                            _prev_codebook = str(_prev_row.iloc[-1]['codebook_var']).strip()
                        except Exception:
                            _prev_codebook = None

                    if _used and isinstance(recommended_keys, list):
                        _filtered = []
                        for k in recommended_keys:
                            v, _ = split_var_confidence(k)
                            v = str(v).strip()
                            if (_prev_codebook and v == _prev_codebook) or (v not in _used):
                                _filtered.append(k)
                        if _filtered:
                            recommended_keys = _filtered
                except Exception:
                    pass
                # select variable
                mapped_variable = st.selectbox('Does this map to any of these variables?', recommended_keys) # type: ignore
                # Always compute and show match confidence immediately after selection (independent of transformations)
                codebook_var, codebook_conf = split_var_confidence(mapped_variable)
                try:
                    conf_int = int(str(codebook_conf).strip().rstrip('%')) if codebook_conf else 0
                except Exception:
                    conf_int = 0
                try:
                    conf_col1, conf_col2 = st.columns([1,3])
                    with conf_col1:
                        st.metric('Match confidence', f"{conf_int}%")
                        # UI usability: Add a simple status label (Strong/Review/Verify) for fast interpretation.
                        try:
                            status = 'Strong' if conf_int >= 80 else ('Review' if conf_int >= 60 else 'Verify')
                            status_emoji = '🟢' if conf_int >= 80 else ('🟠' if conf_int >= 60 else '🔴')
                            st.caption(f"{status_emoji} {status}")
                        except Exception:
                            pass
                    with conf_col2:
                        st.progress(min(max(conf_int, 0), 100) / 100.0)
                        # UI usability: Tooltip-style thresholds explanation as microcopy for clarity.
                        st.caption('Thresholds: 80–100 Strong, 60–79 Review, <60 Verify')
                except Exception:
                    pass
                if relational_mode:
                    patient_id_keys = pre_process_recomendations(to_map_df, 'PID', study)
                    patient_id = st.selectbox('Patient ID:', patient_id_keys) # type: ignore
                    date_keys = pre_process_recomendations(to_map_df, 'date', study)
                    date = st.selectbox('Date:', date_keys) # type: ignore
                else:
                    patient_id = 'None  - 0%'
                    date = 'None  - 0%'
                # select mapping option
                avail_idx = st.radio("Can this variable be mapped to our codebook?",
                                     range(len(mapping_options)),
                                     index=1,
                                     format_func=lambda x: mapping_options[x])  # returns index of options
                notes = st.text_input('Notes about this variable:', '')
                if enable_transformations and example_avail:
                    # Initialize the transformation instructions dictionary if it doesn't exist
                    if 'transformation_instructions' not in st.session_state:
                        st.session_state.transformation_instructions = {}

                    dtype_options = ['float', 'integer', 'string', 'boolean']
                    # Ensure defaults exist for all branches; Categorical does not use these,
                    # but test_transformation() is called with them, so define upfront to avoid UnboundLocalError.
                    source_dtype = None
                    target_dtype = None
                    target_dtype_idx = 0
                    if auto_transform_available == 'yes':
                        # Robustly match the selected codebook entry by description or variable name
                        # Normalize both sides (trim + case-insensitive)
                        norm_target = str(codebook_var).strip().casefold()
                        candidates = [c for c in ['description', 'Description', 'variable_name', 'Variable', 'Variable Name'] if c in codebook.columns]
                        if candidates:
                            parts = []
                            for col in candidates:
                                try:
                                    part = codebook[codebook[col].astype(str).str.strip().str.casefold() == norm_target]
                                    if len(part):
                                        parts.append(part)
                                except Exception:
                                    continue
                            if parts:
                                codebook_var_df = pd.concat(parts).drop_duplicates()
                            else:
                                codebook_var_df = codebook.iloc[0:0]
                        else:
                            # Fallback to original behavior if expected columns are missing
                            codebook_var_df = codebook[codebook['description'] == codebook_var]
                        # Handle case when the filter returns no rows or multiple rows
                        if len(codebook_var_df) != 1:
                            # Safe default values when the expected row isn't found
                            value = float('nan')  # Default to NaN
                            dtype = 'string'       # Default to string type
                        else:
                            # Extract values only when we have exactly one row
                            value = codebook_var_df.Categories.item()
                            dtype = codebook_var_df.dType.item()
                            
                        if isinstance(value, float) and np.isnan(value): # direct
                            transformation_type_idx = 0
                            if variable_to_map not in st.session_state.transformation_instructions:
                                st.session_state.transformation_instructions[variable_to_map] = 'x'
                            try:
                                target_dtype_idx = dtype_options.index(dtype)
                            except:
                                target_dtype_idx = 0
                        else: # categorical
                            transformation_type_idx = 1
                            if variable_to_map not in st.session_state.transformation_instructions:
                                st.session_state.transformation_instructions[variable_to_map] = '{}'
                        generate_instructions = st.button('Auto Generate Transformation Instructions', key='generate')
                        if generate_instructions:
                            # Validate codebook row uniqueness before calling generator
                            # If the description does not uniquely identify a single codebook row, do not call the generator.
                            if len(codebook_var_df) != 1:
                                if len(codebook_var_df) == 0:
                                    st.error("Auto-generation blocked: No unique codebook row found for the selected description. (ERR-CODEBOOK-NO-MATCH)")
                                else:
                                    st.error("Auto-generation blocked: Multiple codebook rows matched the selected description. (ERR-CODEBOOK-MULTI-MATCH)")
                                st.info("Tips: Ensure descriptions in target_variables.csv are unique for each target variable, or select a different mapping. You may also refine the codebook to remove duplicates.")
                            else:
                                prev_instr = st.session_state.transformation_instructions.get(variable_to_map, '')
                                try:
                                    ai_result = generate_transformations(
                                        split_var_confidence(mapped_variable)[0],
                                        variable_to_map,
                                        example_data,
                                        prev_instr,
                                        codebook_var_df
                                    )
                                except Exception as e:
                                    ai_result = None
                                    st.error(f"Auto-generation failed: {e} (ERR-AUTO-GEN-EXC)")
                                # Only update session state with valid strings; otherwise preserve previous or fallback
                                if isinstance(ai_result, str) and ai_result.strip():
                                    if transformation_type_idx == 0:
                                        # Direct expression must be valid
                                        try:
                                            is_valid, msg = validate_expression(ai_result)
                                        except Exception as e:
                                            is_valid, msg = (False, f"Validation error: {e}")
                                        if is_valid:
                                            st.session_state.transformation_instructions[variable_to_map] = ai_result
                                            st.success("Auto-generated direct transformation applied.")
                                        else:
                                            st.error(f"Generated expression invalid: {msg} (ERR-AUTO-GEN-DIRECT-INVALID)")
                                            if prev_instr:
                                                st.info("Preserved previous instructions.")
                                            else:
                                                st.info("Using safe default 'x' as fallback.")
                                                st.session_state.transformation_instructions[variable_to_map] = 'x'
                                    else:
                                        # Categorical: basic sanity check — must look like a dict string
                                        txt = ai_result.strip()
                                        if txt.startswith('{') and txt.endswith('}'):
                                            st.session_state.transformation_instructions[variable_to_map] = ai_result
                                            st.success("Auto-generated categorical mapping applied.")
                                        else:
                                            st.error("Generated categorical mapping is not a dictionary-like string. (ERR-AUTO-GEN-CAT-INVALID)")
                                            if prev_instr:
                                                st.info("Preserved previous instructions.")
                                            else:
                                                st.info("Using safe default '{}' as fallback.")
                                                st.session_state.transformation_instructions[variable_to_map] = '{}'
                                else:
                                    st.error("No valid transformation was returned by the AI provider. (ERR-AUTO-GEN-NONE)")
                                    if prev_instr:
                                        st.info("Preserved previous instructions.")
                                    else:
                                        default_fallback = 'x' if transformation_type_idx == 0 else '{}'
                                        st.info(f"Using safe default '{default_fallback}' as fallback.")
                                        st.session_state.transformation_instructions[variable_to_map] = default_fallback
                    else:
                        generate_instructions = st.button('Auto Generate Transformation Instructions', key='generate', disabled=True, help='Auto transformations are not available for this study as the target codebook does not contain dType, Unit, Categories, or Unit Example columns.')
                        transformation_type_idx = 0
                        if variable_to_map not in st.session_state.transformation_instructions:
                            st.session_state.transformation_instructions[variable_to_map] = 'x'
                        target_dtype_idx = 0

                    col3, col4 = st.columns(2)
                    with col3:
                        transformation_types = ['Direct', 'Categorical']
                        transformation_type = st.selectbox('Type of transformation applied to this variable:', transformation_types, index=transformation_type_idx)
                        # UI usability: Microcopy clarifying Direct vs Categorical inputs to reduce confusion.
                        st.caption("Direct: Use x with +, -, *, / (e.g., x/12, x*2, x-5). Categorical: Provide a Python dict like {'0':'No','1':'Yes'} with string keys.")
                        # UI usability: Lightweight onboarding expander with examples; dismissible via session state.
                        if 'hide_transform_tip' not in st.session_state:
                            st.session_state['hide_transform_tip'] = False
                        if not st.session_state['hide_transform_tip']:
                            with st.expander('How do I choose?'):
                                st.markdown(
                                    "- Direct (numbers): Keep arithmetic simple with x. Examples: `x`, `x*100`, `x/12`, `x-5`.\n"
                                    "- Categorical (labels): Map raw values to labels. Examples: `{'0':'No','1':'Yes'}`, `{'M':'Male','F':'Female'}`."
                                )
                                if st.button('Dismiss tip', key='dismiss_tip'):
                                    st.session_state['hide_transform_tip'] = True
                        if transformation_type == 'Direct':
                            source_dtype = st.selectbox('Source data type:', dtype_options)
                            target_dtype = st.selectbox('Target data type:', dtype_options, index=target_dtype_idx)
                            # Provide real-time validation feedback for Direct expressions
                            st.caption('Allowed operations: +, -, *, /; variable: x (e.g., x/12, x*2, x-5)')
                            # UI usability: Rename "Quick preset" to "Examples" and add x-5 to make patterns explicit.
                            preset_options = {
                                'Choose an example...': None,
                                'Keep as is (x)': 'x',
                                'Scale up (x*100)': 'x*100',
                                'Scale down (x/100)': 'x/100',
                                'Months → Years (x/12)': 'x/12',
                                'Years → Months (x*12)': 'x*12',
                                'Subtract constant (x-5)': 'x-5',
                            }
                            preset_choice = st.selectbox('Examples:', list(preset_options.keys()))
                            if preset_choice and preset_options[preset_choice] is not None and st.button('Apply example', key='apply_preset'):
                                preset_val = preset_options[preset_choice]
                                # Update backing store and the widget state BEFORE instantiation
                                st.session_state.transformation_instructions[variable_to_map] = preset_val
                                st.session_state['transformation_input'] = preset_val
                        else:
                            # Categorical helpers (apply BEFORE creating text_input)
                            # UI usability: Clarify requirement for string keys in categorical map.
                            st.caption("Provide a Python dict like {'0':'No','1':'Yes'} with string keys.")
                            if st.button('Insert template from sample', key='insert_cat_template'):
                                try:
                                    # Build a small dict skeleton from top unique values
                                    uniq = []
                                    seen = set()
                                    for v in example_data:
                                        if v not in seen:
                                            uniq.append(v)
                                            seen.add(v)
                                        if len(uniq) >= 6:
                                            break
                                    template = '{' + ', '.join([f"'{str(k)}': ''" for k in uniq]) + '}'
                                    st.session_state.transformation_instructions[variable_to_map] = template
                                    st.session_state['transformation_input'] = template
                                except Exception:
                                    st.warning('Could not build a template from sample values.')
                        # Ensure the widget key is initialized before creating the widget
                        if 'transformation_input' not in st.session_state:
                            st.session_state['transformation_input'] = st.session_state.transformation_instructions.get(variable_to_map, '')
                        transformation_instruction_final = st.text_input(
                            'Transformation instructions for this variable:',
                            st.session_state.transformation_instructions.get(variable_to_map, ''),
                            key='transformation_input'
                        )
                        st.session_state.transformation_instructions[variable_to_map] = transformation_instruction_final
                        if transformation_type == 'Direct' and transformation_instruction_final:
                            try:
                                is_valid, msg = validate_expression(transformation_instruction_final)
                                if is_valid:
                                    st.success(msg)
                                else:
                                    st.error(f"Invalid expression: {msg}")
                                    # UI usability: Provide actionable tips to recover from common validation errors.
                                    try:
                                        tip = None
                                        low = str(msg).lower()
                                        if 'operator not allowed' in low or 'operator' in low:
                                            tip = 'Only +, -, *, / are allowed. Example: x/12 or x*100.'
                                        elif 'name not allowed' in low:
                                            tip = "Use the variable x only (e.g., x, x/12, x-5)."
                                        elif 'unsupported' in low or 'call' in low:
                                            tip = 'Avoid functions, attributes, or indexing. Keep it as simple arithmetic with x.'
                                        elif 'missing variable' in low:
                                            tip = "Expression must reference x. Start with 'x' and add arithmetic (e.g., x*2)."
                                        if tip:
                                            st.info(f"Tip: {tip}")
                                    except Exception:
                                        pass
                            except Exception as e:
                                st.error(f"Validation error: {e}")
                        elif transformation_type == 'Categorical' and transformation_instruction_final:
                            # Inline validation with actionable feedback
                            txt = transformation_instruction_final.strip()
                            if not (txt.startswith('{') and txt.endswith('}')):
                                st.error("Expected a dict literal like {'0':'No','1':'Yes'} (include braces and quotes around keys).")
                            else:
                                try:
                                    parsed = ast.literal_eval(txt)
                                    if isinstance(parsed, dict):
                                        st.success('Mapping format looks good.')
                                    else:
                                        st.error("Mapping must be a dict (e.g., {'0':'No','1':'Yes'}).")
                                except Exception as e:
                                    st.error(f"Invalid mapping: {e}")
                                    # UI usability: Short guidance to fix common dict literal mistakes.
                                    st.info("Tip: Ensure braces {}, quotes around keys and values, colons between key and value, and commas between pairs. Example: {'0':'No','1':'Yes'}")
                        else:
                            source_dtype = None
                            target_dtype = None
                    
                    with col4:
                        test_transformation(example_data, transformation_type, transformation_instruction_final, source_dtype, target_dtype)
                        if st.session_state.get('transformation_input') != st.session_state.get('last_transformation_input'):
                            st.session_state['last_transformation_input'] = st.session_state.get('transformation_input')
                    transformation_instruction = st.session_state.transformation_instructions.get(variable_to_map, None)
                else:
                    transformation_instruction = None
                    transformation_type = None
                    source_dtype = None
                    target_dtype = None
                submitted = st.button(":green[Submit]", key='submit')
                if submitted:
                    # write mappings to results
                    _ = write_to_results(study, variable_to_map, mapped_variable, notes, avail_idx, results_file, transformation_instruction, transformation_type, source_dtype, target_dtype, patient_id, date)
                    transformation_instruction = None
                    # sleep a few seconds to show results being written
                    time.sleep(0.2)
                    # I need to use session states, the above is a hack to fix death looping, but also this is vagualy equivalant to repaint in react which is what I want
                    # see https://discuss.streamlit.io/t/how-should-st-rerun-behave/54153/2
                    del st.session_state['submit']
                    st.rerun()