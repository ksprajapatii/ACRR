import ast
import json
import argparse
from pathlib import Path


class PythonAnalyzer:

    def __init__(self, source, filename):
        self.source = source
        self.filename = filename
        self.tree = ast.parse(source)
        self.lines = source.splitlines()

    def analyze(self):

        functions = []
        classes = []

        for node in ast.walk(self.tree):

            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):

                positional = node.args.posonlyargs + node.args.args
                keyword = node.args.kwonlyargs

                functions.append({
                    "name": node.name,
                    "start_line": node.lineno,
                    "end_line": node.end_lineno,
                    "lines_of_code": node.end_lineno - node.lineno + 1,
                    "parameters": len(positional) + len(keyword),
                    "parameter_names": [
                        x.arg for x in positional + keyword
                    ],
                    "source": "\n".join(
                        self.lines[node.lineno - 1:node.end_lineno]
                    )
                })

            elif isinstance(node, ast.ClassDef):

                methods = [
                    x.name for x in node.body
                    if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef))
                ]

                classes.append({
                    "name": node.name,
                    "methods": methods,
                    "method_count": len(methods)
                })

        return {
            "file": self.filename,
            "total_functions": len(functions),
            "total_classes": len(classes),
            "functions": functions,
            "classes": classes
        }


def analyze_file(path):

    path = Path(path)

    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path.resolve()}")

    source = path.read_text(encoding="utf-8-sig")

    return PythonAnalyzer(source, str(path)).analyze()


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument("path")
    parser.add_argument("--output", default="outputs/analysis.json")

    args = parser.parse_args()

    path = Path(args.path)

    if path.is_dir():

        results = [
            analyze_file(file)
            for file in path.rglob("*.py")
            if not any(
                part in {".venv", "venv", "__pycache__", ".git"}
                for part in file.parts
            )
        ]

    else:
        results = [analyze_file(path)]

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    output.write_text(
        json.dumps(results, indent=4),
        encoding="utf-8"
    )

    print("\nACRR ANALYSIS COMPLETED")
    print("-----------------------")
    print("Files analyzed:", len(results))
    print("Functions found:", sum(x["total_functions"] for x in results))
    print("Classes found:", sum(x["total_classes"] for x in results))
    print("Output:", output.resolve())


if __name__ == "__main__":
    main()
