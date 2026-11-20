import argparse
import json
from pathlib import Path


REFACTORING_ACTIONS = {
    "deeply nested conditions": [
        "Use guard clauses to reduce nested conditional blocks.",
        "Simplify complex conditional expressions.",
    ],
    "too many parameters": [
        "Consider grouping related parameters into a configuration object.",
        "Review whether the function has too many responsibilities.",
    ],
    "long method": [
        "Extract independent logic into smaller helper functions.",
        "Give each function a single clear responsibility.",
    ],
    "high cyclomatic complexity": [
        "Break complex decision logic into smaller functions.",
        "Simplify branching and conditional expressions.",
    ],
    "large class": [
        "Separate unrelated responsibilities into smaller classes.",
        "Apply the Single Responsibility Principle.",
    ],
    "low maintainability": [
        "Review complex logic and simplify difficult sections.",
        "Improve naming, modularity, and documentation.",
    ],
}


def recommend_actions(smells, components):
    actions = []

    for smell in smells:
        smell_name = str(smell.get("name", "")).lower()

        matched = REFACTORING_ACTIONS.get(smell_name, [])

        for action in matched:
            if action not in actions:
                actions.append(action)

    if components.get("complexity", 0) >= 40:
        action = (
            "Reduce cyclomatic complexity by simplifying "
            "branches and extracting helper functions."
        )
        if action not in actions:
            actions.append(action)

    if components.get("nesting", 0) >= 40:
        action = (
            "Reduce nesting depth using early returns "
            "and simpler control flow."
        )
        if action not in actions:
            actions.append(action)

    if components.get("maintainability", 0) >= 40:
        action = (
            "Improve maintainability by simplifying "
            "the function structure."
        )
        if action not in actions:
            actions.append(action)

    if not actions:
        actions.append(
            "No urgent refactoring action identified. "
            "Continue monitoring this function."
        )

    return actions


def explain_function(function):
    score = function.get("priority_score", 0)
    priority = function.get("priority", "Unknown")
    components = function.get("components", {})
    contributions = function.get("weighted_contributions", {})
    smells = function.get("detected_smells", [])
    reasons = function.get("reasons", [])

    factor_explanations = []

    for name, contribution in contributions.items():
        component_score = components.get(name, 0)

        factor_explanations.append({
            "factor": name,
            "component_score": component_score,
            "weighted_contribution": contribution,
            "weight": (
                contribution / component_score
                if component_score else 0
            ),
            "explanation": (
                f"{name.replace('_', ' ').title()} contributed "
                f"{contribution} points to the total priority score."
            ),
        })

    factor_explanations.sort(
        key=lambda item: item["weighted_contribution"],
        reverse=True,
    )

    actions = recommend_actions(smells, components)

    return {
        "function": function.get("function"),
        "qualified_name": function.get("qualified_name"),
        "file": function.get("file"),
        "start_line": function.get("start_line"),
        "end_line": function.get("end_line"),
        "priority_score": score,
        "priority": priority,
        "explanation": (
            f"This function received a priority score of {score}/100 "
            f"and was classified as {priority} priority."
        ),
        "contributing_factors": factor_explanations,
        "detected_smells": smells,
        "reasons": reasons,
        "recommended_actions": actions,
    }


def explain_priorities(prioritization_report):
    if not isinstance(prioritization_report, dict):
        raise ValueError("Prioritization report must be a JSON object.")

    functions = prioritization_report.get("prioritized_functions")

    if not isinstance(functions, list):
        raise ValueError(
            "Report must contain a prioritized_functions list."
        )

    explanations = [
        explain_function(function)
        for function in functions
    ]

    return {
        "tool": "ACRR Explainable AI Engine",
        "version": "1.2.0",
        "source_report": prioritization_report.get("source_report"),
        "summary": {
            "functions_explained": len(explanations),
        },
        "explanations": explanations,
    }


def render_markdown(report):
    lines = [
        "# ACRR — Explainable Refactoring Report",
        "",
        f"**Functions explained:** "
        f"{report['summary']['functions_explained']}",
        "",
    ]

    for item in report["explanations"]:
        lines.extend([
            "---",
            "",
            f"## {item.get('qualified_name') or item.get('function')}",
            "",
            f"- **File:** {item.get('file')}",
            f"- **Priority:** {item['priority']}",
            f"- **Score:** {item['priority_score']}/100",
            "",
            "### Why was this function prioritized?",
            "",
            item["explanation"],
            "",
            "### Contributing factors",
            "",
            "| Factor | Component score | Weighted contribution |",
            "|---|---:|---:|",
        ])

        for factor in item["contributing_factors"]:
            lines.append(
                f"| {factor['factor']} "
                f"| {factor['component_score']} "
                f"| {factor['weighted_contribution']} |"
            )

        lines.extend([
            "",
            "### Detected code smells",
            "",
        ])

        if item["detected_smells"]:
            for smell in item["detected_smells"]:
                lines.append(
                    f"- **{smell.get('name', 'Unknown')}** "
                    f"({smell.get('severity', 'Unknown')})"
                )
        else:
            lines.append("- No function-level code smells detected.")

        lines.extend([
            "",
            "### Explanation",
            "",
        ])

        for reason in item["reasons"]:
            lines.append(f"- {reason}")

        lines.extend([
            "",
            "### Recommended refactoring actions",
            "",
        ])

        for action in item["recommended_actions"]:
            lines.append(f"- {action}")

        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="ACRR Explainable AI Engine"
    )

    parser.add_argument(
        "report",
        help="Refactoring prioritization JSON report",
    )

    parser.add_argument(
        "--output",
        default="outputs/reports/xai_explanations.json",
        help="JSON explanation report path",
    )

    parser.add_argument(
        "--markdown",
        default="outputs/reports/xai_explanations.md",
        help="Markdown explanation report path",
    )

    args = parser.parse_args()

    input_path = Path(args.report)

    if not input_path.is_file():
        parser.error(f"Input report not found: {input_path}")

    prioritization_report = json.loads(
        input_path.read_text(encoding="utf-8")
    )

    result = explain_priorities(prioritization_report)

    json_path = Path(args.output)
    markdown_path = Path(args.markdown)

    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)

    json_path.write_text(
        json.dumps(result, indent=4, ensure_ascii=False),
        encoding="utf-8",
    )

    markdown_path.write_text(
        render_markdown(result),
        encoding="utf-8",
    )

    print("\n========== ACRR XAI ENGINE ==========")
    print(
        "Functions explained:",
        result["summary"]["functions_explained"],
    )
    print("JSON report:", json_path.resolve())
    print("Markdown report:", markdown_path.resolve())


if __name__ == "__main__":
    main()
