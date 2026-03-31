import streamlit as st
import pandas as pd
import fsspec
import clevercsv
from io import StringIO
import os
import re
from pathlib import Path

# Resolve paths to work from both app/ (streamlit run) and repo root.
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

def add_new_study(study_title, study_description, variables, example_data, context_docs):
    """
    Adds a new study by saving the provided details and files to the filesystem.
    
    Args:
        study_title (str): The title of the study.
        study_description (str): The description of the study.
        variables (UploadedFile): A CSV file containing variable names and descriptions.
        example_data (UploadedFile): An optional CSV file containing example data.
        context_docs (UploadedFile): An optional PDF file containing contextual documents.

    Returns:
        tuple: A tuple containing a boolean for success and a string message.
    """
    if not study_title:
        return False, "Study Title is required. Please enter a title."
    if not variables:
        return False, "Variables Table is required. Please upload a CSV file."

    # SECURITY: Sanitize study_title to prevent path traversal attacks
    safe_title = re.sub(r'[^\w\s-]', '', study_title).strip()
    safe_title = re.sub(r'[-\s]+', '-', safe_title)
    
    if not safe_title or safe_title in ['.', '..']:
        return False, "Invalid study title. Use alphanumeric characters, spaces, and hyphens only."
    
    # SECURITY: Verify resolved path is within input_path to prevent directory traversal
    study_path = Path(input_path) / safe_title
    if not str(study_path.resolve()).startswith(str(Path(input_path).resolve())):
        return False, "Invalid study title."
    
    study_path_str = str(study_path)

    try:
        variables_df = streamlit_csv_reader(variables)[['variable_name', 'description']]
        fs.mkdirs(study_path_str, exist_ok=True)
        if study_description:
            with fs.open(f"{study_path_str}/description.txt", "w") as file:
                file.write(study_description)
        variables_df.to_csv(f"{study_path_str}/dataset_variables.csv")
        if example_data:
            example_df = pd.read_csv(example_data)
            example_df.to_csv(f"{study_path_str}/example_data.csv")
        if context_docs:
            # SECURITY: Validate PDF file before saving
            if not context_docs.name.lower().endswith('.pdf'):
                return False, "Context document must be a PDF file."
            
            # SECURITY: Check file size to prevent DoS (50MB limit)
            max_size = 50 * 1024 * 1024  # 50MB
            content = context_docs.getvalue()
            if len(content) > max_size:
                return False, f"PDF file too large. Maximum size: {max_size/1024/1024:.0f}MB"
            
            # SECURITY: Verify PDF magic bytes to ensure valid PDF format
            if not content.startswith(b'%PDF'):
                return False, "Invalid PDF file format."
            
            pdf_path = Path(study_path_str) / "context.pdf"
            with open(pdf_path, "wb") as file:
                file.write(content)
        return True, f"Study '{study_title}' was added successfully!"
    except Exception as e:
        return False, f"Failed to add study. An error occurred: {e}. Please check your file formats and try again."

def add_study_page():
    """
    Renders the Streamlit page for adding a new study, including form inputs and submission handling.
    """
    # Use resolved input_path so this check matches where the uploader saved the codebook.
    if not fs.exists(f"{input_path}/target_variables.csv"):
        st.write(":red[Please upload a target codebook before submitting a study to map]")
        disable = True
    else:
        disable = False
    st.text("Complete and submit the form below to add a new study to the mapping tool.")
    with st.form("my_form", clear_on_submit=True):
        study_title = st.text_input('Study Title:', '', max_chars=200)
        study_description = st.text_input('Study Description:', '', max_chars=1000)
        variables = st.file_uploader('Variables Table:', type='csv', accept_multiple_files=False, help = "Only CSV format accepted. The File should contain two columns titled 'variable_name' and 'description', If the desription of a variable is unknown the cell should be an empty string.")
        example_data = st.file_uploader('Example Data (optional):', type='csv', accept_multiple_files=False, help = "Optional. To assist in mapping you can upload a file containing example data. The app will automatically select a random subset of this data to display alongside the variable's name and description. Column titles of the example data should correspond to a 'variable_name' in the variables table. ")
        context_docs = st.file_uploader('Contextual Documents (optional):', type=['pdf'], accept_multiple_files=False, help = "This application uses natural language processing to automatically provide variable descriptions. To aid this process you can upload a relevant document such as a study protocol, journal article, or ideally codebook here.")
        submit = st.form_submit_button(":green[Submit]", disabled = disable)  # Clarify action: this submits the filled form; avoids implying creation of an additional study
        if submit:
            success, message = add_new_study(study_title, study_description, variables, example_data, context_docs)
            if success:
                st.success(message)
            else:
                st.error(message)