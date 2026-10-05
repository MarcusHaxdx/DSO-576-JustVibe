from pathlib import Path

import pandas as pd

DATA_PATH = Path("data/filings.parquet")
OUTPUT_SAMPLE_PATH = Path("outputs/filings_clean_sample.csv")


def load_filings(path: str | Path = DATA_PATH) -> pd.DataFrame:
    """Load the original filings parquet file into a DataFrame."""
    return pd.read_parquet(path)


def build_cleaned_filings(filings: pd.DataFrame) -> pd.DataFrame:
    """Create a cleaned copy with only the date field converted to datetime."""
    filings_clean = filings.copy()
    filings_clean["date"] = pd.to_datetime(filings_clean["date"], errors="coerce")
    return filings_clean


def create_cleaned_sample(filings_clean: pd.DataFrame, sample_size: int = 50) -> pd.DataFrame:
    """Create a sample of cleaned records without long text columns."""
    checked_ids = [1, 2, 3, 4, 5]
    other_ids = filings_clean.loc[~filings_clean["id"].isin(checked_ids), "id"].tolist()
    selected_ids = checked_ids + other_ids[: max(sample_size - len(checked_ids), 0)]
    sample = filings_clean[filings_clean["id"].isin(selected_ids)][["id", "symbol", "date", "document_type"]].copy()
    return sample


def main() -> None:
    filings = load_filings()
    filings_clean = build_cleaned_filings(filings)
    sample = create_cleaned_sample(filings_clean)

    OUTPUT_SAMPLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    sample.to_csv(OUTPUT_SAMPLE_PATH, index=False)

    print("Original rows:", len(filings))
    print("Cleaned rows:", len(filings_clean))
    print("Missing values:", int(filings_clean.isna().sum().sum()))
    print("Duplicate rows:", int(filings_clean.duplicated().sum()))
    print("Failed date conversions:", int(filings_clean["date"].isna().sum()))
    print("Unique IDs:", filings_clean["id"].is_unique)
    print("Sample saved to:", OUTPUT_SAMPLE_PATH)


if __name__ == "__main__":
    main()
