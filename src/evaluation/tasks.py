"""Turn the clean ground truth into agent tasks and an answer key. Does not run agents.

One task = one filing folder x one rule type. The agent gets the filing files and a plain
description of the rule, never the DQC message. Tasks with no ground-truth row are kept as
negative tasks (the agent should report nothing), so false alarms can be measured.
"""
import hashlib
import json
from pathlib import Path

import pandas as pd

from analysis.loader import load_clean

RULE_TYPES = (15, 117, 126)
DEV_SHARE = 0.2          # share of filings held out for prompt iteration; the rest is the test split

RULES = {
    15: ("sign check",
         "Find numeric facts whose concept should never be negative (for example payments, "
         "expenses, share counts or rates that the taxonomy defines as positive amounts) but "
         "that are reported with a negative value."),
    117: ("total vs dimensional breakdown",
          "On the face financial statements, a line item reported without dimensions must equal "
          "the sum of its members along an axis reported in the same statement for the same "
          "period. Find totals that do not equal the sum of their dimensional breakdown."),
    126: ("total vs sum of child components",
          "In each financial statement, a parent concept must equal the weighted sum of its "
          "child concepts in the calculation linkbase for the same period. Find parents whose "
          "reported value does not equal that sum."),
}
CAUSES = ["sign_flip", "missing_component", "extra_component", "wrong_value",
          "period_or_context", "scale", "other"]
KEY_COLUMNS = ["task_id", "case_id", "folder_name", "assertion.type", "split", "concept_key",
               "period", "unit", "reported_value", "calculated_value", "sign_flip",
               "period_after_filing"]

OUTPUT_SCHEMA = {
    "task_id": "<the task_id above>",
    "findings": [{
        "concept": "prefix:LocalName, e.g. us-gaap:OperatingExpenses",
        "period": "YYYY-MM-DD to YYYY-MM-DD for a duration, YYYY-MM-DD for an instant",
        "unit": "e.g. USD, shares, pure",
        "reported_value": "number as reported in the instance (full value, not scaled)",
        "calculated_value": "number you computed (sum of components or members); null for rule 15",
        "cause": "one of " + ", ".join(CAUSES) + " (rule 15: null)",
        "evidence": "one or two sentences citing the fact values you used",
    }],
}


def split_of(folder: str) -> str:
    """Deterministic dev/test split by filing, so no filing is in both."""
    h = int(hashlib.md5(folder.encode("utf-8")).hexdigest(), 16) % 1000
    return "dev" if h < DEV_SHARE * 1000 else "test"


def task_id(folder: str, rule_type: int) -> str:
    return f"{folder}__{rule_type}"


def filing_files(xbrl_root: Path, folder: str) -> list:
    """Paths of the files in one filing folder, spelled the way xbrl_root was given."""
    d = Path(xbrl_root) / folder
    return sorted(str(p) for p in d.iterdir() if p.is_file() and not p.name.startswith("."))


def make_prompt(tid: str, rule_type: int, files: list) -> str:
    name, rule = RULES[rule_type]
    return "\n".join([
        f"Task {tid}: audit one SEC XBRL filing for one data-quality rule.",
        "",
        f"Rule {rule_type} ({name}): {rule}",
        "",
        "Filing files (instance document, schema, calculation / definition / label / "
        "presentation linkbases, rendered filing if present):",
        *[f"- {f}" for f in files],
        "",
        "Report every fact that breaks this rule, and only those. If none does, return an "
        "empty findings list. Use the values in the instance document, not rounded or scaled ones.",
        "",
        "Answer with one JSON object and nothing else, in this shape:",
        json.dumps(OUTPUT_SCHEMA, indent=2),
    ])


def build(clean_path, xbrl_root):
    """Return (tasks, answer_key): one task per filing folder x rule type, and one key row per case."""
    df = load_clean(clean_path)
    xbrl_root = Path(xbrl_root)
    folders = sorted(p.name for p in xbrl_root.iterdir() if p.is_dir())
    missing = sorted(set(df["folder_name"]) - set(folders))
    if missing:
        raise ValueError(f"{len(missing)} filing folder(s) in the data are not under {xbrl_root}: {missing[:3]}")

    df["task_id"] = [task_id(f, t) for f, t in zip(df["folder_name"], df["assertion.type"])]
    df["split"] = df["folder_name"].map(split_of)
    df["concept_key"] = df["concept_prefix"] + ":" + df["concept"]
    key = df[KEY_COLUMNS].sort_values(["task_id", "concept_key", "period"]).reset_index(drop=True)

    counts = key.groupby("task_id").size()
    tasks = []
    for folder in folders:
        files = filing_files(xbrl_root, folder)
        for t in RULE_TYPES:
            tid = task_id(folder, t)
            n = int(counts.get(tid, 0))
            tasks.append({"task_id": tid, "folder_name": folder, "rule_type": t,
                          "split": split_of(folder), "n_expected": n,
                          # negative tasks rest on the file being complete for this filing and rule
                          "label": "positive" if n else "assumed_clean",
                          "files": files, "prompt": make_prompt(tid, t, files)})
    return tasks, key


def write(tasks, key, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "tasks.jsonl", "w", encoding="utf-8") as fh:
        for t in tasks:
            fh.write(json.dumps(t) + "\n")
    key.to_csv(out_dir / "answer_key.csv", index=False)


def load_tasks(path) -> pd.DataFrame:
    return pd.read_json(path, lines=True)


def load_key(path) -> pd.DataFrame:
    return pd.read_csv(path, dtype={"case_id": str})
