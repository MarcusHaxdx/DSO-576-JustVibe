"""DQC Review Dashboard (Streamlit). Render only: all counting and scoring lives in src/analysis."""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from analysis import metrics, runs  # noqa: E402
from analysis.filters import FilterSpec, apply_filters  # noqa: E402
from analysis.loader import load_clean  # noqa: E402
from analysis.triage import RULE_LABELS, RULE_ORDER, TriageConfig, rank_cases  # noqa: E402

CLEAN_PATH = REPO / "data" / "clean" / "auditing_clean.csv"
RUNS_PATH = REPO / "data" / "runs" / "agent_runs.csv"

TABS = ["Overview", "Case Explorer", "Review Queue", "Configuration Comparison"]
TYPE_LABELS = {
    15: "15 · sign check",
    117: "117 · total vs dimensional breakdown",
    126: "126 · total vs sum of child components",
}
HIST_MAX_PCT = 500
HIST_BINS = 50
BASE_COLOR = "#4C78A8"
HIGHLIGHT_COLOR = "#E45756"
DASH = "—"

FILTER_DEFAULTS = {
    "f_types": [],
    "f_years": [],
    "f_prefix": "any",
    "f_units": [],
    "f_period": "any",
    "f_sign_flip": False,
    "f_after_filing": False,
    "f_company": "",
}
QUEUE_DEFAULTS = {**{f"q_{r}": True for r in RULE_ORDER}, "q_threshold_pct": 10}


# ---------- data ----------

@st.cache_data(show_spinner=False)
def _load_clean_cached(path: str, mtime: float) -> pd.DataFrame:
    return load_clean(path)


@st.cache_data(show_spinner=False)
def _load_runs_cached(path: str, mtime: float):
    return runs.load_runs(path)


def get_clean() -> pd.DataFrame:
    return _load_clean_cached(str(CLEAN_PATH), CLEAN_PATH.stat().st_mtime)


def get_runs():
    """Runs DataFrame or None; raises if the file is malformed."""
    if not RUNS_PATH.exists():
        return None
    return _load_runs_cached(str(RUNS_PATH), RUNS_PATH.stat().st_mtime)


# ---------- state ----------

def init_state():
    for k, v in {**FILTER_DEFAULTS, **QUEUE_DEFAULTS}.items():
        st.session_state.setdefault(k, v)
    st.session_state.setdefault("active_tab", TABS[0])


def reset_filters():
    for k, v in FILTER_DEFAULTS.items():
        st.session_state[k] = v


def open_cases():
    st.session_state["active_tab"] = TABS[1]


def filter_spec() -> FilterSpec:
    s = st.session_state
    return FilterSpec(
        assertion_types=tuple(s.f_types),
        filing_years=tuple(s.f_years),
        prefix=s.f_prefix,
        units=tuple(s.f_units),
        period_kind=s.f_period,
        only_sign_flip=s.f_sign_flip,
        only_period_after_filing=s.f_after_filing,
        company_query=s.f_company,
    )


def triage_config() -> TriageConfig:
    s = st.session_state
    return TriageConfig(rules_on=tuple(r for r in RULE_ORDER if s[f"q_{r}"]),
                        gap_threshold=s.q_threshold_pct / 100)


# ---------- formatting helpers ----------

def fmt_num(x) -> str:
    if x is None or pd.isna(x):
        return DASH
    return f"{x:,.0f}" if float(x).is_integer() else f"{x:,.6g}"


def fmt_pct(x) -> str:
    return DASH if x is None or pd.isna(x) else f"{x:.1%}"


def fmt_date(x) -> str:
    return DASH if x is None or pd.isna(x) else pd.Timestamp(x).strftime("%Y-%m-%d")


def flags_text(row) -> str:
    out = []
    if row["sign_flip"]:
        out.append("sign flip")
    if row["period_after_filing"]:
        out.append("period after filing")
    return ", ".join(out)


def why_no_discrepancy(row) -> str:
    if row["assertion.type"] not in metrics.COMPARISON_TYPES:
        return "Type 15 sign checks have no calculated value, so there is nothing to compare."
    if row["unit"] != "USD":
        return "Only USD comparison cases get a discrepancy."
    if pd.isna(row["calculated_value"]) or pd.isna(row["reported_value"]):
        return "A reported or calculated value is missing."
    if row["reported_value"] == 0:
        return "Reported value is 0, so the relative gap is undefined."
    return ""


