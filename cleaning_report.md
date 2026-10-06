# Cleaning report — Herculean auditing data

The source is the [Herculean auditing assertion CSV](https://huggingface.co/datasets/TheFinAI/Herculean/blob/52d3ecb97e490a2392717935402cde283e8fa36e/auditing_env/XBRL/mathematical_reasoning.csv). The original download is [data/raw/mathematical_reasoning.csv](data/raw/mathematical_reasoning.csv); all inspection and cleaning logic is in [01-cleaning.ipynb](src/notebook/01-cleaning.ipynb). The notebook is intentionally saved without executed outputs under the workspace rule. Counts below were checked independently against the downloaded CSV.

## 1. State the project vision and question

**Status: Done.** The [project vision](project-start.md) asks which agent-framework and backbone-model configuration a manager should use for financial workflows. For the auditing portion, the business question is: which configuration has the highest audit accuracy, and how do structural, extraction, and calculation error rates differ? The main comparison is ACC across the 20 framework–model configurations in [Table 2 of the paper](https://arxiv.org/html/2605.14355v3). Cost and latency are unavailable by configuration.

## 2. Define one row

**Status: Done.** One CSV row is one DQC assertion occurrence tied to an SEC filing. `(report.accession, assertion.code, assertion.detail)` uniquely identifies all 362 rows in this release. `report.id` and `report.accession` each identify 158 filings and repeat across assertion rows. The paper table has a different grain: one row per framework–model configuration. See the grain and duplicate sections of the [notebook](src/notebook/01-cleaning.ipynb).

## 3. Preserve the source

**Status: Done.** The CSV was downloaded on 2026-10-05 from the [Hugging Face dataset](https://huggingface.co/datasets/TheFinAI/Herculean) at revision `52d3ecb97e490a2392717935402cde283e8fa36e`. Its SHA-256 is `fa52ccea5b80ea8ff1b27e5e38b5510caf74a82682858e1cc53641bbd1f7fdf2`. The original file remains unchanged in `data/raw`. Load it with `pd.read_csv("data/raw/mathematical_reasoning.csv", dtype="string", keep_default_na=False)` so identifiers remain text. The notebook verifies the hash before loading. The configuration rates were transcribed separately from [paper Table 2](https://arxiv.org/html/2605.14355v3) into the notebook; the paper does not provide case-level results in this CSV.

## 4. Inspect columns and types

**Status: Done.** The CSV has 362 rows and 20 columns. All fields are read as strings first. `assertion.run-date` and `report.filing-date` become dates; `report.accepted-timestamp` becomes a timestamp; `report.filing-year` becomes nullable integer. There were **0 failed nonblank conversions** in each of these four fields. CIK, SIC, accession, report ID, and assertion type remain strings because they are identifiers or categories. See the type and failure tables in the [notebook](src/notebook/01-cleaning.ipynb).

## 5. Standardize text

**Status: Done.** All 16 text fields had **0 values changed** by surrounding-whitespace removal. The notebook displays before and after examples; for example `CYTTA CORP.` stays `CYTTA CORP.`, and `DQC.US.0126.9590` stays the same. No text was rewritten. Legal names, punctuation, internal whitespace in assertion details, and leading zeros in accessions are meaningful and preserved.

## 6. Investigate duplicates

**Status: Done.** Exact duplicate rows: **0**. Duplicate composite row keys: **0**. Repeated `report.id` values account for **204 extra rows** beyond 158 unique filings; repeated `(report.accession, assertion.code)` pairs account for **174 extra rows**, because one rule can produce several distinct assertion details in a filing. All 362 rows are kept. See the duplicate table in the [notebook](src/notebook/01-cleaning.ipynb).

## 7. Handle missing data

**Status: Done.** Every source column has **0 blank or whitespace-only values before cleaning**; every cleaned column has **0 missing values after conversion**. No values were filled and no rows were dropped. The per-column before/after table is in the [notebook](src/notebook/01-cleaning.ipynb).

## 8. Check suspicious values

**Status: Done.** Invalid dates, filing-year mismatches, assertion runs before filing, malformed accessions or CIKs, and unexpected form types: **0** each. **43 assertion rows** have acceptance and official filing dates on different calendar days. These dates are retained and flagged because the dates represent different SEC events. One `folder_name` maps to two accessions, so folder name is not used as a filing key. See the flag counts and examples in the [notebook](src/notebook/01-cleaning.ipynb).

## 9. Verify merges

**Status: Not applicable.** No tables were merged. The 20-row paper summary is kept at configuration grain and is not joined to the 362 assertion rows because no case-level prediction key is available. The [notebook](src/notebook/01-cleaning.ipynb) keeps the two views separate.

## 10. Reconcile changes

**Status: Done.** Starting assertion rows: **362**. Removed or added: **0**. Final assertion rows: **362**. Unique filings stay at **158**. The form totals remain **145 10-K** and **217 10-Q** assertion rows. Assertion types remain **110 type 126**, **136 type 117**, and **116 type 15** rows. The reconciliation table is in the [notebook](src/notebook/01-cleaning.ipynb).

## 11. Check calculations

**Status: Done.** Assertion counts use 362 nonmissing rows; filing counts deduplicate 158 nonmissing accessions. Form and assertion-type groups have no missing keys, so no unknown group is introduced. If a later source has missing counts, totals should include only observed values and each average must report its nonmissing denominator; missing group keys should be shown as an explicit unknown group with `dropna=False`. Paper Table 2's ACC/SER/EER/CER are reported percentages over **65 audit instances per configuration**, not estimates from these 362 assertions. The notebook checks that the four published rates sum to 100% within rounding for each of 20 configurations. See [01-cleaning.ipynb](src/notebook/01-cleaning.ipynb).

## 12. Verify individual records

**Status: Done.** The five expected results and reasons are declared before the comparison cell in the [notebook](src/notebook/01-cleaning.ipynb). Independent source checks found:

| Source data row | Original field/value | Expected and reason | Actual cleaned result | Match |
|---|---|---|---|---|
| 1 | accession `0001477932-22-000209` | Same; preserve leading zeros | `0001477932-22-000209` | Yes |
| 3 | filing date `2022-01-24` | Same; retain official date despite earlier acceptance | `2022-01-24` | Yes |
| 5 | document type `10-Q` | Same; retain quarterly category | `10-Q` | Yes |
| 71 | assertion code `DQC.US.0117.9574` | Same; repeated accession and rule has distinct detail | `DQC.US.0117.9574` | Yes |
| 102 | assertion type `15` | Same; keep numeric-looking category as text | `15` | Yes |

## 13. Test reproducibility

**Status: Unresolved.** The source hash, CSV counts, notebook JSON, and code syntax were checked independently, but the notebook cells were **not run**, as required by `AGENTS.md`. From the project root, run `uv run --no-project --with pandas --with jupyterlab jupyter lab src/notebook/01-cleaning.ipynb`, then choose **Restart Kernel and Run All Cells**. The notebook's assertions check the source hash, shape, conversion failures, duplicate keys, missing values, selected records, and paper-rate reconciliation. Until it is run, rendered notebook outputs cannot be confirmed against this report.

## 14. Document remaining limitations

**Status: Done.** The public CSV does not include individual agent predictions, configuration-level cost, latency, or tool traces. The 362 assertion occurrences cannot be mapped to the paper's 65 audit instances per configuration, so configuration errors cannot be assigned to specific filings. This limits conclusions to aggregate framework–model comparisons and DQC case exploration. Resolving it requires case-level evaluation outputs and run metadata from the benchmark authors or new controlled runs. The 43 acceptance/filing date differences are preserved; filing-level confirmation would require checking the corresponding SEC records.
