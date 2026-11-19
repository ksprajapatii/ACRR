import csv
from pathlib import Path

from src.refactoring_evaluator import evaluate_code


def save_experiment_report(
    original,
    refactored,
    experiment_name="Guard Clause Refactoring"
):
    before = evaluate_code(original)
    after = evaluate_code(refactored)

    output_dir = Path("outputs/reports")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "refactoring_experiments.csv"

    metrics = [
        "cyclomatic_complexity",
        "lines_of_code",
        "nesting_depth",
        "maintainability_index"
    ]

    with output_file.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.writer(file)

        writer.writerow([
            "experiment_name",
            "metric",
            "before",
            "after",
            "change"
        ])

        for metric in metrics:
            old_value = before[metric]
            new_value = after[metric]

            writer.writerow([
                experiment_name,
                metric,
                old_value,
                new_value,
                round(new_value - old_value, 2)
            ])

    print("Experiment report saved successfully.")
    print(f"Output: {output_file.resolve()}")

    return output_file


if __name__ == "__main__":

    original_code = """
def check_access(a, b, c):
    if a:
        if b:
            if c:
                return True
    return False
"""

    from src.refactoring_engine import replace_nested_conditions

    refactored_code = replace_nested_conditions(original_code)

    save_experiment_report(
        original_code,
        refactored_code
    )
