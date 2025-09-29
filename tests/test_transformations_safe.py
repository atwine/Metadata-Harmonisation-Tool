#!/usr/bin/env python3
"""
Tests for SafeEvaluator and generic_direct_conversion (Phase 1 objective)
"""
import sys
sys.path.append('.')

from app.components.transformation_utils import (
    SafeEvaluator,
    validate_expression,
    generic_direct_conversion,
)


def test_validate_expression():
    valid = [
        "x",
        "x/12",
        "x*2 - 5",
        "-x",
        "x + 3",
    ]
    invalid = [
        "x**2",            # disallowed operator
        "abs(x)",         # function call not allowed
        "__import__('os')",  # injection attempt
        "(x).__class__",   # attribute access not allowed
    ]

    for expr in valid:
        ok, msg = validate_expression(expr)
        assert ok, f"Expected valid expression, got invalid: {expr} ({msg})"

    for expr in invalid:
        ok, msg = validate_expression(expr)
        assert not ok, f"Expected invalid expression, got valid: {expr}"


def test_generic_direct_conversion_numeric():
    # x = '24' (string), but source values are numeric; select integer so converter coerces first
    # Then apply x/12 => 2.0, return float
    out = generic_direct_conversion("24", "x/12", source_dtype="integer", target_dtype="float")
    assert abs(out - 2.0) < 1e-9

    # x = 10 int, expression x*2 - 5 => 15, return integer
    out = generic_direct_conversion(10, "x*2 - 5", source_dtype="integer", target_dtype="integer")
    assert out == 15

    # negative handling
    out = generic_direct_conversion(5, "-x", source_dtype="integer", target_dtype="integer")
    assert out == -5


def test_generic_direct_conversion_invalid_expressions():
    # Invalid operator ** should raise ValueError
    try:
        _ = generic_direct_conversion(3, "x**2", source_dtype="integer", target_dtype="integer")
        raise AssertionError("Expected ValueError for invalid operator '**'")
    except ValueError:
        pass

    # Function calls should raise ValueError
    try:
        _ = generic_direct_conversion(3, "abs(x)", source_dtype="integer", target_dtype="integer")
        raise AssertionError("Expected ValueError for function calls")
    except ValueError:
        pass


if __name__ == '__main__':
    test_validate_expression()
    test_generic_direct_conversion_numeric()
    test_generic_direct_conversion_invalid_expressions()
    print("All SafeEvaluator/generic_direct_conversion tests passed.")
