# DSO 576 Module 6 Cleaning Assignment Summary

## Branch and repository metadata

- Branch name: cleaning-bella
- Branch URL: not available in this environment because the repository remote is configured as a Hugging Face dataset repo rather than a GitHub project branch.
- Commit ID: e847c6387a92d9440b28446815ec6d1efaf7e02f

## Data source and version

- Data source: TheFinAI/Herculean dataset.
- Local file used: data/filings.parquet
- Version: current workspace snapshot, 73 rows x 6 columns.

## Cleaning decision log

| rule | reason | check |
| --- | --- | --- |
| Convert date to datetime with errors="coerce" | The date field was stored as object/string even though it represents dates and is needed for time-based analysis. | pd.to_datetime(filings['date'], errors='coerce') |
| Keep all rows | No row-level problems were found during inspection. | len(filings_clean) == len(filings) |
| Do not remove missing values | Missing values were 0 in every column. | filings.isna().sum().sum() == 0 |
| Do not remove duplicates | Exact duplicate rows were 0 and IDs were unique. | filings.duplicated().sum() == 0 and filings['id'].is_unique |
| Do not normalize text fields | Whitespace, mixed-case, blank text checks were all 0. | symbol/document_type whitespace and case checks were 0; mda_content and risk_content blank counts were 0 |

## 14-item checklist evidence

1. One row represents one filing record.
2. `id` uniquely identifies each row: `True`.
3. Rows: 73.
4. Unique IDs: 73.
5. Repeated ID rows: 0.
6. Before cleaning, missing values in every column: 0.
7. Exact duplicate rows: 0.
8. `document_type` values: 10-Q = 51, 10-K = 22.
9. Unique company symbols: 8.
10. Whitespace in `symbol`: 0.
11. Mixed-case `symbol` values: 0.
12. Whitespace in `document_type`: 0.
13. Blank `mda_content` rows: 0.
14. Blank `risk_content` rows: 0.

## Five record checks

These records were checked to confirm the expected date conversion result matched the actual cleaned values.

| id | original date | expected cleaned date | actual cleaned date | expected equals actual |
| --- | --- | --- | --- | --- |
| 1 | 2024-02-01 | 2024-02-01 | 2024-02-01 | True |
| 2 | 2024-05-02 | 2024-05-02 | 2024-05-02 | True |
| 3 | 2024-08-01 | 2024-08-01 | 2024-08-01 | True |
| 4 | 2024-11-01 | 2024-11-01 | 2024-11-01 | True |
| 5 | 2025-01-31 | 2025-01-31 | 2025-01-31 | True |

## Validation summary

- Starting rows: 73
- Final rows: 73
- Missing values after cleaning: 0
- Duplicate rows after cleaning: 0
- Failed date conversions: 0
- IDs remain unique: True
- Minimum date: 2024-01-16
- Maximum date: 2026-03-25

## How the cleaning decision was checked

I checked the date conversion by comparing the original string dates with the temporary datetime conversion using `pd.to_datetime(..., errors='coerce')` and confirming the number of failed conversions was 0. I also checked that no rows were lost and that no other columns changed between the original and cleaned DataFrames.

## Files included in the repository

- README.md
- herculean_cleaning.ipynb
- cleaning_pipeline.py
- requirements.txt
- outputs/filings_clean_sample.csv
