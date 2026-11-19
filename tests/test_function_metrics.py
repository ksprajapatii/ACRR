import pytest

from src.refactoring_evaluator import (
    evaluate_function,
    extract_function_source,
    compare_functions
)


ORIGINAL_SOURCE = """
def process_data(a, b, c):
    result = 0
    if a:
        if b:
            if c:
                result = 10
    return result


class Calculator:
    def calculate(self, x, y):
        if x:
            if y:
                return x + y
        return 0
"""


REFACTORED_SOURCE = """
def process_data(a, b, c):
    if not (a and b and c):
        return 0
    return 10


class Calculator:
    def calculate(self, x, y):
        if not x:
            return 0
        if not y:
            return 0
        return x + y
"""


def test_extract_function_source():
    result = extract_function_source(
        ORIGINAL_SOURCE,
        "process_data"
    )

    assert "def process_data" in result
    assert "if a" in result


def test_extract_class_method():
    result = extract_function_source(
        ORIGINAL_SOURCE,
        "calculate"
    )

    assert "def calculate" in result


def test_evaluate_function_returns_all_metrics():
    result = evaluate_function(
        ORIGINAL_SOURCE,
        "process_data"
    )

    assert set(result.keys()) == {
        "cyclomatic_complexity",
        "lines_of_code",
        "nesting_depth",
        "maintainability_index"
    }


def test_function_nesting_decreases():
    before = evaluate_function(
        ORIGINAL_SOURCE,
        "process_data"
    )

    after = evaluate_function(
        REFACTORED_SOURCE,
        "process_data"
    )

    assert after["nesting_depth"] < before["nesting_depth"]


def test_compare_functions_returns_changes():
    result = compare_functions(
        ORIGINAL_SOURCE,
        REFACTORED_SOURCE,
        ["process_data"]
    )

    assert "process_data" in result
    assert "before" in result["process_data"]
    assert "after" in result["process_data"]
    assert "changes" in result["process_data"]


def test_missing_function_raises_error():
    with pytest.raises(ValueError):
        evaluate_function(
            ORIGINAL_SOURCE,
            "missing_function"
        )
