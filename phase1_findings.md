# Phase I Findings: Mathematical Reasoning Assertions

## Source and scope

Source: [TheFinAI/Herculean](https://huggingface.co/datasets/TheFinAI/Herculean), file `auditing_env/XBRL/mathematical_reasoning.csv`.

The dataset documentation describes this file as DQC mathematical-consistency ground-truth assertions generated over SEC EDGAR XBRL filings. The local file analyzed here contains 362 rows and 20 columns. It is a set of assertion occurrences linked to SEC filing and entity metadata, not a table of model runs or predictions.

## What one row represents

One row represents one observed DQC assertion occurrence for an XBRL filing. The row contains an assertion code, textual assertion detail, DQC run metadata, and the associated entity and report fields. Repeated report identifiers are expected because one filing can have multiple assertion occurrences.

This interpretation is supported by the actual fields: `assertion.code`, `assertion.detail`, `assertion.run-date`, `assertion.source`, `assertion.type`, `entity.name`, `report.id`, `report.accession`, `report.filing-year`, and the SEC URLs.

## Relevant columns

| Column | Observed pandas dtype | Supported use |
|---|---|---|
| `assertion.code` | `str` | DQC rule identifier; filter, chart, and case grouping |
| `assertion.detail` | `str` | Assertion text for case-level inspection |
| `assertion.run-date` | `str` | DQC run timestamp as stored; timeline/filter candidate |
| `assertion.severity` | `str` | Severity filter; all observed values are `ERROR` |
| `assertion.source` | `str` | Assertion source; all observed values are `DQC` |
| `assertion.type` | `int64` | Numeric assertion-type code; filter/chart without assigning an unverified label |
| `entity.cik` | `int64` | Entity identifier; filter and grouping |
| `entity.name` | `str` | Entity label; filter and distribution chart |
| `report.accession` | `str` | SEC accession identifier; report-level detail and grouping |
| `report.filing-year` | `int64` | Filing-year filter and time distribution |
| `report.id` | `int64` | Report identifier; report-level grouping |
| `report.document-type` | `str` | `10-K`/`10-Q` filter and comparison |
| `report.base-taxonomy` | `str` | US GAAP taxonomy filter and comparison |
| `report.filing-date` | `str` | Filing-date detail and timeline candidate |
| `report.sec-url` | `str` | Link from a case-detail table to the SEC filing index |

## Key pandas findings

- Shape: 362 rows and 20 columns.
- Missing values: 0 in every column.
- Unique values: 61 `assertion.code` values, 3 `assertion.type` values, 1 `assertion.severity` value, 125 `entity.name` values, 158 `report.id` values, and 3 `report.filing-year` values.
- Filing-year counts: 2022 = 121, 2023 = 103, 2024 = 138.
- Assertion-type counts: type 117 = 136, type 15 = 116, type 126 = 110.
- Severity counts: `ERROR` = 362.
- Document-type counts: `10-Q` = 217, `10-K` = 145.
- Base-taxonomy counts: `US GAAP 2022` = 115, `US GAAP 2023` = 99, `US GAAP 2024` = 74, `US GAAP 2021` = 72, `US GAAP 2020` = 2.
- Most frequent assertion codes: `DQC.US.0117.9574` = 136 and `DQC.US.0126.9590` = 110. The next most frequent is `DQC.US.0015.2419` = 7.
- Highest assertion counts by entity: `NORTHROP GRUMMAN CORP /DE/` = 28, `GlobeStar Therapeutics Corp` = 21, and `The Southern Company` = 15.
- The type-by-year table is available in the notebook. Its counts are: type 15: 2022 = 20, 2023 = 53, 2024 = 43; type 117: 34, 41, 61; type 126: 67, 9, 34.
- The severity-by-year table is not analytically varied because every row is `ERROR`.

All exact column names and dtypes are printed by the notebook rather than renamed or inferred beyond pandas' observed types.

## Dashboard support

### Filters

The data supports filters on `assertion.code`, `assertion.type`, `assertion.severity`, `entity.name`, `entity.cik`, `report.filing-year`, `report.document-type`, `report.base-taxonomy`, `report.creation-software`, and `assertion.source`.

### Charts

The data supports count charts for assertions by `assertion.code`, numeric `assertion.type`, `report.filing-year`, `report.document-type`, `report.base-taxonomy`, and `entity.name`. It can also support cross-tabulations such as assertion type by filing year and assertion counts by entity. A severity chart would show only one category in this file.

### Case-detail table

A case-detail table can show `assertion.code`, `assertion.detail`, `assertion.run-date`, `entity.name`, `entity.cik`, `report.accession`, `report.id`, `report.filing-date`, `report.filing-year`, `report.document-type`, `report.base-taxonomy`, `report.sec-url`, and `folder_name`. The SEC URL can provide a filing-level link, while `assertion.detail` provides the main textual detail for the assertion occurrence.

## What the data can and cannot support

### Can support

- Descriptive analysis of DQC assertion occurrences.
- Filtering and grouping by rule code, numeric type code, severity, entity, report, filing year, document type, taxonomy, and other stored metadata.
- Filing-linked case inspection using the assertion detail and SEC/report identifiers.
- Ground-truth context for a later auditing-agent evaluation design.

### Cannot support from this file alone

The CSV contains no model or framework prediction fields, no agent run identifier, no case-level pass/fail result for an agent, no cost, no latency, and no step/tool-call trace. It therefore cannot calculate model accuracy, error rate, cost efficiency, latency, framework comparisons, or agent reliability by itself. The single observed severity value also prevents a meaningful severity comparison in this local extract.

To evaluate agents, a separate run-level table would need at least model/framework identifiers, a stable case or assertion identifier, the agent output, an evaluation decision or pass/fail label, cost, latency, and preferably tool-call/run metadata.