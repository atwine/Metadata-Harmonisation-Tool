import streamlit as st
import fsspec
import sys
import time

from components.upload_codebook import upload_codebook_page
from components.upload_study import add_study_page
from components.map_study import map_study
from components.about import about_page
from components.download import download_page
from components.initialise_mapping_app import initialise_mapping_recommendations
from components.ai_config_ui import ai_config_ui

results_path = "results"
input_path = "input"
preprocess_path = "preprocess"

fs = fsspec.filesystem("")

study, variables_status, show_about, original_order, relational_mode, enable_transformations = None, None, None, None, None, None  # just to clear error checking

mapping_options = ['To do',
        'Successfully mapped',
        'Marked to reconsider',
        'Marked unmappable']

# SECURITY: Monitor and limit session state size to prevent memory exhaustion
def check_session_state_size():
    """Monitor session state size and clean up old data if needed."""
    try:
        size = sys.getsizeof(st.session_state)
        max_size = 50 * 1024 * 1024  # 50MB limit
        if size > max_size:
            # Clean up old draft data
            keys_to_remove = []
            for key in st.session_state.keys():
                if 'draft' in key or 'transformation_input' in key or 'last_' in key:
                    keys_to_remove.append(key)
            # Remove half of the old keys
            for key in keys_to_remove[:len(keys_to_remove)//2]:
                del st.session_state[key]
    except Exception:
        pass  # Fail silently to not disrupt user experience

# Run cleanup periodically (every 5 minutes)
if 'last_cleanup' not in st.session_state or time.time() - st.session_state.get('last_cleanup', 0) > 300:
    check_session_state_size()
    st.session_state['last_cleanup'] = time.time()

st.set_page_config(
    page_title="Metadata Harmonisation Tool",
    page_icon="",
    layout="wide"
)

with st.sidebar:
    st.write("## Mapping App")
    st.divider()
    # WIZARD NAV: custom button navigation (more intuitive than the default multipage link list).
    # Note: default sidebar navigation is hidden via `.streamlit/config.toml`.
    if st.button('Home', use_container_width=True, type='primary'):
        st.switch_page('app.py')
    if st.button('Upload Codebook', use_container_width=True):
        st.switch_page('pages/1_Upload_Codebook.py')
    if st.button('Upload Studies', use_container_width=True):
        st.switch_page('pages/2_Upload_Studies.py')
    if st.button('Initialise', use_container_width=True):
        st.switch_page('pages/3_Initialise.py')
    if st.button('Map Studies', use_container_width=True):
        st.switch_page('pages/4_Map_Studies.py')
    if st.button('Download Results', use_container_width=True):
        st.switch_page('pages/5_Download_Results.py')
    st.divider()
    # WIZARD NAV: multipage flow uses Streamlit pages/ + st.switch_page (no dropdown selector).
    # st.switch_page requires pages to be in the multipage architecture. [src: https://docs.streamlit.io/develop/api-reference/navigation/st.switch_page]
    ai_config_ui.render_configuration_panel()
    st.divider()

# Home step (About)
about_page()