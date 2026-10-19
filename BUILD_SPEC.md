# BUILD_SPEC: XBRL Audit-Agent Dashboard (DSO 576, Phase 3 MVP)

Build a local Streamlit dashboard on the team's two cleaned datasets. The cleaning pipeline and the analysis backend (`src/`) already exist and pass `pytest`; Phase 3 adds only `app/`. Follow the sections in order. Do not change the data or the analysis functions to fit the UI; if something is missing, add it to the layer that owns it (section 5).

## 1. Revised vision

**User:** a finance-operations / audit-technology manager at a financial firm who is deciding how far to trust AI agents on XBRL filing checks.

**Decisions:**
1. Which agent framework + backbone model setups to shortlist for a pilot on XBRL auditing.
2. Which kinds of DQC (Data Quality Committee) error cases a human should review first, whatever agent is used.

**Why this beats current practice:** today the evidence is one table in the HERCULEAN paper (Table 2) and a CSV of 362 free-text DQC messages. The dashboard (a) ranks the 20 published setups with their error mix and 95% intervals, which shows that the top five are statistically tied and that the framework matters more than the model; (b) turns each ~2 KB DQC message into comparable numbers, groups cases by rule type, flags oddities and ranks cases for review.

**Changed since Phase 1:** Trading is dropped; the scope is Auditing only. Cost, latency and step-level traces are dropped because no per-setup data for them exists. Configuration evidence comes from the published aggregate results (65 audit instances per setup), not from our own agent runs.

## 2. Data (two canonical files, never joined)

Both files are written by `src/cleaning/clean_project_data.py` from the raw files in `data/raw/`. The app reads only `data/clean/`. Do not re-clean in the app.

| File | One row | Rows | Source |
|---|---|---|---|
| `data/clean/auditing_clean.csv` | one DQC rule that fired on one filing | 362 (158 filings, 125 companies) | `auditing_env/XBRL/mathematical_reasoning.csv`, Hugging Face `TheFinAI/Herculean` commit `52d3ecb`, SHA-256 `fa52ccea…7fdf2` |
| `data/clean/published_auditing_results.csv` | one framework + model setup | 20 (5 frameworks × 4 models) | HERCULEAN Table 2, Auditing block, arXiv:2605.14355v3 p. 9 |

**No join:** the grains differ (assertion occurrence vs setup × 65 instances) and no case-level key links them. The sidebar filters of the DQC tabs never affect the Configuration tab, and the reverse.

### 2a. `auditing_clean.csv` (362 × 34)

20 source columns plus 14 derived columns parsed from `assertion.detail`.

| Item | Definition |
|---|---|
| Row key | (`report.accession`, `assertion.code`, `assertion.detail`): unique. `report.id` repeats (204 extra rows) and is not a key |
| `case_id` | added by the loader: first 12 hex characters of SHA-1 of `report.accession + "|" + assertion.code + "|" + assertion.detail` (UTF-8); unique |
| Identifiers | `entity.cik`, `report.id`, `report.accession`, `report.sic-code` are strings (leading zeros kept) |
| `assertion.type` | integer. 15 = sign check (116 rows), 117 = total vs dimensional breakdown (136), 126 = total vs sum of child components (110). `comparison_type` holds the same as text: `sign_check` / `dimensional_breakdown` / `calculation_sum` |
| `reported_value`, `calculated_value` | numbers parsed from the message; `calculated_value` is empty for type 15 by design (116 rows) |
| `unit` | USD 330, shares 15, pure 12, bbl 4, USD/bbl 1. All 32 non-USD rows are type 15, so all 246 comparison rows are USD |
| `period`, `period_start`, `period_end` | `period_start` is empty for the 125 single-date (instant) periods |
| `concept_prefix`, `concept` | `us-gaap` 350; 12 rows use another prefix (company extension or `srt`) |
| `sign_flip` | `calculated_value == -reported_value`, nonzero: 9 rows |
| `period_after_filing` | `period_end` later than `report.filing-date`: 2 rows |
| Dates | stored as the source text; all three date fields parse with 0 failures. The app parses `report.filing-date` for sorting only |