# ---------- sidebar ----------

def render_sidebar(df: pd.DataFrame, n_filtered: int):
    sb = st.sidebar
    sb.header("Filters")
    sb.multiselect("Rule type (assertion.type)", list(TYPE_LABELS), key="f_types",
                   format_func=lambda t: TYPE_LABELS.get(t, str(t)), placeholder="All")
    sb.multiselect("Filing year", sorted(df["report.filing-year"].unique().tolist()),
                   key="f_years", placeholder="All")
    sb.radio("Concept prefix", ["any", "us-gaap", "other"], key="f_prefix", horizontal=True)
    sb.multiselect("Unit", sorted(df["unit"].dropna().unique().tolist()), key="f_units", placeholder="All")
    sb.radio("Period kind", ["any", "range", "instant"], key="f_period", horizontal=True)
    sb.checkbox("Only sign flips", key="f_sign_flip")
    sb.checkbox("Only period after filing date", key="f_after_filing")
    sb.text_input("Company contains", key="f_company")
    sb.button("Reset filters", on_click=reset_filters)
    sb.markdown(f"**{n_filtered} of {len(df)} cases**")


# ---------- tab 1 ----------

def render_overview(f: pd.DataFrame):
    k = metrics.kpis(f)
    c = st.columns(4)
    c[0].metric("Cases", k["cases"])
    c[1].metric("Filings", k["filings"])
    c[2].metric("Companies", k["companies"])
    c[3].metric("Rule types", k["rule_types"])
    st.button("Open these cases", on_click=open_cases, type="primary")

    left, right = st.columns(2)
    by_type = metrics.cases_by_type(f)
    fig = go.Figure(go.Bar(x=[TYPE_LABELS.get(t, str(t)) for t in by_type["assertion.type"]],
                           y=by_type["cases"], marker_color=BASE_COLOR,
                           customdata=by_type["share"],
                           hovertemplate="%{x}<br>%{y} cases (%{customdata:.1%})<extra></extra>"))
    fig.update_layout(title="Cases by rule type (M1)", yaxis_title="cases", height=340,
                      margin=dict(t=40, b=10))
    left.plotly_chart(fig, width="stretch")

    by_year = metrics.cases_by_year(f)
    fig = go.Figure(go.Bar(x=by_year["report.filing-year"].astype(str), y=by_year["cases"],
                           marker_color=BASE_COLOR))
    fig.update_layout(title="Cases by filing year (M4)", yaxis_title="cases", xaxis_type="category",
                      height=340, margin=dict(t=40, b=10))
    right.plotly_chart(fig, width="stretch")

    st.subheader("Flags (M2)")
    fs = metrics.flag_summary(f)
    st.dataframe(pd.DataFrame({
        "flag": ["sign flip", "period after filing date", "non-USD unit", "non-us-gaap prefix"],
        "cases": [fs["sign_flip"], fs["period_after_filing"], fs["non_usd"], fs["non_us_gaap_prefix"]],
    }), hide_index=True)
    if fs["sign_flip_rate"] is None:
        st.markdown(f"Sign-flip rate: {DASH} (no cases with a calculated value)")
    else:
        st.markdown(f"Sign-flip rate: **{fs['sign_flip_rate']:.1%}** "
                    f"({fs['sign_flip']} / {fs['rows_with_calculated']} cases with a calculated value)")

    render_histogram(f)

    with st.expander("Cases by rule code", expanded=False):
        st.dataframe(metrics.cases_by_code(f), hide_index=True,
                     column_config={"share": st.column_config.NumberColumn(format="percent")})
    with st.expander("Top 10 companies", expanded=False):
        st.dataframe(metrics.top_companies(f, 10), hide_index=True)


