import json
from pathlib import Path

import pytest

from src.refactoring_runner import (
    run_refactoring,
    validate_functional_equivalence
)


ORIGINAL_CODE = """
def check_access(a, b, c):
    if a:
        if b:
            if c:
                return True
    return False
"""


def test_functional_equivalence_passes():
    result = validate_functional_equivalence(
        ORIGINAL_CODE,
        """
def check_access(a, b, c):
    if not a:
        return False
    if not b:
        return False
    if not c:
        return False
    return True
""",
        "check_access",
        [
            (True, True, True),
            (True, True, False),
            (True, False, True),
            (False, True, True),
            (False, False, False)
        ]
    )

    assert result["status"] == "passed"
    assert result["test_cases_passed"] == 5
    assert result["test_cases_failed"] == 0


def test_functional_equivalence_detects_mismatch():
    incorrect_code = """
def check_access(a, b, c):
    return True
"""

    result = validate_functional_equivalence(
        ORIGINAL_CODE,
        incorrect_code,
        "check_access",
        [(True, True, False)]
    )

    assert result["status"] == "failed"
    assert result["test_cases_failed"] == 1


def test_runner_creates_refactored_file(tmp_path):
    input_file = tmp_path / "original.py"
    output_file = tmp_path / "refactored.py"
    report_file = tmp_path / "report.json"

    input_file.write_text(
        ORIGINAL_CODE,
        encoding="utf-8"
    )

    original_content = input_file.read_text(
        encoding="utf-8"
    )

    run_refactoring(
        input_file,
        output_file,
        report_file,
        "check_access"
    )

    assert input_file.read_text(
        encoding="utf-8"
    ) == original_content

    assert output_file.exists()
    assert report_file.exists()

    report = json.loads(
        report_file.read_text(encoding="utf-8")
    )

    assert report["syntax_validation"] == "passed"
    assert report["functional_equivalence"]["status"] == "passed"
    assert report["original_source_modified"] is False


def test_runner_rejects_same_input_output_path(tmp_path):
    input_file = tmp_path / "original.py"

    input_file.write_text(
        ORIGINAL_CODE,
        encoding="utf-8"
    )

    with pytest.raises(ValueError):
        run_refactoring(
            input_file,
            input_file,
            tmp_path / "report.json",
            "check_access"
        )
