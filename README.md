# Module 6 Data Cleaning Assignment

## Project
**Team:** Just Vibes  
**Project:** Financial Agent Deployment  
**Student branch:** `Raymond-branch`

## Project Vision
Build a reliable cleaned stock-price dataset for the Financial Agent project.

**Business question:** How do stock prices and trading activity differ across stock symbols and over time?

**Main metrics:** adjusted closing price, price change, and trading volume.

## Data Source
- Source: TheFinAI/Herculean — `prices` subset
- Original file: `Data/prices.parquet`
- Download date: October 5, 2026
- One row represents one stock symbol on one trading date.
- Unique row key: `symbol` + `date`
- The original file is preserved and is not overwritten.

## Cleaning Workflow
The notebook `module6_cleaning.ipynb` performs the following steps:

1. Load the original `Data/prices.parquet`.
2. Trim whitespace from `symbol`.
3. Convert `date` to pandas datetime format.
4. Convert `open`, `high`, `low`, `close`, `adj_close`, and `volume` to numeric types.
5. Check and handle missing required values.
6. Check and remove exact duplicate rows.
7. Check repeated IDs and repeated `symbol` + `date` keys.
8. Validate suspicious values, including invalid OHLC relationships and negative volume.
9. Sort the cleaned data by `symbol` and `date`.
10. Validate the final dataset and save the cleaned output.

## Validation Summary
- Final cleaned rows: 2,656
- Missing values after cleaning: 0
- Exact duplicate rows after cleaning: 0
- Invalid OHLC/volume rows after cleaning: 0
- No table merge was performed for this individual cleaning task.
- Five individual records were checked by comparing original, expected, and actual cleaned values.

## Cleaning Decision Log

| Rule | Reason | Check |
|---|---|---|
| Trim whitespace from `symbol` | Prevent inconsistent ticker labels | Compare symbol values before and after cleaning |
| Convert `date` to datetime | Support reliable time-series analysis | Count failed date conversions |
| Convert numeric columns | Ensure calculations use numeric values | Count failed numeric conversions |
| Handle missing required values | Prevent incomplete records from affecting analysis | Compare missing counts before and after cleaning |
| Remove exact duplicates | Prevent double counting | Count duplicate rows before and after cleaning |
| Validate OHLC and volume | Remove records that violate basic data integrity rules | Count invalid OHLC/volume rows |
| Sort by `symbol` and `date` | Keep a consistent time-series order | Inspect sorted output |
| Preserve original data | Keep the raw source reproducible | Save cleaned output to a separate file |

## Codex / AI Suggestion Check
One suggestion was to convert the `date` column using:

```python
pd.to_datetime(prices["date"], errors="coerce")
```

I checked this suggestion by counting failed conversions after applying it. The conversion was kept only after verifying that it did not introduce invalid dates.

## Reproducibility

### Dependencies
- Python 3
- pandas
- pyarrow

Install the required packages if necessary:

```bash
python3 -m pip install pandas pyarrow
```

### Run Instructions
1. Make sure `Data/prices.parquet` is in the repository.
2. Open `module6_cleaning.ipynb`.
3. Select the Python kernel.
4. Restart the kernel.
5. Run all cells from top to bottom.

The notebook should recreate:

```text
Data/prices_cleaned.parquet
```

## Expected Output Files
- `Data/prices_cleaned.parquet` — cleaned price dataset
- `module6_cleaning.ipynb` — cleaning and validation notebook

## Limitations
This cleaning work uses only the `prices` subset of the Herculean dataset. The values were not independently validated against an external market-data provider. Unusual values were reviewed but were not automatically removed unless they violated the defined integrity rules.

## GitHub Submission Information
- **Branch name:** `Raymond-branch`
- **Branch URL:** https://github.com/MarcusHaxdx/DSO-576-JustVibe/tree/Raymond-branch
- **Cleaning code commit ID:** `2617ad7`

Repository: https://github.com/MarcusHaxdx/DSO-576-JustVibe
