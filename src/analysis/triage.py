"""M5: rule-based review queue. Not a model and not validated."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from analysis.metrics import discrepancy

RULE_LABELS = {
    "sign_flip": "sign flip",
    "period_after_filing": "period after filing date",
    "non_usd_unit": "non-USD unit",
    "non_us_gaap_prefix": "non-us-gaap concept",
    "large_gap": "large gap",
}
DISPLAY_COLUMNS = ["entity.name", "report.filing-date", "assertion.code", "concept_prefix", "concept",
                   "period", "unit", "reported_value", "calculated_value", "rel_diff"]
RANKED_COLUMNS = ["rank", "case_id", "points", "reasons"] + DISPLAY_COLUMNS


@dataclass(frozen=True)
class TriageConfig:
    """Which rules are on, and the large-gap threshold as a fraction (0.10 = 10%)."""

    sign_flip: bool = True
    period_after_filing: bool = True
    non_usd_unit: bool = True
    non_us_gaap_prefix: bool = True
    large_gap: bool = True
    gap_threshold: float = 0.10


def rank_cases(df: pd.DataFrame, config: TriageConfig) -> pd.DataFrame:
    """Cases that trigger at least one enabled rule, ranked for human review.

    One point per rule triggered. Order: points desc, rel_diff desc (empty last),
    filing date desc, case_id A-Z. `rank` is 1..N in that order.
    """
    work = df.copy()
    rel = discrepancy(df).set_index("case_id")["rel_diff"]
    work["rel_diff"] = work["case_id"].map(rel)

    hits = {
        "sign_flip": work["sign_flip"],
        "period_after_filing": work["period_after_filing"],
        "non_usd_unit": work["unit"].ne("USD").fillna(True),
        "non_us_gaap_prefix": work["concept_prefix"].ne("us-gaap").fillna(True),
        "large_gap": (work["rel_diff"] >= config.gap_threshold).fillna(False),
    }
    enabled = [rule for rule in RULE_LABELS if getattr(config, rule)]
    work["points"] = sum((hits[r].astype(int) for r in enabled), pd.Series(0, index=work.index))
    work["reasons"] = [
        "; ".join(RULE_LABELS[r] for r in enabled if hits[r].loc[i]) for i in work.index
    ]
    work = work[work["points"] > 0].copy()
    work["_filing"] = pd.to_datetime(work["report.filing-date"], errors="coerce")
    work = work.sort_values(
        ["points", "rel_diff", "_filing", "case_id"],
        ascending=[False, False, False, True],
        na_position="last",
        kind="stable",
    ).reset_index(drop=True)
    work["rank"] = range(1, len(work) + 1)
    return work[RANKED_COLUMNS]


def queue_status(ranked: pd.DataFrame, case_id: str) -> dict | None:
    """Rank, points and reasons of one case in a `rank_cases` result, or None if not queued."""
    row = ranked[ranked["case_id"] == case_id]
    if row.empty:
        return None
    r = row.iloc[0]
    return {"rank": int(r["rank"]), "points": int(r["points"]), "reasons": r["reasons"]}
