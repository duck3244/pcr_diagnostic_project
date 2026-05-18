"""로컬 파일시스템 기반 단순 저장소.

단일 사용자 MVP라 DB 없이 디렉토리만 사용한다.
"""
from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd


BACKEND_ROOT = Path(__file__).resolve().parent.parent
STORAGE_ROOT = BACKEND_ROOT / "storage"
DATASETS_DIR = STORAGE_ROOT / "datasets"
RUNS_DIR = STORAGE_ROOT / "runs"


def ensure_dirs() -> None:
    DATASETS_DIR.mkdir(parents=True, exist_ok=True)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class DatasetRecord:
    id: str
    filename: str
    uploaded_at: str
    n_rows: int
    n_samples: int
    n_genes: int
    groups: List[str]
    genes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "filename": self.filename,
            "uploaded_at": self.uploaded_at,
            "n_rows": self.n_rows,
            "n_samples": self.n_samples,
            "n_genes": self.n_genes,
            "groups": self.groups,
            "genes": self.genes,
        }


def _dataset_dir(dataset_id: str) -> Path:
    return DATASETS_DIR / dataset_id


def _meta_path(dataset_id: str) -> Path:
    return _dataset_dir(dataset_id) / "meta.json"


def _csv_path(dataset_id: str) -> Path:
    return _dataset_dir(dataset_id) / "data.csv"


def save_dataset(filename: str, contents: bytes) -> DatasetRecord:
    """업로드된 CSV bytes를 저장하고 메타데이터를 산출."""
    ensure_dirs()
    dataset_id = uuid.uuid4().hex[:12]
    dir_ = _dataset_dir(dataset_id)
    dir_.mkdir(parents=True, exist_ok=True)

    csv_path = _csv_path(dataset_id)
    csv_path.write_bytes(contents)

    # 검증 + 메타 수집
    df = pd.read_csv(csv_path)
    required = {"sample_id", "gene", "ct_value"}
    missing = required - set(df.columns)
    if missing:
        shutil.rmtree(dir_, ignore_errors=True)
        raise ValueError(f"필수 컬럼 누락: {sorted(missing)}")

    groups = (
        sorted(df["group"].dropna().astype(str).unique().tolist())
        if "group" in df.columns
        else []
    )
    genes = sorted(df["gene"].dropna().astype(str).unique().tolist())

    record = DatasetRecord(
        id=dataset_id,
        filename=filename,
        uploaded_at=datetime.now(timezone.utc).isoformat(),
        n_rows=int(len(df)),
        n_samples=int(df["sample_id"].nunique()),
        n_genes=int(df["gene"].nunique()),
        groups=groups,
        genes=genes,
    )
    _meta_path(dataset_id).write_text(json.dumps(record.to_dict(), ensure_ascii=False, indent=2))
    return record


def list_datasets() -> List[DatasetRecord]:
    ensure_dirs()
    records: List[DatasetRecord] = []
    for d in sorted(DATASETS_DIR.iterdir(), key=lambda p: p.name) if DATASETS_DIR.exists() else []:
        meta = d / "meta.json"
        if meta.exists():
            data = json.loads(meta.read_text())
            records.append(DatasetRecord(**data))
    records.sort(key=lambda r: r.uploaded_at, reverse=True)
    return records


def get_dataset(dataset_id: str) -> Optional[DatasetRecord]:
    meta = _meta_path(dataset_id)
    if not meta.exists():
        return None
    return DatasetRecord(**json.loads(meta.read_text()))


def load_dataset_df(dataset_id: str) -> pd.DataFrame:
    csv_path = _csv_path(dataset_id)
    if not csv_path.exists():
        raise FileNotFoundError(f"dataset {dataset_id} not found")
    return pd.read_csv(csv_path)


def delete_dataset(dataset_id: str) -> bool:
    dir_ = _dataset_dir(dataset_id)
    if not dir_.exists():
        return False
    shutil.rmtree(dir_)
    return True


def save_run(kind: str, payload: Dict[str, Any]) -> str:
    """ML/QC 등 분석 실행 결과를 runs/ 아래에 저장."""
    ensure_dirs()
    run_id = uuid.uuid4().hex[:12]
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "result.json").write_text(
        json.dumps({"kind": kind, "created_at": datetime.now(timezone.utc).isoformat(), **payload},
                   ensure_ascii=False, indent=2, default=str)
    )
    return run_id


def get_run(run_id: str) -> Optional[Dict[str, Any]]:
    p = RUNS_DIR / run_id / "result.json"
    if not p.exists():
        return None
    return json.loads(p.read_text())
