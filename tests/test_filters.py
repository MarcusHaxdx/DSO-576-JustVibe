import pytest

from analysis.filters import FilterSpec, apply_filters


def test_empty_spec_keeps_everything_and_copies(df):
    out = apply_filters(df, FilterSpec())
    assert len(out) == 11 and out is not df
    out["entity.name"] = "changed"
    assert (df["entity.name"] != "changed").all()          # the input is not modified


@pytest.mark.parametrize("spec, expected", [
    (FilterSpec(assertion_types=(126,)), 4),
    (FilterSpec(assertion_types=(126, 117)), 6),
    (FilterSpec(filing_years=(2023,)), 4),
    (FilterSpec(prefix="us-gaap"), 9),
    (FilterSpec(prefix="other"), 2),
    (FilterSpec(units=("pure",)), 2),
    (FilterSpec(period_kind="instant"), 3),
    (FilterSpec(period_kind="range"), 8),
    (FilterSpec(only_sign_flip=True), 2),
    (FilterSpec(only_period_after_filing=True), 2),
    (FilterSpec(company_query="alp"), 3),
    (FilterSpec(company_query="  ALPHA "), 3),
    (FilterSpec(assertion_types=(15,), units=("USD",)), 2),
    (FilterSpec(assertion_types=(99,)), 0),
])
def test_filters(df, spec, expected):
    assert len(apply_filters(df, spec)) == expected


def test_bad_options_are_rejected():
    with pytest.raises(ValueError):
        FilterSpec(prefix="nope")
    with pytest.raises(ValueError):
        FilterSpec(period_kind="nope")
