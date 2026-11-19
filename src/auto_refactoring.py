import ast
import json
from pathlib import Path


SUPPORTED_SMELL = "Deeply Nested Conditions"


def extract_function_node(source, function_name):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None

    matches = [
        node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == function_name
    ]

    if len(matches) != 1:
        return None

    return matches[0]


def inspect_nested_chain(outer_if):
    conditions = []
    current = outer_if

    while isinstance(current, ast.If):
        if current.orelse or len(current.body) != 1:
            return None

        conditions.append(current.test)
        child = current.body[0]

        if isinstance(child, ast.If):
            current = child
        else:
            return conditions, child

    return None


def is_assignment_guard_pattern(function):
    if len(function.body) != 3:
        return False

    initial, outer_if, final_return = function.body

    if not isinstance(initial, ast.Assign):
        return False

    if len(initial.targets) != 1:
        return False

    if not isinstance(initial.targets[0], ast.Name):
        return False

    if not isinstance(outer_if, ast.If):
        return False

    if not isinstance(final_return, ast.Return):
        return False

    target = initial.targets[0].id

    if not isinstance(final_return.value, ast.Name):
        return False

    if final_return.value.id != target:
        return False

    chain = inspect_nested_chain(outer_if)

    if chain is None:
        return False

    conditions, final_statement = chain

    return (
        len(conditions) >= 2
        and isinstance(final_statement, ast.Assign)
        and len(final_statement.targets) == 1
        and isinstance(final_statement.targets[0], ast.Name)
        and final_statement.targets[0].id == target
    )


def is_loop_continue_pattern(function):
    loops = [
        node for node in function.body
        if isinstance(node, ast.For)
    ]

    if len(loops) != 1:
        return False

    loop = loops[0]

    if len(loop.body) != 1 or not isinstance(loop.body[0], ast.If):
        return False

    chain = inspect_nested_chain(loop.body[0])

    if chain is None:
        return False

    conditions, final_statement = chain

    return (
        len(conditions) >= 2
        and isinstance(final_statement, (ast.AugAssign, ast.Assign))
    )


def is_existing_guard_pattern(function):
    if len(function.body) != 2:
        return False

    outer_if, fallback = function.body

    if not isinstance(outer_if, ast.If):
        return False

    if not isinstance(fallback, ast.Return):
        return False

    chain = inspect_nested_chain(outer_if)

    if chain is None:
        return False

    conditions, final_statement = chain

    return (
        len(conditions) >= 1
        and isinstance(final_statement, ast.Return)
    )


def classify_function(function):
    if is_assignment_guard_pattern(function):
        return (
            "replace_nested_assignment_with_guard",
            "Nested assignment can be converted into an early-return guard."
        )

    if is_loop_continue_pattern(function):
        return (
            "simplify_nested_conditions_in_loops",
            "Nested loop conditions can be simplified using continue."
        )

    if is_existing_guard_pattern(function):
        return (
            "replace_nested_conditions",
            "Supported nested-if return pattern found."
        )

    return (
        None,
        "Function structure is not supported by current transformations."
    )


def find_refactoring_candidates(report_path):
    report_path = Path(report_path)

    if not report_path.is_file():
        raise FileNotFoundError(report_path)

    with report_path.open(encoding="utf-8-sig") as file:
        report = json.load(file)

    if not isinstance(report, list):
        raise ValueError(
            "Expected smell report to contain a top-level list."
        )

    candidates = []

    for record in report:
        if not isinstance(record, dict):
            continue

        source_file = record.get("file")

        if not source_file:
            continue

        source_path = Path(source_file)

        if not source_path.is_file():
            continue

        source = source_path.read_text(encoding="utf-8-sig")
        smells = record.get("function_smells", [])

        for smell in smells:
            if smell.get("smell") != SUPPORTED_SMELL:
                continue

            function_name = smell.get("function")

            if not function_name:
                continue

            function = extract_function_node(
                source,
                function_name
            )

            if function is None:
                candidates.append({
                    "file": str(source_path),
                    "function": function_name,
                    "smell": SUPPORTED_SMELL,
                    "severity": smell.get("severity"),
                    "eligible": False,
                    "transformation": None,
                    "reason": "Function could not be uniquely identified."
                })
                continue

            transformation, reason = classify_function(function)

            candidates.append({
                "file": str(source_path),
                "function": function_name,
                "smell": SUPPORTED_SMELL,
                "severity": smell.get("severity"),
                "eligible": transformation is not None,
                "transformation": transformation,
                "reason": reason
            })

    return candidates


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="ACRR automatic refactoring candidate selector"
    )

    parser.add_argument(
        "--report",
        default="outputs/reports/smell_report.json"
    )

    args = parser.parse_args()

    candidates = find_refactoring_candidates(args.report)

    print("\nACRR AUTOMATIC REFACTORING SELECTION")
    print("------------------------------------")

    if not candidates:
        print("No matching code-smell candidates found.")
        return

    for candidate in candidates:
        print(f"\nFunction: {candidate['function']}")
        print(f"Smell: {candidate['smell']}")
        print(f"Severity: {candidate['severity']}")
        print(f"Eligible: {candidate['eligible']}")
        print(f"Transformation: {candidate['transformation']}")
        print(f"Reason: {candidate['reason']}")


if __name__ == "__main__":
    main()
