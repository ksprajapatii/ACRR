import argparse
import json
from collections import Counter
from pathlib import Path


DEFAULT_WEIGHTS = {
    "smell_severity": 0.40,
    "complexity": 0.30,
    "nesting": 0.20,
    "maintainability": 0.10,
}

DEFAULT_THRESHOLDS = {
    "cyclomatic_complexity": 10,
    "nesting_depth": 3,
}


def _number(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _file_key(value):
    return str(Path(value).resolve()).casefold()


def _priority_label(score):
    if score >= 80:
        return "Critical"
    if score >= 60:
        return "High"
    if score >= 40:
        return "Medium"
    return "Low"


def _smell_score(smells):
    severity_values = {
        "high": 100,
        "medium": 65,
        "low": 30,
    }

    if not smells:
        return 0.0

    return max(
        severity_values.get(
            str(smell.get("severity", "")).lower(), 0
        )
        for smell in smells
    )


def calculate_priority(
    metrics,
    smells,
    weights=None,
    thresholds=None,
):
    weights = weights or DEFAULT_WEIGHTS
    thresholds = thresholds or DEFAULT_THRESHOLDS

    if not metrics:
        raise ValueError("Function metrics cannot be empty.")

    if any(value < 0 for value in weights.values()):
        raise ValueError("Weights cannot be negative.")

    if abs(sum(weights.values()) - 1.0) > 1e-9:
        raise ValueError("Weights must add up to 1.0.")

    complexity_limit = _number(
        thresholds.get("cyclomatic_complexity"), 10
    )
    nesting_limit = _number(
        thresholds.get("nesting_depth"), 3
    )

    if complexity_limit <= 0 or nesting_limit <= 0:
        raise ValueError("Scoring thresholds must be positive.")

    smell_component = _smell_score(smells)

    complexity = min(
        _number(metrics.get("cyclomatic_complexity"))
        / complexity_limit * 100,
        100,
    )

    nesting = min(
        _number(metrics.get("nesting_depth"))
        / nesting_limit * 100,
        100,
    )

    maintainability_index = max(
        0,
        min(_number(metrics.get("maintainability_index"), 100), 100),
    )
    maintainability = 100 - maintainability_index

    components = {
        "smell_severity": round(smell_component, 2),
        "complexity": round(complexity, 2),
        "nesting": round(nesting, 2),
        "maintainability": round(maintainability, 2),
    }

    contributions = {
        name: round(components[name] * weight, 2)
        for name, weight in weights.items()
    }

    score = round(sum(contributions.values()), 2)

    reasons = []

    if smells:
        for smell in smells:
            reasons.append(
                f'{smell.get("severity", "Unknown")} severity smell: '
                f'{smell.get("smell", "Unknown")}. '
                f'{smell.get("explanation", "")}'.strip()
            )

    if complexity >= 70:
        reasons.append("High cyclomatic complexity.")
    elif complexity >= 40:
        reasons.append("Moderate cyclomatic complexity.")

    if nesting >= 70:
        reasons.append("Deeply nested control-flow structure.")
    elif nesting >= 40:
        reasons.append("Moderate nesting depth.")

    if maintainability >= 70:
        reasons.append("Low maintainability index.")

    if not reasons:
        reasons.append("No major prioritization risk detected.")

    return {
        "priority_score": score,
        "priority": _priority_label(score),
        "components": components,
        "weighted_contributions": contributions,
        "reasons": reasons,
    }


def prioritize_repository(report, weights=None, thresholds=None):
    if not isinstance(report, dict):
        raise ValueError("Repository report must be a JSON object.")

    if not isinstance(report.get("files"), list):
        raise ValueError("Repository report must contain a files list.")

    prioritized = []

    for file_record in report["files"]:
        if file_record.get("status") != "success":
            continue

        metrics_list = file_record.get("metrics", [])
        smell_analysis = file_record.get("smell_analysis", {})
        function_smells = smell_analysis.get("function_smells", [])

        smells_by_function = {}

        for smell in function_smells:
            key = (
                _file_key(smell.get("file", file_record.get("file", ""))),
                smell.get("qualified_name") or smell.get("function"),
            )
            smells_by_function.setdefault(key, []).append(smell)

        for metrics in metrics_list:
            identity = (
                _file_key(metrics.get("file", file_record.get("file", ""))),
                metrics.get("qualified_name") or metrics.get("function"),
            )

            matched_smells = smells_by_function.get(identity, [])

            result = calculate_priority(
                metrics,
                matched_smells,
                weights=weights,
                thresholds=thresholds,
            )

            prioritized.append({
                "file": file_record.get("relative_path")
                        or file_record.get("file"),
                "function": metrics.get("function"),
                "qualified_name": metrics.get("qualified_name"),
                "start_line": metrics.get("start_line"),
                "end_line": metrics.get("end_line"),
                "cyclomatic_complexity": metrics.get(
                    "cyclomatic_complexity"
                ),
                "nesting_depth": metrics.get("nesting_depth"),
                "maintainability_index": metrics.get(
                    "maintainability_index"
                ),
                "detected_smells": [
                    {
                        "name": smell.get("smell"),
                        "severity": smell.get("severity"),
                    }
                    for smell in matched_smells
                ],
                **result,
            })

    prioritized.sort(
        key=lambda item: item["priority_score"],
        reverse=True,
    )

    priority_counts = Counter(
        item["priority"] for item in prioritized
    )

    return {
        "tool": "ACRR Refactoring Prioritizer",
        "version": "1.2.0",
        "source_report": report.get("repository"),
        "scoring_weights": weights or DEFAULT_WEIGHTS,
        "scoring_thresholds": thresholds or DEFAULT_THRESHOLDS,
        "summary": {
            "functions_prioritized": len(prioritized),
            "priority_counts": dict(priority_counts),
        },
        "prioritized_functions": prioritized,
    }


def main():
    parser = argparse.ArgumentParser(
        description="ACRR Refactoring Prioritization Engine"
    )
    parser.add_argument("report", help="Repository scan JSON report")
    parser.add_argument(
        "--output",
        default="outputs/reports/refactoring_priorities.json",
        help="Output JSON report path",
    )

    args = parser.parse_args()

    input_path = Path(args.report)
    if not input_path.is_file():
        parser.error(f"Input report not found: {input_path}")

    report = json.loads(input_path.read_text(encoding="utf-8"))
    result = prioritize_repository(report)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, indent=4, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\n========== ACRR REFACTORING PRIORITIZER ==========")
    print("Functions prioritized:", result["summary"]["functions_prioritized"])
    print("Priority counts:", result["summary"]["priority_counts"])

    for item in result["prioritized_functions"]:
        print(
            f'{item["priority_score"]:6.2f} | '
            f'{item["priority"]:8} | '
            f'{item["qualified_name"]}'
        )

    print("Report:", output_path.resolve())


if __name__ == "__main__":
    main()
