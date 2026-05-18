"""ΔΔCt 분석 엔드포인트."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api import storage
from api.routers.qc import _to_jsonable
from api.schemas import DDCTRequest
from pcr_diagnostic import DeltaDeltaCt


router = APIRouter(prefix="/api/quantification", tags=["quantification"])


@router.post("/ddct/{dataset_id}")
def run_ddct(dataset_id: str, request: DDCTRequest) -> dict:
    record = storage.get_dataset(dataset_id)
    if record is None:
        raise HTTPException(404, "Dataset not found")

    df = storage.load_dataset_df(dataset_id)
    if request.target_gene not in df["gene"].unique():
        raise HTTPException(422, f"target_gene '{request.target_gene}' not in dataset")
    if request.reference_gene not in df["gene"].unique():
        raise HTTPException(422, f"reference_gene '{request.reference_gene}' not in dataset")
    if "group" not in df.columns or request.control_group not in df["group"].unique():
        raise HTTPException(422, f"control_group '{request.control_group}' not in dataset")

    ddct = DeltaDeltaCt(df)
    try:
        results = ddct.calculate(
            target_gene=request.target_gene,
            reference_gene=request.reference_gene,
            control_group=request.control_group,
            treatment_groups=request.treatment_groups,
            efficiency_target=request.efficiency_target,
            efficiency_reference=request.efficiency_reference,
        )
    except Exception as e:
        raise HTTPException(500, f"ΔΔCt 분석 실패: {e}")

    # Strip non-serializable internal DataFrames
    payload = _to_jsonable({
        "dataset_id": dataset_id,
        "target_gene": results["target_gene"],
        "reference_gene": results["reference_gene"],
        "control_group": results["control_group"],
        "comparisons": results["comparisons"],
        "request": request.model_dump(),
    })
    run_id = storage.save_run("ddct", payload)
    return {"run_id": run_id, **payload}
