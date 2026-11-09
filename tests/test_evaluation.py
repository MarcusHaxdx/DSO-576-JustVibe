"""Checks for the task builder and the step scorer (src/evaluation).

The real-data tests need data/clean/auditing_clean.csv and the filing folders under
herculean_data/ (git-ignored); they are skipped when either is missing. The 'oracle' and
'empty' runs below are test inputs built from the answer key, never real agent results.
"""
import math
from pathlib import Path

import pandas as pd
import pytest

from analysis.runs import score_runs
from analysis.loader import load_clean
from evaluation.scoring import (Thresholds, load_run, match_task, norm_period, score_run,
                                step_metrics, to_agent_runs, verdicts, wilson)
from evaluation.tasks import build
from evaluation.xbrl import cited_numbers

CLEAN = Path("data/clean/auditing_clean.csv")
XBRL = Path("herculean_data/auditing_env/XBRL")
real_data = pytest.mark.skipif(not (CLEAN.exists() and XBRL.is_dir()),
                               reason="clean data or herculean_data/ filings not found")


# ---------- small pieces ----------

def test_norm_period_accepts_separators():
    assert norm_period("2020-10-01 to 2021-09-30") == "2020-10-01 to 2021-09-30"
    assert norm_period("2020-10-01/2021-09-30") == "2020-10-01 to 2021-09-30"
    assert norm_period(" 2021-12-31 ") == "2021-12-31"
    assert norm_period(None) == ""


def test_wilson_interval():
    lo, hi = wilson(95, 100)
    assert lo == pytest.approx(0.8882, abs=1e-3) and hi == pytest.approx(0.9784, abs=1e-3)
    assert all(math.isnan(x) for x in wilson(0, 0))      # no cases, no interval


def test_cited_numbers_skip_years_and_small():
    assert cited_numbers("In FY 2021 the value of -1,313,536 vs 1,212,736 (3 items)") == [1313536.0, 1212736.0]
    assert cited_numbers("period 2020-10-01 to 2021-09-30") == []


def test_match_prefers_value_agreement_among_duplicates():
    key = pd.DataFrame({"concept_key": ["us-gaap:A", "us-gaap:A"], "period": ["2021-12-31"] * 2,
                        "reported_value": [10.0, 20.0], "calculated_value": [1.0, 2.0]})
    finds = [{"concept": "us-gaap:A", "period": "2021-12-31", "reported_value": 20, "calculated_value": 2},
             {"concept": "US-GAAP:A", "period": "2021-12-31", "reported_value": 10, "calculated_value": 1}]
    assert match_task(key, finds) == {0: 1, 1: 0}


def test_load_run_marks_bad_lines(tmp_path):
    p = tmp_path / "r.jsonl"
    p.write_text('{"task_id": "a", "findings": []}\n{"task_id": "b", "findings": [\n\n{"task_id": "c"}\n')
    run = load_run(p)
    assert run["a"]["findings"] == [] and run["b"] == {"invalid": True} and run["c"] == {"invalid": True}


def test_verdict_thresholds():
    m = pd.DataFrame([
        {"rule_type": 126, "step": "S1 locate", "metric": "recall", "k": 99, "n": 100, "rate": .99, "ci_low": .96, "gate": True},
        {"rule_type": 126, "step": "S1 locate", "metric": "precision", "k": 90, "n": 100, "rate": .90, "ci_low": .83, "gate": True},
        {"rule_type": 126, "step": "S5 explain", "metric": "cited", "k": 9, "n": 10, "rate": .9, "ci_low": .6, "gate": True},
    ])
    v = verdicts(m, Thresholds()).set_index("step")["verdict"]
    assert v["S1 locate"] == "AI + human review"          # the worst gate metric decides
    assert v["S5 explain"] == "too few cases"
    assert v["S4 diagnose"] == "n/a" and v["S6 decide"] == "human"


# ---------- real data ----------