Rules: never sum or average amounts across units; any amount statistic uses `unit == "USD"` rows only. Never show a missing value as 0: show "—" in the detail panel and an empty cell in tables. Flags are marks, not corrections: no value is ever edited.

### 2b. `published_auditing_results.csv` (20 rows)

| Column | Definition |
|---|---|
| `framework` | ReAct Agent, Claude Code, Codex, Hermes, OpenClaw |
| `model`, `model_name` | code and display name: `sonnet` Claude Sonnet 4.6, `gpt` GPT-5.4, `qwen397` Qwen3.5-397B-A17B, `qwen27` Qwen3.5-27B. Show `model_name` on screen |
| `accuracy_pct`, `structural_error_rate_pct`, `extraction_error_rate_pct`, `calculation_error_rate_pct` | published % of 65 audit instances (ACC, SER, EER, CER); each row sums to 100 ± 0.01 (rounding) |
| `audit_instances`, `acc_instances`, `ser_instances`, `eer_instances`, `cer_instances` | 65, and each rate × 65 rounded; they reproduce every published rate to 2 decimals |
| `results_scope`, `source`, `paper_version`, `source_table`, `source_page` | provenance; not shown except in a footnote |

### 2c. Team reconciliation (Module 6 → canonical)

| Topic | Disagreement | Decision |
|---|---|---|
| Base pipeline | five individual cleanings | Ling's `clean_project_data.py` (full-file checks, published table), extended with Jinyang's 14 parsed fields (`src/cleaning/parse_detail.py`) |
| `entity.cik` | kept as source text (Ling, Lingxiao) vs zero-padded to 10 digits (Jinyang) | source text, not padded |
| `assertion.type` | integer (Ling) vs string (Lingxiao) | integer; labels come from the table in 2a |
| `entity.name` | trim only (Ling, Lingxiao) vs also replace `\xa0` (Jinyang) | Jinyang's rule: `\xa0` → space, collapse repeated whitespace, trim (7 values change, 5 of them `\xa0`; company count stays 125) |
| Dates | kept as text (Ling) vs parsed (Lingxiao) | kept as text in the file, validated at clean time (0 failures) |
| Row key | none (Ling), body without timestamp (Jinyang), full detail (Lingxiao) | Lingxiao's key; unique on all 362 rows |
| Repeated `report.id` | all agreed | keep all rows; no imputation, no drops (362 in, 362 out) |
| Acceptance vs filing date | Lingxiao flags 43 rows | not used in the MVP; both dates kept |
| Samples | 47 rows (Ling), 50 rows (Jinyang) | Module 6 artifacts only; the app reads the full file |
| `prices`, `filings` (Raymond, Bella) | trading data | out of scope; not on `main` |

Full cleaning evidence: `cleaning_decision_log.md`, `outputs/cleaning_summary.json`.

## 3. Use cases (select → see → decide)

| # | User selects | Dashboard shows | User decides |
|---|---|---|---|
| UC1 | a minimum ACC, a maximum SER, frameworks and models | ranked setups with counts out of 65, 95% intervals, error mix, tie note | which 2–3 setups to pilot |
| UC2 | a metric for the framework × model grid | heatmap and the spread of framework means vs model means | whether to spend effort on choosing the framework or the model |
| UC3 | opens the DQC overview (or picks a rule type or year) | case counts by rule type, flag counts, size of discrepancies | which rule type to look at first |
| UC4 | a rule type, company or year, then one case | the original DQC message beside the extracted values, the discrepancy and flags | whether the case is a clear pattern (e.g. a pure sign flip) or needs human judgment |
| UC5 | which triage rules are on and the gap threshold | cases ranked by how many rules they trigger, with reasons | which cases go to human review first (exports the list) |

Every view in section 4 serves one of these.

## 4. Dashboard

**Navigation:** a horizontal `st.radio` at the top with four pages, its value held in `st.session_state["page"]` (not `st.tabs`, which cannot be switched from code): **Configuration Shortlist**, **DQC Overview**, **Case Explorer**, **Review Queue**. Starting view: **Configuration Shortlist** with default controls.

### Page 1, Configuration Shortlist (UC1, UC2)

Own controls at the top of the page (the sidebar is hidden or shows only "Filters apply to DQC pages"):

