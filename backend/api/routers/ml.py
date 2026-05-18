"""ML 학습 엔드포인트."""
from __future__ import annotations

import numpy as np
from fastapi import APIRouter, HTTPException
from sklearn.model_selection import train_test_split
from starlette.concurrency import run_in_threadpool

from api import storage
from api.routers.qc import _to_jsonable
from api.schemas import MLTrainRequest
from pcr_diagnostic import PCRClassifier


router = APIRouter(prefix="/api/ml", tags=["ml"])


def _do_train(df, request: MLTrainRequest) -> dict:
    classifier = PCRClassifier(model_type=request.model_type, random_state=request.random_state)
    X, y = classifier.prepare_features(df, target_col=request.target_col)

    unique, counts = np.unique(y, return_counts=True)
    if len(unique) < 2:
        raise ValueError("분류할 클래스가 2개 이상 필요합니다.")

    min_per_class = counts.min()
    stratify = y if min_per_class >= 2 else None
    test_size = max(0.1, min(0.5, request.test_size))

    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=test_size,
        random_state=request.random_state,
        stratify=stratify,
    )
    train_result = classifier.train(X_train, y_train)
    metrics = classifier.evaluate(X_test, y_test)
    importance_df = classifier.get_feature_importance(top_n=15)

    labels = sorted(np.unique(y).tolist())

    return {
        "model_type": request.model_type,
        "target_col": request.target_col,
        "n_samples": int(len(y)),
        "n_features": int(X.shape[1]),
        "labels": labels,
        "class_counts": {str(cls): int(c) for cls, c in zip(unique.tolist(), counts.tolist())},
        "cv_mean": float(train_result["cv_mean"]),
        "cv_std": float(train_result["cv_std"]),
        "accuracy": float(metrics["accuracy"]),
        "precision": float(metrics["precision"]),
        "recall": float(metrics["recall"]),
        "f1_score": float(metrics["f1_score"]),
        "roc_auc": float(metrics["roc_auc"]) if "roc_auc" in metrics else None,
        "confusion_matrix": metrics["confusion_matrix"].tolist(),
        "feature_importance": (
            importance_df.to_dict(orient="records") if not importance_df.empty else []
        ),
    }


@router.post("/train/{dataset_id}")
async def train_model(dataset_id: str, request: MLTrainRequest) -> dict:
    record = storage.get_dataset(dataset_id)
    if record is None:
        raise HTTPException(404, "Dataset not found")

    df = storage.load_dataset_df(dataset_id)
    try:
        result = await run_in_threadpool(_do_train, df, request)
    except ValueError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        raise HTTPException(500, f"ML 학습 실패: {e}")

    payload = _to_jsonable({"dataset_id": dataset_id, **result, "request": request.model_dump()})
    run_id = storage.save_run("ml", payload)
    return {"run_id": run_id, **payload}
