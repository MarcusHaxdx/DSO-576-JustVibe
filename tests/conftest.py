"""Small hand-made clean dataset (11 rows, all 34 columns) with known answers.

These are test fixtures, not real data. The real-data checks live in test_real_data.py.
"""
import numpy as np
import pandas as pd
import pytest

from analysis.loader import REQUIRED_COLUMNS

# key, type, code, cik, name, filing_date, prefix, concept, period, unit, reported, calculated
ROWS = [
    ("a0", 126, "DQC.US.0126.9590", "0000000001", "ALPHA INC", "2022-03-09", "us-gaap", "OperatingCash", "2020-10-01 to 2021-09-30", "USD", -1313536.0, -1212736.0),
    ("a1", 126, "DQC.US.0126.9590", "0000000001", "ALPHA INC", "2022-03-09", "us-gaap", "FinancingCash", "2020-10-01 to 2021-09-30", "USD", 707500.0, -707500.0),
    ("b2", 126, "DQC.US.0126.9590", "0000000002", "BETA CORP", "2022-03-04", "nmrk", "NetIncomeAdj", "2021-01-01 to 2021-12-31", "USD", -300897000.0, 1655371000.0),
    ("b3", 117, "DQC.US.0117.9574", "0000000002", "BETA CORP", "2022-02-07", "us-gaap", "Revenues", "2020-10-01 to 2020-12-31", "USD", 255500000.0, 142400000.0),
    ("c4", 117, "DQC.US.0117.9574", "0000000003", "GAMMA LTD", "2023-02-01", "us-gaap", "Allowance", "2021-12-31", "USD", 19204000.0, -19204000.0),
    ("c5", 15, "DQC.US.0015.1964", "0000000003", "GAMMA LTD", "2023-02-01", "us-gaap", "PaymentsPPE", "2021-09-01 to 2021-11-30", "USD", -1284.0, np.nan),
    ("d6", 15, "DQC.US.0015.757", "0000000004", "DELTA SA", "2023-01-26", "us-gaap", "DiscountRate", "2023-01-01 to 2023-12-31", "pure", -0.0554, np.nan),
    ("d7", 15, "DQC.US.0015.757", "0000000004", "DELTA SA", "2023-01-26", "us-gaap", "DiscountRate", "2023-01-01 to 2023-12-31", "pure", -0.0557, np.nan),
    ("e8", 15, "DQC.US.0015.1964", "0000000005", "EPS CO", "2022-05-01", "us-gaap", "ShareValue", "2021-12-31", "shares", -5.0, np.nan),
    ("e9", 15, "DQC.US.0015.1964", "0000000005", "EPS CO", "2022-05-01", "srt", "AxisValue", "2021-12-31", "USD", -100.0, np.nan),
    ("a10", 126, "DQC.US.0126.9590", "0000000001", "ALPHA INC", "2022-03-09", "us-gaap", "ZeroReported", "2020-10-01 to 2021-09-30", "USD", 0.0, 50.0),
]


def build_clean_frame() -> pd.DataFrame:
    recs = []
    for i, (key, typ, code, cik, name, filed, prefix, concept, period, unit, rep, calc) in enumerate(ROWS):
        start, _, end = period.partition(" to ")
        period_start = pd.Timestamp(start) if end else pd.NaT
        period_end = pd.Timestamp(end if end else start)
        filing = pd.Timestamp(filed)
        rec = {c: "x" for c in REQUIRED_COLUMNS}
        rec.update({
            "assertion.code": code,
            "assertion.detail": f"2022-01-01 00:00:00,{i:03d} [{code}] message {key}",
            "assertion.run-date": filing, "assertion.severity": "ERROR", "assertion.source": "DQC",
            "assertion.type": typ, "entity.cik": cik, "entity.name": name,
            "report.accepted-timestamp": filing, "report.accession": f"{cik}-22-{i:06d}",
            "report.filing-date": filing, "report.filing-year": filing.year,
            "report.id": i, "report.sic-code": 1,
            "timestamp": pd.Timestamp("2022-01-01 00:00:00"), "concept_prefix": prefix, "concept": concept,
            "period": period, "unit": unit, "rule_element_id": np.nan if typ == 15 else "9590",
            "rule_version": "1.0 - x.htm 1", "comparison_type": "x",
            "reported_value": rep, "calculated_value": calc,
            "period_start": period_start, "period_end": period_end,
            "period_after_filing": bool(period_end > filing),
            "sign_flip": bool(pd.notna(calc) and rep != 0 and calc == -rep),
        })
        recs.append(rec)
    return pd.DataFrame(recs)[REQUIRED_COLUMNS]


@pytest.fixture
def clean_csv(tmp_path):
    path = tmp_path / "auditing_clean.csv"
    build_clean_frame().to_csv(path, index=False)
    return path


@pytest.fixture
def df(clean_csv):
    from analysis.loader import load_clean
    return load_clean(clean_csv)


def case_id(df, reported):
    """case_id of the one row whose reported_value is `reported`."""
    ids = df.loc[df["reported_value"] == reported, "case_id"]
    assert len(ids) == 1
    return ids.iloc[0]
