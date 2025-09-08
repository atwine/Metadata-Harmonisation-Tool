import pandas as pd
import numpy as np
import ast
import fsspec
from typing import Tuple, Dict, Any, List
from .transformation_utils import generic_direct_conversion, dtype_conversion

fs = fsspec.filesystem("")


def load_study_data(study: str) -> pd.DataFrame:
    """
    Load original study data from input/{study}/example_data.csv
    """
    path = f"input/{study}/example_data.csv"
    if not fs.exists(path):
        raise FileNotFoundError(f"Original data not found at {path}")
    return pd.read_csv(path)


def load_mapping(study: str) -> pd.DataFrame:
    """
    Load mapping results from results/{study}.csv
    """
    path = f"results/{study}.csv"
    if not fs.exists(path):
        raise FileNotFoundError(f"Mapping results not found at {path}")
    return pd.read_csv(path)


def _apply_direct_series(series: pd.Series, instr: str, source_dtype: str, target_dtype: str) -> Tuple[pd.Series, int, int]:
    """
    Apply direct transformation expression element-wise using SafeEvaluator via generic_direct_conversion.
    Returns transformed series and (success_count, error_count).
    """
    out_vals: List[Any] = []
    success = 0
    errors = 0
    for x in series:
        try:
            y = generic_direct_conversion(x, instr, source_dtype, target_dtype)
            # Treat NaN outputs as errors; otherwise success
            if pd.isna(y):
                out_vals.append(np.nan)
                errors += 1
            else:
                out_vals.append(y)
                success += 1
        except Exception:
            out_vals.append(np.nan)
            errors += 1
    return pd.Series(out_vals, index=series.index), success, errors


def _apply_categorical_series(series: pd.Series, instr: str) -> Tuple[pd.Series, int, int]:
    """
    Apply categorical dictionary mapping safely using ast.literal_eval.
    Mirrors preview behavior: keys coerced to str; inputs coerced to str.
    """
    success = 0
    errors = 0
    try:
        mapping_obj = ast.literal_eval(instr)
        if not isinstance(mapping_obj, dict):
            raise ValueError("Categorical instruction is not a dict literal")
        dictionary = {str(k): v for k, v in mapping_obj.items()}
    except Exception:
        # invalid mapping - all NaN
        return pd.Series([np.nan] * len(series), index=series.index), 0, len(series)

    out_vals: List[Any] = []
    for x in series:
        key = str(x)
        if key in dictionary:
            val = dictionary[key]
            if val is None:
                out_vals.append(np.nan)
                errors += 1
            else:
                out_vals.append(val)
                success += 1
        else:
            out_vals.append(np.nan)
            errors += 1
    return pd.Series(out_vals, index=series.index), success, errors


def apply_transformations(df: pd.DataFrame, mapping_df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Dict[str, int]], List[str]]:
    """
    Apply approved mappings to the full dataset.

    Only rows with marked == 'Successfully mapped' are transformed.
    For missing instructions, values are copied through (optionally dtype-cast) and a warning is recorded.

    Returns:
      - transformed_df: columns named by codebook_var
      - metrics: dict per variable with success/errors counts
      - warnings: list of warning strings
    """
    transformed_cols: Dict[str, pd.Series] = {}
    metrics: Dict[str, Dict[str, int]] = {}
    warnings: List[str] = []

    for _, row in mapping_df.iterrows():
        if str(row.get('marked', '')).strip() != 'Successfully mapped':
            continue

        study_var = row.get('study_var')
        codebook_var = row.get('codebook_var')
        instr = row.get('transformation_instructions')
        ttype = row.get('transformation_type')
        source_dtype = row.get('source_dtype')
        target_dtype = row.get('target_dtype')

        # Initialize metrics
        metrics.setdefault(study_var, {"success": 0, "errors": 0})

        if study_var not in df.columns:
            warnings.append(f"Source column missing: {study_var}")
            continue

        series = df[study_var]

        if not isinstance(instr, str) or not instr.strip():
            # No instructions provided: copy-through, attempt target dtype cast
            warnings.append(f"No transformation for {study_var} -> {codebook_var}; copied through.")
            if isinstance(target_dtype, str) and target_dtype:
                out_vals = [dtype_conversion(x, target_dtype) for x in series]
                out_series = pd.Series(out_vals, index=series.index)
            else:
                out_series = series.copy()
            transformed_cols[codebook_var] = out_series
            # Count non-NaN as success
            metrics[study_var]["success"] += int(out_series.notna().sum())
            metrics[study_var]["errors"] += int(out_series.isna().sum())
            continue

        if ttype == 'Direct':
            out_series, ok, bad = _apply_direct_series(series, instr, source_dtype or 'other', target_dtype or 'other')
        elif ttype == 'Categorical':
            out_series, ok, bad = _apply_categorical_series(series, instr)
        else:
            # Unknown type: copy-through
            warnings.append(f"Unknown transformation type for {study_var}: {ttype}; copied through.")
            out_series = series.copy()
            ok = int(out_series.notna().sum())
            bad = int(out_series.isna().sum())

        transformed_cols[codebook_var] = out_series
        metrics[study_var]["success"] += int(ok)
        metrics[study_var]["errors"] += int(bad)

    transformed_df = pd.DataFrame(transformed_cols)
    return transformed_df, metrics, warnings


def build_mapping_summary(mapping_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build a concise mapping summary for export.
    """
    cols = [
        'study_var', 'codebook_var', 'confidence', 'marked',
        'transformation_type', 'source_dtype', 'target_dtype', 'transformation_instructions'
    ]
    present = [c for c in cols if c in mapping_df.columns]
    summary = mapping_df[present].copy()
    return summary


def generate_validation_report(metrics: Dict[str, Dict[str, int]], warnings: List[str]) -> str:
    lines: List[str] = []
    lines.append("Validation Report")
    lines.append("=================")
    lines.append("")
    total_success = 0
    total_errors = 0
    for var, m in metrics.items():
        s = m.get("success", 0)
        e = m.get("errors", 0)
        total_success += s
        total_errors += e
        lines.append(f"- {var}: success={s}, errors={e}")
    lines.append("")
    lines.append(f"Total successes: {total_success}")
    lines.append(f"Total errors: {total_errors}")
    if warnings:
        lines.append("")
        lines.append("Warnings:")
        for w in warnings:
            lines.append(f"- {w}")
    return "\n".join(lines)
