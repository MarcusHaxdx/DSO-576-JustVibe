# Build prompt: HERCULEAN auditing decision dashboard

Build a local Streamlit dashboard for a model-risk or financial-technology manager choosing an agent-framework and backbone-model configuration for AI-assisted XBRL auditing. Implement the requirements below, using pandas for analysis and Altair for interactive charts. Deliver working application code, dependency updates, concise launch instructions, and the validation results. Respect `AGENTS.md`; preserve existing user changes, keep git read-only, preserve raw data, and do not execute notebook cells. This document specifies a future implementation; it does not claim the dashboard already exists.

## 1. Objective and evidence boundary

Help the manager shortlist configurations by published accuracy and error composition, then explore DQC assertion records to select cases for human investigation. Accuracy is primary. Error composition informs review design. The initial dashboard supports evidence review and pilot selection, not a production deployment approval.

Read `README.md`, `project-start.md`, `data/data_fact.md`, `cleaning_report.md`, `pyproject.toml`, and the source of `src/notebook/01-cleaning.ipynb`. Do not inspect PDF or Word files. The current executable package is a placeholder, and no dashboard exists yet. Dependencies currently include pandas and JupyterLab; Python is >=3.13 and uv is the environment manager.

The earlier vision mentions Trading, execution traces, cost, and latency. The available local evidence supports Auditing only. Deliver the auditing dashboard first. Do not add Trading tabs, simulated runs, invented costs, a cost–performance scatterplot, confidence scores, early stopping, or automatic model routing. Explain unavailable capabilities in the evidence section. Every implemented major feature must map to a use case below.

Maintain two independent data grains:

1. **Published configuration results:** 20 framework–model combinations, each reporting ACC/SER/EER/CER over 65 audit instances. These are paper aggregates, not estimates derived from the local CSV.
2. **DQC assertion corpus:** 362 assertion occurrences from 158 filings, 125 entities, 61 assertion codes, three assertion types, filing years 2022–2024. These are source records, not configuration-specific agent failures.

There is no valid join between these grains. Never assign a configuration's error rates to a filing, assertion, rule type, entity, year, or form. Never multiply percentages by 362 to estimate successes or failures. The 20 configurations are evaluations of benchmark instances, not 1,300 distinct cases.

## 2. Use cases and feature mapping

Use this exact decision sequence to guide implementation:

| ID | User selects/inputs → Dashboard shows → User decides | Major features serving it |
|---|---|---|
| U1 | User selects frameworks and models → Dashboard shows published ACC rankings and a framework-by-model heatmap, with ties and the 65-instance denominator → User decides which configurations to compare for a controlled pilot. | Configuration filters, ranking, heatmap, result table. |
| U2 | User selects two configurations → Dashboard shows their accuracy and structural/extraction/calculation error composition, plus percentage-point differences → User decides which error pattern merits investigation or additional verification in a pilot. | Comparison selectors, paired values, error-composition chart. |
| U3 | User inputs a minimum ACC and maximum SER → Dashboard shows configurations meeting both exploratory criteria and each configuration's margin to the criteria → User decides a shortlist under their stated criteria, without treating it as deployment approval. | Optional threshold controls, eligibility table, shortlist export. |
| U4 | User selects filing years, form types, entities, assertion types/codes, or a search term → Dashboard shows matching assertion counts, distinct filings/entities/rules, corpus distributions, and records → User decides which part of the corpus to investigate. | Independent corpus filters, summary cards, distributions, searchable record table. |
| U5 | User selects an assertion record → Dashboard shows complete DQC detail, filing metadata, date-difference flag, and source links → User decides whether to open the SEC filing and add the record to a manual investigation list. | Record detail, source links, explicit selection, session investigation list and CSV export. |
| U6 | User opens evidence and definitions or checks a source-validation message → Dashboard shows data provenance, grain, calculation definitions, validation status, and missing evidence → User decides whether the evidence is sufficient for the intended comparison or whether new runs are required. | Persistent evidence labels, provenance/definitions section, source validation. |

The investigation list is user-selected source evidence. It is not a prediction of agent failure, a risk score, or proof that a filing is wrong. All source severities are DQC labels; they do not measure agent performance.

