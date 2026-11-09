"""Read-side helpers for the dashboard: task design, what the design can prove, scored results."""
from pathlib import Path

import pandas as pd

from evaluation.scoring import Thresholds, step_metrics, verdicts
from evaluation.tasks import load_key, load_tasks


def load_design(tasks_path, key_path):
    """(tasks, key) as built by eval/build_tasks.py, or None if they have not been built."""
    if not (Path(tasks_path).exists() and Path(key_path).exists()):
        return None
    return load_tasks(tasks_path), load_key(key_path)


def task_summary(tasks: pd.DataFrame) -> pd.DataFrame:
    """Tasks, positive tasks, assumed-clean tasks and flagged cases per split x rule type."""
    g = tasks.groupby(["split", "rule_type"])
    return g.agg(tasks=("task_id", "count"),
                 positive=("label", lambda s: int((s == "positive").sum())),
                 assumed_clean=("label", lambda s: int((s == "assumed_clean").sum())),
                 cases=("n_expected", "sum")).reset_index()


def _restrict(tasks, key, split):
    if split == "all":
        return tasks, key
    return tasks[tasks["split"] == split], key[key["split"] == split]


def best_possible(tasks: pd.DataFrame, key: pd.DataFrame, split: str = "test",
                  th: Thresholds = Thresholds()) -> tuple:
    """The verdict grid a perfect agent would get: the most the case counts can prove.

    Built by scoring a perfect answer for every case, so it uses the same metrics and rule as
    real runs. Returns (verdicts, metrics). This is a property of the design, not a result.
    """
    tasks, key = _restrict(tasks, key, split)
    cases = pd.DataFrame({
        "task_id": key["task_id"], "case_id": key["case_id"], "rule_type": key["assertion.type"],
        "matched": True, "reported_ok": True, "calculated_ok": True, "correct": True,
        "sign_flip": key["sign_flip"].astype(bool),
        "cause": key["sign_flip"].map({True: "sign_flip", False: "other"}), "evidence_ok": True})
    finds = pd.DataFrame({"task_id": key["task_id"], "rule_type": key["assertion.type"],
                          "label": "positive", "matched": True, "cause": cases["cause"],
                          "truth_sign_flip": cases["sign_flip"]})
    status = pd.DataFrame({"task_id": tasks["task_id"], "rule_type": tasks["rule_type"],
                           "label": tasks["label"], "status": "ok",
                           "n_expected": tasks["n_expected"], "n_findings": tasks["n_expected"]})
    m = step_metrics(cases, finds, status)
    return verdicts(m, th), m


def load_results(results_dir):
    """(step_metrics, verdicts) written by eval/score_runs.py, or None if nothing was scored."""
    d = Path(results_dir)
    if not ((d / "step_metrics.csv").exists() and (d / "verdicts.csv").exists()):
        return None
    return pd.read_csv(d / "step_metrics.csv"), pd.read_csv(d / "verdicts.csv")
