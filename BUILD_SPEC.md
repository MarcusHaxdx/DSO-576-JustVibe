# BUILD_SPEC: DQC Review Dashboard (DSO 576, Phase 3 MVP)

Build a local Streamlit dashboard on the team's cleaned auditing ground-truth data. Follow the sections in order. Do not change the data or the analysis functions to fit the UI; if something is missing, add it to the layer that owns it (section 5).

## 1. Revised vision

**User:** a trading-technology manager at an asset manager who is deciding how far to trust AI agents on XBRL filing checks.

**Decision:** which kinds of DQC (Data Quality Committee) cases can be handed to an agent and which must go to a human reviewer; once agent runs exist, which agent + model configuration to trust.

**Why this beats the raw file:** each case is a ~2 KB free-text message with the reported and calculated values buried in a sentence. The tool turns them into comparable numbers, groups cases by rule type, flags oddities, and ranks cases for human review.

**Core use cases** (written out in section 3): UC1 which rule type to look at first; UC2 whether one case is a clear pattern or needs human judgment; UC3 which cases go to human review first; UC4 (optional input) which agent configuration to trust.

**Changed since Phase 1:** Trading is dropped (the professor made it optional); the MVP uses the ground truth only, because no agent has been run yet. The configuration comparison stays in the vision and is specified in section 8 as an optional input, never filled with made-up numbers.

## 2. Data (one canonical file)

`data/clean/auditing_clean.csv`: 362 rows x 34 columns, produced from `mathematical_reasoning.csv` (Hugging Face `TheFinAI/Herculean`, commit `52d3ecb`) by `src/cleaning/clean_auditing.py`. Do not re-clean in the app. The Hugging Face dataset card quotes 4,959 assertions; the file we downloaded has 362 rows (669,724 bytes) covering all 158 filings, and every number in this spec comes from those 362 rows.

| Item | Definition |
|---|---|
| One row | one DQC rule that fired on one filing (362 rows, 158 filings, 125 companies) |
| Row key | `report.accession` + `assertion.code` + message text without its timestamp; unique |
| `assertion.type` | 15 = sign check (116 rows), 117 = total vs dimensional breakdown (136), 126 = total vs sum of child components (110) |
| `reported_value`, `calculated_value` | numbers parsed from `assertion.detail`; `calculated_value` is empty for type 15 by design (116 rows) |
| `unit` | USD 330, shares 15, pure 12, bbl 4, USD/bbl 1; all 32 non-USD rows are type 15, so all 246 comparison rows are USD |
| `period_start` / `period_end` | `period_start` is empty for the 125 single-date (instant) periods |
| `concept_prefix` | `us-gaap` 350; 12 rows use another prefix (company-specific or `srt`) |
| `sign_flip` | `calculated_value == -reported_value`, nonzero: 9 rows |
| `period_after_filing` | `period_end` later than `report.filing-date`: 2 rows |

Rules: never sum or average amounts across units; any amount statistic uses `unit == "USD"` rows only. Never show a missing value as 0: show it as "—" in the detail panel and as an empty cell in tables. Flags are marks, not corrections: no value in the file is ever edited.

## 3. Use cases (select, see, decide)

| # | User selects | Dashboard shows | User decides |
|---|---|---|---|
| UC1 | opens the app (or picks a rule type or filing year) | case counts by rule type, flag counts, how big the discrepancies are | which rule type to look at first |
| UC2 | a rule type, company or year, then one case | the original DQC message beside the extracted values, the discrepancy, the flags | whether the case is a clear pattern (for example a pure sign flip) or needs human judgment |
| UC3 | which triage rules are on and the size threshold | cases ranked by how many rules they trigger, with the reasons | which cases go to human review first (exports the list) |
| UC4 (optional input) | an agent configuration | accuracy against the ground truth, mean cost, mean latency, error types | which configuration to trust |

Every feature in section 4 names the use case it serves; a feature that serves none is not built. UC4 has data only when `data/runs/agent_runs.csv` exists (section 8); without it, tab 4 shows its empty state.

## 4. Dashboard

**Layout:** left sidebar with the global filters; four tabs (Overview, Case Explorer, Review Queue, Configuration Comparison). Starting view: tab **Overview** with no filters set (all 362 cases).

**Global filters** (serve UC1 to UC3 by narrowing the cases every tab shows; one shared filter state):

| Filter | Control | Behaviour |
|---|---|---|
| `assertion.type` | multiselect, labels "15 · sign check", "117 · total vs dimensional breakdown", "126 · total vs sum of child components" | none selected = all |
| `report.filing-year` | multiselect | none selected = all |
| `concept_prefix` | radio: any / us-gaap / other | |
| `unit` | multiselect | none selected = all |
| period kind | radio: any / range / instant | |
| flags | two checkboxes: "Only sign flips", "Only period after filing date" | both checked = both must be true |
| company | text box | case-insensitive substring of `entity.name` |

Filter options are the values present in the data. A reset button clears all filters. The sidebar always shows "N of 362 cases".

