"""Dataset upload/list/preview/delete 엔드포인트."""
from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from api import storage
from api.schemas import DatasetPreview, DatasetSummary


router = APIRouter(prefix="/api/datasets", tags=["datasets"])


MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10MB


@router.post("", response_model=DatasetSummary, status_code=201)
async def upload_dataset(file: UploadFile = File(...)) -> DatasetSummary:
    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(400, "빈 파일입니다.")
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"파일이 너무 큽니다 (>{MAX_UPLOAD_BYTES} bytes).")
    filename = file.filename or "upload.csv"
    if not filename.lower().endswith(".csv"):
        raise HTTPException(415, "현재는 CSV 파일만 지원합니다.")

    try:
        record = storage.save_dataset(filename, contents)
    except ValueError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        raise HTTPException(500, f"저장 실패: {e}")

    return DatasetSummary(**record.to_dict())


@router.get("", response_model=list[DatasetSummary])
def list_datasets() -> list[DatasetSummary]:
    return [DatasetSummary(**r.to_dict()) for r in storage.list_datasets()]


@router.get("/{dataset_id}", response_model=DatasetSummary)
def get_dataset(dataset_id: str) -> DatasetSummary:
    record = storage.get_dataset(dataset_id)
    if record is None:
        raise HTTPException(404, "Dataset not found")
    return DatasetSummary(**record.to_dict())


@router.get("/{dataset_id}/preview", response_model=DatasetPreview)
def preview_dataset(dataset_id: str, n: int = Query(20, ge=1, le=500)) -> DatasetPreview:
    record = storage.get_dataset(dataset_id)
    if record is None:
        raise HTTPException(404, "Dataset not found")
    df = storage.load_dataset_df(dataset_id).head(n)
    # NaN을 None으로 변환하여 JSON 직렬화 가능하게 함
    rows = df.where(pd.notna(df), None).to_dict(orient="records")
    return DatasetPreview(
        columns=df.columns.tolist(),
        rows=rows,
        total_rows=record.n_rows,
    )


@router.delete("/{dataset_id}", status_code=204, response_model=None)
def delete_dataset(dataset_id: str):
    if not storage.delete_dataset(dataset_id):
        raise HTTPException(404, "Dataset not found")
