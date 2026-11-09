import pytest

from analysis.triage import QUEUE_COLUMNS, TriageConfig, rank_cases
from conftest import case_id


def test_only_sign_flip_rule(df):
    q = rank_cases(df, TriageConfig(rules_on=("sign_flip",)))
    assert len(q) == 2 and set(q["reasons"]) == {"sign flip"}


def test_default_rules_and_order(df):
    q = rank_cases(df)
    assert list(q.columns) == QUEUE_COLUMNS
    assert len(q) == 8 and q["rank"].tolist() == list(range(1, 9))
    assert q["points"].is_monotonic_decreasing
    # points 2: largest gap first, then ties by newer filing date
    assert q["case_id"].iloc[0] == case_id(df, -300897000.0)
    assert q["case_id"].iloc[1] == case_id(df, 19204000.0)
    assert q["case_id"].iloc[2] == case_id(df, 707500.0)
    assert q.iloc[0]["reasons"] == "non-us-gaap prefix; large gap"


def test_threshold_changes_the_queue(df):
    q = rank_cases(df, TriageConfig(rules_on=("large_gap",), gap_threshold=3.0))
    assert len(q) == 1 and q["case_id"].iloc[0] == case_id(df, -300897000.0)
    assert len(rank_cases(df, TriageConfig(rules_on=("large_gap",), gap_threshold=0.0))) == 5


def test_non_usd_and_period_rules(df):
    assert len(rank_cases(df, TriageConfig(rules_on=("non_usd",)))) == 3
    assert len(rank_cases(df, TriageConfig(rules_on=("period_after_filing",)))) == 2


def test_no_rules_or_no_rows_give_empty_queue(df):
    assert rank_cases(df, TriageConfig(rules_on=())).empty
    assert rank_cases(df.iloc[0:0]).empty


def test_unknown_rule_rejected():
    with pytest.raises(ValueError):
        TriageConfig(rules_on=("nope",))


def test_ranking_is_deterministic(df):
    a, b = rank_cases(df), rank_cases(df.sample(frac=1, random_state=1))
    assert a["case_id"].tolist() == b["case_id"].tolist()
