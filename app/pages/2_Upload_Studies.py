import streamlit as st

from components.ai_config_ui import ai_config_ui
from components.upload_study import add_study_page

st.set_page_config(layout="wide", page_title="Mapping Tool")

with st.sidebar:
    st.write("## Mapping App")
    st.divider()
    # WIZARD NAV: custom button navigation (more intuitive than the default multipage link list).
    # Note: default sidebar navigation is hidden via `.streamlit/config.toml`.
    if st.button('Home', use_container_width=True):
        st.switch_page('app.py')
    if st.button('Upload Codebook', use_container_width=True):
        st.switch_page('pages/1_Upload_Codebook.py')
    if st.button('Upload Studies', use_container_width=True, type='primary'):
        st.switch_page('pages/2_Upload_Studies.py')
    if st.button('Initialise', use_container_width=True):
        st.switch_page('pages/3_Initialise.py')
    if st.button('Map Studies', use_container_width=True):
        st.switch_page('pages/4_Map_Studies.py')
    if st.button('Download Results', use_container_width=True):
        st.switch_page('pages/5_Download_Results.py')
    st.divider()
    # WIZARD NAV: keep AI configuration available across all steps.
    ai_config_ui.render_configuration_panel()
    st.divider()

add_study_page()

