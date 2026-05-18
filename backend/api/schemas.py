"""API request/response 모델."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DatasetSummary(BaseModel):
    id: str
    filename: str
    uploaded_at: str
    n_rows: int
    n_samples: int
    n_genes: int
    groups: List[str]
    genes: List[str]


class DatasetPreview(BaseModel):
    columns: List[str]
    rows: List[Dict[str, Any]]
    total_rows: int


class QCRequest(BaseModel):
    ct_threshold: float = 35.0
    reference_genes: List[str] = Field(default_factory=list)
    cv_threshold: float = 5.0
    outlier_method: str = "modified_zscore"


class DDCTRequest(BaseModel):
    target_gene: str
    reference_gene: str
    control_group: str
    treatment_groups: Optional[List[str]] = None
    efficiency_target: float = 2.0
    efficiency_reference: float = 2.0


class MLTrainRequest(BaseModel):
    model_type: str = "random_forest"
    target_col: str = "group"
    test_size: float = 0.3
    random_state: int = 42


class RunResponse(BaseModel):
    run_id: str
    kind: str
    created_at: str
    result: Dict[str, Any]
