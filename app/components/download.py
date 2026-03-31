import streamlit as st
import pandas as pd
import fsspec
import io
import zipfile
import re
import logging

logger = logging.getLogger(__name__)
from .transform_engine import (
    load_study_data,
    load_mapping,
    apply_transformations,
    build_mapping_summary,
    generate_validation_report,
)

results_path = "results"
input_path = "input"

fs = fsspec.filesystem("")

def convert_to_download(df):
    """
    Convert a DataFrame to a CSV format and encode it in UTF-8.

    Args:
        df (pd.DataFrame): The DataFrame to convert.

    Returns:
        bytes: The CSV data encoded in UTF-8.
    """
    return df.to_csv().encode('utf-8')

def download_page():
    """
    Display a Streamlit page for downloading study results as CSV files.

    This function lists available study results, allows the user to select one,
    displays the DataFrame, and provides a download button for the selected study.
    """
    # List studies from input/ so initialized studies show up even if no results CSV exists yet.
    try:
        avail_studies = [f for f in fs.ls(f"{input_path}/") if fs.isdir(f)]
        avail_studies = [f.split('/')[-1] for f in avail_studies if not f.split('/')[-1].startswith('.')]
        avail_studies = sorted(avail_studies)
    except Exception:
        avail_studies = []
 
    if len(avail_studies) == 0:
        st.write(':red[No studies available, please initialise the mapping app]')
        return
 
    name = st.selectbox('Select study to download:', avail_studies)
    
    # SECURITY: Validate study name to prevent path traversal
    safe_name = re.sub(r'[^\w\s-]', '', name).strip()
    if safe_name != name or not safe_name:
        st.error("Invalid study name")
        return
    
    results_file = f"{results_path}/{safe_name}.csv"
 
    if not fs.exists(results_file):
        st.warning(f"No results found for '{name}' yet. Map at least one variable in Map Studies to create results.")
        # Optional: allow creating an empty results file (same structure Map Studies creates).
        if st.button('Create empty results file'):
            try:
                vars_df = pd.read_csv(f"{input_path}/{name}/dataset_variables_with_PID_date_recommendations.csv")
                all_variables = vars_df['variable_name']
                empty_df = pd.DataFrame(columns=['study_var', 'codebook_var', 'confidence', 'notes', 'marked', 'patient_id', 'date', 'time'])
                empty_df['study_var'] = all_variables
                empty_df['marked'] = 'To do'
                fs.mkdirs(results_path, exist_ok=True)
                empty_df.to_csv(results_file, index=False)
                st.success('Empty results file created. You can now select it for download.')
                st.rerun()
            except Exception as e:
                st.error(f"Could not create empty results file: {e}")
        return
 
    df = pd.read_csv(results_file)
    df = df.replace('0%', None)  # Explicit assignment instead of inplace
    # only keep the core columns and drop the rest where all values are NaN
    df1 = df[['study_var', 'codebook_var', 'confidence', 'notes', 'marked']]
    df2 = df.drop(columns=['study_var', 'codebook_var', 'confidence', 'notes', 'marked']).dropna(axis=1, how='all')
    df = pd.concat([df1, df2], axis=1)

    # reverse the order of the columns
    df = df.iloc[::-1]

    col1, col2= st.columns(2)
    with col1:
        st.dataframe(df)
    with col2:
        # UX: If no example data exists for the selected study, advise metadata-only users to use CSV export.
        try:
            has_example = fs.exists(f"{input_path}/{name}/example_data.csv")
        except Exception:
            has_example = False
        if not has_example:
            st.info("Metadata-only mapping detected (no example_data.csv). Please download 'Mapping only (CSV)'. The 'Full data package (ZIP)' requires example data.")

        export_mode = st.selectbox(
            "Export format",
            options=["Mapping only (CSV)", "Full data package (ZIP)"]
        )
        # AUDIT: allow exporting the append-only audit trail for compliance/traceability.
        try:
            if fs.exists('logs/mapping_audit.jsonl'):
                with fs.open('logs/mapping_audit.jsonl', 'r') as f:
                    audit_txt = f.read()
                st.download_button(
                    label="Download audit log (JSONL)",
                    data=audit_txt.encode('utf-8'),
                    file_name='mapping_audit.jsonl',
                    mime='application/json',
                )
            else:
                st.caption('Audit log not found (no mapping writes recorded yet).')
        except Exception:
            st.caption('Audit log not available.')
        if export_mode == "Mapping only (CSV)":
            st.download_button(
                label="Download mapping CSV",
                data=convert_to_download(df),
                file_name=f'{name}_mapping_results.csv',
                mime='text/csv',
            )
        else:
            # Build transformed outputs and ZIP package
            steps_total = 5
            progress = st.progress(0)
            status = st.empty()

            try:
                status.text("Loading original data...")
                original_df = load_study_data(safe_name)
                progress.progress(1/steps_total)
            except Exception as e:
                # SECURITY: Log full error but show sanitized message
                logger.error(f"Cannot load original data for study '{safe_name}': {str(e)}")
                st.error(f"Cannot load original data for study '{safe_name}'. Check study configuration.")
                return
            try:
                status.text("Loading mapping results...")
                mapping_df = load_mapping(safe_name)
                progress.progress(2/steps_total)
            except Exception as e:
                # SECURITY: Log full error but show sanitized message
                logger.error(f"Cannot load mapping results for study '{safe_name}': {str(e)}")
                st.error(f"Cannot load mapping results for study '{safe_name}'. Check study configuration.")
                return

            status.text("Applying transformations...")
            transformed_df, metrics, warnings = apply_transformations(original_df, mapping_df)
            progress.progress(3/steps_total)

            status.text("Building reports...")
            mapping_summary = build_mapping_summary(mapping_df)
            validation_report = generate_validation_report(metrics, warnings)
            progress.progress(4/steps_total)

            # Preview transformed data
            st.markdown("#### Preview: transformed data (first 20 rows)")
            st.dataframe(transformed_df.head(20))

            # Compute summary
            total_success = sum(m.get("success", 0) for m in metrics.values())
            total_errors = sum(m.get("errors", 0) for m in metrics.values())
            total_records = total_success + total_errors
            success_rate = (100.0 * total_success / total_records) if total_records else 0.0
            summary_txt = []
            summary_txt.append(f"Study: {name}")
            summary_txt.append(f"Variables processed: {len(metrics)}")
            summary_txt.append(f"Total records processed: {total_records}")
            summary_txt.append(f"Successes: {total_success}")
            summary_txt.append(f"Errors: {total_errors}")
            summary_txt.append(f"Success rate: {success_rate:.2f}%")
            if warnings:
                summary_txt.append("")
                summary_txt.append("Warnings:")
                summary_txt.extend([f"- {w}" for w in warnings])
            summary_txt_str = "\n".join(summary_txt)

            # SECURITY: Check total size before creating ZIP to prevent memory exhaustion
            max_zip_size = 100 * 1024 * 1024  # 100MB
            csv_data = {
                'original_data.csv': original_df.to_csv(index=False),
                'transformed_data.csv': transformed_df.to_csv(index=False),
                'mapping_summary.csv': mapping_summary.to_csv(index=False),
                'validation_report.txt': validation_report,
                'summary.txt': summary_txt_str
            }
            total_size = sum(len(data.encode('utf-8')) for data in csv_data.values())
            if total_size > max_zip_size:
                st.error(f"Export package too large ({total_size/1024/1024:.1f}MB). Maximum: {max_zip_size/1024/1024:.0f}MB")
                return

            # Create ZIP in-memory
            memfile = io.BytesIO()
            with zipfile.ZipFile(memfile, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
                for filename, data in csv_data.items():
                    zf.writestr(filename, data)
            memfile.seek(0)

            status.text("Packaging files...")
            progress.progress(5/steps_total)
            st.success("Export package is ready.")

            st.download_button(
                label="Download full data package (ZIP)",
                data=memfile.getvalue(),
                file_name=f'{name}_data_package.zip',
                mime='application/zip',
            )
            status.empty()

