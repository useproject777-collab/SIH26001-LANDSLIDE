import json
from datetime import datetime
from pathlib import Path
from typing import Any

import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
import pandas as pd
from sqlalchemy import text

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "landslide_model.pkl"
META_PATH = BASE_DIR / "model_metadata.json"

FEATURES = ["rainfall_mm", "slope_degree"]
MIN_SAMPLES = 30


def get_dataset(db) -> pd.DataFrame:
    rows = db.execute(
        text(
            """
            SELECT rainfall_mm, slope_degree, landslide_occurred
            FROM historical_landslides
            WHERE rainfall_mm IS NOT NULL
              AND slope_degree IS NOT NULL
              AND landslide_occurred IS NOT NULL
            ORDER BY recorded_at
            """
        )
    ).mappings().all()
    return pd.DataFrame(rows)


def get_model_status(db) -> dict[str, Any]:
    df = get_dataset(db)
    metadata = {}
    if META_PATH.exists():
        try:
            metadata = json.loads(META_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            metadata = {}

    class_count = int(df["landslide_occurred"].nunique()) if not df.empty else 0
    return {
        "available": MODEL_PATH.exists(),
        "model_path": str(MODEL_PATH),
        "samples_available": int(len(df)),
        "classes_available": class_count,
        "minimum_samples": MIN_SAMPLES,
        "ready_for_training": len(df) >= MIN_SAMPLES and class_count == 2,
        "metadata": metadata,
        "warning": (
            "ML output is experimental until trained on sufficient, representative, validated historical landslide labels."
        ),
    }


def train_model(db) -> dict[str, Any]:
    df = get_dataset(db)
    if len(df) < MIN_SAMPLES:
        raise ValueError(
            f"Need at least {MIN_SAMPLES} labeled historical records; found {len(df)}."
        )
    if df["landslide_occurred"].nunique() != 2:
        raise ValueError("Training requires both positive and negative landslide labels.")

    X = df[FEATURES]
    y = df["landslide_occurred"].astype(int)

    test_size = 0.25 if len(df) >= 40 else 0.30
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=42,
        stratify=y,
    )

    model = RandomForestClassifier(
        n_estimators=300,
        random_state=42,
        class_weight="balanced",
        min_samples_leaf=2,
    )
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    probabilities = model.predict_proba(X_test)[:, 1]
    metrics = {
        "accuracy": round(accuracy_score(y_test, predictions), 4),
        "precision": round(precision_score(y_test, predictions, zero_division=0), 4),
        "recall": round(recall_score(y_test, predictions, zero_division=0), 4),
        "f1": round(f1_score(y_test, predictions, zero_division=0), 4),
        "roc_auc": round(roc_auc_score(y_test, probabilities), 4),
    }

    joblib.dump(model, MODEL_PATH)
    metadata = {
        "model_name": "RandomForest prototype",
        "model_version": "1.0",
        "features": FEATURES,
        "samples": len(df),
        "trained_at": datetime.utcnow().isoformat(),
        **metrics,
        "note": "Experimental model. Do not use metrics as operational validation without representative data.",
    }
    META_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    db.execute(
        text(
            """
            INSERT INTO model_runs
            (model_name, model_version, samples, accuracy, precision_score, recall, f1, roc_auc, artifact_path)
            VALUES
            (:model_name, :model_version, :samples, :accuracy, :precision_score, :recall, :f1, :roc_auc, :artifact_path)
            """
        ),
        {
            "model_name": metadata["model_name"],
            "model_version": metadata["model_version"],
            "samples": len(df),
            "accuracy": metrics["accuracy"],
            "precision_score": metrics["precision"],
            "recall": metrics["recall"],
            "f1": metrics["f1"],
            "roc_auc": metrics["roc_auc"],
            "artifact_path": str(MODEL_PATH),
        },
    )
    db.commit()
    return metadata


def predict_experimental(db, rainfall_mm: float, slope_degree: float) -> dict[str, Any]:
    if not MODEL_PATH.exists():
        return {"available": False}
    model = joblib.load(MODEL_PATH)
    frame = pd.DataFrame([[rainfall_mm, slope_degree]], columns=FEATURES)
    probability = float(model.predict_proba(frame)[0, 1])
    return {
        "available": True,
        "landslide_probability": round(probability, 4),
        "experimental": True,
    }
