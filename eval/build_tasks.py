#!/usr/bin/env python3
"""Build the agent tasks and the answer key from the clean data.

Run from the repo root:  python eval/build_tasks.py
Writes eval/tasks/tasks.jsonl (one prompt per filing x rule type) and eval/tasks/answer_key.csv.
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from evaluation.tasks import build, write  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--clean", default=ROOT / "data/clean/auditing_clean.csv")
    ap.add_argument("--xbrl", default="herculean_data/auditing_env/XBRL",
                    help="filing folders; paths in the prompts are spelled as given here")
    ap.add_argument("--out", default=ROOT / "eval/tasks")
    a = ap.parse_args()

    tasks, key = build(a.clean, a.xbrl)
    write(tasks, key, a.out)
    by = {}
    for t in tasks:
        s = by.setdefault((t["split"], t["rule_type"]), [0, 0, 0])
        s[0] += 1
        s[1] += t["label"] == "positive"
        s[2] += t["n_expected"]
    print(f"{len(tasks)} tasks, {len(key)} answer-key cases -> {a.out}")
    print("split  rule  tasks  positive  cases")
    for (sp, r), (n, p, c) in sorted(by.items()):
        print(f"{sp:5}  {r:4}  {n:5}  {p:8}  {c:5}")


if __name__ == "__main__":
    main()
