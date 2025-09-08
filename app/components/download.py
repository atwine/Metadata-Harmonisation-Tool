import streamlit as st
import pandas as pd
import fsspec
import io
import zipfile
from .transform_engine import (
    load_study_data,
    load_mapping,
    apply_transformations,
    build_mapping_summary,
    generate_validation_report,
)

results_path = "results"

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
    avail_data = [f.split('/')[-1].split('.')[0] for f in fs.ls(f"{results_path}/")]
    if len(avail_data) == 0:
        st.write(':red[No results available, please initialise the mapping app]')
    else:
        name = st.selectbox('Select study to download:', avail_data)
        df = pd.read_csv(f"{results_path}/{name}.csv")
        df.replace('0%', None, inplace=True)
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
            export_mode = st.selectbox(
                "Export format",
                options=["Mapping only (CSV)", "Full data package (ZIP)"]
            )
            if export_mode == "Mapping only (CSV)":
                st.download_button(
                    label="Download mapping CSV",
                    data=convert_to_download(df),
                    file_name=f'{name}_mapping_results.csv',
                    mime='text/csv',
                )
            else:
                # Build transformed outputs and ZIP package
                try:
                    original_df = load_study_data(name)
                except Exception as e:
                    st.error(f"Cannot load original data for study '{name}': {e}")
                    return
                try:
                    mapping_df = load_mapping(name)
                except Exception as e:
                    st.error(f"Cannot load mapping results for study '{name}': {e}")
                    return

                transformed_df, metrics, warnings = apply_transformations(original_df, mapping_df)
                mapping_summary = build_mapping_summary(mapping_df)
                validation_report = generate_validation_report(metrics, warnings)

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

                # Create ZIP in-memory
                memfile = io.BytesIO()
                with zipfile.ZipFile(memfile, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
                    zf.writestr('original_data.csv', original_df.to_csv(index=False))
                    zf.writestr('transformed_data.csv', transformed_df.to_csv(index=False))
                    zf.writestr('mapping_summary.csv', mapping_summary.to_csv(index=False))
                    zf.writestr('validation_report.txt', validation_report)
                    zf.writestr('summary.txt', summary_txt_str)
                memfile.seek(0)

                st.download_button(
                    label="Download full data package (ZIP)",
                    data=memfile.getvalue(),
                    file_name=f'{name}_data_package.zip',
                    mime='application/zip',
                )