**Tab 1, Overview (UC1).** In this order:
1. KPI row from `metrics.kpis`: cases, filings (distinct `report.accession`), companies (distinct `entity.cik`), rule types (distinct `assertion.type`).
2. Button "Open these cases" directly under the KPI row (leads from UC1 to UC2): switches to tab 2 and keeps the filters.
3. Bar chart of cases by `assertion.type` (M1) and bar chart of cases by filing year (M4).
4. Flag summary table (M2) with the sign_flip rate beneath it.
5. Histogram of `rel_diff` (M3) from 0 to 500% in 50 bins, sign-flip cases in a highlight color, with a caption built from `metrics.histogram_counts(df, 5.0)`: cases drawn, cases above 500% (not drawn), and comparison cases with no `rel_diff`. Median and max come from `discrepancy_summary` and cover all cases.
6. Two collapsed sections: "Cases by rule code" (M1) and "Top 10 companies" (M4).

**Tab 2, Case Explorer (UC2).** Sortable table: company, filing date, rule code, concept (shown as `prefix:concept`), period, unit, reported, calculated, flags (comma list). Selecting one row shows a detail panel: the full `assertion.detail` text, the parsed fields, absolute and relative discrepancy (only where M3 defines it; otherwise "—" and a note why), the flags, a link button to `report.sec-url` when it is a non-empty string, and a **queue status** line (leads from UC2 to UC3): the case's rank, points and reasons under the current Review Queue settings, or "not in the queue under the current triage settings".

**Tab 3, Review Queue (UC3).** Toggles for the five triage rules, a slider for the relative-gap threshold (0 to 500%, step 1%, default 10%, disabled while the large-gap rule is off), a ranked table with the columns returned by `rank_cases` (including `case_id`; `reasons` is labeled "why" on screen), and a CSV download of that same DataFrame. At the start all five rules are on and the threshold is 10%. "Reset filters" clears only the global filters, not these settings. A visible note: "Rule-based triage, not a model and not validated."

**Tab 4, Configuration Comparison (UC4).** Always present. Without a runs file it shows only "No agent runs loaded"; a runs file that cannot be loaded or scored (a missing column, or a `case_id` that is not in the ground truth) shows the error message and the same empty state. With runs: score them against the full ground truth, keep only runs on the currently filtered cases (`runs.restrict_to_cases`), then, if no runs remain, show "No agent runs on the currently filtered cases."; otherwise show the configuration table (runs, accuracy, mean cost, mean latency), a scatter of accuracy vs mean cost with one labeled point per configuration, and the error-type breakdown.

## 5. Architecture (build and check each piece alone)

The backend below already exists in `src/analysis/` and is tested (`pytest`). The app must call these functions and must not reimplement them.

| Layer | Job | Public functions | Input to output | Must not |
|---|---|---|---|---|
| `loader.py` | read and validate the clean CSV, add `case_id` | `load_clean` | path to DataFrame (34 columns + `case_id`); raises if a column is missing or the row key is not unique | compute metrics |
| `filters.py` | apply the filter state | `FilterSpec`, `apply_filters` | DataFrame + `FilterSpec` to DataFrame | read files, draw anything |
| `metrics.py` | M1 to M4 and the KPI row | `kpis`, `cases_by_type`, `cases_by_code`, `flag_summary`, `discrepancy`, `discrepancy_summary`, `histogram_counts`, `cases_by_year`, `top_companies` | filtered DataFrame to DataFrame or dict | read files, use global state, call the UI |
| `triage.py` | M5 | `TriageConfig`, `rank_cases` | filtered DataFrame + `TriageConfig` to a ranked DataFrame (`rank`, `case_id`, `points`, `reasons`, display columns) | read files |
| `runs.py` | optional input, M6 | `load_runs`, `score_runs`, `restrict_to_cases`, `config_comparison`, `error_breakdown` | path to DataFrame or None; runs + ground truth to DataFrame | touch the UI |
| `app/` | render only: layout, widgets, chart formatting | none | calls the layers above; owns widget state | count, aggregate or score anything itself, read a CSV |

`case_id` is a stable 12-character id derived from the row key; agent runs refer to cases by it. A number on screen can always be checked by calling the same function in a test.

## 6. Metrics

| ID | Question | Source columns | Calculation | Filters | Use case |
|---|---|---|---|---|---|
| M1 | Which rule types produce the most cases? | `assertion.type`, `assertion.code` | row count and share of the filtered rows, by type and by code | all | UC1 |
| M2 | How many cases look unusual? | `sign_flip`, `period_after_filing`, `unit`, `concept_prefix` | counts per flag; **sign_flip rate** = sign_flip rows / rows with a `calculated_value` (9 / 246 = 3.7%) | all | UC1 |
| M3 | How far apart are reported and calculated? | `reported_value`, `calculated_value`, `unit` | `abs_diff = abs(reported - calculated)`; `rel_diff = abs_diff / abs(reported)`, empty if reported is 0 or calculated is missing; USD rows of types 126 and 117 only; median, max, histogram. Facts in this data: 246 comparison rows, but 15 have `reported_value` 0, so `rel_diff` exists for 231; the largest `rel_diff` is about 38,000%, so the histogram is clipped at 500%: 208 cases drawn, 23 above. `histogram_counts` defines drawn as `rel_diff <= max_rel` and above as `rel_diff > max_rel` | all | UC1, UC2 |
| M4 | Where are the cases concentrated? | `report.filing-year`, `entity.name`, `entity.cik` | count by year; top 10 companies by count | all | UC1 |
| M5 | Which cases should a human see first? | flags, `rel_diff`, `concept_prefix`, `unit` | one point per rule triggered: sign_flip; period_after_filing; non-USD unit; concept prefix other than `us-gaap` (company extension or `srt`); `rel_diff` >= threshold. Rank by points, then `rel_diff` descending, then filing date descending. `reasons` lists the rules | the five rule toggles and the threshold | UC3 |
| M6 | Which configuration is accurate and cheap? | runs table + ground truth | per (agent, model): accuracy = correct runs / runs; mean `cost_usd`; mean `latency_s`; share per `error_type` | all (runs are limited to the filtered cases) | UC4 |

