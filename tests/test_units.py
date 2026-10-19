"""Unit tests on small hand-made data: each layer checked alone."""
import math

import pandas as pd
import pytest

from analysis import metrics, published
from analysis.filters import FilterSpec, apply_filters
from analysis.loader import load_clean
from analysis.triage import TriageConfig, queue_status, rank_cases


# ---- loader -------------------------------------------------------------------------
def test_loader_rejects_missing_column(tmp_path, small_df):
    path = tmp_path / "bad.csv"
    small_df.drop(columns=["case_id", "sign_flip"]).to_csv(path, index=False)
    with pytest.raises(ValueError, match="missing columns"):
        load_clean(path)


def test_loader_rejects_duplicate_key(tmp_path, small_df):
    path = tmp_path / "dup.csv"
    df = small_df.drop(columns=["case_id"])
    pd.concat([df, df.iloc[[0]]]).to_csv(path, index=False)
    with pytest.raises(ValueError, match="not unique"):
        load_clean(path)


def test_loader_types_and_case_id(tmp_path, small_df):
    path = tmp_path / "ok.csv"
    small_df.drop(columns=["case_id"]).to_csv(path, index=False)
    df = load_clean(path)
    assert df["case_id"].tolist() == small_df["case_id"].tolist()
    assert df["case_id"].str.len().eq(12).all()
    assert df["sign_flip"].dtype == bool and df["assertion.type"].dtype == "int64"
    assert df.loc[3, "calculated_value"] != df.loc[3, "calculated_value"]  # NaN, never 0


# ---- filters ------------------------------------------------------------------------
def test_default_filter_keeps_all(small_df):
    assert len(apply_filters(small_df, FilterSpec())) == 8


@pytest.mark.parametrize("spec, expected", [
    (FilterSpec(types=(15,)), 2),
    (FilterSpec(years=(2024,)), 1),
    (FilterSpec(concept_prefix="other"), 1),
    (FilterSpec(units=("shares",)), 1),
    (FilterSpec(period_kind="instant"), 1),
    (FilterSpec(only_sign_flip=True), 1),
    (FilterSpec(only_sign_flip=True, only_period_after_filing=True), 0),
    (FilterSpec(company="grumman"), 1),
])
def test_filters(small_df, spec, expected):
    assert len(apply_filters(small_df, spec)) == expected


def test_filter_rejects_bad_choice(small_df):
    with pytest.raises(ValueError):
        apply_filters(small_df, FilterSpec(period_kind="weekly"))


# ---- metrics ------------------------------------------------------------------------
def test_kpis_and_types(small_df):
    assert metrics.kpis(small_df) == {"cases": 8, "filings": 4, "companies": 4, "rule_types": 3}
    by_type = metrics.cases_by_type(small_df)
    assert by_type.set_index("assertion.type")["cases"].to_dict() == {15: 2, 117: 1, 126: 5}
    assert by_type["share"].sum() == pytest.approx(1.0)


def test_flag_summary_sign_flip_denominator(small_df):
    flags = metrics.flag_summary(small_df).set_index("flag")
    assert flags.loc["sign_flip", "cases"] == 1
    assert flags.loc["sign_flip", "denominator"] == 6  # rows with a calculated_value
    assert flags.loc["non_usd_unit", "cases"] == 1


def test_discrepancy_scope_and_values(small_df):
    d = metrics.discrepancy(small_df).set_index("case_id")
    assert len(d) == 6  # type 15 rows excluded
    assert d.loc[small_df.loc[0, "case_id"], "rel_diff"] == pytest.approx(0.10)
    assert d.loc[small_df.loc[1, "case_id"], "rel_diff"] == pytest.approx(2.0)
    assert math.isnan(d.loc[small_df.loc[2, "case_id"], "rel_diff"])
    assert metrics.histogram_counts(small_df, 5.0) == {"drawn": 4, "above": 1, "without_rel_diff": 1, "max_rel": 5.0}


def test_top_companies_tie_break(small_df):
    top = metrics.top_companies(small_df, 2)
    # Company 1 has 3 cases; Company 0 and Company 2 tie at 2, so name A-Z picks Company 0.
    assert top["cases"].tolist() == [3, 2]
    assert top["entity.name"].tolist() == ["Company 1", "Company 0"]


# ---- triage -------------------------------------------------------------------------
def test_triage_points_and_order(small_df):
    ranked = rank_cases(small_df, TriageConfig())
    assert ranked["rank"].tolist() == list(range(1, len(ranked) + 1))
    assert ranked["points"].is_monotonic_decreasing
    top = ranked.iloc[0]
    assert top["points"] == 2 and "period after filing date" in top["reasons"]


def test_triage_single_rule_and_threshold(small_df):
    only_flip = TriageConfig(period_after_filing=False, non_usd_unit=False, non_us_gaap_prefix=False, large_gap=False)
    assert len(rank_cases(small_df, only_flip)) == 1
    gap_only = TriageConfig(sign_flip=False, period_after_filing=False, non_usd_unit=False,
                            non_us_gaap_prefix=False, gap_threshold=1.0)
    assert len(rank_cases(small_df, gap_only)) == 2  # 200% and 600%


def test_queue_status(small_df):
    ranked = rank_cases(small_df, TriageConfig())
    assert queue_status(ranked, ranked.iloc[0]["case_id"])["rank"] == 1
    assert queue_status(ranked, "not-a-case") is None


# ---- published ----------------------------------------------------------------------
def test_wilson_ci():
    lo, hi = published.wilson_ci(43, 65)
    assert (round(lo, 1), round(hi, 1)) == (54.0, 76.5)
    assert published.wilson_ci(0, 65)[0] == 0.0
    with pytest.raises(ValueError):
        published.wilson_ci(1, 0)


def test_load_published_rejects_bad_sum(tmp_path, real_published):
    bad = real_published.drop(columns=["setup"]).copy()
    bad.loc[0, "accuracy_pct"] += 1
    path = tmp_path / "bad.csv"
    bad.to_csv(path, index=False)
    with pytest.raises(ValueError, match="sum to 100"):
        published.load_published(path)


def test_shortlist_keeps_global_rank(real_published):
    ranked = published.rank_configs(real_published)
    sl = published.shortlist(ranked, frameworks=["Codex"])
    assert sl["rank"].min() == 4
    assert published.shortlist_kpis(published.shortlist(ranked, min_acc=99))["setups"] == 0