| Control | Default |
|---|---|
| Minimum ACC slider, 0–100, step 1 | 0 |
| Maximum SER slider, 0–100, step 1 | 100 |
| Framework multiselect | all |
| Model multiselect (display names) | all |
| Heatmap metric radio: ACC / SER / EER / CER | ACC |

Content, in this order:
1. KPI row from `shortlist_kpis`: setups shown (N of 20), best ACC with its count (e.g. "66.15% · 43/65"), number of setups tied at the best ACC.
2. Ranked table (`rank_configs` → `shortlist`): rank, framework, model, ACC, 95% interval, SER, EER, CER, `acc_instances`/65. Rows with `overlaps_leader` true get a marker. Note under the table: "Marked setups' intervals overlap the leader's, so they are not statistically separated; 65 instances per setup; published aggregates, not our own runs."
3. 100% stacked horizontal bar per shown setup from `error_mix`: ACC, SER, EER, CER, in table order.
4. Framework × model heatmap from `framework_model_matrix` (all 20 setups regardless of the shortlist controls; fixed row/column order; values written in cells), with a caption from `framework_model_effects`: range of framework means vs range of model means.

Empty state: when no setup passes the controls, show "No setup meets these thresholds" and hide items 2–3.

### Pages 2–4 share the DQC sidebar

| Filter | Control | Behaviour |
|---|---|---|
| `assertion.type` | multiselect, labels "15 · sign check", "117 · total vs dimensional breakdown", "126 · total vs sum of child components" | none = all |
| `report.filing-year` | multiselect | none = all |
| `concept_prefix` | radio: any / us-gaap / other | |
| `unit` | multiselect | none = all |
| period kind | radio: any / range / instant | instant = empty `period_start` |
| flags | checkboxes "Only sign flips", "Only period after filing date" | both checked = both must be true |
| company | text box | case-insensitive substring of `entity.name` |

Options are the values present in the data. A reset button clears these filters only. The sidebar always shows "N of 362 cases".

### Page 2, DQC Overview (UC3)
1. KPI row from `kpis`: cases, filings (distinct `report.accession`), companies (distinct `entity.cik`), rule types.
2. Button "Open these cases": sets the page to Case Explorer; filters unchanged.
3. Bar charts: cases by `assertion.type` (M1) and by filing year (M4).
4. Flag summary table (M2) with the sign_flip rate beneath it.
5. Histogram of `rel_diff` (M3) from 0 to 500%, 50 bins, sign-flip cases in a highlight color; caption from `histogram_counts(df, 5.0)`: cases drawn, cases above 500% (not drawn), comparison cases without `rel_diff`. Median and max come from `discrepancy_summary` and cover all cases.
6. Collapsed sections: "Cases by rule code" (M1) and "Top 10 companies" (M4).

### Page 3, Case Explorer (UC4)
Sortable table with single-row selection (`st.dataframe` `on_select`): company, filing date, rule code, concept (`prefix:concept`), period, unit, reported, calculated, flags (comma list). Default sort: filing date descending. Selecting a row shows a detail panel: the full `assertion.detail` text, the parsed fields, `abs_diff` and `rel_diff` (where M3 defines them; otherwise "—" and the reason), the flags, a link button to `report.sec-url`, and a queue status line from `queue_status`: rank, points and reasons under the current Review Queue settings, or "not in the queue under the current triage settings". With nothing selected, show "Select a case to see its details".

### Page 4, Review Queue (UC5)
Toggles for the five triage rules (all on at start), a slider for the gap threshold (0–500%, step 1%, default 10%, disabled while the large-gap rule is off; passed to `TriageConfig.gap_threshold` divided by 100), the ranked table returned by `rank_cases` (`reasons` labeled "why"), and a CSV download of that same DataFrame. Reset filters does not reset these settings. Visible note: "Rule-based triage, not a model and not validated."

## 5. Architecture (each piece built and checked alone)

