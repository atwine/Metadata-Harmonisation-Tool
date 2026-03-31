import streamlit as st
import pandas as pd
import fsspec
import clevercsv
import os
from io import StringIO
import json
from datetime import datetime

"""Paths resolved to work in both app runtime (cwd=app/) and tests.
Prefer local ./input if present, otherwise fall back to repo root /input.
"""
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_CWD_BASE = os.path.abspath(os.getcwd())
_LOCAL_INPUT = os.path.join(_CWD_BASE, "input")
_LOCAL_RESULTS = os.path.join(_CWD_BASE, "results")
_REPO_INPUT = os.path.join(BASE_DIR, "input")
_REPO_RESULTS = os.path.join(BASE_DIR, "results")
input_path = _LOCAL_INPUT if os.path.exists(_LOCAL_INPUT) else _REPO_INPUT
results_path = _LOCAL_RESULTS if os.path.exists(_LOCAL_RESULTS) else _REPO_RESULTS
preprocess_path = "preprocess"

fs = fsspec.filesystem("")

def streamlit_csv_reader(file_up):
    """
    Reads a CSV file uploaded via Streamlit's file uploader and returns a pandas DataFrame.
    
    Args:
        file_up (UploadedFile): The file uploaded via Streamlit's file uploader.
    
    Returns:
        DataFrame: A pandas DataFrame containing the CSV data.
        
    Raises:
        ValueError: If file validation fails
    """
    # SECURITY: Validate file extension
    if not file_up.name.lower().endswith('.csv'):
        raise ValueError("File must be a CSV file")
    
    # SECURITY: Validate file size (10MB limit)
    max_size = 10 * 1024 * 1024
    content = file_up.getvalue()
    if len(content) > max_size:
        raise ValueError(f"File too large. Maximum size: {max_size/1024/1024:.0f}MB")
    
    # SECURITY: Validate content is valid UTF-8 text
    try:
        text_content = content.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError("File must contain valid UTF-8 text")
    
    stringio = StringIO(text_content)
    delim = clevercsv.Sniffer().sniff(stringio.read()).delimiter # type: ignore
    return pd.read_csv(file_up, sep = delim)

def upload_codebook(file_in):
    """
    Processes the uploaded codebook CSV file and saves it to the input path.
    
    Args:
        file_in (UploadedFile): The codebook file uploaded via Streamlit's file uploader.
    """
    target_df = streamlit_csv_reader(file_in)
    try:
        target_df = target_df[['variable_name', 'description', 'dType', 'Unit', 'Categories', 'Unit Example']]
    except:
        target_df = target_df[['variable_name', 'description']]
    fs.mkdirs(f"{input_path}/", exist_ok = True)
    target_df.to_csv(f"{input_path}/target_variables.csv", index = False)
    # Persist lightweight metadata for UX (filename, rows, timestamp) to enable a visible banner across app restarts
    try:
        meta = {
            "filename": getattr(file_in, "name", "target_variables.csv"),
            "rows": int(len(target_df)),
            "saved_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ"),
        }
        with fs.open(f"{input_path}/target_variables.meta.json", "w") as f:
            json.dump(meta, f)
    except Exception:
        # Non-critical: failure to write metadata should not break upload
        pass

def upload_codebook_page():
    """
    Renders the Streamlit page for uploading and displaying the codebook.
    """
    col1, col2 = st.columns(2)
    with col1:
        # Last upload banner: show filename, variable count, and timestamp if previously uploaded
        try:
            _meta_path = f"{input_path}/target_variables.meta.json"
            if fs.exists(_meta_path):
                with fs.open(_meta_path, "r") as _mf:
                    _meta = json.load(_mf)
                _fn = _meta.get("filename", "target_variables.csv")
                _rows = _meta.get("rows")
                _ts = _meta.get("saved_at")
                details = []
                if _rows is not None:
                    details.append(f"{_rows} variables")
                if _ts:
                    details.append(_ts)
                _extra = f" — {' • '.join(details)}" if details else ""
                st.info(f"Last codebook upload: {_fn}{_extra}")
        except Exception:
            pass
        st.write("To Upload a new codebook complete the form below.")
        with st.form("my_form"):
            new_target_df = st.file_uploader(
                'Target Codebook',
                type='csv',
                accept_multiple_files=False,
                help=(
                    "Only CSV format accepted. Required columns: 'variable_name' and 'description'. "
                    "Optional: 'dType', 'Unit', 'Categories', 'Unit Example'."
                )
            )
            # Streamlit forms only transmit widget values on submit; do not disable based on file_uploader here.
            submit = st.form_submit_button(
                ":green[Upload Codebook]",
                help='Note when uploading a new codebook the recommendation engine will rerun for all studies. This may take a few minutes.'
            )
            if submit:
                # Guard: ensure a file was provided; show clear success/failure feedback
                if new_target_df is None:
                    st.error("Please select a codebook CSV before submitting.")
                else:
                    try:
                        upload_codebook(new_target_df)
                        # Success indicator with basic details so users know it worked
                        try:
                            _saved_df = pd.read_csv(f'{input_path}/target_variables.csv')
                            st.success(f"Codebook uploaded successfully: {len(_saved_df)} variables saved.")
                        except Exception:
                            st.success("Codebook uploaded successfully.")
                        # Lightweight toast for additional visibility
                        try:
                            st.toast("Codebook updated", icon="✅")
                        except Exception:
                            pass
                    except Exception as e:
                        st.error(f"Failed to upload codebook: {e}")
        with st.expander("Codebook CSV format (required columns)"):
            st.markdown(
                "- **Required**: `variable_name`, `description`\n"
                "- **Optional**: `dType`, `Unit`, `Categories`, `Unit Example`\n"
                "- **dType supported**: `float`, `integer`, `string`, `boolean` (other values are accepted but default handling applies)\n"
                "- **Study variables CSV**: must also have `variable_name`, `description` (description may be empty)\n"
                "- **Example data CSV (optional)**: column names must match `variable_name` in the variables CSV"
            )
            try:
                _sample_img = os.path.join(BASE_DIR, "assets", "images", "sample_data.png")
                if os.path.exists(_sample_img):
                    st.image(_sample_img, caption="Sample variables CSV format", use_container_width=True)
            except Exception:
                pass
                
    with col2:
        if fs.exists(f'{input_path}/target_variables.csv'):
            st.write("Target Codebook")
            target_df = pd.read_csv(f'{input_path}/target_variables.csv')
            _display_cols = ['variable_name', 'description', 'dType', 'Unit', 'Categories', 'Unit Example']
            _display_cols = [c for c in _display_cols if c in target_df.columns]
            if _display_cols:
                target_df = target_df[_display_cols]
            st.dataframe(target_df, use_container_width=True)
        else:
            st.write("No codebook is currently loaded")