def render_histogram(f: pd.DataFrame):
    st.subheader("Relative discrepancy (M3)")
    d = metrics.discrepancy(f)
    summ = metrics.discrepancy_summary(f)
    comp = d[d["abs_diff"].notna()]
    has_rel = comp[comp["rel_diff"].notna()]
    drawn = has_rel[has_rel["rel_diff"] * 100 <= HIST_MAX_PCT]
    n_above = len(has_rel) - len(drawn)
    n_no_rel = len(comp) - len(has_rel)

    if has_rel.empty:
        st.info("No comparison cases with a relative discrepancy under the current filters.")
    else:
        size = HIST_MAX_PCT / HIST_BINS
        xbins = dict(start=0, end=HIST_MAX_PCT + 1e-9, size=size)
        fig = go.Figure()
        for flip, name, color in [(False, "other cases", BASE_COLOR), (True, "sign flip", HIGHLIGHT_COLOR)]:
            part = drawn[drawn["sign_flip"] == flip]
            fig.add_trace(go.Histogram(x=part["rel_diff"] * 100, xbins=xbins, autobinx=False,
                                       name=name, marker_color=color))
        fig.update_layout(barmode="stack", xaxis_title="rel_diff (%)", yaxis_title="cases",
                          xaxis_range=[0, HIST_MAX_PCT], height=360, margin=dict(t=20, b=10))
        st.plotly_chart(fig, width="stretch")

    st.caption(
        f"{len(has_rel)} cases have a rel_diff; {len(drawn)} are drawn and {n_above} fall above "
        f"{HIST_MAX_PCT}% and are not drawn. {n_no_rel} of the {len(comp)} USD comparison cases "
        f"(types 117/126) have no rel_diff (reported value is 0). "
        f"Over all comparison cases: median rel_diff {fmt_pct(summ['median_rel_diff'])}, "
        f"max {fmt_pct(summ['max_rel_diff'])}; median abs_diff {fmt_num(summ['median_abs_diff'])} USD, "
        f"max {fmt_num(summ['max_abs_diff'])} USD."
    )


# ---------- tab 2 ----------

def render_explorer(f: pd.DataFrame, queue: pd.DataFrame):
    if f.empty:
        st.info("No cases match the current filters.")
        return
    f = f.reset_index(drop=True)
    table = pd.DataFrame({
        "company": f["entity.name"],
        "filing date": f["report.filing-date"].dt.date,
        "rule code": f["assertion.code"],
        "concept": f["concept_prefix"] + ":" + f["concept"],
        "period": f["period"],
        "unit": f["unit"],
        "reported": f["reported_value"],
        "calculated": f["calculated_value"],
        "flags": f.apply(flags_text, axis=1),
    })
    st.caption("Click a row to see its details. Click a column header to sort.")
    event = st.dataframe(table, hide_index=True, on_select="rerun", selection_mode="single-row",
                         key="explorer_table", placeholder="",
                         column_config={"reported": st.column_config.NumberColumn(format="localized"),
                                        "calculated": st.column_config.NumberColumn(format="localized")})
    rows = event.selection.rows if event is not None else []
    if not rows or rows[0] >= len(f):
        st.info("Select a case to see the original DQC message and its details.")
        return
    render_detail(f, f.iloc[rows[0]]["case_id"], queue)


def render_detail(f: pd.DataFrame, cid: str, queue: pd.DataFrame):
    row = metrics.discrepancy(f[f["case_id"] == cid]).iloc[0]
    st.divider()
    st.subheader(f"{row['entity.name']} · {row['assertion.code']}")

    q = queue[queue["case_id"] == cid]
    if q.empty:
        st.markdown("**Queue status:** not in the queue under the current triage settings")
    else:
        qr = q.iloc[0]
        st.markdown(f"**Queue status:** rank {qr['rank']} of {len(queue)}, "
                    f"{qr['points']} point(s): {qr['reasons']}")

    left, right = st.columns([3, 2])
    with left:
        st.markdown("**Original DQC message**")
        st.text_area("assertion.detail", row["assertion.detail"], height=260, disabled=True,
                     label_visibility="collapsed")
    with right:
        fields = [
            ("case_id", row["case_id"]),
            ("rule type", TYPE_LABELS.get(row["assertion.type"], str(row["assertion.type"]))),
            ("concept", f"{row['concept_prefix']}:{row['concept']}"),
            ("period", row["period"] if pd.notna(row["period"]) else DASH),
            ("period start", fmt_date(row["period_start"])),
            ("period end", fmt_date(row["period_end"])),
            ("filing date", fmt_date(row["report.filing-date"])),
            ("unit", row["unit"] if pd.notna(row["unit"]) else DASH),
            ("reported", fmt_num(row["reported_value"])),
            ("calculated", fmt_num(row["calculated_value"])),
            ("abs discrepancy", fmt_num(row["abs_diff"])),
            ("rel discrepancy", fmt_pct(row["rel_diff"])),
            ("flags", flags_text(row) or "none"),
        ]
        st.dataframe(pd.DataFrame(fields, columns=["field", "value"]), hide_index=True)
        if pd.isna(row["abs_diff"]) or pd.isna(row["rel_diff"]):
            note = why_no_discrepancy(row)
            if note:
                st.caption(note)
        url = row["report.sec-url"]
        if isinstance(url, str) and url.strip():
            st.link_button("Open filing on SEC", url.strip())


