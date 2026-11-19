import ast
import copy


class RefactoringError(Exception):
    """Raised when a safe transformation cannot be applied."""


def _parse_source(source):
    try:
        return ast.parse(source)
    except SyntaxError as exc:
        raise RefactoringError(
            f"Invalid Python source: {exc}"
        ) from exc


def _find_function(tree, function_name):
    matches = [
        node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == function_name
    ]

    if len(matches) != 1:
        raise RefactoringError(
            f"Expected exactly one function named '{function_name}'."
        )

    return matches[0]


def _combine_conditions(conditions):
    return ast.BoolOp(
        op=ast.And(),
        values=[copy.deepcopy(condition) for condition in conditions]
    )


def _nested_if_chain(outer_if):
    """Return conditions and final statement of a simple nested-if chain."""
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


def replace_nested_conditions(source):
    """Transform a restricted nested-if return pattern into guard clauses."""
    tree = _parse_source(source)
    transformed = False

    class GuardClauseTransformer(ast.NodeTransformer):

        def visit_FunctionDef(self, node):
            nonlocal transformed
            self.generic_visit(node)

            if len(node.body) != 2:
                return node

            outer_if, fallback = node.body

            if not isinstance(outer_if, ast.If):
                return node

            if not isinstance(fallback, ast.Return):
                return node

            chain = _nested_if_chain(outer_if)

            if chain is None:
                return node

            conditions, final_statement = chain

            if not isinstance(final_statement, ast.Return):
                return node

            guard_statements = []

            for condition in conditions:
                guard_statements.append(
                    ast.If(
                        test=ast.UnaryOp(
                            op=ast.Not(),
                            operand=copy.deepcopy(condition)
                        ),
                        body=[
                            ast.Return(
                                value=copy.deepcopy(fallback.value)
                            )
                        ],
                        orelse=[]
                    )
                )

            guard_statements.append(final_statement)
            node.body = guard_statements
            transformed = True

            return node

    tree = GuardClauseTransformer().visit(tree)
    ast.fix_missing_locations(tree)

    if not transformed:
        raise RefactoringError(
            "No supported nested-if return pattern found. "
            "Original source remains unchanged."
        )

    return ast.unparse(tree)


def replace_nested_assignment_with_guard(source, function_name):
    """
    Transform a nested-if assignment into an early-return guard clause.

    Supported pattern:
        result = fallback
        if a:
            if b:
                result = expression
        return result
    """
    tree = _parse_source(source)
    function = _find_function(tree, function_name)

    if len(function.body) != 3:
        raise RefactoringError(
            "Expected an initial assignment, nested if, and return."
        )

    initial, outer_if, final_return = function.body

    if not isinstance(initial, ast.Assign):
        raise RefactoringError("Initial statement must be an assignment.")

    if len(initial.targets) != 1:
        raise RefactoringError("Multiple assignment targets are unsupported.")

    if not isinstance(initial.targets[0], ast.Name):
        raise RefactoringError("Initial assignment target must be a name.")

    if not isinstance(outer_if, ast.If):
        raise RefactoringError("Expected a nested if statement.")

    if not isinstance(final_return, ast.Return):
        raise RefactoringError("Expected a final return statement.")

    target_name = initial.targets[0].id

    if not isinstance(final_return.value, ast.Name):
        raise RefactoringError("Final return must return the assigned variable.")

    if final_return.value.id != target_name:
        raise RefactoringError("Assignment and return variables do not match.")

    chain = _nested_if_chain(outer_if)

    if chain is None:
        raise RefactoringError("Unsupported nested-if structure.")

    conditions, final_statement = chain

    if len(conditions) < 2:
        raise RefactoringError("At least two nested conditions are required.")

    if not isinstance(final_statement, ast.Assign):
        raise RefactoringError("Nested block must contain an assignment.")

    if (
        len(final_statement.targets) != 1
        or not isinstance(final_statement.targets[0], ast.Name)
        or final_statement.targets[0].id != target_name
    ):
        raise RefactoringError("Nested assignment target does not match.")

    guard = ast.If(
        test=ast.UnaryOp(
            op=ast.Not(),
            operand=_combine_conditions(conditions)
        ),
        body=[
            ast.Return(value=copy.deepcopy(initial.value))
        ],
        orelse=[]
    )

    early_return = ast.Return(
        value=copy.deepcopy(final_statement.value)
    )

    function.body = [
        copy.deepcopy(initial),
        guard,
        early_return
    ]

    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


def simplify_nested_conditions_in_loops(source, function_name):
    """
    Replace nested conditions inside a for-loop with a continue guard.

    Supported pattern:
        for item in items:
            if condition1:
                if condition2:
                    total += expression
    """
    tree = _parse_source(source)
    function = _find_function(tree, function_name)

    matching_loops = [
        node for node in function.body
        if isinstance(node, ast.For)
    ]

    if len(matching_loops) != 1:
        raise RefactoringError(
            "Expected exactly one top-level for-loop in the function."
        )

    loop = matching_loops[0]

    if len(loop.body) != 1 or not isinstance(loop.body[0], ast.If):
        raise RefactoringError(
            "Loop body must contain one nested-if chain."
        )

    chain = _nested_if_chain(loop.body[0])

    if chain is None:
        raise RefactoringError("Unsupported nested-if loop structure.")

    conditions, final_statement = chain

    if len(conditions) < 2:
        raise RefactoringError("At least two nested conditions are required.")

    if not isinstance(final_statement, (ast.AugAssign, ast.Assign)):
        raise RefactoringError(
            "Nested loop statement must be an assignment."
        )

    guard = ast.If(
        test=ast.UnaryOp(
            op=ast.Not(),
            operand=_combine_conditions(conditions)
        ),
        body=[ast.Continue()],
        orelse=[]
    )

    loop.body = [
        guard,
        copy.deepcopy(final_statement)
    ]

    ast.fix_missing_locations(tree)
    return ast.unparse(tree)
