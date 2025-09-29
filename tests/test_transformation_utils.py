import pytest

from app.components.transformation_utils import (
    generic_direct_conversion,
    generic_catagorical_conversion,
    validate_expression,
)


def test_direct_conversion_valid():
    # 24 months -> 2 years
    assert generic_direct_conversion(24, 'x/12', 'integer', 'float') == 2.0
    # keep as is
    assert generic_direct_conversion(5, 'x', 'integer', 'integer') == 5


def test_direct_conversion_invalid_operator():
    # '**' is not allowed by SafeEvaluator
    with pytest.raises(ValueError):
        generic_direct_conversion(5, 'x**2', 'integer', 'integer')


def test_validate_expression():
    ok, msg = validate_expression('x/12')
    assert ok is True
    assert 'valid' in msg.lower()

    bad, msg2 = validate_expression('x**2')
    assert bad is False


def test_categorical_valid_mapping():
    mapping = "{'0':'No','1':'Yes'}"
    assert generic_catagorical_conversion('1', mapping) == 'Yes'
    assert generic_catagorical_conversion('0', mapping) == 'No'
    # missing key returns NaN
    import numpy as np
    assert np.isnan(generic_catagorical_conversion('2', mapping))


def test_categorical_invalid_mapping():
    with pytest.raises(ValueError):
        generic_catagorical_conversion('1', 'x*100')