## 3. Data contracts and preparation

### Published results

Create a version-controlled `data/reference/auditing_configuration_results.csv` using the transcription in notebook cell 16. Read the notebook as JSON/source; do not execute or import it. Store exactly these values, in percentage units 0–100:

| framework | model | ACC_pct | SER_pct | EER_pct | CER_pct |
|---|---|---:|---:|---:|---:|
| ReAct Agent | sonnet | 20.00 | 80.00 | 0.00 | 0.00 |
| ReAct Agent | gpt | 3.08 | 80.00 | 0.00 | 16.92 |
| ReAct Agent | qwen397 | 15.38 | 80.00 | 0.00 | 4.62 |
| ReAct Agent | qwen27 | 18.46 | 80.00 | 0.00 | 1.54 |
| Claude Code | sonnet | 66.15 | 0.00 | 6.15 | 27.69 |
| Claude Code | gpt | 44.62 | 0.00 | 6.15 | 49.23 |
| Claude Code | qwen397 | 36.92 | 3.08 | 9.23 | 50.77 |
| Claude Code | qwen27 | 43.08 | 0.00 | 12.31 | 44.62 |
| Codex | sonnet | 63.08 | 0.00 | 6.15 | 30.77 |
| Codex | gpt | 63.08 | 0.00 | 6.15 | 30.77 |
| Codex | qwen397 | 49.23 | 0.00 | 6.15 | 44.62 |
| Codex | qwen27 | 27.69 | 44.62 | 7.69 | 20.00 |
| Hermes | sonnet | 20.00 | 80.00 | 0.00 | 0.00 |
| Hermes | gpt | 20.00 | 80.00 | 0.00 | 0.00 |
| Hermes | qwen397 | 20.00 | 80.00 | 0.00 | 0.00 |
| Hermes | qwen27 | 16.92 | 80.00 | 0.00 | 3.08 |
| OpenClaw | sonnet | 66.15 | 0.00 | 6.15 | 27.69 |
| OpenClaw | gpt | 66.15 | 0.00 | 6.15 | 27.69 |
| OpenClaw | qwen397 | 43.08 | 0.00 | 10.77 | 46.15 |
| OpenClaw | qwen27 | 36.92 | 0.00 | 7.69 | 55.38 |

Add `audit_instances=65` to each row. The composite key is `(framework, model)`. Preserve model aliases as transcribed; do not guess expanded model names or versions. Label them as source aliases and include their mapping only if verified evidence is later supplied.

Reference: HERCULEAN paper, Auditing portion of Table 2, https://arxiv.org/html/2605.14355v3, as locally transcribed. Record this provenance alongside the reference table. ACC means accuracy; SER structural error rate; EER extraction error rate; CER calculation error rate. Do not invent finer error definitions beyond the available documentation.

Validate 20 unique configurations, numeric rates in [0,100], 65 instances per row, and each row's rate sum within 0.02 percentage points of 100. Preserve published rounding; do not normalize values or reconstruct integer counts. On invalid results, block configuration analysis and show an actionable validation message.

### Assertion corpus

Read `data/raw/mathematical_reasoning.csv` with `pd.read_csv(..., dtype="string", keep_default_na=False)`. Source revision: `52d3ecb97e490a2392717935402cde283e8fa36e`; download date: 2026-10-05; SHA-256: `fa52ccea5b80ea8ff1b27e5e38b5510caf74a82682858e1cc53641bbd1f7fdf2`. Do not modify the raw file or download a newer release automatically.

Use `(report.accession, assertion.code, assertion.detail)` as the assertion key. Use `report.accession` as the filing key and `entity.cik` as the entity key. Neither `folder_name` nor `(report.accession, assertion.code)` is a unique assertion key. Preserve leading zeros and internal detail whitespace. A stable digest of the complete composite key may be used for widget/session identifiers; retain the original fields for exports.

Keep these source columns available:

