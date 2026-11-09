#!/usr/bin/env python3
"""Clean the HERCULEAN auditing ground-truth file (DQC assertions).

Source : TheFinAI/Herculean (Hugging Face), auditing_env/XBRL/mathematical_reasoning.csv
Input  : read-only. The original file is never modified.
Output : <out>/auditing_clean.csv   cleaned data, one row per DQC assertion
         <out>/cleaning_report.txt  counts, checks and flags
         <out>/sample_50.csv        <= 50 rows incl. difficult cases, with a `sample_reason` column

Run    : python clean_auditing.py
         python clean_auditing.py --input path/to/mathematical_reasoning.csv --out output
"""
import argparse
import os
import re
import sys

import numpy as np
import pandas as pd

DEFAULT_INPUT = "herculean_data/auditing_env/XBRL/mathematical_reasoning.csv"
NUM = r"-?[\d,]+(?:\.\d+)?"          # allows decimals such as -0.0554 and thousands separators

# Rows used for the record checks (checklist item 12) and kept in the sample.
RECORD_CHECK_ROWS = {0: "record check: baseline type 126",
                     13: "record check: company-specific prefix (nmrk)",
                     66: "record check: sign flip",
                     188: "record check: decimal value, period after filing date"}
TEXT_117 = "255,500,000 is not equal to the dimensional breakdown of 142,400,000"

# Columns that are empty by design for type 15 (sign check: no expected value, no rule element id).
STRUCTURAL_NULLS = {15: ["rule_element_id", "calculated_value"]}


def to_num(s):
    return s.replace(",", "") if s else None


def parse_detail(row):
    """Pull structured fields out of the free-text assertion.detail."""
    text = row["assertion.detail"]
    t = row["assertion.type"]
    out = {}

    m = re.match(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})", text)
    out["timestamp"] = m.group(1) if m else None

    # prefix:Concept, any namespace (us-gaap, srt, or a company-specific one such as nmrk)
    m = re.search(r"\b([a-z][\w-]*):([A-Z]\w+)", text)
    out["concept_prefix"] = m.group(1) if m else None
    out["concept"] = m.group(2) if m else None

    m = re.search(r"(?:Total period|Period)\s*:\s*([\d-]+(?:\s*to\s*[\d-]+)?)", text)
    out["period"] = m.group(1).strip() if m else None

    # whole value up to the end of the line (units can contain "/", e.g. USD/bbl)
    m = re.search(r"Unit(?: of Total)?[ \t]*:[ \t]*([^\r\n]+?)[ \t]*$", text, re.M)
    out["unit"] = m.group(1) if m else None

    m = re.search(r"Rule Element Id\s*:\s*(\d+)", text)
    out["rule_element_id"] = m.group(1) if m else None

    m = re.search(r"Rule version:\s*(.+?)\s*$", text)
    out["rule_version"] = m.group(1) if m else None

    out["comparison_type"] = None
    out["reported_value"] = None
    out["calculated_value"] = None

    if t == 126:      # total vs sum of child components in the calculation linkbase
        out["comparison_type"] = "calculation_sum"
        m = re.search(rf"Total Value\s*:\s*({NUM})", text)
        out["reported_value"] = to_num(m.group(1)) if m else None
        m = re.search(rf"sum of these child components is ({NUM})", text)
        out["calculated_value"] = to_num(m.group(1)) if m else None
    elif t == 117:    # total vs dimensional breakdown
        out["comparison_type"] = "dimensional_breakdown"
        m = re.search(rf"value of ({NUM}) is not equal to the dimensional breakdown of ({NUM})", text)
        if m:
            out["reported_value"] = to_num(m.group(1))
            out["calculated_value"] = to_num(m.group(2))
    elif t == 15:     # sign check: there is no expected value by design
        out["comparison_type"] = "sign_check"
        m = re.search(rf"has a value of ({NUM}) which is", text)
        out["reported_value"] = to_num(m.group(1)) if m else None

    return pd.Series(out)


class Report:
    def __init__(self):
        self.lines = []

    def add(self, text=""):
        print(text)
        self.lines.append(text)

    def save(self, path):
        with open(path, "w") as f:
            f.write("\n".join(self.lines) + "\n")


