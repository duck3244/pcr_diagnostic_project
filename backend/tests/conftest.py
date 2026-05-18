"""공통 pytest fixture 정의."""
from pathlib import Path

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_DATA_PATH = PROJECT_ROOT / "data" / "sample_pcr_data.csv"


@pytest.fixture(scope="session")
def sample_data_path() -> Path:
    return SAMPLE_DATA_PATH


@pytest.fixture(scope="session")
def sample_data(sample_data_path) -> pd.DataFrame:
    return pd.read_csv(sample_data_path)


@pytest.fixture
def synthetic_pcr_data() -> pd.DataFrame:
    """A small, deterministic PCR dataset used by unit tests."""
    rows = []
    # control: gene_A ~20, GAPDH ~16
    for sample in ["C1", "C2", "C3"]:
        for rep in (1, 2, 3):
            rows.append((sample, "gene_A", 20.0 + 0.1 * rep, "control", rep))
            rows.append((sample, "GAPDH", 16.0 + 0.05 * rep, "control", rep))
    # treatment: gene_A ~15 (upregulated), GAPDH ~16
    for sample in ["T1", "T2", "T3"]:
        for rep in (1, 2, 3):
            rows.append((sample, "gene_A", 15.0 + 0.1 * rep, "treatment", rep))
            rows.append((sample, "GAPDH", 16.0 + 0.05 * rep, "treatment", rep))
    return pd.DataFrame(rows, columns=["sample_id", "gene", "ct_value", "group", "replicate"])
