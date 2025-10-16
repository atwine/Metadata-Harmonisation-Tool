import streamlit as st
import pandas as pd
import fsspec
import clevercsv
import os
from io import StringIO
from dotenv import dotenv_values
from .util import modify_env

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
    """
    stringio = StringIO(file_up.getvalue().decode("utf-8"))
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
        modify_env('auto_transform_available', 'yes')
    except:
        target_df = target_df[['variable_name', 'description']]
        modify_env('auto_transform_available', 'no')
    fs.mkdirs(f"{input_path}/", exist_ok = True)
    target_df.to_csv(f"{input_path}/target_variables.csv", index = False)

def upload_codebook_page():
    """
    Renders the Streamlit page for uploading and displaying the codebook.
    """
    col1, col2 = st.columns(2)
    with col1:
        st.write("To Upload a new codebook complete the form below.")
        with st.form("my_form"):
            # UI: clarify required/optional CSV columns for the codebook; keep behavior unchanged
            new_target_df = st.file_uploader(
                'Target Codebook',
                type='csv',
                accept_multiple_files=False,
                help=(
                    "Only CSV format accepted. Required columns: 'variable_name' and 'description'. "
                    "Optional (enables auto-transformations): 'dType', 'Unit', 'Categories', 'Unit Example'."
                )
            )
            submit = st.form_submit_button(":green[Update Codebook]", help = 'Note when uploading a new codebook the recommendation engine will rerun for all studies. This may take a few minutes.')
            if submit:
                upload_codebook(new_target_df)
        # UI help: compact guidance on expected CSV formats
        with st.expander("Codebook CSV format (required columns)"):
            st.markdown(
                "- **Required**: `variable_name`, `description`\n"
                "- **Optional (enables auto-transformations)**: `dType`, `Unit`, `Categories`, `Unit Example`\n"
                "- **dType supported**: `float`, `integer`, `string`, `boolean` (other values are accepted but default handling applies)\n"
                "- **Study variables CSV**: must also have `variable_name`, `description` (description may be empty)\n"
                "- **Example data CSV (optional)**: column names must match `variable_name` in the variables CSV"
            )
            # Display a sample image to illustrate expected CSV format (requested)
            try:
                _sample_img = os.path.join(BASE_DIR, "assets", "images", "sample_data.png")
                if os.path.exists(_sample_img):
                    st.image(_sample_img, caption="Sample variables CSV format", use_container_width=True)
            except Exception:
                pass
                
    with col2:
        if fs.exists(f'{input_path}/target_variables.csv'):
            st.write("Target Codebook")
            config = dotenv_values(".env")
            if config['auto_transform_available'] == 'yes':
                target_df = pd.read_csv(f'{input_path}/target_variables.csv')[['variable_name', 'description', 'dType', 'Unit', 'Categories', 'Unit Example']]
            else:
                target_df = pd.read_csv(f'{input_path}/target_variables.csv')[['variable_name', 'description']]
                st.write("Auto transformations will not be available for this study as the target codebook does not contain dType, Unit, Categories, or Unit Example columns.")
            st.dataframe(target_df, use_container_width=True)
        else:
            st.write("No codebook is currently loaded")