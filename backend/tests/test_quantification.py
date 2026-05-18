"""DeltaDeltaCt unit tests."""
import numpy as np
import pandas as pd

from pcr_diagnostic import DeltaDeltaCt


def test_ddct_basic_upregulation(synthetic_pcr_data):
    ddct = DeltaDeltaCt(synthetic_pcr_data)
    results = ddct.calculate(
        target_gene="gene_A",
        reference_gene="GAPDH",
        control_group="control",
    )
    assert "treatment" in results["comparisons"]
    treatment = results["comparisons"]["treatment"]
    # gene_A goes from ~20 to ~15 in treatment → strong upregulation (fold change > 1)
    assert treatment["fold_change"] > 1
    assert treatment["delta_delta_ct"] < 0


def test_ddct_returns_log2_fold_change(synthetic_pcr_data):
    ddct = DeltaDeltaCt(synthetic_pcr_data)
    results = ddct.calculate(
        target_gene="gene_A",
        reference_gene="GAPDH",
        control_group="control",
    )
    t = results["comparisons"]["treatment"]
    assert np.isclose(t["log2_fold_change"], np.log2(t["fold_change"]))


def test_ddct_handles_single_sample_group():
    """ttest with one sample should not crash — but may yield nan."""
    rows = [
        ("C1", "gene_A", 20.0, "control", 1),
        ("C1", "GAPDH", 16.0, "control", 1),
        ("C2", "gene_A", 20.1, "control", 1),
        ("C2", "GAPDH", 16.1, "control", 1),
        ("T1", "gene_A", 15.0, "treatment", 1),
        ("T1", "GAPDH", 16.0, "treatment", 1),
    ]
    df = pd.DataFrame(rows, columns=["sample_id", "gene", "ct_value", "group", "replicate"])
    ddct = DeltaDeltaCt(df)
    results = ddct.calculate(
        target_gene="gene_A",
        reference_gene="GAPDH",
        control_group="control",
    )
    # treatment has 1 sample → calculation may include NaN, but must not crash
    assert "treatment" in results["comparisons"] or results["comparisons"] == {}


def test_ddct_export(synthetic_pcr_data, tmp_path):
    ddct = DeltaDeltaCt(synthetic_pcr_data)
    ddct.calculate(
        target_gene="gene_A",
        reference_gene="GAPDH",
        control_group="control",
    )
    out = tmp_path / "ddct.csv"
    ddct.export_results(str(out))
    assert out.exists()
    df = pd.read_csv(out)
    assert "fold_change" in df.columns
    assert len(df) >= 1
