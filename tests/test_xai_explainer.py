import pytest

from src.xai_explainer import (
    explain_function,
    explain_priorities,
    recommend_actions,
    render_markdown,
)


def test_explain_function_returns_all_sections():
    function = {
        "function": "check_access",
        "qualified_name": "check_access",
        "file": "sample.py",
        "priority_score": 72.0,
        "priority": "High",
        "components": {
            "smell_severity": 100,
            "complexity": 40,
            "nesting": 100,
            "maintainability": 0,
        },
        "weighted_contributions": {
            "smell_severity": 40,
            "complexity": 12,
            "nesting": 20,
            "maintainability": 0,
        },
        "detected_smells": [
            {
                "name": "Deeply Nested Conditions",
                "severity": "High",
            }
        ],
        "reasons": ["Deep nesting detected."],
    }

    result = explain_function(function)

    assert result["priority_score"] == 72.0
    assert result["priority"] == "High"
    assert result["contributing_factors"]
    assert result["detected_smells"]
    assert result["reasons"]
    assert result["recommended_actions"]


def test_deep_nesting_recommends_guard_clauses():
    actions = recommend_actions(
        [{"name": "Deeply Nested Conditions"}],
        {"complexity": 0, "nesting": 100, "maintainability": 0},
    )

    assert any("guard clauses" in action.lower() for action in actions)


def test_explain_priorities_handles_empty_report():
    result = explain_priorities({"prioritized_functions": []})

    assert result["summary"]["functions_explained"] == 0
    assert result["explanations"] == []


def test_markdown_report_contains_function_and_recommendations():
    report = explain_priorities({
        "prioritized_functions": [{
            "function": "check_access",
            "qualified_name": "check_access",
            "file": "sample.py",
            "priority_score": 72,
            "priority": "High",
            "components": {"complexity": 40, "nesting": 100},
            "weighted_contributions": {
                "complexity": 12,
                "nesting": 20,
            },
            "detected_smells": [],
            "reasons": ["Deep nesting detected."],
        }]
    })

    markdown = render_markdown(report)

    assert "check_access" in markdown
    assert "Recommended refactoring actions" in markdown
    assert "Deep nesting detected." in markdown


def test_invalid_report_is_rejected():
    with pytest.raises(ValueError):
        explain_priorities({"functions": []})
