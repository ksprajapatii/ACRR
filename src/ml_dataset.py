import csv
import json
import math
import itertools
from collections import Counter, defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "function_dataset.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "ml"
)

TEST_SIZE = 0.20

FEATURE_COLUMNS = [
    "loc",
    "cyclomatic_complexity",
    "nesting_depth",
    "maintainability_index",
]

SMELL_LABELS = [
    "Long Method",
    "Duplicate Code",
    "Excessive Conditional Logic",
    "Too Many Parameters",
    "Deeply Nested Conditions",
    "High Cyclomatic Complexity",
]

TARGET_COLUMNS = [
    "target_" + label.lower().replace(" ", "_")
    for label in SMELL_LABELS
]

IDENTITY_COLUMNS = [
    "file_path",
    "qualified_name",
    "start_line",
    "end_line",
    "file_name",
    "function_name",
]

REQUIRED_COLUMNS = (
    IDENTITY_COLUMNS
    + FEATURE_COLUMNS
    + ["smell_type"]
)


def load_dataset():

    if not INPUT_FILE.exists():
        raise FileNotFoundError(INPUT_FILE)

    with INPUT_FILE.open(
        "r",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        reader = csv.DictReader(file)

        missing = set(REQUIRED_COLUMNS) - set(reader.fieldnames or [])

        if missing:
            raise ValueError(
                f"Missing dataset columns: {sorted(missing)}"
            )

        records = list(reader)

    if not records:
        raise ValueError("Input dataset is empty.")

    return records


def prepare_records(records):

    prepared = []

    for index, record in enumerate(records, start=2):

        row = {}

        for column in IDENTITY_COLUMNS:
            value = record.get(column, "").strip()

            if not value:
                raise ValueError(
                    f"Row {index}: {column} is empty."
                )

            row[column] = value

        for column in FEATURE_COLUMNS:

            try:
                value = float(record[column])
            except (ValueError, TypeError):
                raise ValueError(
                    f"Row {index}: Invalid {column}."
                )

            if not math.isfinite(value):
                raise ValueError(
                    f"Row {index}: Non-finite {column}."
                )

            row[column] = value

        labels = {
            label.strip()
            for label in record["smell_type"].split(";")
            if label.strip()
        }

        if "No Smell" in labels:
            labels.remove("No Smell")

        unknown = labels - set(SMELL_LABELS)

        if unknown:
            raise ValueError(
                f"Row {index}: Unknown smell labels: {sorted(unknown)}"
            )

        for label, target_column in zip(
            SMELL_LABELS,
            TARGET_COLUMNS
        ):
            row[target_column] = int(label in labels)

        prepared.append(row)

    return prepared


def select_test_files(records):

    groups = defaultdict(list)

    for record in records:
        groups[record["file_path"]].append(record)

    file_paths = sorted(groups)

    if len(file_paths) < 2:
        raise ValueError(
            "At least two source files are required for splitting."
        )

    test_group_count = max(
        1,
        round(len(file_paths) * TEST_SIZE)
    )

    test_group_count = min(
        test_group_count,
        len(file_paths) - 1
    )

    total_rows = len(records)
    target_rows = total_rows * TEST_SIZE

    total_label_counts = Counter()

    for record in records:
        for column in TARGET_COLUMNS:
            total_label_counts[column] += record[column]

    best_groups = None
    best_score = float("inf")

    for candidate in itertools.combinations(
        file_paths,
        test_group_count
    ):

        candidate_rows = [
            row
            for file_path in candidate
            for row in groups[file_path]
        ]

        row_error = (
            abs(len(candidate_rows) - target_rows)
            / max(target_rows, 1)
        )

        label_errors = []

        for column in TARGET_COLUMNS:

            total = total_label_counts[column]

            if total == 0:
                continue

            candidate_count = sum(
                row[column] for row in candidate_rows
            )

            observed_ratio = candidate_count / total

            label_errors.append(
                abs(observed_ratio - TEST_SIZE)
            )

        label_error = (
            sum(label_errors) / len(label_errors)
            if label_errors else 0
        )

        score = row_error + (0.5 * label_error)

        if score < best_score:
            best_score = score
            best_groups = candidate

    return set(best_groups), groups


def write_csv(path, records):

    fieldnames = (
        IDENTITY_COLUMNS
        + FEATURE_COLUMNS
        + TARGET_COLUMNS
    )

    with path.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(records)


def build_ml_dataset():

    original = load_dataset()
    records = prepare_records(original)

    test_files, groups = select_test_files(records)

    train_records = [
        row for row in records
        if row["file_path"] not in test_files
    ]

    test_records = [
        row for row in records
        if row["file_path"] in test_files
    ]

    if not train_records or not test_records:
        raise ValueError("Training or testing split is empty.")

    train_files = {
        row["file_path"] for row in train_records
    }

    actual_test_files = {
        row["file_path"] for row in test_records
    }

    overlap = train_files & actual_test_files

    if overlap:
        raise RuntimeError(
            f"Data leakage detected: {sorted(overlap)}"
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    write_csv(
        OUTPUT_DIR / "train.csv",
        train_records
    )

    write_csv(
        OUTPUT_DIR / "test.csv",
        test_records
    )

    report = {
        "input_records": len(records),
        "training_records": len(train_records),
        "testing_records": len(test_records),
        "training_files": sorted(train_files),
        "testing_files": sorted(actual_test_files),
        "file_overlap": sorted(overlap),
        "test_fraction": len(test_records) / len(records),
        "feature_columns": FEATURE_COLUMNS,
        "target_columns": TARGET_COLUMNS,
        "training_label_counts": {},
        "testing_label_counts": {},
    }

    for column in TARGET_COLUMNS:

        report["training_label_counts"][column] = sum(
            row[column] for row in train_records
        )

        report["testing_label_counts"][column] = sum(
            row[column] for row in test_records
        )

    report_path = OUTPUT_DIR / "split_report.json"

    report_path.write_text(
        json.dumps(report, indent=4),
        encoding="utf-8"
    )

    print("\nACRR ML DATASET PREPARATION")
    print("---------------------------")
    print("Total functions:", len(records))
    print("Training functions:", len(train_records))
    print("Testing functions:", len(test_records))
    print("Total source files:", len(groups))
    print("Training files:", len(train_files))
    print("Testing files:", len(actual_test_files))
    print("File overlap:", len(overlap))

    print("\nTEST FILES")

    for file_path in sorted(actual_test_files):
        print("-", file_path)

    print("\nTRAINING LABEL COUNTS")

    for column, count in report["training_label_counts"].items():
        print(f"{column}: {count}")

    print("\nTESTING LABEL COUNTS")

    for column, count in report["testing_label_counts"].items():
        print(f"{column}: {count}")

    print("\nOutput directory:", OUTPUT_DIR)
    print("Split report:", report_path)


if __name__ == "__main__":
    build_ml_dataset()
