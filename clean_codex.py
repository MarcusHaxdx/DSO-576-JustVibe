"""Clean the DQC mathematical-reasoning assertions without changing the source CSV."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


# Resolve paths from this script so running it from another directory is safe.
ROOT = Path(__file__).resolve().parent
INPUT_PATH = ROOT / "herculean_data/auditing_env/XBRL/mathematical_reasoning.csv"
OUTPUT_DIR = ROOT / "output_codex"
OUTPUT_PATH = OUTPUT_DIR / "mathematical_reasoning_clean.csv"

# Amounts in the messages can contain a sign, comma separators, and decimals.
NUMBER = r"[+-]?(?:\d[\d,]*)(?:\.\d+)?"

TIMESTAMP_RE = re.compile(
    r"^\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d+)"
)
PERIOD_RE = re.compile(
    r"(?:Total period|Period)\s*:\s*"
    r"(\d{4}-\d{2}-\d{2}(?:\s+to\s+\d{4}-\d{2}-\d{2})?)",
    re.IGNORECASE,
)
UNIT_RE = re.compile(
    r"^\s*(?:Unit of Total|Unit)\s*:\s*(.*?)\s*$", re.IGNORECASE | re.MULTILINE
)

# Use the identifying phrase for each template. This avoids accidentally taking
# a taxonomy prefix/name from a component or dimension elsewhere in the message.
CONCEPT_PATTERNS = {
    "126": re.compile(
        r"Total Element\s*:\s*([A-Za-z_][\w.-]*):([A-Za-z_][\w.-]*)",
        re.IGNORECASE,
    ),
    "117": re.compile(
        r"\bconcept\s+([A-Za-z_][\w.-]*):([A-Za-z_][\w.-]*)\s+with a value of",
        re.IGNORECASE,
    ),
    "15": re.compile(
        r"^.*?\]\s*([A-Za-z_][\w.-]*):([A-Za-z_][\w.-]*)\s+has a value of",
        re.IGNORECASE | re.DOTALL,
    ),
}

TYPE_126_REPORTED_RE = re.compile(
    rf"Total Value\s*:\s*({NUMBER})", re.IGNORECASE
)
TYPE_126_CALCULATED_RE = re.compile(
    rf"The sum of these child components is\s+({NUMBER})", re.IGNORECASE
)
TYPE_117_VALUES_RE = re.compile(
    rf"with a value of\s+({NUMBER})\s+is not equal to "
    rf"the dimensional breakdown of\s+({NUMBER})",
    re.IGNORECASE,
)
TYPE_15_REPORTED_RE = re.compile(
    rf"has a value of\s+({NUMBER})\s+which is less than zero", re.IGNORECASE
)


def first_group(pattern: re.Pattern[str], text: str) -> object:
    """Return the first capture, or pandas' missing marker if it is absent."""
    match = pattern.search(text)
    return match.group(1) if match else pd.NA


def parse_detail(row: pd.Series) -> pd.Series:
    """Extract only the fields requested from one assertion.detail message."""
    text = row["assertion.detail"]
    assertion_type = row["assertion.type"]

    timestamp = first_group(TIMESTAMP_RE, text)
    period = first_group(PERIOD_RE, text)
    unit = first_group(UNIT_RE, text)

    concept_match = CONCEPT_PATTERNS[assertion_type].search(text)
    if concept_match:
        concept_prefix, concept_name = concept_match.groups()
    else:
        concept_prefix, concept_name = pd.NA, pd.NA

    # Extract reported/calculated values according to the three exact templates.
    # Type 15 deliberately has no calculated value.
    reported_raw: object = pd.NA
    calculated_raw: object = pd.NA
    if assertion_type == "126":
        reported_raw = first_group(TYPE_126_REPORTED_RE, text)
        calculated_raw = first_group(TYPE_126_CALCULATED_RE, text)
    elif assertion_type == "117":
        values_match = TYPE_117_VALUES_RE.search(text)
        if values_match:
            reported_raw, calculated_raw = values_match.groups()
    elif assertion_type == "15":
        reported_raw = first_group(TYPE_15_REPORTED_RE, text)

    return pd.Series(
        {
            "timestamp_raw": timestamp,
            "concept_prefix": concept_prefix,
            "concept_name": concept_name,
            "period": period,
            "unit": unit,
            "reported_value_raw": reported_raw,
            "calculated_value_raw": calculated_raw,
        }
    )


def convert_date(
    frame: pd.DataFrame,
    column: str,
    failures: dict[str, int],
    *,
    date_format: str | None = None,
) -> None:
    """Convert a date column in place and count only failed non-missing inputs."""
    original = frame[column]
    converted = pd.to_datetime(original, format=date_format, errors="coerce")
    failures[column] = int((original.notna() & converted.isna()).sum())
    frame[column] = converted


