from __future__ import annotations

import argparse
import time
from pathlib import Path
from sklearn.model_selection import train_test_split

try:
    from .dataset import load_dataset
    from .model import RetentionXGB
    from .evaluate import evaluate_model
except ImportError:
    from dataset import load_dataset
    from model import RetentionXGB
    from evaluate import evaluate_model


def train(csv_path: str | Path) -> RetentionXGB:
   
    X_train_full, X_test, y_train_full, y_test = load_dataset(csv_path)

    X_train, X_val, y_train, y_val = train_test_split(
        X_train_full, y_train_full, test_size=0.25, random_state=42
    )
    print(f"Train: {len(X_train)} | Val: {len(X_val)} | Test: {len(X_test)}")

    start = time.time()
    model = RetentionXGB()
    model.train(X_train, y_train, X_val=X_val, y_val=y_val)
    training_time = round(time.time() - start, 4)
    print(f"Training time: {training_time}s")

    print("\nEvaluating on held-out test set and saving artifacts...")
    evaluate_model(model, X_test, y_test, training_time_seconds=training_time)

    model.save()

    print("\nTraining complete.")
    return model


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Train the XGBoost retention risk model."
    )
    parser.add_argument(
        "--data",
        type=str,
        required=True,
        help="Path to synthetic_comprehension_dataset.csv",
    )
    args = parser.parse_args()
    train(args.data)