# ---------- tab 3 ----------

def render_queue(queue: pd.DataFrame):
    st.info("Rule-based triage, not a model and not validated.")
    cols = st.columns(len(RULE_ORDER))
    for c, r in zip(cols, RULE_ORDER):
        c.toggle(RULE_LABELS[r], key=f"q_{r}")
    st.slider("Large-gap threshold (rel_diff, %)", 0, HIST_MAX_PCT, step=1, key="q_threshold_pct",
              disabled=not st.session_state["q_large_gap"])

    if queue.empty:
        st.info("No cases in the queue: no rule is on, or no filtered case triggers one.")
        return
    st.markdown(f"**{len(queue)} cases in the queue**")
    st.dataframe(queue, hide_index=True, placeholder="",
                 column_config={
                     "reasons": st.column_config.TextColumn("why (reasons)"),
                     "report.filing-date": st.column_config.DateColumn(format="YYYY-MM-DD"),
                     "reported_value": st.column_config.NumberColumn(format="localized"),
                     "calculated_value": st.column_config.NumberColumn(format="localized"),
                     "rel_diff": st.column_config.NumberColumn(format="percent"),
                 })
    st.download_button("Download queue (CSV)", queue.to_csv(index=False).encode("utf-8"),
                       file_name="review_queue.csv", mime="text/csv")


# ---------- tab 4 ----------

def render_configs(df: pd.DataFrame, f: pd.DataFrame):
    try:
        loaded = get_runs()
        if loaded is None:
            st.info("No agent runs loaded")
            return
        scored = runs.score_runs(loaded, df)
    except Exception as e:  # malformed runs file: show the error and the empty state
        st.error(f"Could not read {RUNS_PATH.relative_to(REPO)}: {e}")
        st.info("No agent runs loaded")
        return

    kept = runs.restrict_to_cases(scored, f)
    if kept.empty:
        st.info("No agent runs on the currently filtered cases.")
        return
    comp = runs.config_comparison(kept)
    st.subheader("Configurations")
    st.dataframe(comp, hide_index=True, column_config={
        "accuracy": st.column_config.NumberColumn(format="percent"),
        "mean_cost_usd": st.column_config.NumberColumn(format="dollar"),
        "mean_latency_s": st.column_config.NumberColumn(format="%.2f s"),
    })
    labels = comp["agent_framework"] + " / " + comp["model"]
    fig = go.Figure(go.Scatter(x=comp["mean_cost_usd"], y=comp["accuracy"], mode="markers+text",
                               text=labels, textposition="top center",
                               marker=dict(size=12, color=BASE_COLOR)))
    fig.update_layout(xaxis_title="mean cost (USD)", yaxis_title="accuracy", yaxis_tickformat=".0%",
                      height=420, margin=dict(t=20, b=10))
    st.plotly_chart(fig, width="stretch")
    st.subheader("Error types")
    st.dataframe(runs.error_breakdown(kept), hide_index=True,
                 column_config={"share": st.column_config.NumberColumn(format="percent")})


# ---------- main ----------

def main():
    st.set_page_config(page_title="DQC Review Dashboard", layout="wide")
    init_state()
    df = get_clean()
    f = apply_filters(df, filter_spec())
    render_sidebar(df, len(f))
    queue = rank_cases(f, triage_config())

    st.title("DQC Review Dashboard")
    t1, t2, t3, t4 = st.tabs(TABS, key="active_tab", on_change="rerun")
    with t1:
        render_overview(f)
    with t2:
        render_explorer(f, queue)
    with t3:
        render_queue(queue)
    with t4:
        render_configs(df, f)


main()
