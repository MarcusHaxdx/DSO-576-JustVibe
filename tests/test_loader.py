import pandas as pd
import pytest

from analysis.loader import REQUIRED_COLUMNS, load_clean, make_case_id, message_body


def test_load_adds_case_id_and_keeps_columns(df):
    assert len(df) == 11
    assert list(df.columns) == REQUIRED_COLUMNS + ["case_id"]
    assert df["case_id"].is_unique and df["case_id"].str.len().eq(12).all()


def test_types_after_loading(df):
    assert pd.api.types.is_datetime64_any_dtype(df["report.filing-date"])
    assert pd.api.types.is_datetime64_any_dtype(df["period_start"])
    assert df["sign_flip"].dtype == bool
    assert df["entity.cik"].iloc[0] == "0000000001"           # leading zeros survive
    assert df["calculated_value"].isna().sum() == 5           # type 15 stays empty, never 0


def test_case_id_is_stable():
    assert make_case_id("acc", "code", "body") == make_case_id("acc", "code", "body")
    assert make_case_id("acc", "code", "body") != make_case_id("acc", "code", "other")


def test_message_body_drops_timestamp_and_code():
    assert message_body("2022-03-09 20:00:03,338 [DQC.US.0126.9590] The statement") == "The statement"


def test_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_clean(tmp_path / "nope.csv")


def test_missing_column_raises(clean_csv):
    pd.read_csv(clean_csv).drop(columns=["unit"]).to_csv(clean_csv, index=False)
    with pytest.raises(ValueError, match="unit"):
        load_clean(clean_csv)


def test_duplicate_row_key_raises(clean_csv):
    d = pd.read_csv(clean_csv)
    pd.concat([d, d.iloc[[0]]]).to_csv(clean_csv, index=False)
    with pytest.raises(ValueError, match="not unique"):
        load_clean(clean_csv)