def convert_amount(
    frame: pd.DataFrame, raw_column: str, output_column: str, failures: dict[str, int]
) -> None:
    """Remove display commas, convert an amount, and record failed conversions."""
    original = frame[raw_column]
    normalized = original.str.replace(",", "", regex=False)
    converted = pd.to_numeric(normalized, errors="coerce")
    failures[output_column] = int((original.notna() & converted.isna()).sum())
    frame[output_column] = converted


def main() -> None:
    # Step 1: read every source field as text. This preserves identifiers such as
    # CIK and leaves the original file untouched.
    source = pd.read_csv(INPUT_PATH, dtype="string")
    rows_before = len(source)
    type_counts_before = source["assertion.type"].value_counts().sort_index()
    duplicate_rows_before = int(source.duplicated().sum())

    # Step 2: parse the free-text message with its assertion-type-specific rules.
    parsed = source.apply(parse_detail, axis=1)
    clean = pd.concat([source.copy(), parsed], axis=1)

    # Step 3: convert extracted amounts to numbers without correcting their values.
    conversion_failures: dict[str, int] = {}
    convert_amount(clean, "reported_value_raw", "reported_value", conversion_failures)
    convert_amount(clean, "calculated_value_raw", "calculated_value", conversion_failures)
    clean.drop(columns=["reported_value_raw", "calculated_value_raw"], inplace=True)

    # Step 4: convert the extracted timestamp and existing date fields to datetime.
    clean.rename(columns={"timestamp_raw": "timestamp"}, inplace=True)
    convert_date(
        clean,
        "timestamp",
        conversion_failures,
        date_format="%Y-%m-%d %H:%M:%S,%f",
    )
    for date_column in (
        "assertion.run-date",
        "report.accepted-timestamp",
        "report.filing-date",
    ):
        convert_date(clean, date_column, conversion_failures)

    # Step 5: split each period. For an instant, both boundaries are that date;
    # for a duration, they are the dates on either side of "to".
    period_parts = clean["period"].str.split(r"\s+to\s+", n=1, expand=True)
    clean["period_start"] = period_parts[0]
    clean["period_end"] = period_parts[1].where(period_parts[1].notna(), period_parts[0])
    convert_date(clean, "period_start", conversion_failures, date_format="%Y-%m-%d")
    convert_date(clean, "period_end", conversion_failures, date_format="%Y-%m-%d")

    # Step 6: standardize only entity.name whitespace (including NBSP via \s) and
    # represent every non-missing CIK as a zero-padded 10-character string.
    clean["entity.name"] = clean["entity.name"].str.strip().str.replace(
        r"\s+", " ", regex=True
    )
    clean["entity.cik"] = clean["entity.cik"].str.zfill(10)

    # Step 7: flag suspicious relationships; never modify either underlying value.
    clean["sign_flip"] = (
        clean["calculated_value"].notna()
        & clean["reported_value"].notna()
        & (clean["reported_value"] != 0)
        & (clean["calculated_value"] == -clean["reported_value"])
    ).astype(bool)
    clean["period_after_filing"] = (
        clean["period_end"].notna()
        & clean["report.filing-date"].notna()
        & (clean["period_end"] > clean["report.filing-date"])
    ).astype(bool)

    # Step 8: save every row. Missing values remain missing, and no deduplication or
    # value imputation is performed.
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    clean.to_csv(OUTPUT_PATH, index=False)

    # Step 9: print the requested reconciliation and data-quality report.
    rows_after = len(clean)
    type_counts_after = clean["assertion.type"].value_counts().sort_index()
    counts_by_type = pd.concat(
        [type_counts_before.rename("before"), type_counts_after.rename("after")], axis=1
    ).fillna(0).astype(int)

    report_fields = [
        "timestamp",
        "concept_prefix",
        "concept_name",
        "period",
        "period_start",
        "period_end",
        "unit",
        "reported_value",
        "calculated_value",
    ]
    missing_by_type = (
        clean[report_fields]
        .isna()
        .groupby(clean["assertion.type"])
        .sum()
        .astype(int)
    )

    print("=== Cleaning report ===")
    print(f"Rows before: {rows_before}")
    print(f"Rows after:  {rows_after}")
    print("\nCounts by assertion.type:")
    print(counts_by_type.to_string())
    print("\nFailed conversions (non-missing input converted to missing):")
    for field, count in conversion_failures.items():
        print(f"{field}: {count}")
    print("\nMissing extracted values by assertion.type:")
    print(missing_by_type.to_string())
    print("\nDuplicates:")
    print(f"Exact duplicate rows before cleaning: {duplicate_rows_before}")
    print(f"Exact duplicate rows after cleaning:  {int(clean.duplicated().sum())}")
    print("\nFlag counts:")
    print(f"sign_flip: {int(clean['sign_flip'].sum())}")
    print(f"period_after_filing: {int(clean['period_after_filing'].sum())}")
    print(f"\nSaved: {OUTPUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
