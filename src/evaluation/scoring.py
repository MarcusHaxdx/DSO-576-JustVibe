"""Score agent runs against the answer key, step by step, and turn the scores into verdicts.

A run file is JSON Lines, one line per task:
    {"task_id": ..., "findings": [...], "model": ..., "agent_framework": ...,
     "cost_usd": ..., "latency_s": ...}
Only task_id and findings are required. A task with no line, or a line that is not valid JSON,
counts as an empty answer and is reported as missing / invalid.

Steps (see eval/README.md): S1 locate, S2+S3 relate and compute (scored together through the
values), S4 diagnose (only sign flips have a label), S5 explain (are the cited numbers in the
filing), S6 decide (no ground truth, so always human).
"""
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from analysis.runs import REL_TOL
from evaluation.xbrl import cited_numbers, fact_values

_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
STEPS = ["S1 locate", "S2+S3 relate and compute", "S4 diagnose", "S5 explain", "S6 decide"]


# ---------- normalising and matching ----------

def norm_concept(s) -> str:
    return str(s or "").strip().lower()


def norm_period(s) -> str:
    """'YYYY-MM-DD to YYYY-MM-DD' for a duration, 'YYYY-MM-DD' for an instant, whatever the separator."""
    dates = _DATE.findall(str(s or ""))
    return " to ".join(dates[:2])