- Assertion: `assertion.code`, `assertion.detail`, `assertion.run-date`, `assertion.severity`, `assertion.source`, `assertion.type`.
- Entity: `entity.cik`, `entity.name`.
- Filing: `report.accepted-timestamp`, `report.accession`, `report.base-taxonomy`, `report.creation-software`, `report.document-type`, `report.entry-url`, `report.filing-date`, `report.filing-year`, `report.id`, `report.sec-url`, `report.sic-code`, `folder_name`.

Parse run date and filing date as dates, accepted timestamp as a timestamp, and filing year as nullable integer. Preserve raw fields alongside parsed values where needed for details/export. Keep assertion type, CIK, SIC, report ID, and accession as strings. Strip only surrounding display whitespace; do not case-fold stored names or rewrite evidence. Derive `accepted_date_differs` from the calendar-date comparison of accepted timestamp and filing date, without inventing a timezone. This is a source-date difference, not a confirmed data error.

Validate hash, 362×20 source shape, unique composite keys, zero blank fields, zero failed nonblank conversions, and the reported category totals. Report checks actually run by the application separately from the notebook's unexecuted status. On missing files, hash mismatch, or invalid schema, block the affected view with a specific message; do not silently serve a partial corpus. Keep the other independent view usable if its own source passes validation.

## 4. Starting view, navigation, and controls

Use a wide layout with the title **HERCULEAN Auditing — Configuration & Evidence Explorer**. Display a short evidence banner: “Published configuration aggregates and a separate DQC assertion corpus; case-level agent predictions, cost, and latency unavailable.”

Use a single section selector with three views, retaining state when navigating:

1. **Compare configurations** — default landing view, serving U1–U3.
2. **Explore DQC assertions** — serving U4–U5.
3. **Evidence & definitions** — serving U6.

On first load show all five frameworks and four models, no active threshold criteria, 20 configurations, highest published ACC of 66.15%, and all three tied leaders. Below the cards show the ACC ranking and heatmap, followed by the paired comparison and optional criteria section. Default comparison: Claude Code/sonnet versus ReAct Agent/sonnet. Do not select a single winner from a tie.

Keep filter state scoped to its data source; show only the current view's controls. Framework/model filters must never change corpus counts. Corpus filters must never change published rates. Label counts as “matching” and, where useful, show unfiltered totals. Provide separate reset buttons for each view's filters.

Configuration controls: framework and model multiselects, all selected initially; independent sort by ACC descending, SER/EER/CER ascending, or framework/model. Resolve display order ties alphabetically without changing tied rank. Empty selections mean no matches, with a reset action. Comparison selectors must draw from matching configurations and require two distinct selections; if fewer than two remain, explain why comparison is unavailable.

Corpus controls: filing year, form (10-K/10-Q), entity (name with CIK), assertion type (literal source labels 15/117/126), assertion code, optional accepted-date-difference-only toggle, and case-insensitive literal substring search across `entity.name`, `entity.cik`, `report.accession`, `assertion.code`, and `assertion.detail`. Use OR within each multiselect and AND across controls; search matches any listed field. Default to all categories, blank search, and flag toggle off. An empty multiselect returns zero rows. Use fixed source option lists to avoid surprising disappearing options. Do not label the run date as an agent execution timestamp.

## 5. Metric and visual contracts

Every chart needs a descriptive title, visible units, source label, relevant denominator, and a matching accessible table. Use percentages to two decimals and differences in percentage points (pp). Fixed 0–100 axes make comparisons consistent. Avoid red/green-only distinctions; pair colors with labels. Tooltips repeat the configuration/category and exact value.

### Configuration analysis — U1–U3

All items below use the reference configuration table. Framework/model filters apply first; corpus filters never apply. Thresholds affect only the eligibility section and its export, not the baseline comparison population.

