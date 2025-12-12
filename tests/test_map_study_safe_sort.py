import pandas as pd

from app.components.map_study import _safe_first_distance


def test_safe_first_distance_valid_string_list():
    assert _safe_first_distance("[0.25, 0.9]") == 0.25


def test_safe_first_distance_valid_list():
    assert _safe_first_distance([0.1, 0.2]) == 0.1


def test_safe_first_distance_empty_list_is_inf():
    assert _safe_first_distance("[]") == float('inf')


def test_safe_first_distance_malformed_is_inf():
    assert _safe_first_distance("not a list") == float('inf')


def test_safe_first_distance_nan_is_inf():
    assert _safe_first_distance(float('nan')) == float('inf')


def test_sorting_uses_safe_first_distance():
    df = pd.DataFrame({
        'variable_name': ['a', 'b', 'c'],
        'target_distances': ['[0.5, 0.6]', 'not a list', '[0.1, 0.2]'],
    })
    df['best_dist'] = [_safe_first_distance(x) for x in df['target_distances']]
    out = df.sort_values('best_dist')['variable_name'].tolist()
    # c has 0.1, a has 0.5, b is malformed => inf (last)
    assert out == ['c', 'a', 'b']
