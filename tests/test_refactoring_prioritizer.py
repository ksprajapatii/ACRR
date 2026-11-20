import pytest

from src.refactoring_prioritizer import (
    calculate_priority,
    prioritize_repository,
)


def test_high_severity_smell_increases_priority():
    metrics = {
        "cyclomatic_complexity": 8,
        "nesting_depth": 2,
        "maintainability_index": 80,
    }

    result = calculate_priority(
        metrics,
        [{"smell": "Deeply Nested Conditions", "severity": "High"}],
    )

    assert result["priority_score"] > 0
    assert result["priority"] in {
        "Critical", "High", "Medium", "Low"
    }
    assert any("Deeply Nested Conditions" in reason
               for reason in result["reasons"])


def test_priority_score_is_between_zero_and_hundred():
    metrics = {
        "cyclomatic_complexity": 100,
        "nesting_depth": 100,
        "maintainability_index": 0,
    }

    result = calculate_priority(metrics, [])

    assert 0 <= result["priority_score"] <= 100


def test_weights_must_add_up_to_one():
    metrics = {
        "cyclomatic_complexity": 5,
        "nesting_depth": 2,
        "maintainability_index": 80,
    }

    with pytest.raises(ValueError):
        calculate_priority(
            metrics,
            [],
            weights={
                "smell_severity": 0.5,
                "complexity": 0.5,
                "nesting": 0.5,
                "maintainability": 0.5,
            },
        )


def test_repository_functions_are_ranked():
    report = {
        "repository": "test-project",
        "files": [
            {
                "file": "sample.py",
                "relative_path": "sample.py",
                "status": "success",
                "metrics": [
                    {
                        "file": "sample.py",
                        "function": "risky",
                        "qualified_name": "risky",
                        "start_line": 1,
                        "end_line": 10,
                        "cyclomatic_complexity": 10,
                        "nesting_depth": 3,
                        "maintainability_index": 50,
                    },
                    {
                        "file": "sample.py",
                        "function": "simple",
                        "qualified_name": "simple",
                        "start_line": 12,
                        "end_line": 14,
                        "cyclomatic_complexity": 1,
                        "nesting_depth": 0,
                        "maintainability_index": 100,
                    },
                ],
                "smell_analysis": {
                    "function_smells": [
                        {
                            "file": "sample.py",
                            "function": "risky",
                            "qualified_name": "risky",
                            "smell": "Deeply Nested Conditions",
                            "severity": "High",
                            "explanation": "Deep nesting detected.",
                        }
                    ]
                },
            }
        ],
    }

    result = prioritize_repository(report)
    functions = result["prioritized_functions"]

    assert result["summary"]["functions_prioritized"] == 2
    assert functions[0]["qualified_name"] == "risky"
    assert functions[0]["priority_score"] > functions[1]["priority_score"]


def test_empty_repository_is_supported():
    result = prioritize_repository({"files": []})

    assert result["summary"]["functions_prioritized"] == 0
    assert result["prioritized_functions"] == []


def test_invalid_threshold_is_rejected():
    metrics = {
        "cyclomatic_complexity": 5,
        "nesting_depth": 2,
        "maintainability_index": 80,
    }

    with pytest.raises(ValueError):
        calculate_priority(
            metrics,
            [],
            thresholds={
                "cyclomatic_complexity": 0,
                "nesting_depth": 3,
            },
        )
