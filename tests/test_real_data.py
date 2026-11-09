"""Acceptance checks from BUILD_SPEC section 10, on the real clean file.

Skipped until data/clean/auditing_clean.csv exists.
"""
from pathlib import Path

import pytest

from analysis import metrics
from analysis.filters import FilterSpec, apply_filters
from analysis.loader import REQUIRED_COLUMNS, load_clean
from analysis.triage import TriageConfig, rank_cases

REAL = Path("data/clean/auditing_clean.csv")
pytestmark = pytest.mark.skipif(not REAL.exists(), reason="data/clean/auditing_clean.csv not found")


@pytest.fixture(scope="module")
def real():
    return load_clean(REAL)


def test_1_loader(real):
    assert len(real) == 362 and len(REQUIRED_COLUMNS) == 34
    assert set(real.columns) == set(REQUIRED_COLUMNS) | {"case_id"}
    assert real["case_id"].is_unique


def test_overview_kpis(real):
    assert metrics.kpis(real) == {"cases": 362, "filings": 158, "companies": 125, "rule_types": 3}


def test_3_discrepancy_coverage(real):
    s = metrics.discrepancy_summary(real)
    d = metrics.discrepancy(real)
    assert s["cases"] == 246 and d["rel_diff"].notna().sum() == 231     # 15 comparison rows have reported_value 0


def test_3_histogram_caption(real):
    c = metrics.histogram_counts(real, 5.0)
    assert c == {"comparison_cases": 246, "with_rel": 231, "without_rel": 15, "drawn": 208, "above": 23}


def test_2_counts_by_type(real):
    out = metrics.cases_by_type(real)
    assert dict(zip(out["assertion.type"], out["cases"])) == {15: 116, 117: 136, 126: 110}


def test_3_flags(real):
    s = metrics.flag_summary(real)
    assert s["sign_flip"] == 9 and s["period_after_filing"] == 2
    assert s["rows_with_calculated"] == 246
    assert s["sign_flip_rate"] == pytest.approx(9 / 246)
    assert s["non_usd"] == 32 and s["non_us_gaap_prefix"] == 12


def test_4_filter_type_126(real):
    assert len(apply_filters(real, FilterSpec(assertion_types=(126,)))) == 110


def test_5_discrepancy(real):
    d = metrics.discrepancy(real)
    row = d[(d["reported_value"] == -1313536) & (d["calculated_value"] == -1212736)]
    assert len(row) >= 1
    assert (row["abs_diff"] == 100800).all()
    assert row["rel_diff"].tolist() == pytest.approx([0.0767] * len(row), abs=1e-4)
    flips = d[d["sign_flip"]]
    assert len(flips) == 9 and flips["rel_diff"].notna().all()
    assert flips["rel_diff"].tolist() == pytest.approx([2.0] * 9)


def test_6_units_never_mixed(real):
    d = metrics.discrepancy(real)
    non_usd = d[d["unit"] != "USD"]
    assert len(non_usd) == 32 and non_usd["calculated_value"].isna().all()
    assert non_usd["abs_diff"].isna().all()
    assert (real.loc[real["assertion.type"] == 15, "calculated_value"].isna()).all()   # never 0


def test_7_triage_sign_flip_only(real):
    assert len(rank_cases(real, TriageConfig(rules_on=("sign_flip",)))) == 9

