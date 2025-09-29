import numpy as np
import pandas as pd

from app.components.transform_engine import apply_transformations


def _mapping_row(
    study_var,
    codebook_var,
    instr,
    ttype,
    source_dtype=None,
    target_dtype=None,
    marked='Successfully mapped',
):
    return {
        'study_var': study_var,
        'codebook_var': codebook_var,
        'transformation_instructions': instr,
        'transformation_type': ttype,
        'source_dtype': source_dtype,
        'target_dtype': target_dtype,
        'marked': marked,
    }


def test_apply_transformations_direct():
    df = pd.DataFrame({'age_months': [24, 12, np.nan]})
    mapping_df = pd.DataFrame([
        _mapping_row(
            'age_months', 'age_years', 'x/12', 'Direct', 'integer', 'float'
        )
    ])

    out_df, metrics, warnings = apply_transformations(df, mapping_df)

    assert 'age_years' in out_df.columns
    assert out_df['age_years'].iloc[0] == 2.0
    assert out_df['age_years'].iloc[1] == 1.0
    assert np.isnan(out_df['age_years'].iloc[2])

    m = metrics['age_months']
    assert m['success'] == 2
    assert m['errors'] == 1
    assert warnings == []


def test_apply_transformations_categorical():
    df = pd.DataFrame({'sex': ['0', '1', '2']})
    mapping = "{'0':'F','1':'M'}"
    mapping_df = pd.DataFrame([
        _mapping_row(
            'sex', 'sex_mapped', mapping, 'Categorical'
        )
    ])

    out_df, metrics, warnings = apply_transformations(df, mapping_df)

    assert list(out_df['sex_mapped'])[:2] == ['F', 'M']
    assert pd.isna(out_df['sex_mapped'].iloc[2])

    m = metrics['sex']
    assert m['success'] == 2
    assert m['errors'] == 1


def test_unknown_type_copies_through():
    df = pd.DataFrame({'value': [1, 2, None]})
    mapping_df = pd.DataFrame([
        _mapping_row('value', 'value_copy', 'ignored', 'Unknown')
    ])

    out_df, metrics, warnings = apply_transformations(df, mapping_df)

    out = list(out_df['value_copy'])
    # Pandas may coerce integers to floats and represent missing as NaN; allow that.
    assert out[0] == 1
    assert out[1] == 2
    assert pd.isna(out[2])
    m = metrics['value']
    assert m['success'] == 2
    assert m['errors'] == 1
    assert any('Unknown transformation type' in w for w in warnings)
