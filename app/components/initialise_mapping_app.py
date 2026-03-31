import streamlit as st
import fsspec
import os
from dotenv import dotenv_values
from .get_recommendations import get_embeddings, get_recommendations, get_PID_date_recommendations
from .generate_descriptions import generate_descriptions, convert_pdf_to_txt
from .util import modify_env, delete_files_and_folders, get_ollama_client, get_ai_provider, OLLAMA_CHAT_MODEL

fs = fsspec.filesystem("")

# Resolve paths to work from both app/ (streamlit run) and tests/
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_CWD_BASE = os.path.abspath(os.getcwd())
_LOCAL_INPUT = os.path.join(_CWD_BASE, "input")
_LOCAL_RESULTS = os.path.join(_CWD_BASE, "results")
_REPO_INPUT = os.path.join(BASE_DIR, "input")
_REPO_RESULTS = os.path.join(BASE_DIR, "results")
input_path = _LOCAL_INPUT if os.path.exists(_LOCAL_INPUT) else _REPO_INPUT
results_path = _LOCAL_RESULTS if os.path.exists(_LOCAL_RESULTS) else _REPO_RESULTS

def initialise_mapping_recommendations():
    """
    Initialise the mapping recommendations by checking for AI provider connection and necessary files.
    """
    config = dotenv_values(".env")

    # Check for AI provider connection status
    ai_provider = get_ai_provider()
    ai_provider_available = ai_provider is not None
    
    if ai_provider_available:
        provider_info = ai_provider.get_provider_info()
        provider_name = provider_info['provider'].title()
        model_name = provider_info['chat_model']
        st.write(f":green[Connected to {provider_name}. Using model: `{model_name}` :white_check_mark:]")
    else:
        # Fallback to Ollama connection check
        ollama_client = get_ollama_client()
        if ollama_client:
            st.write(f":green[Connected to Ollama. Using model: `{OLLAMA_CHAT_MODEL}` :white_check_mark:]")
            ai_provider_available = True
        else:
            st.write(":red[No AI provider configured. Please configure an AI provider in the sidebar or ensure Ollama is running locally.]")

    st.divider()

    default_init_prompt = "As an AI, you're given the task of translating short variable names from a public health study into the most likely full variable name."
    init_prompt = st.text_input('Initialisation Prompt', value=config.get('init_prompt', default_init_prompt), max_chars=1000)
    
    if config.get('init_prompt') != init_prompt:
        modify_env('init_prompt', init_prompt)

    st.caption("Changing this prompt affects how AI fills in missing descriptions. Re-run the Recommendation Engine to apply. Existing non-empty descriptions are not overwritten.")
    cols = st.columns([1,3])
    with cols[0]:
        if st.button('Reset to default', key='reset_init_prompt'):
            modify_env('init_prompt', default_init_prompt)
            st.success('Prompt reset to default.')
            st.rerun()
    with cols[1]:
        with st.expander('Prompt tips'):
            st.markdown(
                "- **Keep it concise and directive** to ensure consistent outputs.\n"
                "- **Specify style** (short label vs full sentence) and use public health terminology.\n"
                "- **Avoid speculation**; ask to infer only from provided context.\n"
                "- **Model differences** may change tone; stable prompts are brief and explicit."
            )

    st.divider()
    
    ready_to_run = fs.exists(f'{input_path}/target_variables.csv')
    if ready_to_run:
        if fs.exists(f'{input_path}/target_variables_with_embeddings.csv'):
            st.write(":green[Codebook Uploaded and Embeddings Fetched :white_check_mark:]")
        else:
            st.write(":green[Codebook Uploaded, ] :red[Embeddings Not Fetched]")
    else:
        st.write(":red[Please upload a codebook to map]")

    if ready_to_run:
        avail_studies = [f.split('/')[-1] for f in fs.ls(f"{input_path}/") if fs.isdir(f) and not f.split('/')[-1].startswith('.')]
        uploaded = [s for s in avail_studies if fs.exists(f"{input_path}/{s}/dataset_variables.csv")]
        mapped = [s for s in avail_studies if fs.exists(f'{input_path}/{s}/dataset_variables_with_recommendations.csv')]

        if uploaded:
            # Create a summary message for the expander
            if len(uploaded) == len(mapped):
                summary_message = f":green[{len(uploaded)} studies uploaded. All have recommendations. :white_check_mark:]"
                expanded_default = False
            else:
                summary_message = f":orange[{len(uploaded)} studies uploaded, but only {len(mapped)} have recommendations. Click to see details.]"
                expanded_default = True

            with st.expander(summary_message, expanded=expanded_default):
                for study_name in sorted(uploaded):
                    if study_name in mapped:
                        st.markdown(f"&nbsp;&nbsp;&nbsp;- **{study_name}**: :white_check_mark: Recommendations created.")
                    else:
                        st.markdown(f"&nbsp;&nbsp;&nbsp;- **{study_name}**: :x: Ready to be initialised.")
        else:
            st.write(":red[Please upload a study to map]")

        run = st.button("Run Recommendation Engine", key='run', disabled=not ai_provider_available)
        if run:
            with st.spinner('Thinking... :coffee:'):
                convert_pdf_to_txt()
                generate_descriptions()
                get_embeddings()
                get_recommendations()
                get_PID_date_recommendations()
            st.success("Recommendation engine finished!")
            st.rerun()

        st.divider()

        if st.button(":red[Clear Workspace]", key='clear'):
            delete_files_and_folders(input_path)
            delete_files_and_folders(results_path)
            st.cache_data.clear()
            st.rerun()