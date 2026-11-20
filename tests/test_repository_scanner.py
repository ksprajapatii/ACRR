import json

from src.repository_scanner import discover_python_files, scan_repository


def test_discover_python_files_ignores_virtual_environment(tmp_path):
    (tmp_path / "app.py").write_text("def hello():\n    return 'hello'\n")

    excluded = tmp_path / ".venv"
    excluded.mkdir()
    (excluded / "ignored.py").write_text("def ignored(): pass\n")

    files = discover_python_files(tmp_path)

    assert len(files) == 1
    assert files[0].name == "app.py"


def test_scan_repository_generates_report(tmp_path):
    source = tmp_path / "app.py"
    source.write_text(
        "def calculate(a, b):\n"
        "    if a:\n"
        "        if b:\n"
        "            return a + b\n"
        "    return 0\n"
    )

    output = tmp_path / "report.json"

    report = scan_repository(tmp_path, output_path=output)

    assert report["summary"]["files_discovered"] == 1
    assert report["summary"]["files_scanned"] == 1
    assert report["summary"]["files_failed"] == 0
    assert report["summary"]["total_functions"] == 1
    assert output.exists()

    saved_report = json.loads(output.read_text(encoding="utf-8"))
    assert saved_report["tool"] == "ACRR Repository Scanner"


def test_scan_continues_after_invalid_python_file(tmp_path):
    (tmp_path / "valid.py").write_text("def hello():\n    return 1\n")
    (tmp_path / "invalid.py").write_text("def broken(:\n")

    report = scan_repository(tmp_path)

    assert report["summary"]["files_discovered"] == 2
    assert report["summary"]["files_scanned"] == 1
    assert report["summary"]["files_failed"] == 1
    assert len(report["errors"]) == 1
