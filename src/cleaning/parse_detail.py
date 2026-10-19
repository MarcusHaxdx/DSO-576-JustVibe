"""Derived fields parsed from the free-text DQC `assertion.detail` message.

Ported from Jinyang Yuan's Module 6 cleaner (`clean_auditing.py`, branch `Jinyang-Yuan`).
The parsing rules are unchanged; dates and the timestamp are kept as text so the clean
file stores source-formatted values.
"""
from __future__ import annotations

import re

import pandas as pd

NUM = r"-?[\d,]+(?:\.\d+)?"  # allows decimals such as -0.0554 and thousands separators

DERIVED_COLUMNS = [
    "timestamp",
    "concept_prefix",
    "concept",
    "period",
    "unit",
    "rule_element_id",
    "rule_version",
    "comparison_type",
    "reported_value",
    "calculated_value",
    "period_start",
    "period_end",
    "period_after_filing",
    "sign_flip",
]

# Empty by design: type 15 (sign check) has no expected value and no rule element id.
STRUCTURAL_NULLS = {15: ["rule_element_id", "calculated_value"]}


def _to_num(text: str | None) -> str | None:
    return text.replace(",", "") if text else None


def parse_one(text: str, assertion_type: int) -> dict:
    """Return the parsed fields of one assertion message."""
    out: dict = {}

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

    if assertion_type == 126:  # total vs sum of child components in the calculation linkbase
        out["comparison_type"] = "calculation_sum"
        m = re.search(rf"Total Value\s*:\s*({NUM})", text)
        out["reported_value"] = _to_num(m.group(1)) if m else None
        m = re.search(rf"sum of these child components is ({NUM})", text)
        out["calculated_value"] = _to_num(m.group(1)) if m else None
    elif assertion_type == 117:  # total vs dimensional breakdown
        out["comparison_type"] = "dimensional_breakdown"
        m = re.search(rf"value of ({NUM}) is not equal to the dimensional breakdown of ({NUM})", text)
        if m:
            out["reported_value"] = _to_num(m.group(1))
            out["calculated_value"] = _to_num(m.group(2))
    elif assertion_type == 15:  # sign check: there is no expected value by design
        out["comparison_type"] = "sign_check"
        m = re.search(rf"has a value of ({NUM}) which is", text)
        out["reported_value"] = _to_num(m.group(1)) if m else None

    return out


def add_derived_fields(cleaned: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Append the 14 derived columns; return the frame and a dict of checks.

    `cleaned` must already have integer `assertion.type` and text `report.filing-date`.
    """
    parsed = pd.DataFrame(
        [parse_one(text, int(t)) for text, t in zip(cleaned["assertion.detail"], cleaned["assertion.type"])],
        index=cleaned.index,
    )
    parsed["reported_value"] = pd.to_numeric(parsed["reported_value"], errors="coerce")
    parsed["calculated_value"] = pd.to_numeric(parsed["calculated_value"], errors="coerce")

    has_range = parsed["period"].str.contains(" to ", na=False)
    parts = parsed["period"].str.split(r"\s*to\s*", regex=True, expand=True)
    if parts.shape[1] < 2:
        parts[1] = None
    parsed["period_start"] = parts[0].where(has_range)
    parsed["period_end"] = parts[1].where(has_range, parts[0])

    start = pd.to_datetime(parsed["period_start"], errors="coerce")
    end = pd.to_datetime(parsed["period_end"], errors="coerce")
    filing = pd.to_datetime(cleaned["report.filing-date"], errors="coerce")
    parsed["period_after_filing"] = end > filing
    parsed["sign_flip"] = (parsed["calculated_value"] == -parsed["reported_value"]) & (parsed["reported_value"] != 0)

    unexpected_nulls = 0
    for field in ["timestamp", "concept_prefix", "concept", "period", "unit",
                  "rule_element_id", "rule_version", "reported_value", "calculated_value"]:
        missing = parsed[field].isna()
        allowed = cleaned["assertion.type"].map(lambda t: field in STRUCTURAL_NULLS.get(int(t), []))
        unexpected_nulls += int((missing & ~allowed).sum())

    checks = {
        "derived_columns": DERIVED_COLUMNS,
        "unexpected_missing_derived_values": unexpected_nulls,
        "period_ranges": int(has_range.sum()),
        "period_instants": int((~has_range).sum()),
        "period_parse_failures": int(end.isna().sum() + (start.isna() & has_range).sum()),
        "reported_value_missing": int(parsed["reported_value"].isna().sum()),
        "calculated_value_missing": int(parsed["calculated_value"].isna().sum()),
        "sign_flip": int(parsed["sign_flip"].sum()),
        "period_after_filing": int(parsed["period_after_filing"].sum()),
        "reported_equals_calculated": int((parsed["reported_value"] == parsed["calculated_value"]).sum()),
        "unit_counts": parsed["unit"].value_counts().to_dict(),
        "concept_prefix_counts": parsed["concept_prefix"].value_counts().to_dict(),
    }
    return pd.concat([cleaned, parsed[DERIVED_COLUMNS]], axis=1), checks
