from pathlib import Path

import pandas as pd
import pytest

from analysis.loader import COLUMNS, make_case_id

ROOT = Path(__file__).resolve().parents[1]
CLEAN_DQC = ROOT / "data" / "clean" / "auditing_clean.csv"
CLEAN_PUBLISHED = ROOT / "data" / "clean" / "published_auditing_results.csv"


def _case(i, **overrides):
    row = {c: "" for c in COLUMNS}
    row.update({
        "assertion.code": f"DQC.US.0126.{i}", "assertion.detail": f"detail {i}", "assertion.type": 126,
        "entity.cik": str(1000 + i % 3), "entity.name": f"Company {i % 3}", "report.accession": f"acc-{i % 4}",
        "report.filing-date": f"2023-0{1 + i % 9}-15", "report.filing-year": 2023, "concept_prefix": "us-gaap",
        "concept": "Assets", "period": "2022-01-01 to 2022-12-31", "unit": "USD",
        "reported_value": 100.0, "calculated_value": 90.0, "period_start": "2022-01-01",
        "period_end": "2022-12-31", "period_after_filing": False, "sign_flip": False,
    })
    row.update(overrides)
    return row


@pytest.fixture
def small_df():
    """Eight hand-made cases covering each flag and edge case."""
    rows = [
        _case(0),                                                             # rel 10%
        _case(1, reported_value=50.0, calculated_value=-50.0, sign_flip=True),  # rel 200%
        _case(2, reported_value=0.0, calculated_value=5.0),                   # no rel_diff
        _case(3, **{"assertion.type": 15, "assertion.code": "DQC.US.0015.1"},
              calculated_value=float("nan"), unit="shares", period="2022-12-31",
              period_start=pd.NA, period_end="2022-12-31"),
        _case(4, **{"assertion.type": 117, "report.filing-year": 2024}, concept_prefix="srt",
              reported_value=1000.0, calculated_value=999.0),                 # rel 0.1%
        _case(5, period_after_filing=True, reported_value=10.0, calculated_value=70.0),  # rel 600%
        _case(6, **{"entity.name": "Northrop GRUMMAN Corp", "entity.cik": "9999"}),
        _case(7, **{"assertion.type": 15, "assertion.code": "DQC.US.0015.2"},
              calculated_value=float("nan"), unit="USD"),
    ]
    df = pd.DataFrame(rows)
    df["period_start"] = df["period_start"].replace("", pd.NA)
    df.insert(0, "case_id", [make_case_id(a, c, d) for a, c, d in
                             zip(df["report.accession"], df["assertion.code"], df["assertion.detail"])])
    return df


@pytest.fixture(scope="session")
def real_df():
    from analysis.loader import load_clean
    if not CLEAN_DQC.exists():
        pytest.skip("Run python src/cleaning/clean_project_data.py first.")
    return load_clean(CLEAN_DQC)


@pytest.fixture(scope="session")
def real_published():
    from analysis.published import load_published
    if not CLEAN_PUBLISHED.exists():
        pytest.skip("Run python src/cleaning/clean_project_data.py first.")
    return load_published(CLEAN_PUBLISHED)
