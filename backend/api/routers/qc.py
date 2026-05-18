"""QC 분석 엔드포인트."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException

from api import storage
from api.schemas import QCRequest
from pcr_diagnostic import QualityControl


def _to_jsonable(obj: Any) -> Any:
    """numpy/pandas 스칼라를 표준 Python 타입으로 변환."""
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(v) for v in obj]
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        f = float(obj)
        return f if not np.isnan(f) else None
    if isinstance(obj, np.ndarray):
        return _to_jsonable(obj.tolist())
    if isinstance(obj, pd.DataFrame):
        return _to_jsonable(obj.where(pd.notna(obj), None).to_dict(orient="records"))
    if isinstance(obj, float) and np.isnan(obj):
        return None
    return obj


router = APIRouter(prefix="/api/qc", tags=["qc"])


def _boxplot_data(df: pd.DataFrame) -> list[dict]:
    """Per-gene Ct values, suitable for plotly boxplot."""
    valid = df.dropna(subset=["ct_value"])
    out = []
    for gene, sub in valid.groupby("gene"):
        out.append({"gene": str(gene), "ct_values": sub["ct_value"].tolist()})
    return out


@router.post("/{dataset_id}")
def run_qc(dataset_id: str, request: QCRequest) -> dict:
    record = storage.get_dataset(dataset_id)
    if record is None:
        raise HTTPException(404, "Dataset not found")

    df = storage.load_dataset_df(dataset_id)
    qc = QualityControl(df)

    ct_check = qc.check_ct_range(threshold=request.ct_threshold)
    ntc_check = qc.check_ntc()
    reproducibility = qc.check_reproducibility(cv_threshold=request.cv_threshold)
    outliers = qc.detect_outliers(method=request.outlier_method)
    efficiency = (
        qc.estimate_efficiency(exclude_genes=request.reference_genes)
        if "concentration" in df.columns else {}
    )

    payload = _to_jsonable({
        "dataset_id": dataset_id,
        "ct_check": ct_check,
        "ntc_check": ntc_check,
        "reproducibility": reproducibility,
        "outliers": outliers if not outliers.empty else [],
        "efficiency": efficiency,
        "boxplot": _boxplot_data(df),
        "request": request.model_dump(),
    })
    run_id = storage.save_run("qc", payload)
    return {"run_id": run_id, **payload}
