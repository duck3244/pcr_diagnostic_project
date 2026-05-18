"""QualityControl unit tests."""
import numpy as np
import pandas as pd
import pytest

from pcr_diagnostic import QualityControl


def test_ct_range_pass(synthetic_pcr_data):
    qc = QualityControl(synthetic_pcr_data)
    result = qc.check_ct_range(threshold=35.0)
    assert bool(result["pass"]) is True
    assert result["above_threshold"] == 0


def test_ct_range_fail():
    df = pd.DataFrame({
        "sample_id": ["A", "B"],
        "gene": ["g", "g"],
        "ct_value": [25.0, 40.0],
        "group": ["x", "y"],
    })
    qc = QualityControl(df)
    result = qc.check_ct_range(threshold=35.0)
    assert bool(result["pass"]) is False
    assert result["above_threshold"] == 1


def test_ntc_check_no_amplification():
    df = pd.DataFrame({
        "sample_id": ["NTC_1", "S001"],
        "gene": ["g", "g"],
        "ct_value": [np.nan, 22.0],
        "group": ["ntc", "control"],
    })
    qc = QualityControl(df)
    result = qc.check_ntc()
    assert bool(result["pass"]) is True
    assert result["ntc_count"] == 1
    assert result["amplified_count"] == 0


def test_ntc_check_contamination():
    df = pd.DataFrame({
        "sample_id": ["NTC_1"],
        "gene": ["g"],
        "ct_value": [30.0],
        "group": ["ntc"],
    })
    qc = QualityControl(df)
    result = qc.check_ntc()
    assert bool(result["pass"]) is False
    assert result["amplified_count"] == 1


def test_reproducibility_low_cv(synthetic_pcr_data):
    qc = QualityControl(synthetic_pcr_data)
    result = qc.check_reproducibility(cv_threshold=5.0)
    assert result["high_cv_count"] == 0


def test_detect_outliers_modified_zscore_finds_obvious_outlier():
    rows = []
    for rep in range(1, 11):
        rows.append(("S1", "g", 20.0 + 0.01 * rep, "x", rep))
    rows.append(("S1", "g", 35.0, "x", 11))  # obvious outlier
    df = pd.DataFrame(rows, columns=["sample_id", "gene", "ct_value", "group", "replicate"])
    qc = QualityControl(df)
    outliers = qc.detect_outliers(method="modified_zscore")
    assert len(outliers) == 1
    assert outliers.iloc[0]["ct_value"] == 35.0


def test_detect_outliers_handles_nan():
    """Regression: outlier index mapping with NaN values."""
    rows = [
        ("S1", "g", np.nan, "x", 1),
        ("S1", "g", 20.0, "x", 2),
        ("S1", "g", 20.01, "x", 3),
        ("S1", "g", 20.02, "x", 4),
        ("S1", "g", 20.03, "x", 5),
        ("S1", "g", 20.04, "x", 6),
        ("S1", "g", 35.0, "x", 7),  # outlier
    ]
    df = pd.DataFrame(rows, columns=["sample_id", "gene", "ct_value", "group", "replicate"])
    qc = QualityControl(df)
    outliers = qc.detect_outliers(method="modified_zscore")
    assert len(outliers) == 1
    original_idx = int(outliers.iloc[0]["index"])
    assert df.loc[original_idx, "ct_value"] == 35.0


def test_detect_outliers_invalid_method():
    df = pd.DataFrame({
        "sample_id": ["S1"] * 4,
        "gene": ["g"] * 4,
        "ct_value": [20.0, 20.1, 20.2, 20.3],
        "group": ["x"] * 4,
    })
    qc = QualityControl(df)
    with pytest.raises(ValueError, match="지원하지 않는 method"):
        qc.detect_outliers(method="bogus")


def test_estimate_efficiency_skips_non_serial_dilution():
    """Reference gene with constant concentration must not produce bogus efficiency."""
    rows = []
    for sample, conc in [("S1", 100), ("S2", 100), ("S3", 100)]:
        for rep in (1, 2, 3):
            rows.append((sample, "GAPDH", 16.0 + 0.01 * rep, "control", rep, conc))
    df = pd.DataFrame(rows, columns=["sample_id", "gene", "ct_value", "group", "replicate", "concentration"])
    qc = QualityControl(df)
    eff = qc.estimate_efficiency()
    assert eff["GAPDH"] is None  # only one concentration level


def test_estimate_efficiency_with_serial_dilution():
    rows = []
    # serial dilution: at 10x dilution, ideal slope = -3.32 → 100% efficiency
    for conc in [1000, 100, 10, 1]:
        ct = 15.0 - 3.32 * np.log10(conc / 1000.0)
        for rep in (1, 2, 3):
            rows.append(("S", "gene_A", ct + 0.01 * rep, "control", rep, conc))
    df = pd.DataFrame(rows, columns=["sample_id", "gene", "ct_value", "group", "replicate", "concentration"])
    qc = QualityControl(df)
    eff = qc.estimate_efficiency()
    assert eff["gene_A"] is not None
    assert 90 <= eff["gene_A"]["efficiency"] <= 110


def test_estimate_efficiency_exclude_reference_gene():
    rows = []
    for conc in [1000, 100, 10]:
        ct = 15.0 - 3.32 * np.log10(conc / 1000.0)
        rows.append(("S", "gene_A", ct, "control", 1, conc))
        rows.append(("S", "GAPDH", 16.0, "control", 1, conc))
    df = pd.DataFrame(rows, columns=["sample_id", "gene", "ct_value", "group", "replicate", "concentration"])
    qc = QualityControl(df)
    eff = qc.estimate_efficiency(exclude_genes=["GAPDH"])
    assert eff["GAPDH"] is None
    assert eff["gene_A"] is not None
