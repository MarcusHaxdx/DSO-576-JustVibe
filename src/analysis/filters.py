"""Apply the dashboard's global filters. Does not read files or compute metrics."""
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class FilterSpec:
    """Empty tuples / 'any' / False / '' mean 'no restriction'."""
    assertion_types: tuple = ()
    filing_years: tuple = ()
    prefix: str = "any"            # "any" | "us-gaap" | "other"
    units: tuple = ()
    period_kind: str = "any"       # "any" | "range" | "instant"
    only_sign_flip: bool = False
    only_period_after_filing: bool = False
    company_query: str = ""         # case-insensitive substring of entity.name

    def __post_init__(self):
        if self.prefix not in ("any", "us-gaap", "other"):
            raise ValueError(f"prefix must be 'any', 'us-gaap' or 'other', got {self.prefix!r}")
        if self.period_kind not in ("any", "range", "instant"):
            raise ValueError(f"period_kind must be 'any', 'range' or 'instant', got {self.period_kind!r}")


def apply_filters(df: pd.DataFrame, spec: FilterSpec) -> pd.DataFrame:
    """Return the rows of `df` that satisfy every active filter (a new DataFrame)."""
    mask = pd.Series(True, index=df.index)
    if spec.assertion_types:
        mask &= df["assertion.type"].isin(spec.assertion_types)
    if spec.filing_years:
        mask &= df["report.filing-year"].isin(spec.filing_years)
    if spec.prefix == "us-gaap":
        mask &= df["concept_prefix"] == "us-gaap"
    elif spec.prefix == "other":
        mask &= df["concept_prefix"] != "us-gaap"
    if spec.units:
        mask &= df["unit"].isin(spec.units)
    if spec.period_kind == "range":
        mask &= df["period_start"].notna()
    elif spec.period_kind == "instant":
        mask &= df["period_start"].isna()
    if spec.only_sign_flip:
        mask &= df["sign_flip"]
    if spec.only_period_after_filing:
        mask &= df["period_after_filing"]
    if spec.company_query.strip():
        mask &= df["entity.name"].str.contains(spec.company_query.strip(), case=False, regex=False, na=False)
    return df[mask].copy()
