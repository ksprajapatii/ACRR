import csv
import math
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATASET_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "function_dataset.csv"
)

REQUIRED_COLUMNS = {
    "file_name",
    "file_path",
    "qualified_name",
    "start_line",
    "end_line",
    "function_name",
    "source_code",
    "loc",
    "cyclomatic_complexity",
    "nesting_depth",
    "maintainability_index",
    "smell_type",
    "severity",
    "detection_method",
    "smell_count",
}

VALID_SEVERITIES = {"Low", "Medium", "High", "None"}

NUMERIC_COLUMNS = [
    "loc",
    "cyclomatic_complexity",
    "nesting_depth",
    "maintainability_index",
    "smell_count",
]


def validate_dataset():

    errors = []
    warnings = []

    if not DATASET_FILE.exists():
        print("ERROR: Dataset file does not exist.")
        return False

    with DATASET_FILE.open(
        "r",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        reader = csv.DictReader(file)

        columns = set(reader.fieldnames or [])

        missing_columns = REQUIRED_COLUMNS - columns

        if missing_columns:
            errors.append(
                f"Missing columns: {sorted(missing_columns)}"
            )
            records = []
        else:
            records = list(reader)

    if not records:
        errors.append("Dataset is empty.")

    seen_records = set()

    for index, record in enumerate(records, start=2):

        row_errors = []

        for column in REQUIRED_COLUMNS:
            if not record.get(column, "").strip():
                row_errors.append(
                    f"{column} is empty"
                )

        if row_errors:
            errors.append(
                f"Row {index}: " + "; ".join(row_errors)
            )
            continue

        identity = (
            record["file_path"],
            record["qualified_name"],
            record["start_line"],
        )

        if identity in seen_records:
            warnings.append(
                f"Row {index}: Possible duplicate identity "
                f"{identity}"
            )

        seen_records.add(identity)

        # Validate numeric fields.
        numeric_values = {}

        for column in NUMERIC_COLUMNS:
            try:
                value = float(record[column])

                if not math.isfinite(value):
                    raise ValueError

                numeric_values[column] = value

            except ValueError:
                errors.append(
                    f"Row {index}: Invalid numeric value "
                    f"in {column}"
                )

        if len(numeric_values) == len(NUMERIC_COLUMNS):

            if any(
                numeric_values[column] < 0
                for column in NUMERIC_COLUMNS
            ):
                errors.append(
                    f"Row {index}: Negative metric detected"
                )

            if numeric_values["smell_count"] != int(
                numeric_values["smell_count"]
            ):
                errors.append(
                    f"Row {index}: smell_count must be an integer"
                )


            for column in ("start_line", "end_line"):
                if column in numeric_values:
                    if numeric_values[column] != int(numeric_values[column]):
                        errors.append(
                            f"Row {index}: {column} must be an integer"
                        )
        # Validate smell labels.
        smells = record["smell_type"].split("; ")
        severities = record["severity"].split("; ")

        if len(smells) != len(severities):
            errors.append(
                f"Row {index}: Smell and severity counts differ"
            )

        for severity in severities:
            if severity not in VALID_SEVERITIES:
                errors.append(
                    f"Row {index}: Invalid severity {severity}"
                )

        try:
            smell_count = int(record["smell_count"])
        except ValueError:
            continue

        if smell_count != len(smells) - (
            1 if smells == ["No Smell"] else 0
        ):
            errors.append(
                f"Row {index}: smell_count does not match labels"
            )

        if smell_count == 0 and (
            smells != ["No Smell"]
            or severities != ["None"]
        ):
            errors.append(
                f"Row {index}: Incorrect No Smell representation"
            )

        if smell_count > 0 and "No Smell" in smells:
            errors.append(
                f"Row {index}: No Smell cannot coexist "
                "with detected smells"
            )

    print("\nACRR DATASET VALIDATION")
    print("-----------------------")
    print("Records checked:", len(records))
    print("Errors:", len(errors))
    print("Warnings:", len(warnings))

    if errors:
        print("\nVALIDATION ERRORS")

        for error in errors:
            print("[ERROR]", error)

    if warnings:
        print("\nVALIDATION WARNINGS")

        for warning in warnings:
            print("[WARNING]", warning)

    if not errors:
        print("\nDataset validation: PASSED")
        return True

    print("\nDataset validation: FAILED")
    return False


if __name__ == "__main__":
    validate_dataset()

