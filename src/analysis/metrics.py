"""Pure functions for metrics M1-M4. Input: a (filtered) DataFrame. No files, no state."""
import pandas as pd

COMPARISON_TYPES = (126, 117)   # rule types that have a calculated value


def _share(count: pd.Series, total: int) -> pd.Series:
    return count / total if total else count.astype(float)


def kpis(df: pd.DataFrame) -> dict:
    """Overview KPI row: cases, filings (distinct report.accession), companies (distinct
    entity.cik) and rule types (distinct assertion.type)."""
    return {
        "cases": int(len(df)),
        "filings": int(df["report.accession"].nunique()),
        "companies": int(df["entity.cik"].nunique()),
        "rule_types": int(df["assertion.type"].nunique()),
    }


def cases_by_type(df: pd.DataFrame) -> pd.DataFrame:
    """M1: cases and share per assertion.type, largest first."""
    out = df.groupby("assertion.type").size().rename("cases").reset_index()
    out["share"] = _share(out["cases"], len(df))
    return out.sort_values(["cases", "assertion.type"], ascending=[False, True]).reset_index(drop=True)


def cases_by_code(df: pd.DataFrame) -> pd.DataFrame:
    """M1: cases and share per rule code (with its type), largest first."""
    out = df.groupby(["assertion.code", "assertion.type"]).size().rename("cases").reset_index()
    out["share"] = _share(out["cases"], len(df))
    return out.sort_values(["cases", "assertion.code"], ascending=[False, True]).reset_index(drop=True)


def flag_summary(df: pd.DataFrame) -> dict:
    """M2: counts of unusual cases and the sign_flip rate.

    sign_flip_rate = sign_flip rows / rows that have a calculated_value (None if there are none).
    """
    with_calc = int(df["calculated_value"].notna().sum())
    sign_flip = int(df["sign_flip"].sum())
    return {
        "cases": int(len(df)),
        "sign_flip": sign_flip,
        "period_after_filing": int(df["period_after_filing"].sum()),
        "non_usd": int((df["unit"] != "USD").sum()),
        "non_us_gaap_prefix": int((df["concept_prefix"] != "us-gaap").sum()),
        "rows_with_calculated": with_calc,
        "sign_flip_rate": (sign_flip / with_calc) if with_calc else None,
    }


def discrepancy(df: pd.DataFrame) -> pd.DataFrame:
    """M3: add `abs_diff` and `rel_diff` columns (a new DataFrame).

    Only USD rows of types 126 and 117 that have both values get `abs_diff`.
    `rel_diff` = abs_diff / abs(reported); empty when reported is 0. All other rows are NaN.
    """
    out = df.copy()
    eligible = (out["assertion.type"].isin(COMPARISON_TYPES) & (out["unit"] == "USD")
                & out["reported_value"].notna() & out["calculated_value"].notna())
    abs_diff = (out["reported_value"] - out["calculated_value"]).abs()
    denom = out["reported_value"].abs().where(out["reported_value"] != 0)
    out["abs_diff"] = abs_diff.where(eligible)
    out["rel_diff"] = (abs_diff / denom).where(eligible)
    return out


def discrepancy_summary(df: pd.DataFrame) -> dict:
    """M3: count, median and max of abs_diff and rel_diff over the eligible rows (None if none)."""
    d = discrepancy(df)
    a, r = d["abs_diff"].dropna(), d["rel_diff"].dropna()
    return {
        "cases": int(len(a)),
        "median_abs_diff": float(a.median()) if len(a) else None,
        "max_abs_diff": float(a.max()) if len(a) else None,
        "median_rel_diff": float(r.median()) if len(r) else None,
        "max_rel_diff": float(r.max()) if len(r) else None,
    }


def histogram_counts(df: pd.DataFrame, max_rel: float) -> dict:
    """M3: the numbers for the histogram caption.

    `max_rel` is the right edge of the histogram as a fraction (5.0 = 500%).
    comparison_cases = rows that have an abs_diff; with_rel = rows that also have a rel_diff;
    without_rel = the difference (reported_value is 0); drawn = rel_diff <= max_rel;
    above = rel_diff > max_rel.
    """
    d = discrepancy(df)
    comparison = int(d["abs_diff"].notna().sum())
    rel = d["rel_diff"].dropna()
    return {
        "comparison_cases": comparison,
        "with_rel": int(len(rel)),
        "without_rel": comparison - int(len(rel)),
        "drawn": int((rel <= max_rel).sum()),
        "above": int((rel > max_rel).sum()),
    }


def cases_by_year(df: pd.DataFrame) -> pd.DataFrame:
    """M4: cases per filing year, oldest first."""
    out = df.groupby("report.filing-year").size().rename("cases").reset_index()
    return out.sort_values("report.filing-year").reset_index(drop=True)


def top_companies(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """M4: the n companies with the most cases (ties broken by name)."""
    out = df.groupby(["entity.cik", "entity.name"]).size().rename("cases").reset_index()
    out = out.sort_values(["cases", "entity.name"], ascending=[False, True])
    return out.head(n).reset_index(drop=True)