Why these triage rules: a sign flip is quick to verify; a late period is a date oddity; a non-USD value cannot be compared with the rest; a prefix outside `us-gaap` is harder to check against the main US-GAAP taxonomy; a large gap is a large error.

## 7. Technical choices

- Python 3.12 (create the environment with `python3.12 -m venv .venv`; the machine's default `python3` may be 3.13). Pinned in `requirements.txt`: pandas 2.3.0, numpy 1.26.4, pytest 7.4.4, streamlit 1.66.0, plotly 7.1.0, **pyarrow 21.0.0** (newer pyarrow needs NumPy 2 and crashes `st.dataframe` with numpy 1.26.4).
- No database: the file is about 1 MB, so pandas filters in memory are fast enough.
- Load the clean CSV and the runs file (if present) with `st.cache_data`, keyed by each file's modified time; filters are boolean masks on that DataFrame.
- `app/main.py` adds `<repo>/src` to `sys.path` and passes absolute paths (resolved from the repo root) to `load_clean` and `load_runs`, so the app runs from any directory. `pytest.ini` (`pythonpath = src`) covers tests only. Code imports as `from analysis.loader import load_clean`.
- Run locally: `pip install -r requirements.txt`, then `streamlit run app/main.py`. Deployment is optional and out of scope for the MVP.
- Repository layout (use exactly this):

```
data/clean/auditing_clean.csv     data/runs/agent_runs.csv (optional)
src/cleaning/clean_auditing.py    src/analysis/{loader,filters,metrics,triage,runs}.py
app/main.py                       tests/test_*.py        requirements.txt   pytest.ini
```

## 8. Optional input: agent runs

`data/runs/agent_runs.csv`, one row per run: `run_id`, `case_id`, `agent_framework`, `model`, `answer_reported`, `answer_calculated`, `cost_usd`, `latency_s`, `error_type` (structural / extraction / calculation; blank when the run is correct).

A run is **correct** when `answer_reported` equals the ground-truth `reported_value` and, where the ground truth has a `calculated_value`, `answer_calculated` equals it too (numbers equal within a relative tolerance of 1e-9). Type 15 cases are scored on the reported value only. Do not create, simulate or fill this file; the app never writes it. For tests, use a clearly named fixture under `tests/fixtures/` and never show it in the app.

## 9. Build order (stop and check after each step)

0. Run `pytest`: the backend (loader, filters, metrics, triage, runs) is done. `tests/test_real_data.py` checks acceptance items 1 to 7 on the real file (it needs `data/clean/auditing_clean.csv`).
1. App shell: sidebar filters and the Overview tab. 2. Case Explorer and the detail panel. 3. Review Queue and CSV download. 4. Tab 4 with its empty state and, if a runs file exists, its tables.

## 10. Acceptance checks

1. The loader returns 362 rows and 34 columns plus `case_id`; the row key is unique.
2. M1 counts by type are 15: 116, 117: 136, 126: 110.
3. M2: 9 sign-flip cases, 2 `period_after_filing` cases, sign_flip rate 3.7% (9 / 246). KPI row: 362 cases, 158 filings, 125 companies, 3 rule types.
4. Filtering `assertion.type = 126` gives 110 rows in every tab, and the sidebar says "110 of 362 cases".
5. M3: for the case whose reported value is -1,313,536 and calculated value -1,212,736, `abs_diff` is 100,800 and `rel_diff` is about 7.7%. For every sign-flip case `rel_diff` is exactly 200%. The histogram covers 231 cases (208 drawn, 23 above 500%) and its caption says so; 15 of the 246 comparison cases have no `rel_diff`.
6. No amount statistic mixes units; no empty `calculated_value` is shown as 0.
7. Review Queue: with only the sign-flip rule on, it lists exactly 9 cases; the CSV download has the same rows as the table.
8. Selecting a case shows the original message text and its queue status line.
9. With no runs file, tab 4 shows "No agent runs loaded" and the other tabs work.
10. "Open these cases" switches to tab 2 and the filters are unchanged.
11. `pytest` passes without the app running (64 tests with the real data; it covers items 1 to 7 and the runs scoring).

## 11. Out of scope

Trading workflows, running agents, authentication, editing data, mobile layout, visual polish.
