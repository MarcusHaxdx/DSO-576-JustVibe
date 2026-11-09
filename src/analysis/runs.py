"""Optional input: agent runs (M6). Never creates or simulates runs."""
from pathlib import Path

import numpy as np
import pandas as pd

DEFAULT_PATH = Path("data/runs/agent_runs.csv")
RUN_COLUMNS = ["run_id", "case_id", "agent_framework", "model", "answer_reported",
               "answer_calculated", "cost_usd", "latency_s", "error_type"]
_NUMERIC = ["answer_reported", "answer_calculated", "cost_usd", "latency_s"]
REL_TOL = 1e-9


def load_runs(path=DEFAULT_PATH):
    """Read the runs file; return None if it does not exist (the dashboard has no runs tab; eval/ uses this).

    Raises ValueError if a required column is missing.
    """
    path = Path(path)
    if not path.exists():
        return None
    runs = pd.read_csv(path)
    missing = [c for c in RUN_COLUMNS if c not in runs.columns]
    if missing:
        raise ValueError(f"Runs file is missing columns: {missing}")
    for c in _NUMERIC:
        runs[c] = pd.to_numeric(runs[c], errors="coerce")
    return runs


def score_runs(runs: pd.DataFrame, truth: pd.DataFrame) -> pd.DataFrame:
    """Add a boolean `correct` column to `runs`.

    Correct = answer_reported equals the ground-truth reported_value and, where the ground
    truth has a calculated_value, answer_calculated equals it too (relative tolerance 1e-9).
    Raises ValueError if a run refers to a case_id that is not in `truth`.
    """
    unknown = set(runs["case_id"]) - set(truth["case_id"])
    if unknown:
        raise ValueError(f"{len(unknown)} run(s) refer to unknown case_id values")
    t = truth[["case_id", "reported_value", "calculated_value"]]
    m = runs.merge(t, on="case_id", how="left", validate="many_to_one")
    ok_rep = np.isclose(m["answer_reported"].astype(float), m["reported_value"].astype(float),
                        rtol=REL_TOL, atol=0.0)
    needs_calc = m["calculated_value"].notna()
    ok_calc = np.isclose(m["answer_calculated"].astype(float), m["calculated_value"].astype(float),
                         rtol=REL_TOL, atol=0.0)
    out = runs.copy()
    out["correct"] = (ok_rep & (~needs_calc | ok_calc)).astype(bool)
    return out


def restrict_to_cases(scored: pd.DataFrame, cases: pd.DataFrame) -> pd.DataFrame:
    """Keep only the runs whose case_id is in `cases` (for example the filtered cases)."""
    return scored[scored["case_id"].isin(cases["case_id"])].copy()


def config_comparison(scored: pd.DataFrame) -> pd.DataFrame:
    """M6: runs, accuracy, mean cost and mean latency per (agent_framework, model)."""
    g = scored.groupby(["agent_framework", "model"])
    out = g.agg(runs=("run_id", "count"), accuracy=("correct", "mean"),
                mean_cost_usd=("cost_usd", "mean"), mean_latency_s=("latency_s", "mean")).reset_index()
    return out.sort_values(["accuracy", "mean_cost_usd"], ascending=[False, True]).reset_index(drop=True)


def error_breakdown(scored: pd.DataFrame) -> pd.DataFrame:
    """M6: per configuration, the share of its runs that failed with each error_type.

    Incorrect runs without an error_type are reported as 'unlabeled'.
    """
    s = scored.copy()
    s["error_type"] = s["error_type"].where(s["error_type"].notna() & (s["error_type"] != ""), None)
    s.loc[~s["correct"] & s["error_type"].isna(), "error_type"] = "unlabeled"
    totals = s.groupby(["agent_framework", "model"]).size().rename("total").reset_index()
    errs = (s[~s["correct"]].groupby(["agent_framework", "model", "error_type"]).size()
            .rename("runs").reset_index())
    out = errs.merge(totals, on=["agent_framework", "model"])
    out["share"] = out["runs"] / out["total"]
    return out.drop(columns="total").sort_values(["agent_framework", "model", "error_type"]).reset_index(drop=True)
