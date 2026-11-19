import pytest

from src.refactoring_engine import (
    replace_nested_conditions,
    RefactoringError
)

from src.refactoring_evaluator import (
    evaluate_code,
    compare_code
)


ORIGINAL_CODE = """
def check_access(a, b, c):
    if a:
        if b:
            if c:
                return True
    return False
"""


def test_guard_clause_transformation():
    result = replace_nested_conditions(ORIGINAL_CODE)

    assert "if not a:" in result
    assert "if not b:" in result
    assert "if not c:" in result
    assert "return True" in result


def test_functional_equivalence():
    result = replace_nested_conditions(ORIGINAL_CODE)

    original_namespace = {}
    refactored_namespace = {}

    exec(ORIGINAL_CODE, original_namespace)
    exec(result, refactored_namespace)

    original = original_namespace["check_access"]
    refactored = refactored_namespace["check_access"]

    cases = [
        (True, True, True),
        (True, True, False),
        (True, False, True),
        (False, True, True),
        (False, False, False),
    ]

    for case in cases:
        assert original(*case) == refactored(*case)


def test_nesting_depth_improves():
    result = replace_nested_conditions(ORIGINAL_CODE)

    before = evaluate_code(ORIGINAL_CODE)
    after = evaluate_code(result)

    assert after["nesting_depth"] < before["nesting_depth"]


def test_unsupported_pattern_is_rejected():
    source = """
def example(x):
    if x:
        print("hello")
    return None
"""

    with pytest.raises(RefactoringError):
        replace_nested_conditions(source)


def test_comparison_returns_both_results():
    result = replace_nested_conditions(ORIGINAL_CODE)
    comparison = compare_code(ORIGINAL_CODE, result)

    assert "before" in comparison
    assert "after" in comparison
