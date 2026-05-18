"""PCRDataLoader unit tests."""
import pandas as pd
import pytest

from pcr_diagnostic import PCRDataLoader


def test_load_sample_csv(sample_data_path):
    loader = PCRDataLoader(sample_data_path)
    data = loader.load_data()
    assert not data.empty
    assert {"sample_id", "gene", "ct_value"} <= set(data.columns)


def test_metadata_after_load(sample_data_path):
    loader = PCRDataLoader(sample_data_path)
    loader.load_data()
    md = loader.get_metadata()
    assert md["total_samples"] > 0
    assert "gene_A" in md["genes"]


def test_s011_group_corrected(sample_data_path):
    """Regression: row for S011 used to have group='gene_B'."""
    loader = PCRDataLoader(sample_data_path)
    data = loader.load_data()
    s011_groups = set(data.loc[data["sample_id"] == "S011", "group"].dropna().unique())
    assert s011_groups == {"control"}


def test_missing_file_raises(tmp_path):
    loader = PCRDataLoader(tmp_path / "does_not_exist.csv")
    with pytest.raises(FileNotFoundError):
        loader.load_data()


def test_missing_required_column(tmp_path):
    bad = tmp_path / "bad.csv"
    pd.DataFrame({"sample_id": ["A"], "gene": ["g"]}).to_csv(bad, index=False)
    loader = PCRDataLoader(bad)
    with pytest.raises(ValueError, match="필수 컬럼"):
        loader.load_data()


def test_unsupported_extension(tmp_path):
    bad = tmp_path / "bad.txt"
    bad.write_text("hello")
    loader = PCRDataLoader(bad)
    with pytest.raises(ValueError, match="지원하지 않는 파일 형식"):
        loader.load_data()


def test_calculate_mean_ct_default_group(synthetic_pcr_data, tmp_path):
    csv = tmp_path / "synth.csv"
    synthetic_pcr_data.to_csv(csv, index=False)
    loader = PCRDataLoader(csv)
    loader.load_data()
    mean_ct = loader.calculate_mean_ct()
    assert {"sample_id", "gene", "ct_mean", "ct_std", "n_replicates"} <= set(mean_ct.columns)
    assert (mean_ct["n_replicates"] == 3).all()


def test_calculate_mean_ct_does_not_mutate_default(synthetic_pcr_data, tmp_path):
    """Regression for mutable default argument anti-pattern."""
    csv = tmp_path / "synth.csv"
    synthetic_pcr_data.to_csv(csv, index=False)
    loader = PCRDataLoader(csv)
    loader.load_data()
    loader.calculate_mean_ct(group_by=["sample_id"])
    # second call without args should still default to ['sample_id', 'gene']
    second = loader.calculate_mean_ct()
    assert "gene" in second.columns


def test_filter_by_gene(synthetic_pcr_data, tmp_path):
    csv = tmp_path / "synth.csv"
    synthetic_pcr_data.to_csv(csv, index=False)
    loader = PCRDataLoader(csv)
    loader.load_data()
    only_a = loader.filter_by_gene("gene_A")
    assert set(only_a["gene"].unique()) == {"gene_A"}
