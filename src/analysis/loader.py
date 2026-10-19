"""Read and validate the canonical DQC file and add `case_id`."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

SOURCE_COLUMNS = [
    "assertion.code", "assertion.detail", "assertion.run-date", "assertion.severity",
    "assertion.source", "assertion.type", "entity.cik", "entity.name",
    "report.accepted-timestamp", "report.accession", "report.base-taxonomy",
    "report.creation-software", "report.document-type", "report.entry-url",
    "report.filing-date", "report.filing-year", "report.id", "report.sec-url",
    "report.sic-code", "folder_name",
]
DERIVED_COLUMNS = [
    "timestamp", "concept_prefix", "concept", "period", "unit", "rule_element_id",
    "rule_version", "comparison_type", "reported_value", "calculated_value",
    "period_start", "period_end", "period_after_filing", "sign_flip",
]
COLUMNS = SOURCE_COLUMNS + DERIVED_COLUMNS
ROW_KEY = ["report.accession", "assertion.code", "assertion.detail"]

INT_COLUMNS = ["assertion.type", "report.filing-year"]
FLOAT_COLUMNS = ["reported_value", "calculated_value"]
BOOL_COLUMNS = ["period_after_filing", "sign_flip"]


def make_case_id(accession: str, code: str, detail: str) -> str:
    """First 12 hex characters of SHA-1 over 'accession|code|detail' (UTF-8)."""
    return hashlib.sha1(f"{accession}|{code}|{detail}".encode("utf-8")).hexdigest()[:12]


def load_clean(path: str | Path) -> pd.DataFrame:
    """Return the 362-row DQC frame with typed columns and a unique `case_id`.

    Raises ValueError if a column is missing, a value does not convert, or the row key
    or `case_id` is not unique.
    """
    raw = pd.read_csv(path, dtype="string", keep_default_na=False)
    missing = [c for c in COLUMNS if c not in raw.columns]
    if missing:
        raise ValueError(f"Clean DQC file is missing columns: {missing}")
    df = raw[COLUMNS].copy()

    # Empty text means "not present" (e.g. calculated_value for type 15, period_start for instants).
    df = df.replace("", pd.NA)
    for col in INT_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="raise").astype("int64")
    for col in FLOAT_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="raise").astype("float64")
    for col in BOOL_COLUMNS:
        values = df[col].str.lower()
        if not values.isin(["true", "false"]).all():
            raise ValueError(f"Column {col} must hold only True/False.")
        df[col] = values.eq("true").astype(bool)

    if df[ROW_KEY].duplicated().any():
        raise ValueError("Row key (report.accession, assertion.code, assertion.detail) is not unique.")
    df.insert(
        0,
        "case_id",
        [make_case_id(a, c, d) for a, c, d in zip(df["report.accession"], df["assertion.code"], df["assertion.detail"])],
    )
    if not df["case_id"].is_unique:
        raise ValueError("case_id is not unique.")
    return df
