"""M6-M8: the 20 published HERCULEAN Auditing setups (aggregate results, 65 instances each)."""
from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable

import pandas as pd

METRICS = {
    "acc": "accuracy_pct",
    "ser": "structural_error_rate_pct",
    "eer": "extraction_error_rate_pct",
    "cer": "calculation_error_rate_pct",
}
OUTCOME_LABELS = {"acc": "ACC", "ser": "SER", "eer": "EER", "cer": "CER"}
REQUIRED_COLUMNS = ["framework", "model", "model_name", *METRICS.values(), "audit_instances",
                    "acc_instances", "ser_instances", "eer_instances", "cer_instances"]
FRAMEWORK_ORDER = ["ReAct Agent", "Claude Code", "Codex", "Hermes", "OpenClaw"]
MODEL_ORDER = ["Claude Sonnet 4.6", "GPT-5.4", "Qwen3.5-397B-A17B", "Qwen3.5-27B"]


def load_published(path: str | Path) -> pd.DataFrame:
    """Read and validate the 20-row published table.

    Raises ValueError if a column is missing, there are not 20 unique setups, a rate is outside
    0-100, or a row's four rates do not sum to 100 +/- 0.01.
    """
    df = pd.read_csv(path)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Published file is missing columns: {missing}")
    if len(df) != 20 or df[["framework", "model"]].duplicated().any():
        raise ValueError("Expected 20 unique framework/model setups.")
    rates = df[list(METRICS.values())]
    if ((rates < 0) | (rates > 100)).any().any():
        raise ValueError("A published rate is outside 0-100.")
    if (rates.sum(axis=1).sub(100).abs() > 0.01 + 1e-9).any():
        raise ValueError("A setup's four rates do not sum to 100 +/- 0.01.")
    df["setup"] = df["framework"] + " + " + df["model_name"]
    return df


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for k successes out of n, returned in percent."""
    if n <= 0:
        raise ValueError("n must be positive")
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return 100 * max(0.0, centre - half), 100 * min(1.0, centre + half)


def rank_configs(df: pd.DataFrame) -> pd.DataFrame:
    """All 20 setups with `rank` (competition rank on ACC; ties share a rank) and a 95% ACC interval.

    Display order: ACC desc, SER asc, CER asc, framework A-Z, model_name A-Z.
    """
    out = df.copy()
    out["rank"] = out["accuracy_pct"].rank(method="min", ascending=False).astype(int)
    ci = [wilson_ci(int(k), int(n)) for k, n in zip(out["acc_instances"], out["audit_instances"])]
    out["acc_ci_low"] = [lo for lo, _ in ci]
    out["acc_ci_high"] = [hi for _, hi in ci]
    out = out.sort_values(
        ["accuracy_pct", "structural_error_rate_pct", "calculation_error_rate_pct", "framework", "model_name"],
        ascending=[False, True, True, True, True],
        kind="stable",
    ).reset_index(drop=True)
    leader_low = out.loc[out["accuracy_pct"].idxmax(), "acc_ci_low"]
    out["overlaps_leader"] = out["acc_ci_high"] >= leader_low
    first = ["rank", "setup", "framework", "model_name", "accuracy_pct", "acc_ci_low", "acc_ci_high"]
    return out[first + [c for c in out.columns if c not in first]]


def shortlist(
    ranked: pd.DataFrame,
    min_acc: float = 0.0,
    max_ser: float = 100.0,
    frameworks: Iterable[str] | None = None,
    models: Iterable[str] | None = None,
) -> pd.DataFrame:
    """Rows of `rank_configs` output that pass the controls; ranks stay global (out of 20).

    `models` are display names. None or empty means all.
    """
    mask = (ranked["accuracy_pct"] >= min_acc) & (ranked["structural_error_rate_pct"] <= max_ser)
    if frameworks:
        mask &= ranked["framework"].isin(list(frameworks))
    if models:
        mask &= ranked["model_name"].isin(list(models))
    return ranked[mask].reset_index(drop=True)


def shortlist_kpis(shortlisted: pd.DataFrame) -> dict:
    """KPI row: setups shown, best ACC and its count, how many setups tie at the best ACC."""
    if shortlisted.empty:
        return {"setups": 0, "best_acc": None, "best_acc_instances": None,
                "audit_instances": None, "tied_at_best": 0}
    best = shortlisted["accuracy_pct"].max()
    top = shortlisted[shortlisted["accuracy_pct"] == best]
    return {
        "setups": int(len(shortlisted)),
        "best_acc": float(best),
        "best_acc_instances": int(top["acc_instances"].iloc[0]),
        "audit_instances": int(top["audit_instances"].iloc[0]),
        "tied_at_best": int(len(top)),
    }


def error_mix(df: pd.DataFrame) -> pd.DataFrame:
    """M7, long format: `setup`, `framework`, `model_name`, `outcome` (ACC/SER/EER/CER), `pct`, `instances`.

    Rows keep the order of `df` (pass a shortlist to get table order).
    """
    rows = []
    for _, r in df.iterrows():
        for key, col in METRICS.items():
            rows.append({
                "setup": r["setup"], "framework": r["framework"], "model_name": r["model_name"],
                "outcome": OUTCOME_LABELS[key], "pct": float(r[col]), "instances": int(r[f"{key}_instances"]),
            })
    return pd.DataFrame(rows, columns=["setup", "framework", "model_name", "outcome", "pct", "instances"])


def framework_model_matrix(df: pd.DataFrame, metric: str = "acc") -> pd.DataFrame:
    """M8: frameworks (rows) x model display names (columns) of one metric ('acc', 'ser', 'eer', 'cer')."""
    if metric not in METRICS:
        raise ValueError(f"metric must be one of {list(METRICS)}")
    return (
        df.pivot(index="framework", columns="model_name", values=METRICS[metric])
        .reindex(index=FRAMEWORK_ORDER, columns=MODEL_ORDER)
    )


def framework_model_effects(df: pd.DataFrame, metric: str = "acc") -> dict:
    """M8: mean of the metric per framework and per model, and the range (max - min) of each."""
    if metric not in METRICS:
        raise ValueError(f"metric must be one of {list(METRICS)}")
    col = METRICS[metric]
    fw = df.groupby("framework")[col].mean().round(2).sort_values(ascending=False)
    md = df.groupby("model_name")[col].mean().round(2).sort_values(ascending=False)
    return {
        "metric": metric,
        "framework_means": fw,
        "model_means": md,
        "framework_range": round(float(fw.max() - fw.min()), 2),
        "model_range": round(float(md.max() - md.min()), 2),
    }
