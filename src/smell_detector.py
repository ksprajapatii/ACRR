import ast
import json
import argparse
from pathlib import Path

from src.metrics_extractor import extract_metrics, extract_qualified_names


DEFAULT_THRESHOLDS = {
    "long_method_loc": 20,
    "high_complexity": 10,
    "too_many_parameters": 5,
    "deep_nesting": 3,
    "large_class_methods": 10,
    "large_class_loc": 200,
    "excessive_conditionals": 5,
    "low_maintainability": 20
}


def detect_duplicates(source, qualified_names):

    tree = ast.parse(source)
    qualified_names = extract_qualified_names(tree)
    fingerprints = {}

    for node in ast.walk(tree):

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):

            fingerprint = ast.dump(
                ast.Module(body=node.body, type_ignores=[]),
                include_attributes=False
            )

            fingerprints.setdefault(fingerprint, []).append({
                "function": node.name,
                "qualified_name": qualified_names[id(node)],
                "start_line": node.lineno,
                "end_line": getattr(node, "end_lineno", node.lineno)
            })

    return [
        group for group in fingerprints.values()
        if len(group) > 1
    ]

def detect_smells(file_path, thresholds=None):

    thresholds = {
        **DEFAULT_THRESHOLDS,
        **(thresholds or {})
    }

    path = Path(file_path)
    source = path.read_text(encoding="utf-8-sig")
    tree = ast.parse(source)
    qualified_names = extract_qualified_names(tree)

    metrics = extract_metrics(path)

    function_smells = []
    file_smells = []
    class_smells = []

    for metric in metrics:

        name = metric["function"]

        def add(smell, severity, value, threshold, explanation):

            function_smells.append({
                "file": str(path),
                "function": name,
                "qualified_name": metric["qualified_name"],
                "start_line": metric["start_line"],
                "end_line": metric["end_line"],
                "smell": smell,
                "severity": severity,
                "measured_value": value,
                "threshold": threshold,
                "explanation": explanation,
                "detection_type": "heuristic"
            })

        if metric["loc"] >= thresholds["long_method_loc"]:

            add(
                "Long Method", "Medium",
                metric["loc"], thresholds["long_method_loc"],
                "Function exceeds the configured LOC threshold."
            )

        if metric["cyclomatic_complexity"] >= thresholds["high_complexity"]:

            add(
                "High Cyclomatic Complexity", "High",
                metric["cyclomatic_complexity"],
                thresholds["high_complexity"],
                "Function has high cyclomatic complexity."
            )

        if metric["parameters"] >= thresholds["too_many_parameters"]:

            add(
                "Too Many Parameters", "Medium",
                metric["parameters"],
                thresholds["too_many_parameters"],
                "Function has reached or exceeded the parameter threshold."
            )

        if metric["nesting_depth"] >= thresholds["deep_nesting"]:

            add(
                "Deeply Nested Conditions", "High",
                metric["nesting_depth"],
                thresholds["deep_nesting"],
                "Function contains deeply nested control-flow blocks."
            )

        if metric["conditionals"] >= thresholds["excessive_conditionals"]:

            add(
                "Excessive Conditional Logic", "High",
                metric["conditionals"],
                thresholds["excessive_conditionals"],
                "Function contains many conditional constructs."
            )

    # Maintainability Index is a FILE-level metric, not a function metric.
    if metrics:

        mi = metrics[0]["maintainability_index"]

        if mi < thresholds["low_maintainability"]:

            file_smells.append({
                "file": str(path),
                "function": None,
                "smell": "Low Maintainability",
                "severity": "High",
                "measured_value": mi,
                "threshold": thresholds["low_maintainability"],
                "explanation": (
                    "The complete Python file has a low Radon "
                    "Maintainability Index."
                ),
                "detection_type": "file_level_heuristic"
            })

    # Large Class detection.
    for node in ast.walk(tree):

        if not isinstance(node, ast.ClassDef):
            continue

        methods = [
            item for item in node.body
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]

        class_loc = (
            getattr(node, "end_lineno", node.lineno)
            - node.lineno + 1
        )

        if (
            len(methods) >= thresholds["large_class_methods"]
            or class_loc >= thresholds["large_class_loc"]
        ):

            class_smells.append({
                "file": str(path),
                "class": node.name,
                "smell": "Large Class",
                "severity": "Medium",
                "measured_value": {
                    "methods": len(methods),
                    "loc": class_loc
                },
                "threshold": {
                    "methods": thresholds["large_class_methods"],
                    "loc": thresholds["large_class_loc"]
                },
                "explanation": "Class exceeds configured size thresholds.",
                "detection_type": "heuristic"
            })

    # Exact normalized AST duplicate detection.
    for group in detect_duplicates(source, qualified_names):

        for item in group:

            function_smells.append({
                "file": str(path),
                "function": item["function"],
                "qualified_name": item["qualified_name"],
                "start_line": item["start_line"],
                "end_line": item["end_line"],
                "smell": "Duplicate Code",
                "severity": "Medium",
                "measured_value": len(group),
                "threshold": 2,
                "explanation": (
                    "Identical normalized AST function bodies "
                    "were found."
                ),
                "detection_type": "exact_ast_match"
            })
    all_smells = function_smells + file_smells + class_smells

    return {
        "file": str(path),
        "thresholds": thresholds,
        "functions_analyzed": len(metrics),
        "total_smells": len(all_smells),
        "function_smells": function_smells,
        "file_smells": file_smells,
        "class_smells": class_smells,
        "smells": all_smells
    }


def main():

    parser = argparse.ArgumentParser(
        description="ACRR Code Smell Detection Engine"
    )

    parser.add_argument("path")

    parser.add_argument(
        "--output",
        default="outputs/reports/smell_report.json"
    )

    args = parser.parse_args()

    target = Path(args.path)

    excluded = {
        ".venv", "venv", "__pycache__", ".git",
        "build", "dist"
    }

    if target.is_file():
        files = [target]

    elif target.is_dir():
        files = [
            file for file in target.rglob("*.py")
            if not any(part in excluded for part in file.parts)
        ]

    else:
        raise FileNotFoundError(target)

    reports = [
        detect_smells(file)
        for file in files
        if file.suffix == ".py"
    ]

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    output.write_text(
        json.dumps(reports, indent=4),
        encoding="utf-8"
    )

    total = sum(r["total_smells"] for r in reports)

    print("\nACRR CODE SMELL ANALYSIS")
    print("------------------------")
    print("Files analyzed:", len(reports))
    print("Functions analyzed:", sum(
        r["functions_analyzed"] for r in reports
    ))
    print("Total warnings:", total)

    for report in reports:

        for smell in report["smells"]:

            subject = (
                smell.get("function")
                or smell.get("class")
                or "FILE"
            )

            print(
                f'{smell["smell"]} | {subject} | '
                f'{smell["severity"]}'
            )

    print("\nReport:", output.resolve())


if __name__ == "__main__":
    main()



