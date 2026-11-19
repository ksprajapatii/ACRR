import ast
import csv
import argparse
from pathlib import Path

from radon.complexity import cc_visit
from radon.metrics import mi_visit, mi_rank
from radon.raw import analyze


def calculate_nesting(node):

    class Visitor(ast.NodeVisitor):

        def __init__(self):
            self.depth = 0
            self.maximum = 0

        def visit_FunctionDef(self, node):
            return

        def visit_AsyncFunctionDef(self, node):
            return

        def visit_ClassDef(self, node):
            return

        def visit_branch(self, node):

            self.depth += 1
            self.maximum = max(self.maximum, self.depth)

            for child in node.body:
                self.visit(child)

            for child in getattr(node, "orelse", []):
                self.visit(child)

            self.depth -= 1

        visit_If = visit_branch
        visit_For = visit_branch
        visit_AsyncFor = visit_branch
        visit_While = visit_branch

    visitor = Visitor()

    for child in node.body:
        visitor.visit(child)

    return visitor.maximum


import ast


def extract_qualified_names(tree):
    qualified_names = {}

    class QualifiedNameVisitor(ast.NodeVisitor):
        def __init__(self):
            self.scope = []

        def visit_ClassDef(self, node):
            self.scope.append(node.name)
            self.generic_visit(node)
            self.scope.pop()

        def visit_FunctionDef(self, node):
            qualified_names[id(node)] = ".".join(self.scope + [node.name])
            self.scope.append(node.name)
            self.generic_visit(node)
            self.scope.pop()

        def visit_AsyncFunctionDef(self, node):
            qualified_names[id(node)] = ".".join(self.scope + [node.name])
            self.scope.append(node.name)
            self.generic_visit(node)
            self.scope.pop()

    visitor = QualifiedNameVisitor()
    visitor.visit(tree)

    return qualified_names


def extract_metrics(file_path):

    path = Path(file_path)

    source = path.read_text(encoding="utf-8-sig")

    tree = ast.parse(source)
    qualified_names = extract_qualified_names(tree)

    complexity_blocks = cc_visit(source)

    complexity_map = {
        (block.name, block.lineno): block.complexity
        for block in complexity_blocks
    }

    maintainability = mi_visit(source, multi=True)

    raw_metrics = analyze(source)

    records = []

    for node in ast.walk(tree):

        if not isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            continue

        start = node.lineno
        end = getattr(node, "end_lineno", start)

        positional = node.args.posonlyargs + node.args.args
        keyword_only = node.args.kwonlyargs

        parameters = len(positional) + len(keyword_only)

        complexity = complexity_map.get(
            (node.name, start), 1
        )

        calls = set()

        for item in ast.walk(node):

            if isinstance(item, ast.Call):

                if isinstance(item.func, ast.Name):
                    calls.add(item.func.id)

                elif isinstance(item.func, ast.Attribute):
                    calls.add(item.func.attr)

        conditionals = sum(
            isinstance(item, (ast.If, ast.IfExp, ast.Match))
            for item in ast.walk(node)
        )

        loops = sum(
            isinstance(item, (ast.For, ast.AsyncFor, ast.While))
            for item in ast.walk(node)
        )

        records.append({

            "file": str(path),
            "function": node.name,
                "qualified_name": qualified_names[id(node)],
            "start_line": start,
            "end_line": end,
            "loc": end - start + 1,
            "parameters": parameters,
            "cyclomatic_complexity": complexity,
            "branches": max(0, complexity - 1),
            "nesting_depth": calculate_nesting(node),
            "conditionals": conditionals,
            "loops": loops,
            "dependencies": len(calls),
            "function_calls": ", ".join(sorted(calls)),
            "maintainability_index": round(maintainability, 2),
            "maintainability_rank": mi_rank(maintainability),
            "file_sloc": raw_metrics.sloc,
            "file_comments": raw_metrics.comments

        })

    return records


def analyze_path(target):

    target = Path(target)

    excluded = {
        ".venv", "venv", "__pycache__", ".git",
        "build", "dist"
    }

    if target.is_file():

        if target.suffix != ".py":
            raise ValueError("Please provide a Python file.")

        files = [target]

    elif target.is_dir():

        files = [
            file for file in target.rglob("*.py")
            if not any(part in excluded for part in file.parts)
        ]

    else:
        raise FileNotFoundError(target)

    records = []

    for file in files:
        records.extend(extract_metrics(file))

    return records


def main():

    parser = argparse.ArgumentParser(
        description="ACRR Software Metrics Extractor"
    )

    parser.add_argument("path")

    parser.add_argument(
        "--output",
        default="outputs/metrics/software_metrics.csv"
    )

    args = parser.parse_args()

    records = analyze_path(args.path)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    if records:

        with output.open(
            "w", newline="", encoding="utf-8-sig"
        ) as csvfile:

            writer = csv.DictWriter(
                csvfile,
                fieldnames=list(records[0].keys())
            )

            writer.writeheader()
            writer.writerows(records)

    print("\nACRR SOFTWARE METRICS")
    print("---------------------")
    print("Functions analyzed:", len(records))
    print("Output:", output.resolve())

    for record in records:

        print(
            f'\nFunction: {record["function"]}'
            f'\nLOC: {record["loc"]}'
            f'\nComplexity: {record["cyclomatic_complexity"]}'
            f'\nParameters: {record["parameters"]}'
            f'\nNesting: {record["nesting_depth"]}'
            f'\nMaintainability Index: {record["maintainability_index"]}'
        )


if __name__ == "__main__":
    main()




