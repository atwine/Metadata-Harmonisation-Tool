import streamlit as st
import fsspec

from components.ai_config_ui import ai_config_ui
from components.map_study import map_study

results_path = "results"
input_path = "input"
preprocess_path = "preprocess"

fs = fsspec.filesystem("")

mapping_options = [
    'To do',
    'Successfully mapped',
    'Marked to reconsider',
    'Marked unmappable'
]

st.set_page_config(layout="wide", page_title="Mapping Tool")

study, variables_status = None, None
show_about, original_order, relational_mode, enable_transformations = False, False, True, True

with st.sidebar:
    st.write("## Mapping App")
    st.divider()
    # WIZARD NAV: custom button navigation (more intuitive than the default multipage link list).
    # Note: default sidebar navigation is hidden via `.streamlit/config.toml`.
    if st.button('Home', use_container_width=True):
        st.switch_page('app.py')
    if st.button('Upload Codebook', use_container_width=True):
        st.switch_page('pages/1_Upload_Codebook.py')
    if st.button('Upload Studies', use_container_width=True):
        st.switch_page('pages/2_Upload_Studies.py')
    if st.button('Initialise', use_container_width=True):
        st.switch_page('pages/3_Initialise.py')
    if st.button('Map Studies', use_container_width=True, type='primary'):
        st.switch_page('pages/4_Map_Studies.py')
    if st.button('Download Results', use_container_width=True):
        st.switch_page('pages/5_Download_Results.py')
    st.divider()
    # WIZARD NAV: Map Studies requires a study selection.
    # Placed above the AI config panel so it is visible without scrolling.
    if fs.exists(f'{input_path}/'):
        avail_studies = [f for f in fs.ls(f"{input_path}/") if fs.isdir(f)]
        avail_studies = [f.split('/')[-1] for f in avail_studies if f.split('/')[-1][0] != '.']
        avail_studies = sorted(avail_studies)
        if avail_studies:
            # UI: use a single session_state-backed key for the selectbox.
            # This avoids index/bookkeeping logic that can override user selection on reruns.
            if 'selected_study' in st.session_state and st.session_state['selected_study'] not in avail_studies:
                try:
                    del st.session_state['selected_study']
                except Exception:
                    pass
            study = st.selectbox('Study', avail_studies, key='selected_study')
            variables_status = st.selectbox('View variables:', mapping_options, key='variables_status')

    st.divider()
    # WIZARD NAV: keep AI configuration available across all steps.
    ai_config_ui.render_configuration_panel()
    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        show_about = st.checkbox("About", value=False, help='Show an about section for the dataset you have selected.')
    with col2:
        original_order = st.checkbox('Unsort', value=False, help='Show variables in the original order of incoming datasets. This can be helpful if you believe one variable is related to a neighbouring variable in the table.')

    col3, col4 = st.columns(2)
    with col3:
        relational_mode = st.checkbox('Relational Mode', value=True, help='Enable this to map date and index (eg patient ID) to each variable. Use this if the goal is to populate a relational database.')
    with col4:
        enable_transformations = st.checkbox('Transform Mode', value=True, help='This adds functionality to create and test transformations instructions for each variable. These instructions can then be used to transform data to a common format. Example transformation instructions available [here](https://github.com/csag-uct/Metadata-Harmonisation-Tool/pull/19#issuecomment-2356409576). Only available if example data is provided.')

if study is not None and variables_status is not None:
    map_study(study, variables_status, show_about, original_order, relational_mode, enable_transformations)
else:
    st.write(':red[No studies available. Please initialise the mapping app]')

