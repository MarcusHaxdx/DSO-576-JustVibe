"""The shared DQC filter state and how it is applied."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

PREFIX_CHOICES = ("any", "us-gaap", "other")
PERIOD_CHOICES = ("any", "range", "instant")


@dataclass(frozen=True)
class FilterSpec:
    """Empty tuples mean "all"; the defaults select all 362 cases."""

    types: tuple[int, ...] = ()
    years: tuple[int, ...] = ()
    concept_prefix: str = "any"
    units: tuple[str, ...] = ()
    period_kind: str = "any"
    only_sign_flip: bool = False
    only_period_after_filing: bool = False
    company: str = ""


def apply_filters(df: pd.DataFrame, spec: FilterSpec) -> pd.DataFrame:
    """Return the rows of `df` that pass every filter in `spec` (original order kept)."""
    if spec.concept_prefix not in PREFIX_CHOICES:
        raise ValueError(f"concept_prefix must be one of {PREFIX_CHOICES}")
    if spec.period_kind not in PERIOD_CHOICES:
        raise ValueError(f"period_kind must be one of {PERIOD_CHOICES}")

    mask = pd.Series(True, index=df.index)
    if spec.types:
        mask &= df["assertion.type"].isin(spec.types)
    if spec.years:
        mask &= df["report.filing-year"].isin(spec.years)
    if spec.concept_prefix == "us-gaap":
        mask &= df["concept_prefix"].eq("us-gaap").fillna(False)
    elif spec.concept_prefix == "other":
        mask &= df["concept_prefix"].ne("us-gaap").fillna(True)
    if spec.units:
        mask &= df["unit"].isin(spec.units).fillna(False)
    if spec.period_kind == "range":
        mask &= df["period_start"].notna()
    elif spec.period_kind == "instant":
        mask &= df["period_start"].isna()
    if spec.only_sign_flip:
        mask &= df["sign_flip"]
    if spec.only_period_after_filing:
        mask &= df["period_after_filing"]
    if spec.company.strip():
        mask &= df["entity.name"].str.contains(spec.company.strip(), case=False, regex=False).fillna(False)
    return df[mask.astype(bool)]
