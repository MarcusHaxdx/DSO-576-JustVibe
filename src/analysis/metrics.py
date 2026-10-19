"""DQC metrics M1-M4 and the KPI row. Every function takes an already-filtered frame."""
from __future__ import annotations

import pandas as pd

TYPE_LABELS = {
    15: "15 · sign check",
    117: "117 · total vs dimensional breakdown",
    126: "126 · total vs sum of child components",
}
COMPARISON_TYPES = (117, 126)

_DISCREPANCY_COLUMNS = ["case_id", "assertion.type", "reported_value", "calculated_value",
                        "abs_diff", "rel_diff", "sign_flip"]


def _share(counts: pd.Series, total: int) -> pd.Series:
    return counts / total if total else counts * 0.0


def kpis(df: pd.DataFrame) -> dict:
    """Cases, filings (distinct accession), companies (distinct CIK), rule types."""
    return {
        "cases": int(len(df)),
        "filings": int(df["report.accession"].nunique()),
        "companies": int(df["entity.cik"].nunique()),
        "rule_types": int(df["assertion.type"].nunique()),
    }


def cases_by_type(df: pd.DataFrame) -> pd.DataFrame:
    """M1: columns `assertion.type`, `label`, `cases`, `share`; ordered by type code."""
    counts = df["assertion.type"].value_counts().sort_index()
    out = counts.rename("cases").rename_axis("assertion.type").reset_index()
    out.insert(1, "label", out["assertion.type"].map(TYPE_LABELS))
    out["share"] = _share(out["cases"], len(df))
    return out


def cases_by_code(df: pd.DataFrame) -> pd.DataFrame:
    """M1: columns `assertion.code`, `assertion.type`, `cases`, `share`; most cases first, then code A-Z."""
    out = (
        df.groupby(["assertion.code", "assertion.type"]).size().rename("cases").reset_index()
        .sort_values(["cases", "assertion.code"], ascending=[False, True], kind="stable")
        .reset_index(drop=True)
    )
    out["share"] = _share(out["cases"], len(df))
    return out


def flag_summary(df: pd.DataFrame) -> pd.DataFrame:
    """M2: one row per flag with `cases`, `denominator`, `rate`.

    The sign_flip denominator is rows that have a `calculated_value`; the others use all rows.
    """
    n = len(df)
    with_calc = int(df["calculated_value"].notna().sum())
    rows = [
        ("sign_flip", "Sign flip (calculated = −reported)", int(df["sign_flip"].sum()), with_calc),
        ("period_after_filing", "Period ends after filing date", int(df["period_after_filing"].sum()), n),
        ("non_usd_unit", "Unit is not USD", int(df["unit"].ne("USD").fillna(True).sum()), n),
        ("non_us_gaap_prefix", "Concept prefix is not us-gaap", int(df["concept_prefix"].ne("us-gaap").fillna(True).sum()), n),
    ]
    out = pd.DataFrame(rows, columns=["flag", "label", "cases", "denominator"])
    out["rate"] = [c / d if d else float("nan") for c, d in zip(out["cases"], out["denominator"])]
    return out


def discrepancy(df: pd.DataFrame) -> pd.DataFrame:
    """M3: comparison rows (USD, type 117 or 126, calculated present) with `abs_diff` and `rel_diff`.

    `rel_diff` is a fraction (2.0 = 200%) and is empty when `reported_value` is 0.
    """
    comp = df[
        df["assertion.type"].isin(COMPARISON_TYPES)
        & df["unit"].eq("USD").fillna(False)
        & df["calculated_value"].notna()
    ].copy()
    comp["abs_diff"] = (comp["reported_value"] - comp["calculated_value"]).abs()
    denom = comp["reported_value"].abs()
    comp["rel_diff"] = (comp["abs_diff"] / denom).where(denom != 0)
    return comp[_DISCREPANCY_COLUMNS].reset_index(drop=True)


def discrepancy_summary(df: pd.DataFrame) -> dict:
    """M3 summary over all comparison rows (not clipped)."""
    d = discrepancy(df)
    rel = d["rel_diff"].dropna()
    return {
        "comparison_cases": int(len(d)),
        "with_rel_diff": int(len(rel)),
        "without_rel_diff": int(d["rel_diff"].isna().sum()),
        "median_rel_diff": float(rel.median()) if len(rel) else None,
        "max_rel_diff": float(rel.max()) if len(rel) else None,
        "median_abs_diff": float(d["abs_diff"].median()) if len(d) else None,
    }


def histogram_counts(df: pd.DataFrame, max_rel: float = 5.0) -> dict:
    """Caption counts for the clipped histogram: drawn (rel_diff <= max_rel), above, without rel_diff."""
    d = discrepancy(df)
    rel = d["rel_diff"]
    return {
        "drawn": int((rel <= max_rel).sum()),
        "above": int((rel > max_rel).sum()),
        "without_rel_diff": int(rel.isna().sum()),
        "max_rel": max_rel,
    }


def cases_by_year(df: pd.DataFrame) -> pd.DataFrame:
    """M4: columns `report.filing-year`, `cases`; ordered by year."""
    return (
        df["report.filing-year"].value_counts().sort_index()
        .rename("cases").rename_axis("report.filing-year").reset_index()
    )


def top_companies(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """M4: `entity.name`, `entity.cik`, `cases`; most cases first, ties by name A-Z."""
    out = (
        df.groupby(["entity.cik", "entity.name"]).size().rename("cases").reset_index()
        .sort_values(["cases", "entity.name"], ascending=[False, True], kind="stable")
        .head(n).reset_index(drop=True)
    )
    return out[["entity.name", "entity.cik", "cases"]]
