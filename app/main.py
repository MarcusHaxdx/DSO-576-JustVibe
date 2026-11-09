"""Project dashboard (Streamlit): the cleaned DQC ground truth, the review queue, and the
step-level agent evaluation. Render only: counting and scoring live in src/analysis and
src/evaluation. The ground-truth tabs follow BUILD_SPEC.md and are adapted from
fresh_agent_app/app/main.py; the Project and Agent evaluation tabs are new.

Run from anywhere:  streamlit run app/main.py
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402
from plotly.subplots import make_subplots  # noqa: E402

from analysis import metrics  # noqa: E402
from analysis.filters import FilterSpec, apply_filters  # noqa: E402
from analysis.loader import load_clean  # noqa: E402
from analysis.triage import RULE_LABELS, RULE_ORDER, TriageConfig, rank_cases  # noqa: E402
from evaluation.report import best_possible, load_design, load_results, task_summary  # noqa: E402
from evaluation.scoring import STEPS, Thresholds  # noqa: E402

CLEAN_PATH = REPO / "data" / "clean" / "auditing_clean.csv"
REPORT_PATH = REPO / "output" / "cleaning_report.txt"
TASKS_PATH = REPO / "eval" / "tasks" / "tasks.jsonl"
KEY_PATH = REPO / "eval" / "tasks" / "answer_key.csv"
RESULTS_DIR = REPO / "eval" / "results"

TABS = ["Project", "Ground truth", "Case Explorer", "Review Queue", "Agent evaluation"]
TYPE_LABELS = {
    15: "15 · sign check",
    117: "117 · total vs dimensional breakdown",
    126: "126 · total vs sum of child components",
}
HIST_MAX_PCT = 500
HIST_BINS = 50
BASE_COLOR = "#4C78A8"
HIGHLIGHT_COLOR = "#E45756"
VERDICT_COLORS = {"AI": "#54A24B", "AI + human review": "#ECA82C", "human": "#E45756",
                  "too few cases": "#BAB0AC", "n/a": "#EEEEEE"}
DASH = "—"

FILTER_DEFAULTS = {"f_types": [], "f_years": [], "f_prefix": "any", "f_units": [],
                   "f_period": "any", "f_sign_flip": False, "f_after_filing": False, "f_company": ""}
QUEUE_DEFAULTS = {**{f"q_{r}": True for r in RULE_ORDER}, "q_threshold_pct": 10}

STEP_TEXT = {
    "S1 locate": "find the failing fact (concept, period) and flag nothing else",
    "S2+S3 relate and compute": "read the reported value and sum the children or members",
    "S4 diagnose": "name the cause (only sign flips have a label)",
    "S5 explain": "every number cited is a fact in the filing",
    "S6 decide": "materiality and sign-off: no ground truth, human by definition",
}


# ---------- data ----------

def _mtime(p: Path) -> float:
    return p.stat().st_mtime if p.exists() else 0.0


@st.cache_data(show_spinner=False)
def _clean(path: str, mtime: float) -> pd.DataFrame:
    return load_clean(path)


@st.cache_data(show_spinner=False)
def _design(mt_tasks: float, mt_key: float):
    return load_design(TASKS_PATH, KEY_PATH)


@st.cache_data(show_spinner=False)
def _results(mt_metrics: float, mt_verdicts: float):
    return load_results(RESULTS_DIR)


def get_clean() -> pd.DataFrame:
    return _clean(str(CLEAN_PATH), _mtime(CLEAN_PATH))


def get_design():
    return _design(_mtime(TASKS_PATH), _mtime(KEY_PATH))


def get_results():
    return _results(_mtime(RESULTS_DIR / "step_metrics.csv"), _mtime(RESULTS_DIR / "verdicts.csv"))


# ---------- state ----------

def init_state():
    for k, v in {**FILTER_DEFAULTS, **QUEUE_DEFAULTS}.items():
        st.session_state.setdefault(k, v)
    st.session_state.setdefault("active_tab", TABS[0])


def reset_filters():
    for k, v in FILTER_DEFAULTS.items():
        st.session_state[k] = v


def open_cases():
    st.session_state["active_tab"] = "Case Explorer"


def filter_spec() -> FilterSpec:
    s = st.session_state
    return FilterSpec(assertion_types=tuple(s.f_types), filing_years=tuple(s.f_years),
                      prefix=s.f_prefix, units=tuple(s.f_units), period_kind=s.f_period,
                      only_sign_flip=s.f_sign_flip, only_period_after_filing=s.f_after_filing,
                      company_query=s.f_company)


def triage_config() -> TriageConfig:
    s = st.session_state
    return TriageConfig(rules_on=tuple(r for r in RULE_ORDER if s[f"q_{r}"]),
                        gap_threshold=s.q_threshold_pct / 100)


# ---------- formatting ----------

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


def active_filters() -> list:
    """Plain-language list of the sidebar filters that are currently narrowing the cases."""
    s = st.session_state
    out = []
    if s.f_types:
        out.append("rule type " + ", ".join(str(t) for t in s.f_types))
    if s.f_years:
        out.append("filing year " + ", ".join(str(y) for y in s.f_years))
    if s.f_prefix != "any":
        out.append(f"prefix = {s.f_prefix}")
    if s.f_units:
        out.append("unit " + ", ".join(s.f_units))
    if s.f_period != "any":
        out.append(f"period = {s.f_period}")
    if s.f_sign_flip:
        out.append("only sign flips")
    if s.f_after_filing:
        out.append("only period after filing")
    if s.f_company.strip():
        out.append(f'company contains "{s.f_company.strip()}"')
    return out


def no_match(where: str):
    """Empty state for 0 filtered cases: say which filters caused it and how to get data back."""
    act = active_filters()
    st.warning(f"No cases match the current filters, so {where} has nothing to show.")
    msg = "Active filters: " + "; ".join(act) + ". " if act else ""
    if st.session_state.f_sign_flip and st.session_state.f_after_filing:
        msg += "No case is both a sign flip and dated after filing (9 and 2 cases, no overlap). "
    if st.session_state.f_company.strip():
        msg += "The company search matches part of the name, without regard to case (try a shorter word). "
    st.markdown(msg + "Remove a filter in the sidebar, or reset them all:")
    st.button("Reset filters", on_click=reset_filters, key=f"reset_{where}")


def verdict_grid(v: pd.DataFrame, ceiling: bool = False):
    """Step x rule type table of verdicts, coloured by verdict. A ceiling grid (what a perfect
    agent could earn) is faded and says "at most", so it is never read as a result."""
    g = v.pivot(index="step", columns="rule_type", values="verdict").reindex(STEPS)
    g.columns = [TYPE_LABELS.get(c, str(c)) for c in g.columns]
    alpha = "55" if ceiling else ""

    def style(x):
        return f"background-color: {VERDICT_COLORS.get(x, '#FFFFFF')}{alpha}; color: #222"
    styled = g.style.map(style)
    if ceiling:
        styled = styled.format(lambda x: x if x in ("n/a", "human", "too few cases") else f"at most: {x}")
    return styled


# ---------- sidebar ----------

def render_sidebar(df: pd.DataFrame, n_filtered: int):
    sb = st.sidebar
    sb.header("Filters")
    sb.caption("Apply to Ground truth, Case Explorer and Review Queue.")
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


# ---------- tab: project ----------

def render_project(df: pd.DataFrame):
    st.markdown(
        "**Question.** A trading-technology manager must decide how far to trust AI agents on "
        "XBRL filing checks: which steps of the audit job, for which DQC rule types, can an "
        "agent take over, and which must stay with a human reviewer?")
    st.caption("Scope: one agent + model, run 2–3 times. Choosing between models is out of scope.")

    k = metrics.kpis(df)
    fs = metrics.flag_summary(df)
    c = st.columns(5)
    c[0].metric("DQC cases", k["cases"])
    c[1].metric("Filings", k["filings"])
    c[2].metric("Companies", k["companies"])
    c[3].metric("Rule types", k["rule_types"])
    c[4].metric("Sign flips", fs["sign_flip"],
                help=f"{fs['sign_flip']} of {fs['rows_with_calculated']} cases with a calculated value")

    st.subheader("Pipeline and where each result is")
    design = get_design()
    results = get_results()
    rows = [
        ("1 · Clean", "mathematical_reasoning.csv → 362 rows, 34 columns, 0 dropped, 0 failed conversions",
         "done", "Ground truth"),
        ("2 · Triage", "rule-based ranking of cases for human review (not a model, not validated)",
         "done", "Review Queue"),
        ("3 · Task design", f"{len(design[0])} filing × rule tasks, {len(design[1])} answer-key cases"
         if design else "run `python eval/build_tasks.py`", "done" if design else "to do", "Agent evaluation"),
        ("4 · Agent runs", "one agent + model answers each task, 2–3 repeats; scored step by step",
         "scored" if results else "not run yet", "Agent evaluation"),
    ]
    st.dataframe(pd.DataFrame(rows, columns=["stage", "what", "status", "tab"]), hide_index=True)

    st.subheader("Answer so far")
    if results:
        st.markdown("Verdicts from the scored agent runs (worst run counts):")
        st.dataframe(verdict_grid(results[1]))
    else:
        st.warning("No agent has been run yet, so there is no measured verdict. "
                   "The grid below is the most a **perfect** agent could earn with these case "
                   "counts on the test split. It shows what the design can prove, not how any agent did.")
        if design:
            v, _ = best_possible(*design, split="test")
            st.dataframe(verdict_grid(v, ceiling=True))
            capped = v[~v["step"].isin(["S4 diagnose", "S6 decide"]) & (v["verdict"] != "AI")]
            for r in capped.itertuples(index=False):
                st.markdown(f"- **Rule {r.rule_type}, {r.step}: at most '{r.verdict}'** even for a "
                            f"perfect agent ({r.basis}).")
    st.markdown(
        "- **S6 (materiality, sign-off) stays human:** the data has no label for it.\n"
        "- **S4 (diagnosis) cannot be decided:** sign flips are the only labelled cause, too few to test.")

    st.subheader("Data and limits")
    st.markdown(
        "- Source: Hugging Face `TheFinAI/Herculean`, `auditing_env/XBRL/mathematical_reasoning.csv`, "
        "commit `52d3ecb`, CC BY 4.0.\n"
        "- The dataset card lists 4,959 assertions; the downloaded file has 362. Filings without a "
        "case are *assumed* clean, so measured false alarms are an upper bound.\n"
        "- Every row is a DQC error (severity ERROR); clean examples come only from those filing × rule "
        "pairs with no case.\n"
        "- Flags (sign flip, period after filing) mark rows; no value is ever changed.")
    if REPORT_PATH.exists():
        with st.expander("Cleaning report (output/cleaning_report.txt)"):
            st.code(REPORT_PATH.read_text(encoding="utf-8"), language=None)


# ---------- tab: ground truth ----------

def render_overview(f: pd.DataFrame):
    if f.empty:
        no_match("the Ground truth tab")
        return
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
                           y=by_type["cases"], marker_color=BASE_COLOR, customdata=by_type["share"],
                           hovertemplate="%{x}<br>%{y} cases (%{customdata:.1%})<extra></extra>"))
    fig.update_layout(title="Cases by rule type", yaxis_title="cases", height=340, margin=dict(t=40, b=10))
    left.plotly_chart(fig, width="stretch")

    by_year = metrics.cases_by_year(f)
    fig = go.Figure(go.Bar(x=by_year["report.filing-year"].astype(str), y=by_year["cases"],
                           marker_color=BASE_COLOR))
    fig.update_layout(title="Cases by filing year", yaxis_title="cases", xaxis_type="category",
                      height=340, margin=dict(t=40, b=10))
    right.plotly_chart(fig, width="stretch")

    st.subheader("Flags")
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
    with st.expander("Cases by rule code"):
        st.dataframe(metrics.cases_by_code(f), hide_index=True,
                     column_config={"share": st.column_config.NumberColumn(format="percent")})
    with st.expander("Top 10 companies"):
        st.dataframe(metrics.top_companies(f, 10), hide_index=True)


def render_histogram(f: pd.DataFrame):
    st.subheader("Relative discrepancy")
    d = metrics.discrepancy(f)
    summ = metrics.discrepancy_summary(f)
    c = metrics.histogram_counts(f, HIST_MAX_PCT / 100)
    drawn = d[d["rel_diff"].notna() & (d["rel_diff"] <= HIST_MAX_PCT / 100)]
    if c["with_rel"] == 0:
        if c["comparison_cases"] == 0:
            st.info("No histogram: the filtered cases have no calculated value to compare. Only rule types "
                    "117 and 126 in USD have one (type 15 is a sign check, and every non-USD case is "
                    "type 15). Add rule type 117 or 126 in the sidebar to see the gap sizes.")
        else:
            st.info(f"No histogram: all {c['comparison_cases']} filtered comparison cases have a reported value "
                    "of 0, so the relative gap is undefined. The absolute gaps are in the caption below.")
    else:
        xbins = dict(start=0, end=HIST_MAX_PCT + 1e-9, size=HIST_MAX_PCT / HIST_BINS)
        fig = go.Figure()
        for flip, name, color in [(False, "other cases", BASE_COLOR), (True, "sign flip", HIGHLIGHT_COLOR)]:
            part = drawn[drawn["sign_flip"] == flip]
            fig.add_trace(go.Histogram(x=part["rel_diff"] * 100, xbins=xbins, autobinx=False,
                                       name=name, marker_color=color))
        fig.update_layout(barmode="stack", xaxis_title="rel_diff (%)", yaxis_title="cases",
                          xaxis_range=[0, HIST_MAX_PCT], height=360, margin=dict(t=20, b=10))
        st.plotly_chart(fig, width="stretch")
    st.caption(
        f"{c['with_rel']} cases have a rel_diff; {c['drawn']} are drawn and {c['above']} "
        f"fall above {HIST_MAX_PCT}% and are not drawn. {c['without_rel']} of the {c['comparison_cases']} "
        f"USD comparison cases (types 117/126) have no rel_diff (reported value is 0). "
        f"Median rel_diff {fmt_pct(summ['median_rel_diff'])}, max {fmt_pct(summ['max_rel_diff'])}; "
        f"median abs_diff {fmt_num(summ['median_abs_diff'])} USD, max {fmt_num(summ['max_abs_diff'])} USD.")


# ---------- tab: case explorer ----------

def render_explorer(f: pd.DataFrame, queue: pd.DataFrame):
    if f.empty:
        no_match("the Case Explorer")
        return
    f = f.reset_index(drop=True)
    table = pd.DataFrame({
        "company": f["entity.name"], "filing date": f["report.filing-date"].dt.date,
        "rule code": f["assertion.code"], "concept": f["concept_prefix"] + ":" + f["concept"],
        "period": f["period"], "unit": f["unit"], "reported": f["reported_value"],
        "calculated": f["calculated_value"], "flags": f.apply(flags_text, axis=1)})
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
        st.markdown(f"**Queue status:** rank {qr['rank']} of {len(queue)}, {qr['points']} point(s): {qr['reasons']}")
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


# ---------- tab: review queue ----------

def render_queue(queue: pd.DataFrame, n_filtered: int):
    st.info("Rule-based triage, not a model and not validated.")
    for c, r in zip(st.columns(len(RULE_ORDER)), RULE_ORDER):
        c.toggle(RULE_LABELS[r], key=f"q_{r}")
    st.slider("Large-gap threshold (rel_diff, %)", 0, HIST_MAX_PCT, step=1, key="q_threshold_pct",
              disabled=not st.session_state["q_large_gap"])
    if queue.empty:
        if not any(st.session_state[f"q_{r}"] for r in RULE_ORDER):
            st.info("The queue is empty because every triage rule is off. Turn on at least one rule above.")
        elif n_filtered == 0:
            no_match("the Review Queue")
        else:
            st.info(f"None of the {n_filtered} filtered cases triggers a rule that is on. Turn on more "
                    "rules, lower the large-gap threshold, or widen the sidebar filters.")
        return
    st.markdown(f"**{len(queue)} cases in the queue**")
    st.dataframe(queue, hide_index=True, placeholder="", column_config={
        "reasons": st.column_config.TextColumn("why (reasons)"),
        "report.filing-date": st.column_config.DateColumn(format="YYYY-MM-DD"),
        "reported_value": st.column_config.NumberColumn(format="localized"),
        "calculated_value": st.column_config.NumberColumn(format="localized"),
        "rel_diff": st.column_config.NumberColumn(format="percent")})
    st.download_button("Download queue (CSV)", queue.to_csv(index=False).encode("utf-8"),
                       file_name="review_queue.csv", mime="text/csv")


# ---------- tab: agent evaluation ----------

def render_evaluation():
    st.caption("Not affected by the sidebar filters: the evaluation covers every filing × rule task.")
    th = Thresholds()
    st.markdown(
        f"**Decision rule (fixed before any test run).** A step goes to **AI** if the lower 95% "
        f"Wilson bound of every gate metric is ≥ {th.ai:.0%}, to **AI + human review** if ≥ "
        f"{th.review:.0%}, otherwise **human**. Fewer than {th.min_n} cases on a gate metric: "
        f"**too few cases**. With repeated runs of the same agent + model, the worst run counts.")
    st.dataframe(pd.DataFrame({"step": list(STEP_TEXT), "what is scored": list(STEP_TEXT.values())}),
                 hide_index=True)

    design = get_design()
    if not design:
        st.info("Tasks not built yet. Run `python eval/build_tasks.py` from the repo root.")
        return
    tasks, key = design
    st.subheader("Tasks")
    st.caption("One task = one filing × one rule type. Assumed-clean tasks should come back empty; "
               "they measure false alarms. Dev is for prompt iteration, test for the reported numbers.")
    st.dataframe(task_summary(tasks), hide_index=True)

    results = get_results()
    st.subheader("Measured verdicts")
    if not results:
        st.info("No agent runs scored yet. Run agents on `eval/tasks/tasks.jsonl`, save one JSON line "
                "per task in `eval/runs/`, then `python eval/score_runs.py eval/runs/*.jsonl`.")
    else:
        m, v = results
        st.markdown(f"Runs scored: {', '.join(sorted(m['run'].unique()))}")
        st.dataframe(verdict_grid(v))
        with st.expander("Why each cell got its verdict"):
            st.dataframe(v, hide_index=True)
        render_metric_chart(m, th)
        with st.expander("All step metrics"):
            st.dataframe(m, hide_index=True, column_config={
                c: st.column_config.NumberColumn(format="percent") for c in ("rate", "ci_low", "ci_high")})

    st.subheader("What the design can prove")
    split = st.radio("Split", ["test", "all"], horizontal=True, key="power_split",
                     help="'all' adds the dev filings: more cases, but they were open for prompt iteration.")
    v, m = best_possible(tasks, key, split=split)
    st.caption("Verdicts a perfect agent would get with these case counts. A design property, not a result.")
    st.dataframe(verdict_grid(v, ceiling=True))
    with st.expander("Case counts behind each gate metric"):
        st.dataframe(m[m["gate"]][["rule_type", "step", "metric", "n", "ci_low"]], hide_index=True,
                     column_config={"ci_low": st.column_config.NumberColumn("best 95% CI low", format="percent")})


def render_metric_chart(m: pd.DataFrame, th: Thresholds):
    """Rate with its 95% interval for every gate metric, one panel per rule type."""
    g = m[m["gate"] & (m["n"] > 0)].copy()
    g["label"] = g["step"] + " · " + g["metric"]
    types = sorted(g["rule_type"].unique())
    fig = make_subplots(rows=1, cols=len(types), shared_yaxes=True,
                        subplot_titles=[TYPE_LABELS.get(t, str(t)) for t in types])
    palette = [BASE_COLOR, HIGHLIGHT_COLOR, "#54A24B", "#ECA82C", "#B279A2", "#9D755D"]
    for i, t in enumerate(types, 1):
        for j, (run, part) in enumerate(g[g["rule_type"] == t].groupby("run")):
            fig.add_trace(go.Scatter(
                x=part["rate"], y=part["label"], mode="markers", name=run, legendgroup=run,
                showlegend=i == 1, marker=dict(color=palette[j % len(palette)], size=9),
                error_x=dict(type="data", symmetric=False, array=part["ci_high"] - part["rate"],
                             arrayminus=part["rate"] - part["ci_low"]),
                customdata=part[["k", "n"]],
                hovertemplate="%{y}<br>%{x:.1%} (%{customdata[0]} / %{customdata[1]})<extra>" + run + "</extra>"),
                row=1, col=i)
        for x, dash in ((th.ai, "solid"), (th.review, "dot")):
            fig.add_vline(x=x, line_dash=dash, line_color="#888", row=1, col=i)
    fig.update_xaxes(range=[0, 1.02], tickformat=".0%")
    fig.update_layout(height=120 + 40 * g["label"].nunique(), margin=dict(t=40, b=10),
                      legend_title_text="run")
    st.plotly_chart(fig, width="stretch")
    st.caption(f"Dots are rates; bars are 95% Wilson intervals. Solid line: AI bar ({th.ai:.0%}); "
               f"dotted: review bar ({th.review:.0%}). A step passes on its interval's left end.")


# ---------- main ----------

def main():
    st.set_page_config(page_title="DQC Audit: what can AI take over?", layout="wide")
    init_state()
    df = get_clean()
    f = apply_filters(df, filter_spec())
    render_sidebar(df, len(f))
    queue = rank_cases(f, triage_config())

    st.title("DQC audit: which steps can AI take over?")
    tabs = st.tabs(TABS, key="active_tab", on_change="rerun")
    with tabs[0]:
        render_project(df)
    with tabs[1]:
        render_overview(f)
    with tabs[2]:
        render_explorer(f, queue)
    with tabs[3]:
        render_queue(queue, len(f))
    with tabs[4]:
        render_evaluation()


main()