| Layer | Job | Public functions | Input → output | Must not |
|---|---|---|---|---|
| `src/cleaning/clean_project_data.py` (+ `parse_detail.py`) | raw → the two clean files + Module 6 evidence | `main` (CLI); `add_derived_fields` | `data/raw/*` → `data/clean/*.csv`, `outputs/*` | be imported by the app |
| `analysis/loader.py` | read and validate the DQC file, add `case_id` | `load_clean` | path → DataFrame (34 + `case_id`); raises if a column is missing or the key is not unique | compute metrics |
| `analysis/filters.py` | apply DQC filter state | `FilterSpec`, `apply_filters` | DataFrame + `FilterSpec` → DataFrame | read files, draw |
| `analysis/metrics.py` | M1–M4 and KPIs | `kpis`, `cases_by_type`, `cases_by_code`, `flag_summary`, `discrepancy`, `discrepancy_summary`, `histogram_counts`, `cases_by_year`, `top_companies` | filtered DataFrame → DataFrame or dict | read files, use global state |
| `analysis/triage.py` | M5 | `TriageConfig`, `rank_cases`, `queue_status` | filtered DataFrame + `TriageConfig` → ranked DataFrame (`rank`, `case_id`, `points`, `reasons`, display columns incl. `rel_diff`); ranked + `case_id` → dict or None | read files |
| `analysis/published.py` | M6–M8 | `load_published`, `wilson_ci`, `rank_configs`, `shortlist`, `shortlist_kpis`, `error_mix`, `framework_model_matrix`, `framework_model_effects` | path → validated DataFrame (adds `setup` = "framework + model_name"); DataFrame + controls → DataFrame or dict | touch the DQC data or the UI |
| `app/main.py` | render only: navigation, widgets, charts | — | calls the layers above; owns widget state | count, aggregate, score or read a CSV itself |

`load_published` raises if there are not 20 rows, a rate is outside 0–100, or a row's four rates do not sum to 100 ± 0.01. Every number on screen comes from one of these functions, so a test can check it without the app.

## 6. Metrics

| ID | Question | Source columns | Calculation | Controls |
|---|---|---|---|---|
| M1 | Which rule types produce the most cases? | `assertion.type`, `assertion.code` | row count and share of filtered rows, by type and by code | DQC filters |
| M2 | How many cases look unusual? | `sign_flip`, `period_after_filing`, `unit`, `concept_prefix` | count per flag; sign_flip rate = sign_flip rows / rows with a `calculated_value` (9 / 246 = 3.7%) | DQC filters |
| M3 | How far apart are reported and calculated? | `reported_value`, `calculated_value`, `unit` | `abs_diff = |reported − calculated|`; `rel_diff = abs_diff / |reported|` as a fraction (2.0 = 200%; the UI shows %), empty if reported is 0 or calculated missing; USD rows of types 117 and 126 only; median, max, histogram (drawn = `rel_diff <= max_rel`, above = `> max_rel`) | DQC filters |
| M4 | Where are cases concentrated? | `report.filing-year`, `entity.name`, `entity.cik` | count by year; top 10 companies by count, ties broken by name A–Z | DQC filters |
| M5 | Which cases should a human see first? | flags, `rel_diff`, `concept_prefix`, `unit` | one point per rule triggered: sign_flip; period_after_filing; unit ≠ USD; prefix ≠ `us-gaap`; `rel_diff` ≥ threshold. Sort by points desc, `rel_diff` desc (empty last), filing date desc; `rank` = 1..N in that order; `reasons` lists the rules | rule toggles, threshold |
| M6 | Which setups are most accurate, and is the lead real? | `accuracy_pct`, `acc_instances`, `audit_instances` | Wilson 95% interval (z = 1.96, in %) on `acc_instances`/65; `rank` = competition rank on ACC desc over all 20 (ties share a rank; filtering never re-ranks); `overlaps_leader` = interval high ≥ leader's interval low; display order ACC desc, SER asc, CER asc, framework A–Z, model A–Z | shortlist controls |
| M7 | How does each setup fail? | SER, EER, CER, ACC columns | the four published % per setup (`error_mix`, long format) | shortlist controls |
| M8 | Does framework or model matter more? | `framework`, `model`, chosen metric | 5 × 4 matrix; mean per framework and per model; range (max − min) of each set of means | heatmap metric |

Why these triage rules: a sign flip is quick to verify; a late period is a date oddity; a non-USD value cannot be compared with the rest; a non-`us-gaap` concept is harder to check against the main taxonomy; a large gap is a large error.

