from src.refactoring_evaluator import (
    count_source_lines,
    evaluate_code
)


def test_source_line_count():
    source = """
def example():
    # comment
    x = 10

    return x
"""
    assert count_source_lines(source) == 3


def test_nested_code_line_count():
    source = """
def check_access(a, b, c):
    if a:
        if b:
            if c:
                return True
    return False
"""
    assert count_source_lines(source) == 6


def test_evaluator_returns_all_metrics():
    source = """
def example(x):
    if x:
        return True
    return False
"""
    result = evaluate_code(source)

    assert "cyclomatic_complexity" in result
    assert "lines_of_code" in result
    assert "nesting_depth" in result
    assert "maintainability_index" in result


def test_nesting_depth():
    source = """
def example(a):
    if a:
        if a:
            return True
    return False
"""
    result = evaluate_code(source)

    assert result["nesting_depth"] == 2
