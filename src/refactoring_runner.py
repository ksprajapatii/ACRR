import argparse
import ast
import copy
import json
from pathlib import Path

from src.refactoring_engine import (
    replace_nested_conditions,
    replace_nested_assignment_with_guard,
    simplify_nested_conditions_in_loops,
    RefactoringError
)
from src.refactoring_evaluator import (
    evaluate_code,
    compare_functions
)
from src.auto_refactoring import find_refactoring_candidates


DEFAULT_TEST_CASES = [
    (True, True, True),
    (True, True, False),
    (True, False, True),
    (False, True, True),
    (False, False, False),
]


TRANSFORMATION_FUNCTIONS = {
    "replace_nested_conditions": replace_nested_conditions,
    "replace_nested_assignment_with_guard":
        replace_nested_assignment_with_guard,
    "simplify_nested_conditions_in_loops":
        simplify_nested_conditions_in_loops,
}


def get_test_cases(function_name):

    if function_name == "check_access":
        return DEFAULT_TEST_CASES

    if function_name == "process_data":
        return [
            (True, True, True, 10, 20),
            (True, True, False, 10, 20),
            (True, False, True, 10, 20),
            (False, True, True, 10, 20),
            (False, False, False, 10, 20),
            (True, True, True, 0, 0),
            (True, True, True, -5, 15),
        ]

    if function_name == "calculate_total":
        return [
            (None, [], 0.0),
            (
                None,
                [{"active": True, "quantity": 2, "price": 100}],
                0.0
            ),
            (
                None,
                [
                    {"active": True, "quantity": 2, "price": 100},
                    {"active": False, "quantity": 5, "price": 200},
                    {"active": True, "quantity": 0, "price": 300},
                    {"active": True, "quantity": 3, "price": 50},
                ],
                0.18
            ),
            (
                None,
                [{"active": False, "quantity": 4, "price": 50}],
                0.05
            ),
            (
                None,
                [{"active": True, "quantity": -2, "price": 100}],
                0.10
            ),
        ]

    raise ValueError(
        f"No test cases configured for function: {function_name}"
    )


def load_function(source, function_name):
    """Compile only the selected function definition."""

    tree = ast.parse(source)

    matches = [
        node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == function_name
    ]

    if len(matches) != 1:
        raise ValueError(
            f"Expected exactly one top-level function named "
            f"'{function_name}'."
        )

    function_node = copy.deepcopy(matches[0])

    isolated_module = ast.Module(
        body=[function_node],
        type_ignores=[]
    )

    ast.fix_missing_locations(isolated_module)

    namespace = {"__builtins__": __builtins__}

    exec(
        compile(isolated_module, "<selected-function>", "exec"),
        namespace
    )

    return namespace[function_name]


def validate_functional_equivalence(
    original_source,
    refactored_source,
    function_name,
    test_cases
):
    original_function = load_function(
        original_source, function_name
    )

    refactored_function = load_function(
        refactored_source, function_name
    )

    passed = 0
    failed = 0
    failures = []

    for case in test_cases:
        try:
            original_result = original_function(*case)
            refactored_result = refactored_function(*case)

            if original_result == refactored_result:
                passed += 1
            else:
                failed += 1
                failures.append({
                    "input": repr(case),
                    "original_result": repr(original_result),
                    "refactored_result": repr(refactored_result)
                })

        except Exception as exc:
            failed += 1
            failures.append({
                "input": repr(case),
                "error": str(exc)
            })

    return {
        "status": "passed" if failed == 0 else "failed",
        "function": function_name,
        "test_cases_passed": passed,
        "test_cases_failed": failed,
        "failures": failures
    }


def select_automatic_candidates(input_path, smell_report):

    candidates = find_refactoring_candidates(smell_report)

    selected = []

    for candidate in candidates:
        candidate_path = Path(candidate["file"]).resolve()

        if candidate_path != input_path:
            continue

        if not candidate["eligible"]:
            continue

        transformation = candidate["transformation"]

        if transformation not in TRANSFORMATION_FUNCTIONS:
            continue

        selected.append(candidate)

    # Avoid applying the same transformation twice to one function.
    unique = {}
    for candidate in selected:
        unique[candidate["function"]] = candidate

    selected = list(unique.values())

    if not selected:
        raise RefactoringError(
            "No eligible refactoring candidates found for "
            f"{input_path}. Check the smell report and input file."
        )

    return selected


def apply_transformation(source, function_name, transformation):

    if transformation not in TRANSFORMATION_FUNCTIONS:
        raise RefactoringError(
            f"Unknown transformation: {transformation}"
        )

    transformer = TRANSFORMATION_FUNCTIONS[transformation]

    if transformation == "replace_nested_conditions":
        return transformer(source)

    return transformer(source, function_name)