| Metric or visual | Question answered | Source columns and calculation | Relevant filters/interactions |
|---|---|---|---|
| Matching configuration count | How many alternatives am I considering? | Count unique `(framework, model)` rows after filtering. | Framework/model. Show 0 in empty state. |
| Best ACC and tied leaders | Which matching configurations have the highest published accuracy? | `max(ACC_pct)` and every row equal to that value; no averaging across configurations. | Framework/model. Undefined best value displays “—” for no matches. |
| Horizontal ACC ranking | Which configurations perform best on published accuracy? | One bar per composite configuration, height/length `ACC_pct`; descending order by default, equal rates have equal rank. | Framework/model and sort control; selection may populate comparison A, with explicit confirmation in the UI. |
| Framework × model heatmap | Does the same model differ across frameworks? | One cell per `(framework, model)`, color and text=`ACC_pct`; no aggregation or interpolation. | Framework/model. Filtered/unavailable cells are absent or gray, never zero. |
| Published results table | What are all four rates for each alternative? | Display framework, model, ACC/SER/EER/CER and `audit_instances` unchanged. | Framework/model; sorting; export current table. |
| Paired comparison and error-composition chart | Where do these two configurations differ? | Two horizontal stacked bars using ACC/SER/EER/CER, and table with each raw rate plus `A_rate - B_rate` pp; higher ACC and lower error rates are favorable. | Framework/model and A/B selectors. Preserve rounding in stacks; note totals may differ from 100 by rounding. |
| Criteria eligibility and count | Which configurations meet my exploratory thresholds? | When enabled, eligible iff `ACC_pct >= min_ACC` AND `SER_pct <= max_SER`; count eligible rows. Display margins `ACC_pct - min_ACC` and `max_SER - SER_pct` in pp. | Framework/model and optional threshold controls. Include eligible/ineligible rows and reasons; export eligible subset. |

Criteria controls are disabled initially. Enabling them starts at min ACC=0% and max SER=100%, with a clear “unrestricted criteria” label, until the user changes them. Accept values from 0 to 100 at 0.01 precision; comparisons use the stored published values, inclusive at boundaries. No unrequested default safety threshold. If none qualify, say “No configurations meet these criteria” and keep the comparison visible. Do not claim significance, generalization, or production readiness from these small aggregate evaluations.

Do not average framework/model accuracies into a headline performance score: the dashboard compares configurations. There are no case-level labels to support significance tests, error-by-rule charts, or per-filing success estimates.

### Assertion exploration — U4–U5

Let `F` denote the corpus after all corpus controls. Every item here uses `F`; framework/model/criteria controls do not apply.

| Metric or visual | Question answered | Source columns and calculation | Relevant filters/interactions |
|---|---|---|---|
| Assertion occurrences | How many source evidence records match? | `len(F)`; row grain, not unique rule count. | All corpus controls. |
| Distinct filings, entities, rules | How broad is the matching corpus? | `nunique(report.accession)`, `nunique(entity.cik)`, `nunique(assertion.code)` respectively. | All corpus controls; never sum distinct counts across overlapping groups. |
| Assertion type distribution | Which source rule categories dominate the selection? | Group by `assertion.type`, count rows; share=`group rows / len(F) * 100`. Horizontal bars plus counts/shares table. | All corpus controls; clicking a type can explicitly set its filter. Type numbers are categories, not magnitudes. |
| Filing-year × form distribution | How are matching assertions distributed across filing years and forms? | Group by `report.filing-year`, `report.document-type`, count rows; grouped bars, chronological years. Include distinct filings per group in the companion table. | All corpus controls. This is corpus composition, not an agent-performance time trend. |
| Top assertion codes | Which rules supply the most matching examples? | Count rows by `assertion.code`, descending; top 10 with alphabetical tie ordering. Full counts table remains available; optional share uses `len(F)` including codes outside top 10. | All corpus controls; selecting a code can explicitly set its filter. |
| Date-difference count | How many matching assertion records have differing acceptance and filing dates? | Sum `accepted_date_differs` over `F`; label “assertion records,” not filings. | All corpus controls including flag-only toggle; show definition beside value. |
| Record table and detail | What evidence supports this specific source assertion? | No aggregation. Table: entity name/CIK, accession, filing date, form, assertion type/code, severity, and detail preview. Detail: full assertion text and all source metadata, including both dates, taxonomy, software, source, report ID, folder, and URLs. | All corpus controls; single-row selection by composite key, stable sort/pagination, detail follows selected row. |
| Manual investigation list | Which records did I explicitly choose to investigate? | Unique selected composite keys, joined only to the same corpus; display selected count and source fields. | Session-wide selection persists across corpus filters; label list scope and how many are outside current filters. Add/remove/clear controls affect session state only. |

