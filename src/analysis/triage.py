"""M5: rule-based review ranking. Not a model and not validated."""
from dataclasses import dataclass

import pandas as pd

from .metrics import discrepancy

RULE_LABELS = {
    "sign_flip": "sign flip",
    "period_after_filing": "period after filing date",
    "non_usd": "non-USD unit",
    "non_us_gaap_prefix": "non-us-gaap prefix",
    "large_gap": "large gap",
}
RULE_ORDER = tuple(RULE_LABELS)

QUEUE_COLUMNS = ["rank", "case_id", "points", "reasons", "entity.name", "report.filing-date",
                 "assertion.type", "assertion.code", "concept", "period", "unit",
                 "reported_value", "calculated_value", "rel_diff"]


@dataclass(frozen=True)
class TriageConfig:
    rules_on: tuple = RULE_ORDER
    gap_threshold: float = 0.10     # large_gap fires when rel_diff >= this

    def __post_init__(self):
        unknown = [r for r in self.rules_on if r not in RULE_LABELS]
        if unknown:
            raise ValueError(f"Unknown triage rules: {unknown}")


def rank_cases(df: pd.DataFrame, cfg: TriageConfig = TriageConfig()) -> pd.DataFrame:
    """Rank the cases that trigger at least one active rule (one point per rule).

    Order: points, then rel_diff, then filing date (all descending, empty last), then case_id.
    Returns QUEUE_COLUMNS; `reasons` lists the rules triggered. `df` needs a `case_id` column.
    """
    d = discrepancy(df)
    hits = {
        "sign_flip": d["sign_flip"].astype(bool),
        "period_after_filing": d["period_after_filing"].astype(bool),
        "non_usd": d["unit"] != "USD",
        "non_us_gaap_prefix": d["concept_prefix"] != "us-gaap",
        "large_gap": d["rel_diff"] >= cfg.gap_threshold,    # NaN compares False
    }
    active = [r for r in RULE_ORDER if r in cfg.rules_on]
    if not active or d.empty:
        return pd.DataFrame(columns=QUEUE_COLUMNS)

    d["points"] = sum(hits[r].astype(int) for r in active)
    labels = pd.concat([hits[r].map({True: RULE_LABELS[r], False: ""}) for r in active], axis=1)
    d["reasons"] = labels.apply(lambda row: "; ".join(x for x in row if x), axis=1)

    d = d[d["points"] > 0]
    d = d.sort_values(["points", "rel_diff", "report.filing-date", "case_id"],
                      ascending=[False, False, False, True], na_position="last", kind="stable")
    d = d.reset_index(drop=True)
    d["rank"] = d.index + 1
    return d[QUEUE_COLUMNS]
