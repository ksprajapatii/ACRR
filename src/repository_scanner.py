import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from src.metrics_extractor import extract_metrics
from src.smell_detector import detect_smells


DEFAULT_EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    "build",
    "dist",
    ".idea",
    ".vscode",
}


def discover_python_files(root, excluded_dirs=None):
    """Discover Python files without entering excluded directories."""
    root = Path(root).resolve()

    if not root.exists():
        raise FileNotFoundError(f"Path does not exist: {root}")

    if root.is_file():
        if root.suffix.lower() != ".py":
            raise ValueError("The supplied file must have a .py extension.")
        return [root]

    excluded = DEFAULT_EXCLUDED_DIRS | set(excluded_dirs or set())
    files = []

    for directory, dirnames, filenames in __import__("os").walk(root):
        dirnames[:] = sorted(
            name for name in dirnames if name not in excluded
        )

        for filename in sorted(filenames):
            if filename.lower().endswith(".py"):
                files.append(Path(directory) / filename)

    return sorted(files)


def scan_repository(root, output_path=None, excluded_dirs=None):
    """Analyze all discovered Python files and produce a repository report."""
    root = Path(root).resolve()
    files = discover_python_files(root, excluded_dirs)

    file_results = []
    errors = []

    total_functions = 0
    total_classes = 0
    total_smells = 0

    smell_counts = Counter()
    severity_counts = Counter()

    for index, file_path in enumerate(files, start=1):
        print(
            f"[{index}/{len(files)}] Scanning: "
            f"{file_path.relative_to(root) if root.is_dir() else file_path.name}"
        )

        try:
            metrics = extract_metrics(file_path)
            analysis = detect_smells(file_path)

            source = file_path.read_text(encoding="utf-8-sig")
            import ast
            tree = ast.parse(source)

            classes = [
                node for node in ast.walk(tree)
                if isinstance(node, ast.ClassDef)
            ]

            smells = analysis["smells"]

            total_functions += len(metrics)
            total_classes += len(classes)
            total_smells += len(smells)

            for smell in smells:
                smell_counts[smell["smell"]] += 1
                severity_counts[smell["severity"]] += 1

            file_results.append({
                "file": str(file_path),
                "relative_path": (
                    str(file_path.relative_to(root))
                    if root.is_dir()
                    else file_path.name
                ),
                "status": "success",
                "functions_analyzed": len(metrics),
                "classes_analyzed": len(classes),
                "metrics": metrics,
                "smell_analysis": analysis,
            })

        except Exception as exc:
            errors.append({
                "file": str(file_path),
                "error_type": type(exc).__name__,
                "error": str(exc),
            })

            file_results.append({
                "file": str(file_path),
                "relative_path": (
                    str(file_path.relative_to(root))
                    if root.is_dir()
                    else file_path.name
                ),
                "status": "failed",
                "error_type": type(exc).__name__,
                "error": str(exc),
            })

            print(f"  ERROR: {type(exc).__name__}: {exc}")

    successful_files = len(file_results) - len(errors)

    report = {
        "tool": "ACRR Repository Scanner",
        "version": "1.1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repository": str(root),
        "summary": {
            "files_discovered": len(files),
            "files_scanned": successful_files,
            "files_failed": len(errors),
            "total_functions": total_functions,
            "total_classes": total_classes,
            "total_smells": total_smells,
            "smell_counts": dict(smell_counts.most_common()),
            "severity_counts": dict(severity_counts.most_common()),
        },
        "files": file_results,
        "errors": errors,
    }

    if output_path:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report, indent=4, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"\nReport saved: {output.resolve()}")

    print("\n========== ACRR REPOSITORY SCAN ==========")
    print(f"Files discovered : {len(files)}")
    print(f"Files scanned    : {successful_files}")
    print(f"Files failed     : {len(errors)}")
    print(f"Functions        : {total_functions}")
    print(f"Classes          : {total_classes}")
    print(f"Code smells      : {total_smells}")

    print("\nSmell distribution:")
    for name, count in smell_counts.most_common():
        print(f"  {name}: {count}")

    return report


def main():
    parser = argparse.ArgumentParser(
        description="ACRR Batch Repository Scanner"
    )

    parser.add_argument(
        "path",
        help="Python file or repository directory to scan",
    )

    parser.add_argument(
        "--output",
        default="outputs/reports/repository_scan.json",
        help="JSON report output path",
    )

    parser.add_argument(
        "--exclude",
        nargs="*",
        default=[],
        help="Additional directory names to exclude",
    )

    args = parser.parse_args()

    try:
        scan_repository(
            root=args.path,
            output_path=args.output,
            excluded_dirs=set(args.exclude),
        )
    except (FileNotFoundError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
