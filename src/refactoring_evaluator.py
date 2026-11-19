import ast
from radon.complexity import cc_visit
from radon.metrics import mi_visit


def calculate_nesting(source):
    tree = ast.parse(source)
    maximum = 0

    class NestingVisitor(ast.NodeVisitor):
        def __init__(self):
            self.depth = 0

        def visit_If(self, node):
            nonlocal maximum
            self.depth += 1
            maximum = max(maximum, self.depth)
            self.generic_visit(node)
            self.depth -= 1

    NestingVisitor().visit(tree)
    return maximum


def count_source_lines(source):
    """Count non-empty, non-comment physical source lines."""
    return sum(
        1 for line in source.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )


def evaluate_code(source):
    """Evaluate metrics for an entire Python source file."""
    complexity_blocks = cc_visit(source)

    return {
        "cyclomatic_complexity": sum(
            block.complexity for block in complexity_blocks
        ),
        "lines_of_code": count_source_lines(source),
        "nesting_depth": calculate_nesting(source),
        "maintainability_index": round(
            mi_visit(source, multi=True), 2
        ),
    }


def extract_function_source(source, function_name):
    """
    Extract exactly one function or class method by name.

    Raises ValueError if the function is missing or ambiguous.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise ValueError(
            f"Invalid Python source: {exc}"
        ) from exc

    matches = [
        node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == function_name
    ]

    if len(matches) != 1:
        raise ValueError(
            f"Expected exactly one function named '{function_name}', "
            f"found {len(matches)}."
        )

    return ast.unparse(matches[0])


def evaluate_function(source, function_name):
    """Calculate quality metrics for one function or method."""
    function_source = extract_function_source(
        source,
        function_name
    )

    complexity_blocks = cc_visit(function_source)

    return {
        "cyclomatic_complexity": sum(
            block.complexity for block in complexity_blocks
        ),
        "lines_of_code": count_source_lines(function_source),
        "nesting_depth": calculate_nesting(function_source),
        "maintainability_index": round(
            mi_visit(function_source, multi=True), 2
        ),
    }


def compare_code(original, refactored):
    """Compare metrics for complete source files."""
    before = evaluate_code(original)
    after = evaluate_code(refactored)

    changes = {
        metric: round(after[metric] - before[metric], 2)
        for metric in before
    }

    print("\nACRR BEFORE-AND-AFTER EVALUATION")
    print("--------------------------------")

    for metric in before:
        print(f"\n{metric}")
        print(f"Before: {before[metric]}")
        print(f"After : {after[metric]}")
        print(f"Change: {changes[metric]}")

    return {
        "before": before,
        "after": after,
        "changes": changes
    }


def compare_functions(original, refactored, function_names):
    """
    Compare metrics independently for selected functions.

    Returns a dictionary containing before, after and change
    values for each function.
    """
    results = {}

    for function_name in function_names:
        before = evaluate_function(
            original,
            function_name
        )

        after = evaluate_function(
            refactored,
            function_name
        )

        changes = {
            metric: round(after[metric] - before[metric], 2)
            for metric in before
        }

        results[function_name] = {
            "before": before,
            "after": after,
            "changes": changes
        }

    return results
