import argparse
import json
from pathlib import Path

import joblib
import numpy as np

from src.metrics_extractor import extract_metrics


ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "outputs" / "models" / "acrr_random_forest.joblib"

FEATURES = [
    "loc",
    "cyclomatic_complexity",
    "nesting_depth",
    "maintainability_index",
]

TARGETS = [
    "target_long_method",
    "target_duplicate_code",
    "target_excessive_conditional_logic",
    "target_too_many_parameters",
    "target_deeply_nested_conditions",
    "target_high_cyclomatic_complexity",
]


def predict_file(file_path, threshold=0.5):
    file_path = Path(file_path).resolve()

    if not file_path.is_file():
        raise FileNotFoundError(f"Python file not found: {file_path}")

    if file_path.suffix.lower() != ".py":
        raise ValueError("Only Python (.py) files are supported.")

    if not MODEL_PATH.is_file():
        raise FileNotFoundError(f"Trained model not found: {MODEL_PATH}")

    model = joblib.load(MODEL_PATH)
    metrics = extract_metrics(file_path)

    if not metrics:
        return []

    X = np.array([
        [float(row.get(feature, 0) or 0) for feature in FEATURES]
        for row in metrics
    ], dtype=float)

    probabilities = model.predict_proba(X)
    predictions = model.predict(X)

    results = []

    for row_index, metric in enumerate(metrics):
        detected = []

        for target_index, target in enumerate(TARGETS):
            estimator = model.estimators_[target_index]
            classes = list(estimator.classes_)

            if 1 in classes:
                positive_index = classes.index(1)
                confidence = float(
                    probabilities[target_index][row_index][positive_index]
                )
            else:
                confidence = 0.0

            if confidence >= threshold:
                detected.append({
                    "smell": target.replace("target_", ""),
                    "confidence": round(confidence, 4),
                })

        results.append({
            "function": metric.get("function"),
            "qualified_name": metric.get("qualified_name"),
            "start_line": metric.get("start_line"),
            "end_line": metric.get("end_line"),
            "predicted_smells": detected,
        })

    return results


def main():
    parser = argparse.ArgumentParser(
        description="ACRR machine-learning code smell predictor"
    )
    parser.add_argument("file", help="Path to a Python source file")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Confidence threshold (default: 0.5)",
    )
    parser.add_argument(
        "--output",
        help="Optional JSON output path",
    )

    args = parser.parse_args()

    if not 0 <= args.threshold <= 1:
        parser.error("--threshold must be between 0 and 1")

    results = predict_file(args.file, args.threshold)

    # Apply the requested confidence threshold.
    for result in results:
        result["predicted_smells"] = [
            smell for smell in result["predicted_smells"]
            if smell["confidence"] >= args.threshold
        ]

    report = {
        "project": "ACRR",
        "analysis_type": "Machine Learning Prediction",
        "source_file": str(Path(args.file).resolve()),
        "confidence_threshold": args.threshold,
        "functions_analyzed": len(results),
        "functions_with_predicted_smells": sum(
            bool(item["predicted_smells"]) for item in results
        ),
        "results": results,
    }

    output = json.dumps(report, indent=4)

    if args.output:
        output_path = Path(args.output).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output, encoding="utf-8")
        print("Report saved:", output_path)

    print(output)


if __name__ == "__main__":
    main()