For zero matching records, display zero count cards and a reset hint. Suppress percentage calculations and chart marks instead of dividing by zero. Clear a stale detail selection when its row leaves `F`; do not silently substitute another assertion.

Render full details as plain text, preserving evidence; optionally provide a separate readable display of literal `\\n`/`\\t` sequences while retaining the exact raw text for download. Do not truncate the detail panel. Open `report.sec-url` and `report.entry-url` in new tabs after validating an http(s) SEC host (`sec.gov` or a subdomain); render invalid links as text. Do not fetch filing contents automatically or execute source text as HTML.

### Evidence & definitions — U6

Show source paths/links, CSV revision/download date/hash, observed source dimensions, source validation results, composite keys, the independent grains, metric formulas, acronym definitions, filter scopes, and the notebook's unexecuted status. A small reconciliation table must show actual observed counts versus the expected 362 assertions, 158 filings, 125 entities, 61 rules, and 20 configurations; distinguish observed checks from static documentation.

Explain that the earlier 4,959-row vision does not describe this pinned 362-row release. The 65 audit instances per configuration cannot be mapped to the 362 assertion occurrences. Date-difference flags are preserved source facts, not confirmed filing defects. Cost, latency, run-level predictions, execution traces, and Trading evaluation data are absent from the current local sources.

List future evidence needed for the broader project: task/instance IDs mapped to assertions/filings; framework/model/version and run IDs; predictions and reference labels; workflow-specific outcomes; timestamps/statuses; cost records with currency; step/tool traces; repeated runs for Trading stability. New data requires an explicit contract and validated keys before any join or new view. Present this as explanatory text, not nonfunctional controls.

## 6. Important interactions and exports

- Changes rerun the active view while preserving scoped filters, comparison choices where valid, and the investigation list in `st.session_state`.
- Chart selection is optional sugar over explicit controls. If implemented, visibly update the corresponding widget; do not maintain hidden chart filters. A reset clears chart selections too.
- Configuration exports contain exactly the displayed matching results or explicitly labeled eligible subset, with all four rates, denominator, active criteria if any, and source reference. Preserve published values, no derived pseudo-counts.
- Corpus export contains all matching records, not just the current table page. Investigation-list export contains all manually chosen records, including those outside current filters. Include composite-key fields, original detail, source URLs, and the derived date flag. Clearly label each export's scope and row count.
- CSV serialization must preserve identifier text and quote multiline details correctly. Keep raw values; document importing identifier columns as text in spreadsheet software. Downloads are user-triggered and do not write over source files.
- No email, external publication, SEC scraping, or live agent execution is part of the dashboard.

## 7. Architecture and implementation scope

Keep analysis functions pure and separate from Streamlit rendering so calculations can be verified without running a notebook. Recommended new files for the implementation:

```text
src/project/dashboard.py                  # Streamlit entry point and view rendering
src/project/dashboard_data.py             # Paths, cached loading boundary, validation
src/project/dashboard_analysis.py         # Filtering, grouping, comparison, criteria
data/reference/auditing_configuration_results.csv
tests/test_dashboard_analysis.py           # Focused grain/formula/filter checks
```

Use `pathlib` paths relative to the package/project, not the shell working directory. Use pandas for transformations, Altair for charts, Streamlit for controls and `st.cache_data` for validated data loads. Include file content hash or modification metadata in cache invalidation so changed sources trigger validation. Do not create a database or API server for these two small tables. Session-only manual selections require no persistence service.

During implementation, add Streamlit and Altair to `pyproject.toml` with uv and update its lockfile if generated. Use the existing pandas dependency. Add a test runner as a development dependency only if needed for the chosen checks. Keep changes limited to dashboard-related files and the README launch/usage instructions; do not refactor the placeholder package or rewrite the cleaning notebook. No new notebook is necessary.

Expected launch from project root: `uv run streamlit run src/project/dashboard.py`. Make imports work under that exact invocation. Runtime should require no network connection; external source links open only when selected. Use concise user-facing labels and explanations instead of implementation details.