def run_refactoring(
    input_path,
    output_path,
    report_path,
    function_name="check_access",
    smell_report=None
):

    input_path = Path(input_path).resolve()
    output_path = Path(output_path).resolve()
    report_path = Path(report_path).resolve()

    if not input_path.is_file():
        raise FileNotFoundError(
            f"Input file not found: {input_path}"
        )

    if input_path in (output_path, report_path):
        raise ValueError(
            "Output and report paths must not overwrite the input."
        )

    if output_path == report_path:
        raise ValueError(
            "Python output and JSON report need different paths."
        )

    original_source = input_path.read_text(
        encoding="utf-8-sig"
    )

    before = evaluate_code(original_source)

    if smell_report:
        mode = "automatic"

        selected = select_automatic_candidates(
            input_path,
            smell_report
        )

    else:
        mode = "manual"

        selected = [{
            "function": function_name,
            "transformation": "replace_nested_conditions",
            "severity": None,
            "smell": "Manual selection"
        }]

    refactored_source = original_source
    transformation_results = []

    # Apply each selected transformation independently.
    for candidate in selected:

        selected_function = candidate["function"]
        transformation = candidate["transformation"]

        refactored_source = apply_transformation(
            refactored_source,
            selected_function,
            transformation
        )

        transformation_results.append({
            "function": selected_function,
            "transformation": transformation,
            "severity": candidate.get("severity")
        })

    # Stage 1: Syntax validation.
    ast.parse(refactored_source)

    # Stage 2: Functional equivalence for every selected function.
    equivalence_results = []

    for candidate in selected:

        selected_function = candidate["function"]

        test_cases = get_test_cases(selected_function)

        equivalence = validate_functional_equivalence(
            original_source,
            refactored_source,
            selected_function,
            test_cases
        )

        equivalence_results.append(equivalence)

    failed_results = [
        result for result in equivalence_results
        if result["status"] != "passed"
    ]

    if failed_results:
        raise RefactoringError(
            "Functional equivalence validation failed. "
            "Refactored output was not saved. "
            f"Failed functions: "
            f"{[item['function'] for item in failed_results]}"
        )

    # Stage 3: Calculate metrics.
    after = evaluate_code(refactored_source)

    changes = {
        metric: round(after[metric] - before[metric], 2)
        for metric in before
    }

    # Stage 4: Save only after all validations pass.
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    output_path.write_text(
        refactored_source,
        encoding="utf-8"
    )

    total_passed = sum(
        item["test_cases_passed"]
        for item in equivalence_results
    )

    total_failed = sum(
        item["test_cases_failed"]
        for item in equivalence_results
    )

    function_metrics = compare_functions(
        original_source,
        refactored_source,
        [item["function"] for item in selected]
    )

    report = {
        "experiment": "ACRR Automatic Code Refactoring",
        "function_level_metrics": function_metrics,
        "mode": mode,
        "status": "success",
        "input_file": str(input_path),
        "output_file": str(output_path),
        "original_source_modified": False,
        "selected_transformations": transformation_results,
        "syntax_validation": "passed",
        "functional_equivalence": {
            "status": "passed",
            "functions": equivalence_results,
            "total_test_cases_passed": total_passed,
            "total_test_cases_failed": total_failed
        },
        "before_metrics": before,
        "after_metrics": after,
        "metric_changes": changes
    }

    report_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    report_path.write_text(
        json.dumps(report, indent=4),
        encoding="utf-8"
    )

    print("\nACRR REFACTORING RUNNER")
    print("----------------------")
    print(f"Mode: {mode.upper()}")

    for item in transformation_results:
        print(f"\nFunction: {item['function']}")
        print(f"Transformation: {item['transformation']}")

    print("\nSyntax validation: PASSED")
    print("Functional equivalence: PASSED")
    print(
        f"Test cases: {total_passed} passed, "
        f"{total_failed} failed"
    )

    print(f"\nRefactored file: {output_path}")
    print(f"JSON report: {report_path}")
    print("\nOriginal source was not modified.")

    return report


def main():

    parser = argparse.ArgumentParser(
        description="ACRR automated refactoring runner"
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Input Python source file"
    )

    parser.add_argument(
        "--output",
        required=True,
        help="Output path for refactored Python file"
    )

    parser.add_argument(
        "--report",
        default="outputs/reports/refactoring_run.json",
        help="JSON experiment report path"
    )

    parser.add_argument(
        "--function",
        default="check_access",
        help="Function to validate in manual mode"
    )

    parser.add_argument(
        "--smell-report",
        default=None,
        help="Smell report JSON for automatic function selection"
    )

    args = parser.parse_args()

    try:
        run_refactoring(
            args.input,
            args.output,
            args.report,
            args.function,
            args.smell_report
        )

    except (
        RefactoringError,
        SyntaxError,
        ValueError,
        OSError
    ) as exc:
        parser.exit(
            1,
            f"\nACRR REFACTORING FAILED: {exc}\n"
        )


if __name__ == "__main__":
    main()
