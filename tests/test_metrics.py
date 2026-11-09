import pytest

from analysis import metrics
from analysis.filters import FilterSpec, apply_filters


def test_cases_by_type(df):
    out = metrics.cases_by_type(df)
    assert dict(zip(out["assertion.type"], out["cases"])) == {15: 5, 126: 4, 117: 2}
    assert out["cases"].tolist() == [5, 4, 2]                       # largest first
    assert out["share"].sum() == pytest.approx(1.0)


def test_cases_by_code(df):
    out = metrics.cases_by_code(df)
    assert out["cases"].sum() == 11
    assert out.iloc[0]["assertion.code"] == "DQC.US.0126.9590"       # 4 cases, ties by code


def test_flag_summary(df):
    s = metrics.flag_summary(df)
    assert s["cases"] == 11 and s["sign_flip"] == 2 and s["period_after_filing"] == 2
    assert s["non_usd"] == 3 and s["non_us_gaap_prefix"] == 2
    assert s["rows_with_calculated"] == 6
    assert s["sign_flip_rate"] == pytest.approx(2 / 6)


def test_flag_summary_empty(df):
    s = metrics.flag_summary(apply_filters(df, FilterSpec(assertion_types=(99,))))
    assert s["cases"] == 0 and s["sign_flip_rate"] is None


def test_discrepancy_values(df):
    d = metrics.discrepancy(df).set_index("reported_value")
    assert d.loc[-1313536.0, "abs_diff"] == 100800
    assert d.loc[-1313536.0, "rel_diff"] == pytest.approx(100800 / 1313536)
    assert d.loc[707500.0, "rel_diff"] == pytest.approx(2.0)          # sign flip = exactly 200%
    assert d.loc[19204000.0, "rel_diff"] == pytest.approx(2.0)
    assert d.loc[0.0, "abs_diff"] == 50 and d.loc[0.0, "rel_diff"] != d.loc[0.0, "rel_diff"]  # reported 0 -> NaN


def test_discrepancy_only_for_usd_comparison_rows(df):
    d = metrics.discrepancy(df)
    assert d.loc[d["assertion.type"] == 15, ["abs_diff", "rel_diff"]].isna().all().all()
    assert d["abs_diff"].notna().sum() == 6 and d["rel_diff"].notna().sum() == 5


def test_discrepancy_does_not_modify_input(df):
    before = list(df.columns)
    metrics.discrepancy(df)
    assert list(df.columns) == before


def test_discrepancy_summary(df):
    s = metrics.discrepancy_summary(df)
    assert s["cases"] == 6
    assert s["median_abs_diff"] == pytest.approx(19911500)
    assert s["max_abs_diff"] == pytest.approx(1956268000)
    assert s["median_rel_diff"] == pytest.approx(2.0)


def test_discrepancy_summary_empty(df):
    s = metrics.discrepancy_summary(apply_filters(df, FilterSpec(assertion_types=(15,))))
    assert s["cases"] == 0 and s["median_rel_diff"] is None


def test_cases_by_year_and_top_companies(df):
    y = metrics.cases_by_year(df)
    assert dict(zip(y["report.filing-year"], y["cases"])) == {2022: 7, 2023: 4}
    top = metrics.top_companies(df, n=2)
    assert top["entity.name"].tolist() == ["ALPHA INC", "BETA CORP"]   # 3 cases, then a tie broken by name
    assert top["cases"].tolist() == [3, 2]


def test_discrepancy_ignores_non_usd_comparison_rows(df):
    """Amounts in other units must never get a discrepancy (units are never mixed)."""
    changed = df.copy()
    changed.loc[changed["reported_value"] == -1313536.0, "unit"] = "EUR"
    d = metrics.discrepancy(changed).set_index("reported_value")
    assert d.loc[-1313536.0, ["abs_diff", "rel_diff"]].isna().all()
    assert metrics.discrepancy_summary(changed)["cases"] == 5


def test_kpis(df):
    assert metrics.kpis(df) == {"cases": 11, "filings": 11, "companies": 5, "rule_types": 3}


def test_kpis_empty(df):
    assert metrics.kpis(apply_filters(df, FilterSpec(assertion_types=(99,)))) == {
        "cases": 0, "filings": 0, "companies": 0, "rule_types": 0}


def test_histogram_counts(df):
    c = metrics.histogram_counts(df, 5.0)
    assert c == {"comparison_cases": 6, "with_rel": 5, "without_rel": 1, "drawn": 4, "above": 1}
    assert c["drawn"] + c["above"] == c["with_rel"]


def test_histogram_counts_edge_is_inclusive(df):
    assert metrics.histogram_counts(df, 2.0)["drawn"] == 4        # the two sign flips sit exactly at 2.0
    assert metrics.histogram_counts(df, 0.0)["drawn"] == 0


def test_histogram_counts_empty(df):
    empty = apply_filters(df, FilterSpec(assertion_types=(15,)))
    assert metrics.histogram_counts(empty, 5.0) == {
        "comparison_cases": 0, "with_rel": 0, "without_rel": 0, "drawn": 0, "above": 0}