def to_float(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return math.nan
    return f


def same_value(a, b) -> bool:
    a, b = to_float(a), to_float(b)
    return not (math.isnan(a) or math.isnan(b)) and bool(np.isclose(a, b, rtol=REL_TOL, atol=0.0))


def match_task(key_rows: pd.DataFrame, findings: list) -> dict:
    """Pair key rows with findings on (concept, period), one to one.

    When several findings share a concept and period (the same fact can fail in two
    statements), the pair whose values agree wins. Returns {key index: finding index}.
    """
    pairs = []
    for ki, k in key_rows.iterrows():
        for fi, f in enumerate(findings):
            if norm_concept(f.get("concept")) == norm_concept(k["concept_key"]) and \
                    norm_period(f.get("period")) == norm_period(k["period"]):
                score = 2 * same_value(f.get("reported_value"), k["reported_value"]) + \
                    same_value(f.get("calculated_value"), k["calculated_value"])
                pairs.append((-score, ki, fi))
    pairs.sort()
    used_k, used_f, out = set(), set(), {}
    for _, ki, fi in pairs:
        if ki not in used_k and fi not in used_f:
            out[ki] = fi
            used_k.add(ki)
            used_f.add(fi)
    return out


# ---------- reading runs ----------

def load_run(path) -> dict:
    """Read a run file into {task_id: record}; bad lines are kept as {'invalid': True}."""
    out = {}
    for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
            tid = rec["task_id"]
            if not isinstance(rec.get("findings"), list):
                raise ValueError("findings is not a list")
        except (ValueError, KeyError, TypeError):
            m = re.search(r'"task_id"\s*:\s*"([^"]+)"', line)
            out[m.group(1) if m else f"<line {n}>"] = {"invalid": True}
            continue
        out[tid] = rec
    return out


def evidence_supported(finding: dict, folder: Path) -> bool:
    """True if the evidence cites at least one number and every cited number is a fact value
    in the filing, or the finding's own reported / calculated value or their difference."""
    cited = cited_numbers(finding.get("evidence", ""))
    if not cited:
        return False
    rep, calc = to_float(finding.get("reported_value")), to_float(finding.get("calculated_value"))
    own = {abs(v) for v in (rep, calc, rep - calc) if not math.isnan(v)}
    facts = fact_values(str(folder))
    return all(any(np.isclose(c, v, rtol=REL_TOL, atol=0.5) for v in own) or c in facts
               for c in cited)


def score_run(run: dict, tasks: pd.DataFrame, key: pd.DataFrame, xbrl_root) -> tuple:
    """Return (cases, findings, task_status) tables for one run over the given tasks."""
    xbrl_root = Path(xbrl_root)
    case_rows, find_rows, task_rows = [], [], []
    key_by_task = {t: g for t, g in key.groupby("task_id")}
    for t in tasks.itertuples(index=False):
        rec = run.get(t.task_id)
        status = "missing" if rec is None else "invalid" if rec.get("invalid") else "ok"
        findings = rec.get("findings", []) if status == "ok" else []
        findings = [f for f in findings if isinstance(f, dict)]
        k = key_by_task.get(t.task_id, key.iloc[0:0])
        matched = match_task(k, findings)
        matched_f = {fi: ki for ki, fi in matched.items()}
        task_rows.append({"task_id": t.task_id, "rule_type": t.rule_type, "label": t.label,
                          "status": status, "n_expected": len(k), "n_findings": len(findings)})
        for fi, f in enumerate(findings):
            ki = matched_f.get(fi)
            find_rows.append({"task_id": t.task_id, "rule_type": t.rule_type, "label": t.label,
                              "matched": ki is not None,
                              "cause": f.get("cause"),
                              "truth_sign_flip": bool(k.loc[ki, "sign_flip"]) if ki is not None else None})
        for ki, row in k.iterrows():
            f = findings[matched[ki]] if ki in matched else None
            needs_calc = pd.notna(row["calculated_value"])
            rep_ok = f is not None and same_value(f.get("reported_value"), row["reported_value"])
            calc_ok = f is not None and (not needs_calc or same_value(f.get("calculated_value"), row["calculated_value"]))
            case_rows.append({
                "task_id": t.task_id, "case_id": row["case_id"], "rule_type": t.rule_type,
                "matched": f is not None, "reported_ok": rep_ok, "calculated_ok": calc_ok,
                "correct": rep_ok and calc_ok, "sign_flip": bool(row["sign_flip"]),
                "cause": f.get("cause") if f else None,
                "evidence_ok": evidence_supported(f, xbrl_root / t.folder_name) if f else False,
                "answer_reported": to_float(f.get("reported_value")) if f else math.nan,
                "answer_calculated": to_float(f.get("calculated_value")) if f else math.nan,
            })
    cases = pd.DataFrame(case_rows, columns=[
        "task_id", "case_id", "rule_type", "matched", "reported_ok", "calculated_ok", "correct",
        "sign_flip", "cause", "evidence_ok", "answer_reported", "answer_calculated"])
    finds = pd.DataFrame(find_rows, columns=["task_id", "rule_type", "label", "matched", "cause",
                                             "truth_sign_flip"])
    return cases, finds, pd.DataFrame(task_rows)


# ---------- metrics and verdicts ----------

def wilson(k: int, n: int, z: float = 1.96) -> tuple:
    """Wilson score interval for k successes out of n; (nan, nan) when n is 0."""
    if n == 0:
        return math.nan, math.nan
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def _metric(step, name, k, n, gate=True):
    lo, hi = wilson(int(k), int(n))
    return {"step": step, "metric": name, "k": int(k), "n": int(n),
            "rate": k / n if n else math.nan, "ci_low": lo, "ci_high": hi, "gate": gate}


def step_metrics(cases, finds, task_status) -> pd.DataFrame:
    """One row per rule type x metric, with Wilson 95% intervals. `gate` marks the metrics a
    verdict depends on; the others are context."""
    rows = []
    for t in sorted(task_status["rule_type"].unique()):
        c = cases[cases["rule_type"] == t]
        f = finds[finds["rule_type"] == t]
        ts = task_status[task_status["rule_type"] == t]
        clean = ts[ts["label"] == "assumed_clean"]
        m = c[c["matched"]]
        out = [
            _metric("S1 locate", "recall (flagged cases found)", c["matched"].sum(), len(c)),
            _metric("S1 locate", "precision (findings that match a case)", f["matched"].sum(), len(f)),
            _metric("S1 locate", "specificity (clean tasks with no finding)",
                    (clean["n_findings"] == 0).sum(), len(clean)),
            _metric("S2+S3 relate and compute", "values correct, given found", m["correct"].sum(), len(m)),
            _metric("S5 explain", "cited numbers all in filing, given found", m["evidence_ok"].sum(), len(m)),
            _metric("end to end", "case correct (found and values right)", c["correct"].sum(), len(c), gate=False),
            _metric("output", "tasks with a valid answer", (ts["status"] == "ok").sum(), len(ts), gate=False),
        ]
        if t != 15:
            flips = m[m["sign_flip"]]
            said_flip = f[f["matched"] & (f["cause"] == "sign_flip")]
            out += [
                _metric("S4 diagnose", "sign flips named, given found", (flips["cause"] == "sign_flip").sum(), len(flips)),
                _metric("S4 diagnose", "'sign_flip' causes that are real",
                        said_flip["truth_sign_flip"].astype(bool).sum(), len(said_flip)),
            ]
        for r in out:
            r["rule_type"] = int(t)
        rows += out
    return pd.DataFrame(rows)


@dataclass
class Thresholds:
    ai: float = 0.95        # lower 95% bound needed to hand the step to the agent
    review: float = 0.80    # lower bound needed for "agent + human review"
    min_n: int = 30         # fewer cases than this: no verdict


def verdicts(metrics: pd.DataFrame, th: Thresholds = Thresholds()) -> pd.DataFrame:
    """Step x rule type grid. Each cell takes the worst gate metric over all runs: a step is
    handed over only if every run clears the bar on every gate metric. A metric with fewer than
    min_n cases blocks a pass ("too few cases") but not a clear fail."""
    rows = []
    for t in sorted(metrics["rule_type"].unique()):
        for step in STEPS:
            g = metrics[(metrics["rule_type"] == t) & (metrics["step"] == step) & metrics["gate"]]
            if step == "S6 decide":
                v, basis = "human", "no ground truth for materiality or sign-off"
            elif g.empty:
                v, basis = "n/a", "no label for this rule type"
            else:
                big = g[g["n"] >= th.min_n]
                worst = big.loc[big["ci_low"].idxmin()] if not big.empty else None
                lo = worst["ci_low"] if worst is not None else math.nan
                v = "AI" if lo >= th.ai else "AI + human review" if lo >= th.review else "human"
                basis = "" if worst is None else \
                    f"worst: {worst['metric']} {worst['rate']:.1%} (95% CI low {lo:.1%}, n={worst['n']})"
                if len(big) < len(g) and (big.empty or v != "human"):     # a clear fail stands; a pass needs every metric
                    small = g.loc[g["n"].idxmin()]
                    v, basis = "too few cases", f"{small['metric']}: n={small['n']} < {th.min_n}"
            rows.append({"rule_type": int(t), "step": step, "verdict": v, "basis": basis})
    return pd.DataFrame(rows)


def to_agent_runs(cases: pd.DataFrame, run: dict, run_name: str) -> pd.DataFrame:
    """Per-case rows in the dashboard's data/runs/agent_runs.csv schema (BUILD_SPEC section 8).

    A task's cost and latency are split evenly over its cases. error_type: a case not found
    is 'structural', a wrong reported value 'extraction', a wrong calculated value 'calculation'.
    """
    rows = []
    n_per_task = cases.groupby("task_id").size()
    for c in cases.itertuples(index=False):
        rec = run.get(c.task_id) or {}
        n = n_per_task[c.task_id]
        err = None if c.correct else "structural" if not c.matched else \
            "extraction" if not c.reported_ok else "calculation"
        rows.append({"run_id": f"{run_name}:{c.case_id}", "case_id": c.case_id,
                     "agent_framework": rec.get("agent_framework", run_name),
                     "model": rec.get("model", run_name),
                     "answer_reported": c.answer_reported, "answer_calculated": c.answer_calculated,
                     "cost_usd": to_float(rec.get("cost_usd")) / n,
                     "latency_s": to_float(rec.get("latency_s")) / n, "error_type": err})
    return pd.DataFrame(rows)
