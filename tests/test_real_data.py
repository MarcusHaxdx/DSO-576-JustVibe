"""BUILD_SPEC.md section 9 acceptance checks 1-8 on the real clean files."""
import pytest

from analysis import metrics, published
from analysis.filters import FilterSpec, apply_filters
from analysis.loader import COLUMNS
from analysis.triage import TriageConfig, rank_cases


# ---- configuration shortlist (checks 1-4) ----------------------------------------------
def test_check1_published_loads(real_published):
    assert len(real_published) == 20
    sums = real_published[list(published.METRICS.values())].sum(axis=1)
    assert sums.between(99.99, 100.01).all()


def test_check2_leaders_and_intervals(real_published):
    ranked = published.rank_configs(real_published)
    top = ranked[ranked["rank"] == 1]
    assert set(top["setup"]) == {"Claude Code + Claude Sonnet 4.6", "OpenClaw + Claude Sonnet 4.6",
                                 "OpenClaw + GPT-5.4"}
    assert (top["accuracy_pct"] == 66.15).all() and (top["acc_instances"] == 43).all()
    assert round(top["acc_ci_low"].iloc[0], 1) == 54.0 and round(top["acc_ci_high"].iloc[0], 1) == 76.5
    nxt = ranked[ranked["rank"] == 4]
    assert set(nxt["setup"]) == {"Codex + Claude Sonnet 4.6", "Codex + GPT-5.4"}
    assert round(nxt["acc_ci_low"].iloc[0], 1) == 50.9 and round(nxt["acc_ci_high"].iloc[0], 1) == 73.8
    assert ranked["overlaps_leader"].head(5).all()
    kpi = published.shortlist_kpis(ranked)
    assert (kpi["setups"], kpi["best_acc"], kpi["best_acc_instances"], kpi["tied_at_best"]) == (20, 66.15, 43, 3)


def test_check3_shortlist_counts(real_published):
    ranked = published.rank_configs(real_published)
    assert len(published.shortlist(ranked, max_ser=0)) == 10
    assert len(published.shortlist(ranked, min_acc=60, max_ser=0)) == 5
    weak = ranked[ranked["framework"].isin(["ReAct Agent", "Hermes"])]
    assert len(weak) == 8 and (weak["structural_error_rate_pct"] == 80).all()


def test_check4_framework_vs_model(real_published):
    eff = published.framework_model_effects(real_published, "acc")
    assert eff["framework_means"]["OpenClaw"] == 53.08 and eff["framework_means"]["ReAct Agent"] == 14.23
    assert eff["model_means"]["Claude Sonnet 4.6"] == 47.08 and eff["model_means"]["Qwen3.5-27B"] == 28.61
    assert eff["framework_range"] == 38.85 and eff["model_range"] == 18.47
    assert published.framework_model_matrix(real_published, "acc").shape == (5, 4)
    assert len(published.error_mix(real_published)) == 80


# ---- DQC (checks 5-8) -----------------------------------------------------------------
def test_check5_loader_and_kpis(real_df):
    assert real_df.shape == (362, len(COLUMNS) + 1) and len(COLUMNS) == 34
    assert real_df["case_id"].is_unique
    assert metrics.kpis(real_df) == {"cases": 362, "filings": 158, "companies": 125, "rule_types": 3}
    assert metrics.cases_by_type(real_df).set_index("assertion.type")["cases"].to_dict() == {15: 116, 117: 136, 126: 110}


def test_check6_flags(real_df):
    flags = metrics.flag_summary(real_df).set_index("flag")
    assert flags.loc["sign_flip", "cases"] == 9 and flags.loc["sign_flip", "denominator"] == 246
    assert round(flags.loc["sign_flip", "rate"] * 100, 1) == 3.7
    assert flags.loc["period_after_filing", "cases"] == 2


def test_check7_discrepancy(real_df):
    d = metrics.discrepancy(real_df)
    case = d[(d["reported_value"] == -1313536) & (d["calculated_value"] == -1212736)]
    assert len(case) == 1
    assert case["abs_diff"].iloc[0] == 100800
    assert case["rel_diff"].iloc[0] == pytest.approx(0.0767, abs=5e-4)
    flips = d[d["sign_flip"]]
    assert len(flips) == 9 and (flips["rel_diff"] == 2.0).all()
    s = metrics.discrepancy_summary(real_df)
    assert (s["comparison_cases"], s["with_rel_diff"], s["without_rel_diff"]) == (246, 231, 15)
    assert metrics.histogram_counts(real_df, 5.0) == {"drawn": 208, "above": 23, "without_rel_diff": 15, "max_rel": 5.0}


def test_check8_review_queue_sign_flip_only(real_df):
    only_flip = TriageConfig(period_after_filing=False, non_usd_unit=False, non_us_gaap_prefix=False, large_gap=False)
    ranked = rank_cases(real_df, only_flip)
    assert len(ranked) == 9 and (ranked["reasons"] == "sign flip").all()


def test_check9_type_filter_backend(real_df):
    assert len(apply_filters(real_df, FilterSpec(types=(126,)))) == 110


def test_check11_no_unit_mixing_and_no_fake_zero(real_df):
    compared = real_df["case_id"].isin(metrics.discrepancy(real_df)["case_id"])
    assert set(real_df.loc[compared, "unit"]) == {"USD"}
    assert real_df.loc[real_df["assertion.type"] == 15, "calculated_value"].isna().all()