## 7. Technical choices

- Python ≥ 3.11 (backend tested on 3.11.8 with pandas 3.0.5), Streamlit ≥ 1.40 (for `st.dataframe` row selection), Plotly, pytest; see `requirements.txt`.
- No database: the two files total about 1 MB; pandas boolean masks in memory are fast enough.
- Load both clean files once with `st.cache_data`, keyed by file modified time.
- `app/main.py` adds `<repo>/src` to `sys.path` and resolves data paths from the repo root, so it runs from any directory. `pytest.ini` sets `pythonpath = src`. Imports look like `from analysis.loader import load_clean`.
- Run: `pip install -r requirements.txt`, `python src/cleaning/clean_project_data.py`, `pytest`, `streamlit run app/main.py`. Deployment is out of scope; nothing depends on local-only state, so Streamlit Community Cloud would work later.
- Layout (use exactly this):

```
data/raw/mathematical_reasoning.csv   data/raw/benchmark_results.csv
data/clean/auditing_clean.csv         data/clean/published_auditing_results.csv
src/cleaning/{clean_project_data,parse_detail}.py   src/analysis/{loader,filters,metrics,triage,published}.py
app/main.py (Phase 3)   tests/{conftest,test_units,test_real_data}.py   outputs/   requirements.txt   pytest.ini
```

## 8. Build order (stop and check after each step)

0. Already done in Phase 2: run `python src/cleaning/clean_project_data.py`, then `pytest` (33 tests: unit tests per layer, and `test_real_data.py` checks acceptance items 1–8 plus the backend parts of 9 and 11 on the real files). Phase 3 starts at step 1 and adds only `app/`.
1. App shell: navigation and Configuration Shortlist page.
2. DQC sidebar filters and DQC Overview.
3. Case Explorer and detail panel.
4. Review Queue and CSV download.

## 9. Acceptance checks

1. `load_published` returns 20 rows; every row's rates sum to 99.99–100.01.
2. With default controls, rank 1 is a three-way tie at 66.15% (43/65): Claude Code + Claude Sonnet 4.6, OpenClaw + Claude Sonnet 4.6, OpenClaw + GPT-5.4; interval ≈ 54.0–76.5%. Next are Codex + Claude Sonnet 4.6 and Codex + GPT-5.4 at 63.08% (41/65), interval ≈ 50.9–73.8%, shown with rank 4.
3. Max SER = 0 leaves 10 setups; adding min ACC = 60 leaves 5. All 8 ReAct Agent and Hermes setups have SER 80%.
4. Framework mean ACC ranges 14.23 (ReAct Agent) to 53.08 (OpenClaw), range 38.85; model mean ACC ranges 28.61 (Qwen3.5-27B) to 47.08 (Claude Sonnet 4.6), range 18.47.
5. `load_clean` returns 362 rows, 34 columns plus a unique `case_id`. KPI row: 362 cases, 158 filings, 125 companies, 3 rule types. By type: 15: 116, 117: 136, 126: 110.
6. M2: 9 sign flips, 2 period-after-filing, sign_flip rate 3.7% (9/246).
7. M3: the case with reported −1,313,536 and calculated −1,212,736 has `abs_diff` 100,800 and `rel_diff` ≈ 7.7%; every sign flip has `rel_diff` exactly 200%. 246 comparison rows, 231 with `rel_diff` (15 have reported 0): 208 drawn, 23 above 500%.
8. Review Queue with only the sign-flip rule on lists exactly 9 cases; the CSV has the same rows as the table.
9. Filtering `assertion.type = 126` gives 110 rows on pages 2–4, the sidebar shows "110 of 362 cases", and page 1 is unchanged.
10. "Open these cases" switches to Case Explorer with the filters unchanged; selecting a case shows its original message and queue status.
11. No amount statistic mixes units; no empty `calculated_value` appears as 0.

## 10. Out of scope

Trading workflows, running our own agents, cost and latency, joining DQC cases to setups, authentication, editing data, mobile layout, visual polish. Possible extension after the MVP: a per-run results file keyed by `case_id`, scored against `auditing_clean.csv`.
