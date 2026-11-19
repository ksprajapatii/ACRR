import ast
import csv
import json
from pathlib import Path

from src.refactoring_evaluator import evaluate_function
from src.smell_detector import detect_smells
from src.metrics_extractor import extract_qualified_names


PROJECT_ROOT = Path(__file__).resolve().parent.parent

SOURCE_DIRECTORIES = [
    PROJECT_ROOT / "data" / "sample_code",
    PROJECT_ROOT / "data" / "raw" / "repositories" / "click" / "src" / "click",
]

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "function_dataset.csv"
)


def extract_functions(file_path, smell_report):
    source = file_path.read_text(encoding="utf-8-sig")
    tree = ast.parse(source)
    qualified_names = extract_qualified_names(tree)

    function_smells = smell_report.get("function_smells", [])

    records = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            continue

        function_source = ast.get_source_segment(source, node)

        if not function_source:
            continue

        try:
            metrics = evaluate_function(function_source, node.name)
        except (ValueError, TypeError, KeyError) as error:
            print(
                f"Skipped function {node.name} "
                f"in {file_path.name}: {error}"
            )
            continue

        # Match detector results using the exact function identity.
        qualified_name = qualified_names[id(node)]

        detected_smells = [
            smell
            for smell in function_smells
            if (
                smell.get("qualified_name") == qualified_name
                and smell.get("start_line") == node.lineno
            )
        ]

        if detected_smells:
            smell_types = [
                smell["smell"]
                for smell in detected_smells
            ]

            severities = [
                smell["severity"]
                for smell in detected_smells
            ]

            detection_methods = [
                smell.get("detection_type", "Unknown")
                for smell in detected_smells
            ]
        else:
            smell_types = ["No Smell"]
            severities = ["None"]
            detection_methods = ["None"]

        records.append({
            "file_name": file_path.name,
            "file_path": file_path.relative_to(PROJECT_ROOT).as_posix(),
            "qualified_name": qualified_name,
            "start_line": node.lineno,
            "end_line": getattr(node, "end_lineno", node.lineno),
            "function_name": node.name,
            "source_code": function_source,
            "loc": metrics["lines_of_code"],
            "cyclomatic_complexity":
                metrics["cyclomatic_complexity"],
            "nesting_depth": metrics["nesting_depth"],
            "maintainability_index":
                metrics["maintainability_index"],
            "smell_type": "; ".join(smell_types),
            "severity": "; ".join(severities),
            "detection_method": "; ".join(detection_methods),
            "smell_count": len(detected_smells),
        })

    return records


def build_dataset():
    all_records = []

    for directory in SOURCE_DIRECTORIES:

        if not directory.exists():
            continue

        for file_path in sorted(directory.rglob("*.py")):

            try:
                # Run the existing smell detector.
                smell_report = detect_smells(file_path)

                # Extract functions and attach their labels.
                records = extract_functions(
                    file_path,
                    smell_report
                )

                all_records.extend(records)

            except (SyntaxError, UnicodeDecodeError) as error:
                print(f"Skipped {file_path}: {error}")

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    fieldnames = [
        "file_name",
        "file_path",
        "qualified_name",
        "start_line",
        "end_line",
        "function_name",
        "source_code",
        "loc",
        "cyclomatic_complexity",
        "nesting_depth",
        "maintainability_index",
        "smell_type",
        "severity",
        "detection_method",
        "smell_count",
    ]

    with OUTPUT_FILE.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as csv_file:

        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(all_records)

    total_smells = sum(
        record["smell_count"]
        for record in all_records
    )

    print("\nACRR DATASET BUILDER")
    print("--------------------")
    print("Functions extracted:", len(all_records))
    print("Total smell labels:", total_smells)
    print(
        "Functions without smells:",
        sum(
            record["smell_count"] == 0
            for record in all_records
        )
    )
    print("Dataset saved:", OUTPUT_FILE)

    return all_records


if __name__ == "__main__":
    build_dataset()



