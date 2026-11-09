import pandas as pd
import pytest

from analysis.filters import FilterSpec, apply_filters
from analysis.runs import RUN_COLUMNS, config_comparison, error_breakdown, load_runs, restrict_to_cases, score_runs
from conftest import case_id


def make_runs(df):
    c126, c117, c15 = case_id(df, -1313536.0), case_id(df, 255500000.0), case_id(df, -1284.0)
    rows = [
        # run_id, case_id, agent, model, answer_reported, answer_calculated, cost, latency, error
        ("r1", c126, "A", "m1", -1313536.0, -1212736.0, 0.10, 10.0, None),
        ("r2", c117, "A", "m1", 255500000.0, 1.0, 0.20, 20.0, "calculation"),
        ("r3", c15, "A", "m1", -1284.0, None, 0.30, 30.0, None),         # type 15: reported only
        ("r4", c126, "B", "m2", -1313536.0, -1212736.0, 0.01, 5.0, None),
        ("r5", c15, "B", "m2", -9.0, None, 0.02, 7.0, "extraction"),
        ("r6", c117, "B", "m2", None, None, 0.03, 9.0, None),             # empty answer, no label
    ]
    return pd.DataFrame(rows, columns=RUN_COLUMNS)


def test_missing_file_returns_none(tmp_path):
    assert load_runs(tmp_path / "agent_runs.csv") is None


def test_missing_column_raises(tmp_path):
    p = tmp_path / "r.csv"
    pd.DataFrame({"run_id": [1]}).to_csv(p, index=False)
    with pytest.raises(ValueError):
        load_runs(p)


def test_load_roundtrip(tmp_path, df):
    p = tmp_path / "r.csv"
    make_runs(df).to_csv(p, index=False)
    assert len(load_runs(p)) == 6


def test_scoring_rules(df):
    s = score_runs(make_runs(df), df).set_index("run_id")["correct"]
    assert s.to_dict() == {"r1": True, "r2": False, "r3": True, "r4": True, "r5": False, "r6": False}


def test_unknown_case_id_rejected(df):
    runs = make_runs(df)
    runs.loc[0, "case_id"] = "doesnotexist"
    with pytest.raises(ValueError):
        score_runs(runs, df)


def test_config_comparison(df):
    out = config_comparison(score_runs(make_runs(df), df)).set_index("model")
    assert out.loc["m1", "runs"] == 3 and out.loc["m1", "accuracy"] == pytest.approx(2 / 3)
    assert out.loc["m2", "accuracy"] == pytest.approx(1 / 3)
    assert out.loc["m1", "mean_cost_usd"] == pytest.approx(0.2)
    assert out.loc["m2", "mean_latency_s"] == pytest.approx(7.0)
    assert out.index[0] == "m1"                                       # best accuracy first


def test_error_breakdown(df):
    out = error_breakdown(score_runs(make_runs(df), df))
    got = {(r.model, r.error_type): r.share for r in out.itertuples()}
    assert got == {("m1", "calculation"): pytest.approx(1 / 3),
                   ("m2", "extraction"): pytest.approx(1 / 3),
                   ("m2", "unlabeled"): pytest.approx(1 / 3)}


def test_restrict_to_cases(df):
    scored = score_runs(make_runs(df), df)
    only_126 = restrict_to_cases(scored, apply_filters(df, FilterSpec(assertion_types=(126,))))
    assert set(only_126["run_id"]) == {"r1", "r4"}
    assert len(restrict_to_cases(scored, df.iloc[0:0])) == 0
    assert len(scored) == 6                                            # the input is not modified