def build_sample(clean, n=50, seed=42):
    reasons = {}

    def tag(idx, why):
        for i in idx:
            reasons.setdefault(i, []).append(why)

    tag(clean.index[clean["sign_flip"]], "sign flip (calculated == -reported)")
    tag(clean.index[clean["period_after_filing"]], "period ends after filing date")
    tag([i for i in RECORD_CHECK_ROWS if i in clean.index], "record check")
    for i in clean.index[clean["assertion.detail"].str.contains(TEXT_117, regex=False)][:1]:
        tag([i], "record check: type 117 total vs dimensional breakdown")

    need = max(0, n - len(reasons))
    types = sorted(clean["assertion.type"].unique())
    per = need // len(types)
    extra = need - per * len(types)
    rest = clean.drop(index=list(reasons))
    for k, t in enumerate(types):
        take = per + (1 if k < extra else 0)
        pool = rest[rest["assertion.type"] == t]
        pick = pool.sample(min(take, len(pool)), random_state=seed).index
        tag(pick, f"random sample, type {t}")

    sample = clean.loc[sorted(reasons)].copy()
    sample.insert(0, "sample_reason", [" | ".join(reasons[i]) for i in sample.index])
    return sample.head(n)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", default=DEFAULT_INPUT)
    ap.add_argument("--out", default="output")
    args = ap.parse_args()

    rep = Report()
    os.makedirs(args.out, exist_ok=True)

    # ---- load (read-only) -------------------------------------------------
    df = pd.read_csv(args.input, dtype={"entity.cik": str})
    rep.add(f"input file : {args.input}")
    rep.add(f"rows, cols : {df.shape}")

    # ---- parse the free text ----------------------------------------------
    parsed = df.apply(parse_detail, axis=1)
    clean = pd.concat([df.copy(), parsed], axis=1)
    n0 = len(clean)

    # ---- item 4: types ------------------------------------------------------
    rep.add("\n[item 4] type conversions (failed = values that could not be converted, set to NaN)")
    for c in ["reported_value", "calculated_value"]:
        before = int(clean[c].notnull().sum())
        clean[c] = pd.to_numeric(clean[c], errors="coerce")
        after = int(clean[c].notnull().sum())
        rep.add(f"  {c}: non-null before={before}, after={after}, failed={before - after}")
    for c in ["report.filing-date", "report.accepted-timestamp", "assertion.run-date"]:
        conv = pd.to_datetime(clean[c], errors="coerce")
        rep.add(f"  {c}: failed conversions = {int(conv.isnull().sum())}")
        clean[c] = conv
    clean["timestamp"] = pd.to_datetime(clean["timestamp"], format="%Y-%m-%d %H:%M:%S,%f", errors="coerce")
    rep.add(f"  timestamp (from detail text): failed conversions = {int(clean['timestamp'].isnull().sum())}")

    # ---- period: range or single date (instant) ------------------------------
    has_range = clean["period"].str.contains(" to ", na=False)
    parts = clean["period"].str.split(r"\s*to\s*", expand=True)
    if parts.shape[1] < 2:
        parts[1] = None
    clean["period_start"] = pd.to_datetime(parts[0].where(has_range), errors="coerce")
    clean["period_end"] = pd.to_datetime(parts[1].where(has_range, parts[0]), errors="coerce")
    rep.add(f"  period: {int(has_range.sum())} ranges, {int((~has_range).sum())} single dates (instant)")

    # ---- item 5: text -------------------------------------------------------
    before = clean["entity.name"]
    after = before.str.strip().str.replace(r"\s+", " ", regex=True)   # \s also matches the non-breaking space
    changed = before != after
    clean["entity.name"] = after
    rep.add(f"\n[item 5] entity.name changed by trim / whitespace collapse: {int(changed.sum())}")
    for i in clean.index[changed][:3]:
        rep.add(f"  {before[i]!r} -> {after[i]!r}")
    clean["entity.cik"] = clean["entity.cik"].astype(str).str.zfill(10)   # CIK is a 10-digit identifier
    rep.add(f"  unique entity.name before/after: {df['entity.name'].nunique()}/{clean['entity.name'].nunique()}"
            f" | unique entity.cik: {clean['entity.cik'].nunique()}"
            f" | max names per cik: {int(clean.groupby('entity.cik')['entity.name'].nunique().max())}")

    # ---- item 6: duplicates -----------------------------------------------------
    clean["body"] = clean["assertion.detail"].str.split(r"\]\s", n=1, regex=True).str[1]
    row_key = ["report.accession", "assertion.code", "body"]
    weak_key = ["report.accession", "assertion.code", "concept_prefix", "concept", "period", "reported_value"]
    n_exact = int(df.duplicated().sum())
    n_key = int(clean.duplicated(subset=row_key).sum())
    rep.add("\n[item 6] duplicates")
    rep.add(f"  exact duplicate rows (original file): {n_exact}")
    rep.add(f"  repeated report.id: {int(df['report.id'].duplicated().sum())} (a filing has several assertions)")
    rep.add(f"  repeated on a short key {weak_key}: {int(clean.duplicated(subset=weak_key).sum())}"
            " (different statements / dimensions, so NOT removed)")
    rep.add(f"  repeated on the final row key {row_key}: {n_key}")

    # ---- item 7: missing data ------------------------------------------------------
    fields = ["timestamp", "concept_prefix", "concept", "period", "unit", "rule_element_id",
              "rule_version", "reported_value", "calculated_value"]
    nulls = clean[fields].isnull().groupby(clean["assertion.type"]).sum().T
    rep.add("\n[item 7] missing values in extracted fields, by assertion.type")
    rep.add(nulls.to_string())
    unexpected = 0
    for t in nulls.columns:
        for f in fields:
            if nulls.loc[f, t] and f not in STRUCTURAL_NULLS.get(t, []):
                unexpected += int(nulls.loc[f, t])
    rep.add(f"  unexpected missing values (not structural): {unexpected}")
    rep.add("  structural = type 15 has no rule element id and no expected value, so these stay empty (not filled, rows kept)")
    for c in df.columns:
        if df[c].isnull().any():
            rep.add(f"  original column with missing values: {c} = {int(df[c].isnull().sum())}")

    # ---- item 8: flags (mark, never correct) -----------------------------------
    clean["period_after_filing"] = clean["period_end"] > clean["report.filing-date"]
    clean["sign_flip"] = (clean["calculated_value"] == -clean["reported_value"]) & (clean["reported_value"] != 0)
    same = (clean["calculated_value"] == clean["reported_value"]) & clean["calculated_value"].notnull()
    n_cmp = int(clean["calculated_value"].notnull().sum())
    rep.add("\n[item 8] suspicious values: flagged, values are NOT changed")
    rep.add(f"  sign_flip (calculated == -reported): {int(clean['sign_flip'].sum())}")
    rep.add(f"  period_after_filing: {int(clean['period_after_filing'].sum())}")
    rep.add(f"  reported == calculated (every row is a DQC error, so expected 0): {int(same.sum())}")
    rep.add(f"  period_start after period_end: {int((clean['period_start'] > clean['period_end']).sum())}")

    # ---- item 10 / 11: reconciliation and denominators ------------------------------
    rep.add("\n[item 10] reconciliation")
    rep.add(f"  rows: original {n0} -> cleaned {len(clean)} | dropped: {n0 - len(clean)}")
    t_before = df["assertion.type"].value_counts().sort_index()
    t_after = clean["assertion.type"].value_counts().sort_index()
    rep.add("  rows by assertion.type (original / cleaned): "
            + ", ".join(f"{t}: {t_before[t]}/{t_after[t]}" for t in t_before.index))
    rep.add("[item 11] denominators")
    rep.add(f"  sign_flip rate = {int(clean['sign_flip'].sum())}/{n_cmp} = "
            f"{clean['sign_flip'].sum() / max(n_cmp, 1):.1%} (denominator = rows that have a calculated_value; "
            f"{int(clean['calculated_value'].isnull().sum())} type-15 rows have none)")

    # ---- hard checks: stop if the cleaning changed the data in an unaccounted way ------
    problems = []
    if len(clean) != len(df):
        problems.append("row count changed")
    if not (t_before == t_after).all():
        problems.append("rows by type changed")
    if n_key != 0:
        problems.append("final row key is not unique")
    if problems:
        rep.add("\nFAILED CHECKS: " + "; ".join(problems))
        rep.save(os.path.join(args.out, "cleaning_report.txt"))
        sys.exit(1)

    # ---- write outputs -------------------------------------------------------------
    clean = clean.drop(columns=["body"])
    clean.to_csv(os.path.join(args.out, "auditing_clean.csv"), index=False)
    sample = build_sample(clean)
    sample.to_csv(os.path.join(args.out, "sample_50.csv"), index=False)
    rep.add(f"\nwrote {args.out}/auditing_clean.csv ({len(clean)} rows), "
            f"{args.out}/sample_50.csv ({len(sample)} rows), {args.out}/cleaning_report.txt")
    rep.save(os.path.join(args.out, "cleaning_report.txt"))


if __name__ == "__main__":
    main()
