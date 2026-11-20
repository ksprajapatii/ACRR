import argparse
import ast
import io
import json
import textwrap
import tokenize
from datetime import datetime, timezone
from pathlib import Path

from radon.metrics import h_visit

from src.metrics_extractor import extract_qualified_names


def halstead_to_dict(report):
    """Convert Radon's HalsteadReport into a JSON-compatible dictionary."""
    return {
        field: getattr(report, field)
        for field in report._fields
    }


class FunctionStructureVisitor(ast.NodeVisitor):
    """Count structural constructs without entering nested scopes."""

    def __init__(self):
        self.counts = {
            "return_count": 0,
            "raise_count": 0,
            "yield_count": 0,
            "await_count": 0,
            "assert_count": 0,
            "exception_handler_count": 0,
            "comprehension_count": 0,
            "boolean_operation_count": 0,
            "branch_points": 0,
            "nested_function_count": 0,
            "nested_class_count": 0,
        }

    def visit_FunctionDef(self, node):
        self.counts["nested_function_count"] += 1

    def visit_AsyncFunctionDef(self, node):
        self.counts["nested_function_count"] += 1

    def visit_ClassDef(self, node):
        self.counts["nested_class_count"] += 1

    def visit_Lambda(self, node):
        # Do not count constructs inside a nested lambda.
        return

    def visit_Return(self, node):
        self.counts["return_count"] += 1
        self.generic_visit(node)

    def visit_Raise(self, node):
        self.counts["raise_count"] += 1
        self.generic_visit(node)

    def visit_Yield(self, node):
        self.counts["yield_count"] += 1
        self.generic_visit(node)

    def visit_YieldFrom(self, node):
        self.counts["yield_count"] += 1
        self.generic_visit(node)

    def visit_Await(self, node):
        self.counts["await_count"] += 1
        self.generic_visit(node)

    def visit_Assert(self, node):
        self.counts["assert_count"] += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        self.counts["exception_handler_count"] += 1
        self.generic_visit(node)

    def visit_ListComp(self, node):
        self.counts["comprehension_count"] += 1
        self.generic_visit(node)

    def visit_SetComp(self, node):
        self.counts["comprehension_count"] += 1
        self.generic_visit(node)

    def visit_DictComp(self, node):
        self.counts["comprehension_count"] += 1
        self.generic_visit(node)

    def visit_GeneratorExp(self, node):
        self.counts["comprehension_count"] += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node):
        self.counts["boolean_operation_count"] += 1
        self.generic_visit(node)

    def visit_If(self, node):
        self.counts["branch_points"] += 1
        self.generic_visit(node)

    def visit_IfExp(self, node):
        self.counts["branch_points"] += 1
        self.generic_visit(node)

    def visit_For(self, node):
        self.counts["branch_points"] += 1
        self.generic_visit(node)

    def visit_AsyncFor(self, node):
        self.counts["branch_points"] += 1
        self.generic_visit(node)

    def visit_While(self, node):
        self.counts["branch_points"] += 1
        self.generic_visit(node)

    def visit_Match(self, node):
        self.counts["branch_points"] += 1
        self.generic_visit(node)


def count_comment_lines(source):
    """Return unique source lines containing Python comments."""
    comment_lines = set()

    tokens = tokenize.generate_tokens(io.StringIO(source).readline)

    for token in tokens:
        if token.type == tokenize.COMMENT:
            comment_lines.add(token.start[0])

    return comment_lines


def analyze_advanced_metrics(file_path):
    """Extract file-level and function-level advanced metrics."""
    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    if path.suffix.lower() != ".py":
        raise ValueError("Advanced metrics require a Python file.")

    source = path.read_text(encoding="utf-8-sig")
    tree = ast.parse(source, filename=str(path))
    lines = source.splitlines()

    physical_loc = len(lines)
    nonblank_loc = sum(bool(line.strip()) for line in lines)

    comment_lines = count_comment_lines(source)
    comment_count = len(comment_lines)

    file_halstead = halstead_to_dict(h_visit(source).total)

    file_metrics = {
        "physical_loc": physical_loc,
        "nonblank_loc": nonblank_loc,
        "comment_lines": comment_count,
        "comment_density_percent": round(
            comment_count / physical_loc * 100, 2
        ) if physical_loc else 0.0,
        "halstead": file_halstead,
    }

    qualified_names = extract_qualified_names(tree)
    function_metrics = []

    function_nodes = [
        node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]

    for node in sorted(
        function_nodes,
        key=lambda item: (item.lineno, item.col_offset),
    ):
        end_line = getattr(node, "end_lineno", node.lineno)
        function_source = ast.get_source_segment(source, node) or ""

        visitor = FunctionStructureVisitor()

        for child in node.body:
            visitor.visit(child)

        function_comment_count = sum(
            node.lineno <= line <= end_line
            for line in comment_lines
        )

        function_loc = end_line - node.lineno + 1

        dedented_source = textwrap.dedent(function_source)

        function_halstead = halstead_to_dict(
            h_visit(dedented_source).total
        )

        function_metrics.append({
            "function": node.name,
            "qualified_name": qualified_names.get(id(node), node.name),
            "start_line": node.lineno,
            "end_line": end_line,
            "function_loc": function_loc,
            "comment_lines": function_comment_count,
            "comment_density_percent": round(
                function_comment_count / function_loc * 100, 2
            ) if function_loc else 0.0,
            "structural_metrics": visitor.counts,
            "halstead": function_halstead,
        })

    return {
        "file": str(path),
        "file_metrics": file_metrics,
        "total_functions": len(function_metrics),
        "functions": function_metrics,
    }


def main():
    parser = argparse.ArgumentParser(
        description="ACRR Advanced Code Metrics Analyzer"
    )

    parser.add_argument("path", help="Python source file")
    parser.add_argument(
        "--output",
        default="outputs/reports/advanced_metrics.json",
        help="JSON output path",
    )

    args = parser.parse_args()

    result = analyze_advanced_metrics(args.path)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "tool": "ACRR Advanced Metrics",
        "version": "1.1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        **result,
    }

    output.write_text(
        json.dumps(report, indent=4, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\n========== ACRR ADVANCED METRICS ==========")
    print("File:", result["file"])
    print("Functions:", result["total_functions"])
    print("Physical LOC:", result["file_metrics"]["physical_loc"])
    print("Comment density:",
          result["file_metrics"]["comment_density_percent"], "%")
    print("Halstead volume:",
          result["file_metrics"]["halstead"]["volume"])
    print("Report:", output.resolve())


if __name__ == "__main__":
    main()
