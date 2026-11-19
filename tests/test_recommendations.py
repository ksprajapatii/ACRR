from src.recommendation_engine import generate_recommendations


def test_parameter_recommendation():

    report = [{
        "smells": [{
            "file": "sample.py",
            "function": "calculate",
            "smell": "Too Many Parameters",
            "severity": "Medium",
            "measured_value": 5,
            "detection_type": "heuristic"
        }]
    }]

    results = generate_recommendations(report)

    assert len(results) == 1

    assert (
        results[0]["recommended_technique"]
        == "Introduce Parameter Object"
    )

    assert results[0]["ml_prediction"] is None

    print("Parameter recommendation test passed")


def test_guard_clause_recommendation():

    report = [{
        "smells": [{
            "file": "sample.py",
            "function": "process",
            "smell": "Deeply Nested Conditions",
            "severity": "High",
            "measured_value": 3,
            "detection_type": "heuristic"
        }]
    }]

    results = generate_recommendations(report)

    assert (
        results[0]["recommended_technique"]
        == "Replace Nested Conditions with Guard Clauses"
    )

    print("Guard clause recommendation test passed")


if __name__ == "__main__":

    test_parameter_recommendation()
    test_guard_clause_recommendation()

    print("\nAll recommendation tests passed")