def oracle_run(tasks, key):
    """Perfect answers taken from the key, with evidence that cites the reported value."""
    run = {t["task_id"]: {"task_id": t["task_id"], "findings": []} for t in tasks}
    for r in key.itertuples(index=False):
        run[r.task_id]["findings"].append({
            "concept": r.concept_key, "period": r.period, "unit": r.unit,
            "reported_value": r.reported_value,
            "calculated_value": None if pd.isna(r.calculated_value) else r.calculated_value,
            "cause": "sign_flip" if r.sign_flip else ("other" if pd.notna(r.calculated_value) else None),
            "evidence": f"The fact is reported as {r.reported_value:,}."})
    return run


@pytest.fixture(scope="module")
def built():
    tasks, key = build(CLEAN, XBRL)
    return tasks, key, pd.DataFrame(tasks)


@real_data
def test_build_counts(built):
    tasks, key, tdf = built
    assert len(tasks) == 157 * 3 and len(key) == 362
    assert (tdf["label"] == "positive").sum() == 158 and tdf["n_expected"].sum() == 362
    assert key.groupby("folder_name")["split"].nunique().max() == 1      # no filing in both splits
    assert not any("DQC" in t["prompt"] for t in tasks)                  # the answer is never in the prompt


@real_data
def test_oracle_scores_perfectly(built):
    tasks, key, tdf = built
    cases, finds, status = score_run(oracle_run(tasks, key), tdf, key, XBRL)
    m = step_metrics(cases, finds, status)
    assert (m["rate"] == 1.0).all(), m[m["rate"] != 1.0]
    v = verdicts(m).set_index(["rule_type", "step"])["verdict"]
    for t in (15, 117, 126):
        for step in ("S1 locate", "S2+S3 relate and compute", "S5 explain"):
            assert v[(t, step)] == "AI"
    assert v[(126, "S4 diagnose")] == "too few cases"                    # only 8 sign flips


@real_data
def test_empty_run_finds_nothing_but_raises_no_alarm(built):
    tasks, key, tdf = built
    cases, finds, status = score_run({}, tdf, key, XBRL)
    m = step_metrics(cases, finds, status).set_index(["rule_type", "metric"])["rate"]
    assert m[(126, "recall (flagged cases found)")] == 0
    assert m[(126, "specificity (clean tasks with no finding)")] == 1
    assert (status["status"] == "missing").all()
    v = verdicts(step_metrics(cases, finds, status)).set_index(["rule_type", "step"])["verdict"]
    assert v[(126, "S1 locate")] == "human"


@real_data
def test_errors_are_caught_and_exported_for_the_dashboard(built):
    tasks, key, tdf = built
    run = oracle_run(tasks, key)
    tid = key.loc[key["assertion.type"] == 126, "task_id"].iloc[0]
    f = run[tid]["findings"][0]
    f["calculated_value"] += 1                                         # wrong sum
    f["evidence"] = "The sum of the components is 987,654,321."        # number not in the filing
    clean_tid = tdf.loc[tdf["label"] == "assumed_clean", "task_id"].iloc[0]
    run[clean_tid]["findings"].append(dict(f))                         # false alarm on a clean task
    cases, finds, status = score_run(run, tdf, key, XBRL)
    bad = cases[cases["task_id"] == tid].iloc[0]
    assert bad["matched"] and bad["reported_ok"] and not bad["calculated_ok"] and not bad["evidence_ok"]
    assert finds["matched"].sum() == len(key) and (~finds["matched"]).sum() == 1

    exported = to_agent_runs(cases, run, "oracle")
    scored = score_runs(exported, load_clean(CLEAN))
    assert (~scored["correct"]).sum() == 1
    assert exported.loc[~scored["correct"], "error_type"].item() == "calculation"


@real_data
def test_best_possible_grid_and_task_summary(built):
    from evaluation.report import best_possible, task_summary
    _, key, tdf = built
    s = task_summary(tdf)
    assert s["tasks"].sum() == 471 and s["cases"].sum() == 362
    v, _ = best_possible(tdf, key, split="test")
    v = v.set_index(["rule_type", "step"])["verdict"]
    assert v[(126, "S1 locate")] == "AI + human review"            # 72 clean test tasks < 73
    assert v[(117, "S1 locate")] == "AI" and v[(15, "S4 diagnose")] == "n/a"
    v_all, _ = best_possible(tdf, key, split="all")
    assert v_all.set_index(["rule_type", "step"])["verdict"][(126, "S1 locate")] == "AI"
