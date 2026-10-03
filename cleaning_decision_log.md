# Module 6 Cleaning Decision Log

## Scope and sequence

This log records the proposed rules before the cleaning pipeline is run. The primary analysis source for the project question is the published Auditing aggregate table in HERCULEAN Table 2, not the DQC assertion CSV. The DQC file is retained as a separate source for cleaning checks and context. The two sources will not be joined.

The local DQC source is `data/mathematical_reasoning.csv`, from TheFinAI/Herculean, `auditing_env/XBRL/mathematical_reasoning.csv`. Initial inspection used Python's CSV parser and found 4,959 physical lines, 362 parsed records, and 20 fields. Its rows are DQC assertion occurrences, not agent predictions. The existing `data/benchmark_results.csv` is a structured 20-row transcription of the paper's Auditing table, but it has no source/version fields; its values will be checked against Table 2 (paper page 9) and copied to a clearly sourced, separate table.

## Proposed rules, reasons, and checks

| Rule | Reason | Check before accepting output |
|---|---|---|
| Read the DQC file with a CSV parser that supports quoted embedded newlines; use `keep_default_na=False`. | Physical lines are not records, and assertion details contain meaningful multi-line text. | Assert 362 records, 20 columns, 4,959 physical lines, and compare each parsed source record with its cleaned output record. |
| Keep `entity.cik`, `report.accession`, `report.id`, and `report.sic-code` as strings; do not pad, numerically recast, or otherwise normalize identifiers. | These fields identify entities/reports or encode a code; lexical formatting, including leading zeroes, is significant. | Check leading-zero accession values and exact string equality for five predeclared records. |
| Convert only `assertion.type` and `report.filing-year` to numeric analysis types; parse the three date/timestamp fields for validation only and preserve their source text. | These columns have numeric/date meaning; conversion should not silently alter displayed source values. | Count conversion/parse failures on the full file and require zero failures before emitting the sample. |
| Trim surrounding whitespace only from categorical metadata fields, never from `assertion.detail`, identifiers, URLs, or source date strings. | Metadata whitespace can interfere with grouping; detail formatting and identifiers must remain intact. | Count values changed by trimming and compare every protected field with the source. |
| Do not drop repeated `report.id` values. Drop exact duplicate rows only if full-row comparison finds any, after reviewing their meaning. | A report may contain multiple assertion occurrences; `report.id` is not a row key. | Report exact duplicate count separately from repeated-ID group/extra-record counts; retain every assertion occurrence. |
| Do not impute or drop missing values. | Missingness should be reported, not hidden; no business rule for filling these source fields has been established. | Report missing counts for every column before and after; require no unplanned row/column changes. |
| Flag unusual/suspicious values for review; do not automatically correct negative amounts or DQC assertions. | A DQC assertion describes a reported issue; a surprising value is not by itself proof of a transcription error. | Validate date parsing, filing year/date consistency, category domains, and report suspicious detail examples without rewriting them. |
| Keep the DQC assertions and published benchmark aggregates separate; perform no merge. | There is no verified case-level key connecting these 362 assertion occurrences to HERCULEAN's 65 evaluation instances or its per-configuration outcomes. | Assert source tables retain distinct schemas and document merge as not applicable. |
| Preserve all 362 parsed DQC records in memory; export at most 50 deterministic cleaned sample records, including the five planned checks. | The assignment requests a shareable sample, while all checks must cover the full selected source. | Report starting/final full-record counts and exported sample count; sample must be no larger than 50. |
| Treat each published rate as a percentage over the paper's 65 audit instances; derive counts only as a validation aid. | The published table is aggregate output, not case-level predictions. | Check all four percentages are in range, sum to 100% per configuration, and round back from integer counts over 65. |

## Five record checks: expected results declared before transformation

The row numbers below are 1-based CSV data-record numbers (header excluded). The expected result is preservation, not an inferred correction. The pipeline will compare these expectations against the emitted sample only after the rules above have been applied.

| Source record | Original value observed | Expected result | Reason |
|---:|---|---|---|
| 1 | `report.accession` = `0001477932-22-000209` | Preserve the exact string, including leading zeroes. | SEC accession is an identifier, not a number. |
| 1 | `assertion.detail` is 3,467 characters with 27 embedded line breaks; begins `2022-03-09 20:00:03,338 [DQC.US.0126.9590]` | Preserve the complete parsed cell exactly, including line breaks. | Quoted newlines are part of the detail, not extra CSV records or disposable whitespace. |
| 2 | `report.id` = `411725`; `report.accession` = `0001477932-22-000209` | Keep this record even though its `report.id` repeats; preserve the ID as text. | Multiple assertion occurrences may belong to one report; the row is not uniquely identified by `report.id`. |
| 3 | `assertion.type` = `126` (source text) | Convert to integer `126` for analysis; the exported sample contains the same lexical value `126`. | This field is a numeric DQC rule code, unlike identifiers that must remain text. |
| 181 | `assertion.detail` begins `2023-01-06 10:30:33,684 [DQC.US.0015.6070] us-gaap:OtherReceivables has a value of -4,200,000 which is less than zero.` | Preserve the reported negative value and detail verbatim; flag for inspection, do not “fix” it. | It is an assertion describing a potentially suspicious source fact, not evidence that the CSV value is corrupt. |
| 362 | `report.accession` = `0001493152-24-033153`; `assertion.code` = `DQC.US.0015.2923`; `report.filing-year` = `2024` | Preserve the identifier, rule code, and year exactly. | Checks a later-year record and another leading-zero SEC accession. |

