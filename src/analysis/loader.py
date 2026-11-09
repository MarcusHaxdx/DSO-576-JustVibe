"""Load and validate the canonical clean auditing data. Does not compute metrics."""
import hashlib
from pathlib import Path

import pandas as pd

DEFAULT_PATH = Path("data/clean/auditing_clean.csv")

ORIGINAL_COLUMNS = [
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
REQUIRED_COLUMNS = ORIGINAL_COLUMNS + DERIVED_COLUMNS

_DATE_COLUMNS = ["report.filing-date", "report.accepted-timestamp", "assertion.run-date",
                 "timestamp", "period_start", "period_end"]
_TEXT_COLUMNS = {"entity.cik": str, "report.accession": str, "rule_element_id": str}


def message_body(detail: str) -> str:
    """The DQC message without its leading '<timestamp> [<code>] ' part."""
    _, sep, tail = str(detail).partition("] ")
    return tail if sep else str(detail)


def make_case_id(accession: str, code: str, body: str) -> str:
    """Stable 12-character id derived from the row key."""
    return hashlib.sha1(f"{accession}|{code}|{body}".encode("utf-8")).hexdigest()[:12]


def load_clean(path=DEFAULT_PATH) -> pd.DataFrame:
    """Read the clean CSV, check its columns and row key, and add `case_id`.

    Raises FileNotFoundError if the file is missing and ValueError if a required
    column is missing or the row key (accession, code, message text) is not unique.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Clean data not found: {path}")
    header = pd.read_csv(path, nrows=0).columns
    missing = [c for c in REQUIRED_COLUMNS if c not in header]
    if missing:
        raise ValueError(f"Clean data is missing columns: {missing}")

    df = pd.read_csv(path, dtype=_TEXT_COLUMNS, parse_dates=_DATE_COLUMNS)
    for flag in ("sign_flip", "period_after_filing"):
        df[flag] = df[flag].astype(bool)

    bodies = df["assertion.detail"].map(message_body)
    df["case_id"] = [make_case_id(a, c, b) for a, c, b in
                     zip(df["report.accession"], df["assertion.code"], bodies)]
    if df["case_id"].duplicated().any():
        raise ValueError("Row key (accession, code, message text) is not unique")
    return df