## 8. Build order

1. **Confirm sources and freeze contracts (U6).** Inspect local documentation and notebook source, check the CSV schema/hash and independent counts, and create the reference table from the explicit transcription above. Resolve any disagreement visibly; do not replace sources silently.
2. **Implement data preparation and analysis (U1–U4, U6).** Build separate loaders, validation, scoped filters, grouping functions, ranking/tie handling, comparison deltas, and inclusive criteria evaluation. Verify grain and denominator calculations before UI work.
3. **Build the landing comparison view (U1–U3).** Add navigation, evidence banner, default filters/cards, ranking, heatmap, results table, paired error view, optional criteria and exports. Keep absence of cost/latency explicit.
4. **Build corpus exploration (U4–U5).** Add independent corpus controls, counts, distributions, stable row selection, complete detail, validated SEC links, and session investigation list/exports.
5. **Complete evidence and state handling (U6).** Add provenance, metric definitions, observed validation results, limitations, scoped resets, empty states, and invalid-source states. Verify that views never cross-filter or join independent grains.
6. **Verify and document.** Run focused automated checks and a Streamlit smoke test, inspect charts/tables at a desktop viewport, and verify readable navigation at a narrower viewport. Update README with uv setup, launch, source boundaries, and export behavior. Report checks run and unresolved issues; do not populate notebook outputs.

## 9. Concrete acceptance checks

1. **Baseline integrity:** With no filters, corpus cards show 362 assertions, 158 filings, 125 entities, 61 rules. Form groups are 145 10-K and 217 10-Q assertion rows. Type groups are 116 type 15, 136 type 117, and 110 type 126. Date-difference count is 43 assertion records. All category counts reconcile to the same filtered row population.
2. **Landing and ties:** First load shows 20 configurations and 66.15% best ACC, with Claude Code/sonnet, OpenClaw/sonnet, and OpenClaw/gpt all identified as tied leaders. All configuration denominators are 65; no card uses 362 as the ACC denominator.
3. **Known comparison:** For A=Claude Code/sonnet and B=ReAct Agent/sonnet, display ACC delta +46.15 pp, SER delta −80.00 pp, EER delta +6.15 pp, CER delta +27.69 pp. Published values remain unchanged even when chart stacks differ slightly from 100 due to rounding.
4. **Criteria boundaries:** With all configurations, min ACC=60.00 and max SER=0.00 yields five eligible configurations: Claude Code/sonnet, Codex/sonnet, Codex/gpt, OpenClaw/sonnet, OpenClaw/gpt. At min ACC=66.15 and max SER=0.00, exactly the three tied leaders qualify. At min ACC=100.00, none qualify. Disabled criteria do not imply a shortlist.
5. **Independent filtering:** Corpus type=126 gives 110 assertions. Corpus form=10-Q gives 217 assertions after resetting other corpus filters. Neither changes published rates/configuration counts. Framework=ReAct Agent gives four configurations and leaves corpus counts unchanged. Searching an impossible literal yields zero matches without an exception or NaN percentages.
6. **Record identity and evidence:** The first source accession remains `0001477932-22-000209` in the UI and exported text. Distinct details sharing accession and assertion code stay distinct. Detail shows complete text and the original filing metadata; a valid SEC link points to the exact source URL. Date flags do not overwrite dates.
7. **Selection/export state:** Add two distinct assertion records to the investigation list, change filters to hide one, and confirm both remain selected with the scope explained. Export has exactly two unique composite keys and intact full details. Matching-corpus export includes all matches across table pages. Clearing the list changes no source file.
8. **Validation and unavailable evidence:** Exercise missing file, incorrect hash, duplicate configuration key, and out-of-range rate using temporary test fixtures. The affected view reports the specific problem without fabricated fallback values. No cost/latency charts, configuration-specific failed filings, Trading results, or unsupported rule-level accuracy appear.
9. **Execution:** The stated uv launch command starts the app, all three views render with actual sources, scoped reset controls work, percentage axes/units and source labels are visible, and exports round-trip with identifiers read as strings. No raw data or notebook outputs change.