## Codex suggestion and verification status

Codex suggestion: “One filing can have multiple assertion occurrences, so do not deduplicate on `report.id`.”

Two examples from the original CSV are shown for user review:

| Source record | `report.id` | `report.accession` | Assertion information |
|---:|---|---|---|
| 1 | `411725` | `0001477932-22-000209` | `DQC.US.0126.9590`, type `126`; detail begins `2022-03-09 20:00:03,338` and describes the `NetCashProvidedByUsedInOperatingActivities` calculation. |
| 2 | `411725` | `0001477932-22-000209` | `DQC.US.0126.9590`, type `126`; detail begins `2022-03-09 20:00:03,339` and describes the `NetCashProvidedByUsedInFinancingActivities` calculation. |

The two `assertion.detail` values differ. The original file has 0 exact full-row duplicate rows, 86 repeated `report.id` groups, 290 rows in those groups, and 204 excess occurrences beyond one row per ID. Rows were retained because each row represents an assertion occurrence, while `report.id` identifies the filing. The user reviewed the two examples, agreed both should be retained, and checked that 362 source records minus 158 distinct `report.id` values equals 204 excess occurrences. This records the user's check of the Codex suggestion.

## Results

The pipeline was run against the full local source on 2026-10-01. It uses pandas' quoted-field CSV parser with all source fields initially read as strings. The source CSV's SHA-256 was unchanged before and after the run: `fa52ccea5b80ea8ff1b27e5e38b5510caf74a82682858e1cc53641bbd1f7fdf2`.

| Check | Observed result | Decision/output |
|---|---:|---|
| Physical text lines / parsed DQC records / fields | 4,959 / 362 / 20 | Embedded newlines in quoted descriptions are preserved; no line-based parsing. |
| Full-file records before / after cleaning | 362 / 362 | No records removed. |
| Exact duplicate rows | 0 | Nothing to deduplicate. |
| `report.id` repeated groups / records in those groups / excess occurrences | 86 / 290 / 204 | All retained; `report.id` is not the assertion-row key. |
| Missing or blank values before / after | 0 / 0 across all 20 columns | No imputation or missing-row deletion. |
| `assertion.type`, `report.filing-year` conversion failures | 0, 0 | Numeric validation succeeded; source text is retained except analysis types in memory. |
| Default-inferred integer fields and cleaned types | `entity.cik`, `report.id`, and `report.sic-code`: `int64` -> string; `assertion.type` and `report.filing-year`: remain `int64` | The first three values are identifiers/codes, not quantities. Full maps are in `outputs/cleaning_summary.json`. |
| Date parse failures (`assertion.run-date`, `report.accepted-timestamp`, `report.filing-date`) | 0, 0, 0 | Source date strings retained. |
| Surrounding-whitespace changes / filing-year-date mismatches | 0 / 0 | No text normalization changed values; no date/year mismatch. |
| Invalid document types / non-DQC source values | 0 / 0 | All checked category values passed. |
| Negative-value detail pattern | 103 records | Retained and flagged as assertion content, not automatically corrected. |
| Cleaned sample | 47 rows | Five targeted records plus 45 evenly spaced source positions; overlap leaves 47 unique rows. |
| Five distinct predeclared source records (six field checks) | 6/6 passed | Original, expected, actual, and reason are in `outputs/record_checks.csv`. |

The existing `data/benchmark_results.csv` has 20 unique framework/model combinations and matched the Auditing block of Table 2 (paper page 9). The sourced derivative labels all rows as published aggregate results. The paper reports 65 audit instances per configuration. Integer counts derived from the percentages reproduce every published metric to two decimal places; the four rounded rates sum to 99.99%-100.01% per configuration, a rounding tolerance of 0.01 percentage point.

The highest ACC is a three-way tie at 66.15% (43/65): Claude Code + Claude Sonnet 4.6, OpenClaw + Claude Sonnet 4.6, and OpenClaw + GPT-5.4. Each reports SER 0.00% (0/65), EER 6.15% (4/65), and CER 27.69% (18/65). Codex + GPT-5.4 and Codex + Claude Sonnet 4.6 follow at 63.08% (41/65), SER 0.00%, EER 6.15%, CER 30.77%. These are shortlist candidates for further testing, not evidence of statistical significance or deployment readiness.

No merge was performed. The two sources have different units of observation and no verified case-level key between the 362 DQC assertions and the 65 paper evaluation instances. The paper does not provide individual predictions, run traces, repeated-run uncertainty, cost, or latency.

Reproduction: `python -m pip install -r requirements.txt`, then `python clean_project_data.py`. The original DQC CSV remains unchanged. The five expectations above were written before the pipeline was run.
