import json
import argparse
import ast
from pathlib import Path


RECOMMENDATIONS = {

    "Long Method": {
        "technique": "Extract Method",
        "description": "Divide a long function into smaller functions with clear responsibilities.",
        "reason": "Long functions are harder to understand, test, debug and maintain.",
        "benefits": [
            "Improves readability",
            "Separates responsibilities",
            "Makes unit testing easier",
            "Improves code reuse"
        ],
        "risks": [
            "Incorrect extraction may change variable scope",
            "Excessive extraction can create unnecessary function calls"
        ],
        "automation": "Requires semantic review"
    },

    "High Cyclomatic Complexity": {
        "technique": "Decompose Function",
        "description": "Break complex decision-making logic into smaller functions.",
        "reason": "High cyclomatic complexity indicates many independent execution paths.",
        "benefits": [
            "Reduces complexity of individual functions",
            "Improves testability",
            "Simplifies control flow"
        ],
        "risks": [
            "Incorrect decomposition may change execution order",
            "Shared state may complicate extraction"
        ],
        "automation": "Requires semantic review"
    },

    "Too Many Parameters": {
        "technique": "Introduce Parameter Object",
        "description": "Group related function parameters into a dedicated configuration or data object.",
        "reason": "A large parameter list makes function calls harder to understand and maintain.",
        "benefits": [
            "Simplifies function signatures",
            "Groups related data",
            "Improves readability"
        ],
        "risks": [
            "Requires changes to function callers",
            "Unrelated parameters should not be grouped arbitrarily"
        ],
        "automation": "Requires caller analysis"
    },

    "Deeply Nested Conditions": {
        "technique": "Replace Nested Conditions with Guard Clauses",
        "description": "Use early returns or early exits to reduce nested control flow.",
        "reason": "Deep nesting makes the execution path difficult to follow.",
        "benefits": [
            "Reduces nesting depth",
            "Improves readability",
            "Makes exceptional conditions explicit"
        ],
        "risks": [
            "Early returns can change behavior if side effects are reordered",
            "All execution paths must be tested"
        ],
        "automation": "Requires semantic review"
    },

    "Duplicate Code": {
        "technique": "Extract Common Function",
        "description": "Move identical logic into a reusable shared function.",
        "reason": "Duplicated logic increases maintenance effort and the chance of inconsistent fixes.",
        "benefits": [
            "Reduces code duplication",
            "Centralizes common behavior",
            "Simplifies maintenance"
        ],
        "risks": [
            "Similar-looking code may have different business meanings",
            "Shared function may introduce unnecessary coupling"
        ],
        "automation": "Requires semantic review"
    },

    "Large Class": {
        "technique": "Extract Class",
        "description": "Separate unrelated responsibilities into focused classes.",
        "reason": "Large classes can accumulate multiple responsibilities.",
        "benefits": [
            "Improves separation of concerns",
            "Reduces class responsibilities",
            "Improves maintainability"
        ],
        "risks": [
            "Changes object relationships",
            "May increase inter-class dependencies"
        ],
        "automation": "Requires architectural review"
    },

    "Excessive Conditional Logic": {
        "technique": "Replace Conditional with Polymorphism",
        "description": "Move behavior-specific conditional branches into separate implementations.",
        "reason": "Large conditional structures can make adding new behaviors difficult.",
        "benefits": [
            "Separates behavior",
            "Improves extensibility",
            "Reduces large conditional blocks"
        ],
        "risks": [
            "May introduce unnecessary classes",
            "Requires careful design of common interfaces"
        ],
        "automation": "Requires architectural review"
    },

    "Low Maintainability": {
        "technique": "Refactor Maintainability Hotspots",
        "description": "Inspect high-complexity, long and deeply nested functions in the affected file.",
        "reason": "The file-level Maintainability Index indicates that the file deserves further inspection.",
        "benefits": [
            "Targets problematic code",
            "Prioritizes maintenance work",
            "Provides measurable quality indicators"
        ],
        "risks": [
            "A low file-level score does not identify the exact problematic function",
            "Refactoring the wrong component may provide little improvement"
        ],
        "automation": "Requires hotspot analysis"
    }
}


def extract_function_source(file_path, function_name):

    if not function_name:
        return None

    path = Path(file_path)

    if not path.is_file():
        return None

    try:
        source = path.read_text(encoding="utf-8-sig")
        tree = ast.parse(source)
        lines = source.splitlines()

        matches = []

        for node in ast.walk(tree):

            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == function_name:

                    start = node.lineno - 1
                    end = node.end_lineno

                    matches.append("\n".join(lines[start:end]))

        if len(matches) == 1:
            return matches[0]

        if len(matches) > 1:
            return (
                "Multiple functions have this name. "
                "Source selection requires qualified-name matching."
            )

    except (OSError, SyntaxError, UnicodeError):
        return None

    return None


def generate_recommendations(smell_report):

    reports = (
        smell_report
        if isinstance(smell_report, list)
        else [smell_report]
    )

    results = []

    for report in reports:

        for smell in report.get("smells", []):

            smell_name = smell.get("smell")

            recommendation = RECOMMENDATIONS.get(smell_name)

            if recommendation is None:
                continue

            file_path = smell.get("file", "")
            function_name = smell.get("function")

            source = extract_function_source(
                file_path,
                function_name
            )

            if smell_name == "Low Maintainability":
                source = (
                    "File-level issue: inspect individual function "
                    "metrics to identify maintainability hotspots."
                )

            result = {

                "file": file_path,
                "function": function_name,
                "class": smell.get("class"),

                "detected_smell": smell_name,

                "severity": smell.get("severity"),

                "measured_value": smell.get("measured_value"),

                "detection_type": smell.get("detection_type"),

                "original_source": source,

                "recommended_technique": recommendation["technique"],

                "recommendation_explanation": recommendation["description"],

                "why_recommended": recommendation["reason"],

                "expected_benefits": recommendation["benefits"],

                "potential_risks": recommendation["risks"],

                "automation_status": "Recommendation only; source not modified",

                "automation_requirements": recommendation["automation"],

                "ml_prediction": None,

                "recommendation_method": "Rule-based baseline",

                "actual_improvement": None

            }

            results.append(result)

    return results


def main():

    parser = argparse.ArgumentParser(
        description="ACRR Refactoring Recommendation Engine"
    )

    parser.add_argument(
        "--input",
        default="outputs/reports/smell_report.json"
    )

    parser.add_argument(
        "--output",
        default="outputs/reports/refactoring_recommendations.json"
    )

    args = parser.parse_args()

    input_path = Path(args.input)

    if not input_path.is_file():
        raise FileNotFoundError(
            f"Smell report not found: {input_path.resolve()}"
        )

    smell_report = json.loads(
        input_path.read_text(encoding="utf-8-sig")
    )

    recommendations = generate_recommendations(smell_report)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        json.dumps(recommendations, indent=4),
        encoding="utf-8"
    )

    print("\nACRR RECOMMENDATION ENGINE")
    print("--------------------------")

    print("Recommendations generated:", len(recommendations))

    for item in recommendations:

        print(
            f'\nFunction: {item["function"] or item["class"] or "FILE"}'
            f'\nDetected: {item["detected_smell"]}'
            f'\nRecommended: {item["recommended_technique"]}'
            f'\nMethod: {item["recommendation_method"]}'
        )

    print("\nOriginal source files were not modified.")

    print("Output:", output_path.resolve())


if __name__ == "__main__":
    main()
