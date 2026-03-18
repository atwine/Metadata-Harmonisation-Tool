import streamlit as st
import pandas as pd
import fsspec
from typing import Tuple, List, Dict

fs = fsspec.filesystem("")


def _read_csv_safe(path: str) -> pd.DataFrame | None:
    try:
        return pd.read_csv(path)
    except Exception:
        return None


def _file_size_info(path: str) -> int | None:
    try:
        info = fs.info(path)
        return int(info.get('size', 0))
    except Exception:
        return None


def validate_codebook_file() -> Dict[str, List[str]]:
    """
    Validate the target codebook at input/target_variables.csv

    Checks:
    - File exists and loads
    - At least one of description/variable name columns exists
    - Recommended columns presence (dType, Categories, Unit, Unit Example)
    - Duplicate descriptions or variable names (case-insensitive, trimmed)
    - Empty identifier rows
    - File size warning
    """
    path = "input/target_variables.csv"
    out: Dict[str, List[str]] = {"errors": [], "warnings": []}

    if not fs.exists(path):
        out["errors"].append(f"Codebook file not found: {path}")
        return out

    size = _file_size_info(path)
    if size and size > 50 * 1024 * 1024:  # 50MB
        out["warnings"].append("Codebook CSV is large (>50MB); loading may be slow.")

    df = _read_csv_safe(path)
    if df is None:
        out["errors"].append("Codebook could not be parsed as CSV.")
        return out

    cols = set(df.columns)
    name_cols = [c for c in ["variable_name", "Variable", "Variable Name"] if c in cols]
    desc_cols = [c for c in ["description", "Description"] if c in cols]
    if not name_cols and not desc_cols:
        out["errors"].append("Codebook must include either a variable name column (e.g., 'variable_name') or a description column (e.g., 'description').")

    for rec in ["dType", "Categories", "Unit", "Unit Example"]:
        if rec not in cols:
            out["warnings"].append(f"Recommended column missing: {rec}")

    def _dup_report(series: pd.Series, label: str):
        ser = series.astype(str).str.strip().str.casefold()
        dups = ser[ser.duplicated(keep=False)]
        if not dups.empty:
            samples = sorted(dups.unique().tolist())[:5]
            out["warnings"].append(f"Duplicate {label} entries: {samples} (showing up to 5)")

    if name_cols:
        _dup_report(df[name_cols[0]], "variable_name")
    if desc_cols:
        _dup_report(df[desc_cols[0]], "description")

    # Empty identifier rows
    if name_cols or desc_cols:
        if name_cols and desc_cols:
            empty_rows = df[(df[name_cols[0]].astype(str).str.strip() == '') & (df[desc_cols[0]].astype(str).str.strip() == '')]
        elif name_cols:
            empty_rows = df[df[name_cols[0]].astype(str).str.strip() == '']
        else:
            empty_rows = df[df[desc_cols[0]].astype(str).str.strip() == '']
        if not empty_rows.empty:
            out["warnings"].append(f"{len(empty_rows)} codebook rows have empty identifiers (name/description).")

    return out


def validate_study_files(study: str) -> Dict[str, List[str]]:
    """
    Validate study-specific inputs under input/{study}

    Checks:
    - example_data.csv exists, parsable, non-empty
    - dataset_variables_with_PID_date_recommendations.csv exists, columns ok
    - Intersection between dataset variables and example_data columns
    - File size warnings
    """
    out: Dict[str, List[str]] = {"errors": [], "warnings": []}

    # Ensure ex_df is defined even when example data is absent; example data is optional.
    ex_df = None
    ex_path = f"input/{study}/example_data.csv"
    if not fs.exists(ex_path):
        # Treat missing example_data.csv as a warning so metadata-only workflows are supported.
        out["warnings"].append("No example_data.csv provided (optional).")
    else:
        ex_size = _file_size_info(ex_path)
        if ex_size and ex_size > 100 * 1024 * 1024:
            out["warnings"].append("example_data.csv is large (>100MB); operations may be slow.")
        ex_df = _read_csv_safe(ex_path)
        if ex_df is None:
            out["errors"].append("example_data.csv could not be parsed as CSV.")
        elif len(ex_df) == 0:
            out["warnings"].append("example_data.csv has 0 rows.")

    rec_path = f"input/{study}/dataset_variables_with_PID_date_recommendations.csv"
    if not fs.exists(rec_path):
        out["errors"].append(f"Missing: {rec_path}")
        rec_df = None
    else:
        rec_df = _read_csv_safe(rec_path)
        if rec_df is None:
            out["errors"].append("recommendations CSV could not be parsed as CSV.")

    # Column checks
    if rec_df is not None:
        cols = set(rec_df.columns)
        needed = ["variable_name", "description"]
        for n in needed:
            if n not in cols:
                out["warnings"].append(f"Recommendations file missing column: {n}")

        # Column intersection with example_data
        # Guard on both rec_df and ex_df to avoid UnboundLocalError when example data is absent.
        if ex_df is not None:
            inter = sorted(set(rec_df.get('variable_name', [])).intersection(set(ex_df.columns)))
            if len(inter) == 0:
                out["warnings"].append("No overlap between dataset variables and example_data.csv columns. Preview may be empty.")

    return out


def render_validation_widget(study: str):
    """Render a compact validation panel in the UI."""
    with st.expander("Validation", expanded=False):
        codebook = validate_codebook_file()
        study_res = validate_study_files(study)

        any_errors = bool(codebook["errors"] or study_res["errors"])
        if any_errors:
            st.error("Validation found issues.")
        else:
            st.success("No critical issues detected.")

        if codebook["errors"]:
            st.markdown("**Codebook errors**")
            for e in codebook["errors"]:
                st.error(f"- {e}")
        if study_res["errors"]:
            st.markdown("**Study errors**")
            for e in study_res["errors"]:
                st.error(f"- {e}")

        if codebook["warnings"]:
            st.markdown("**Codebook warnings**")
            for w in codebook["warnings"]:
                st.warning(f"- {w}")
        if study_res["warnings"]:
            st.markdown("**Study warnings**")
            for w in study_res["warnings"]:
                st.warning(f"- {w}")
