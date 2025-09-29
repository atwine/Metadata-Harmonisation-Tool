#!/usr/bin/env python3
"""
Basic tests for transform_engine.apply_transformations
"""
import sys
sys.path.append('.')

import pandas as pd
from app.components.transform_engine import apply_transformations, build_mapping_summary, generate_validation_report


def test_apply_transformations():
    # Original data with a numeric column and a categorical column
    df = pd.DataFrame({
        'height_m': [1.70, 1.80, 'bad', 1.65],
        'flag': ['0', '1', '2', None]
    })

    # Mapping DataFrame including one direct and one categorical mapping
    mapping_df = pd.DataFrame([
        {
            'study_var': 'height_m',
            'codebook_var': 'Height',
            'marked': 'Successfully mapped',
            'transformation_type': 'Direct',
            'source_dtype': 'float',
            'target_dtype': 'float',
            'transformation_instructions': 'x*100',
            'confidence': '95%'
        },
        {
            'study_var': 'flag',
            'codebook_var': 'FlagYN',
            'marked': 'Successfully mapped',
            'transformation_type': 'Categorical',
            'source_dtype': None,
            'target_dtype': None,
            'transformation_instructions': "{'0': 'no', '1': 'yes'}",
            'confidence': '90%'
        }
    ])

    transformed_df, metrics, warnings = apply_transformations(df, mapping_df)

    # Check columns exist
    assert 'Height' in transformed_df.columns
    assert 'FlagYN' in transformed_df.columns

    # Height in cm; invalid entry should be NaN
    vals = list(transformed_df['Height'])
    assert abs(vals[0] - 170.0) < 1e-9
    assert abs(vals[1] - 180.0) < 1e-9
    assert pd.isna(vals[2])
    assert abs(vals[3] - 165.0) < 1e-9

    # Categorical mapping
    flags = list(transformed_df['FlagYN'])
    assert flags[0] == 'no'
    assert flags[1] == 'yes'
    assert pd.isna(flags[2])
    assert pd.isna(flags[3])

    # Metrics should count successes and errors
    assert metrics['height_m']['success'] == 3  # three numeric outputs (including NaN?)
    assert metrics['height_m']['errors'] == 1    # one failure ('bad')

    # Build mapping summary and validation report
    summary = build_mapping_summary(mapping_df)
    assert 'transformation_instructions' in summary.columns

    report = generate_validation_report(metrics, warnings)
    assert 'Validation Report' in report

    print('OK: transform_engine basic test passed')


if __name__ == '__main__':
    test_apply_transformations()
    print('All transform_engine tests passed.')
