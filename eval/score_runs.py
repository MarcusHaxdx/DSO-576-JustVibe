#!/usr/bin/env python3
"""Score one or more agent run files and print the step x rule-type verdict grid.

Run from the repo root:  python eval/score_runs.py eval/runs/claude-opus_1.jsonl eval/runs/claude-opus_2.jsonl
Writes step_metrics.csv, verdicts.csv and cases.csv to --out (default eval/results/).
Scores the test split unless --split says otherwise; the dev split is for prompt iteration.
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from evaluation.scoring import Thresholds, load_run, score_run, step_metrics, to_agent_runs, verdicts  # noqa: E402
from evaluation.tasks import load_key, load_tasks  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("runs", nargs="+", help="run files (JSON Lines); the file name is the run name")
    ap.add_argument("--tasks", default=ROOT / "eval/tasks/tasks.jsonl")
    ap.add_argument("--key", default=ROOT / "eval/tasks/answer_key.csv")
    ap.add_argument("--xbrl", default=ROOT / "herculean_data/auditing_env/XBRL")
    ap.add_argument("--split", choices=["test", "dev", "all"], default="test")
    ap.add_argument("--out", default=ROOT / "eval/results")
    ap.add_argument("--ai", type=float, default=Thresholds.ai)
    ap.add_argument("--review", type=float, default=Thresholds.review)
    ap.add_argument("--min-n", type=int, default=Thresholds.min_n)
    ap.add_argument("--export-agent-runs", metavar="CSV",
                    help="also write per-case rows in the dashboard's agent_runs.csv schema")
    a = ap.parse_args()

    tasks, key = load_tasks(a.tasks), load_key(a.key)
    known = set(tasks["task_id"])
    if a.split != "all":
        tasks = tasks[tasks["split"] == a.split]
        key = key[key["split"] == a.split]

    all_metrics, all_cases, exports = [], [], []
    for path in a.runs:
        name = Path(path).stem
        run = load_run(path)
        unknown = set(run) - known
        cases, finds, status = score_run(run, tasks, key, a.xbrl)
        print(f"{name}: {(status['status'] == 'ok').sum()} answered, "
              f"{(status['status'] == 'missing').sum()} missing, {(status['status'] == 'invalid').sum()} invalid "
              f"of {len(status)} {a.split} tasks; {len(unknown)} unknown task ids ignored")
        m = step_metrics(cases, finds, status)
        m.insert(0, "run", name)
        cases.insert(0, "run", name)
        all_metrics.append(m)
        all_cases.append(cases)
        exports.append(to_agent_runs(cases.drop(columns="run"), run, name))

    metrics = pd.concat(all_metrics, ignore_index=True)
    grid = verdicts(metrics, Thresholds(a.ai, a.review, a.min_n))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(out / "step_metrics.csv", index=False)
    grid.to_csv(out / "verdicts.csv", index=False)
    pd.concat(all_cases, ignore_index=True).to_csv(out / "cases.csv", index=False)
    if a.export_agent_runs:
        pd.concat(exports, ignore_index=True).to_csv(a.export_agent_runs, index=False)

    pd.set_option("display.width", 200)
    pd.set_option("display.max_colwidth", 90)
    print(f"\nthresholds: AI if 95% CI low >= {a.ai:.0%}, AI + review if >= {a.review:.0%}, "
          f"no verdict below n={a.min_n}; worst run counts\n")
    print(grid.pivot(index="step", columns="rule_type", values="verdict").reindex(grid["step"].unique()).to_string())
    print(f"\nwrote {out}/step_metrics.csv, verdicts.csv, cases.csv")


if __name__ == "__main__":
    main()
