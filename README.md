---
license: cc-by-4.0
language:
- en
pretty_name: Herculean
tags:
- finance
- llm-agents
- benchmark
- xbrl
- sec-filings
- trading
size_categories:
- 1K<n<10K
configs:
- config_name: filings
  data_files: data/filings.parquet
- config_name: news
  data_files: data/news.parquet
- config_name: prices
  data_files: data/prices.parquet
---

# Herculean: A Financial Agentic Benchmark

An offline evaluation benchmark for LLM agents performing five financial-analysis
tasks: **trading**, **hedging**, **report generation**, **report evaluation**, and
**XBRL filing auditing**. All tasks run against fully offline data — no live
market or web access — so runs are reproducible and bit-comparable across
models.

This release ships two artifacts:

1. **`env.duckdb`** — a single DuckDB database (and equivalent Parquet files
   under `data/`) containing daily prices, news highlights, and 10-K/10-Q
   filing excerpts for **8 mega-cap US equities**
   (AAPL, ADBE, AMZN, GOOGL, META, MSFT, NVDA, TSLA), covering
   **2024-12-01 → 2026-03-31**. Used by the trading, hedging,
   report-generation, and report-evaluation skills.
2. **`auditing_env/`** — **158 SEC XBRL filings** (10-K and 10-Q, fiscal years
   2021–2023) with full instance documents and calculation/definition/label/
   presentation linkbases, plus chunked **US-GAAP Taxonomy** (2021–2024) and a
   `mathematical_reasoning.csv` ground-truth file containing **4,959
   mathematical-consistency assertions** flagged by the SEC's XBRL US Data
   Quality Committee (DQC) rules. Used by the auditing skill.

Code that consumes this dataset (the five skills, their MCP servers, and the
runner) lives at <https://github.com/xueqing-peng/claude-agent-trading> *(update
to your public repo URL)*.

## Dataset structure

```
.
├── env.duckdb                                     # 27 MB, 3 tables
├── data/
│   ├── filings.parquet                            # 73 rows  — 10-K/10-Q MD&A + risk text
│   ├── news.parquet                               # 3,888 rows — daily news highlights
│   └── prices.parquet                             # 2,656 rows — daily OHLC + adj_close + volume
├── auditing_env/
│   ├── XBRL/
│   │   ├── 10k-<ticker>-<period>/                 # 158 filing folders
│   │   │   ├── <ticker>-<period>.xsd              # taxonomy schema
│   │   │   ├── <ticker>-<period>.htm              # rendered filing
│   │   │   ├── <ticker>-<period>_htm.xml          # XBRL instance document
│   │   │   ├── <ticker>-<period>_cal.xml          # calculation linkbase
│   │   │   ├── <ticker>-<period>_def.xml          # definition linkbase
│   │   │   ├── <ticker>-<period>_lab.xml          # label linkbase
│   │   │   └── <ticker>-<period>_pre.xml          # presentation linkbase
│   │   └── mathematical_reasoning.csv             # 4,959 DQC ground-truth assertions
│   └── US_GAAP_Taxonomy/
│       └── gaap_chunks_{2021,2022,2023,2024}/
│           ├── chunks_core.jsonl                  # ~20k concept chunks per year
│           ├── chunks_relations.jsonl             # ~50k pres/calc/def/ref/enum edges
│           └── meta.json                          # per-year stats and provenance
├── croissant.json                                 # Croissant 1.0 metadata + RAI fields
└── README.md
```

### `env.duckdb` schemas

| table     | rows  | columns |
|-----------|-------|---------|
| `prices`  | 2,656 | `id`, `symbol`, `date`, `open`, `high`, `low`, `close`, `adj_close`, `volume` |
| `news`    | 3,888 | `id`, `symbol`, `date`, `highlights` |
| `filings` |    73 | `id`, `symbol`, `date`, `document_type` (10-K / 10-Q), `mda_content`, `risk_content` |

The `data/*.parquet` files are exact dumps of these three tables (sorted by
`(symbol, date)`, ZSTD-compressed) for users who prefer
`datasets.load_dataset(...)` over installing DuckDB.

## Loading

**With Hugging Face Datasets (Parquet):**

```python
from datasets import load_dataset
prices  = load_dataset("TheFinAI/Herculean", "prices",  split="train")
news    = load_dataset("TheFinAI/Herculean", "news",    split="train")
filings = load_dataset("TheFinAI/Herculean", "filings", split="train")
```

**With DuckDB (single file):**

```python
import duckdb
con = duckdb.connect("env.duckdb", read_only=True)
con.execute("SELECT symbol, date, close FROM prices WHERE symbol='TSLA' ORDER BY date").df()
```

**Auditing data:** stream the JSONL chunks directly, or point the `auditing`
skill's MCP server at the `auditing_env/` root.

## Intended use

- Benchmarking LLM agents on **multi-day, tool-using financial tasks** with
  fixed offline data so results are reproducible across models, providers, and
  reruns.
- **Auditing** XBRL numeric facts: comparing reported values against values
  derived from calculation linkbases and US-GAAP balance/period semantics.
- Studying **agent reasoning quality** (not predictive accuracy of the market).

## Out-of-scope use

- **Not for live trading.** Prices and news are historical and incomplete; the
  data set is engineered for benchmarking, not strategy backtesting.
- **Not a forecast benchmark.** The label of a "good" trading decision in this
  benchmark is reasoning quality and adherence to the skill spec, not realized
  P&L.
- **Not a financial-advice corpus.** Outputs of any agent run on this data
  must not be presented as investment advice.

## Limitations

- **Small symbol universe** (8 US mega-cap tech equities) — sector and
  market-cap bias is severe; results will not generalize to small caps,
  non-US markets, or non-tech sectors.
- **Short window** (~16 months of prices/news) — captures one regime; not
  enough for cross-cycle evaluation.
- **News field** is an LLM-summarized "highlights" string per (symbol, date),
  not raw articles; it inherits any biases of the upstream summarizer.
- **Filing text** is restricted to MD&A and risk-factor sections only; no
  full-document semantics.
- **XBRL filings** sample (158) is biased toward filings flagged by DQC
  rules — useful for auditing benchmarks, not representative of the full
  EDGAR population.

## Biases and risks

- **Survivor / large-cap bias** in the equity panel.
- **English-only**, US-GAAP-only, US-issuer-only.
- **Temporal coverage ends 2026-03-31** — agents must not rely on
  out-of-window information leaks.
- **No PII**: prices, news headlines, public filings, and a public XBRL
  taxonomy. SEC filings name corporate officers as part of the public record;
  no private-individual data is included.

## Source and provenance

- **Prices**: derived from publicly available end-of-day OHLCV feeds.
- **News highlights**: condensed daily digests for each (symbol, date).
- **Filings (text excerpts)**: extracted from public SEC EDGAR 10-K / 10-Q
  filings.
- **XBRL filings (`auditing_env/XBRL/`)**: downloaded directly from SEC
  EDGAR (<https://www.sec.gov/edgar>). SEC content is in the **public
  domain** in the United States.
- **`mathematical_reasoning.csv`**: assertions produced by the
  XBRL US Data Quality Committee (DQC) rule set
  (<https://xbrl.us/data-quality/rules-guidance/>) over the EDGAR corpus.
- **US-GAAP Taxonomy chunks**: derived from the official FASB US-GAAP
  Financial Reporting Taxonomy
  (<https://www.fasb.org/Page/PageContent?PageId=/xbrl/2024gaap.html>),
  which is published by FASB for use without charge.

## Collection and preprocessing

- **Prices/news/filings** ingested into a single DuckDB file and re-exported
  to ZSTD-compressed Parquet, sorted by `(symbol, date)`, no other
  transformations.
- **XBRL filings** are stored byte-identical to their EDGAR-published form;
  the only added artifact is the per-folder layout convention.
- **Taxonomy chunks**: each US-GAAP concept is serialized into a single
  text "chunk" plus a relations file linking concepts via the standard
  XBRL linkbases (presentation, calculation, definition, reference,
  enumeration). See each year's `meta.json` for chunk counts.

## Synthetic data

No generative model was used to fabricate prices, filings, or taxonomy
content. The `news.highlights` field is an LLM-summarized condensation of
publicly reported events; the underlying events are not synthetic but the
phrasing is model-generated and may contain summarization errors.

## Social impact

The benchmark is designed to **measure and improve agent reasoning under
realistic financial-analysis tool use**. Misuses to guard against:
treating model outputs as actual investment recommendations, or training a
trading system on this data and deploying it without out-of-sample,
out-of-distribution validation. Users publishing results are encouraged to
report failure cases alongside aggregate scores.

## License

- **Data**: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) — you
  may share and adapt with attribution.
- **SEC EDGAR XBRL filings** included in `auditing_env/XBRL/` are US Federal
  government public-domain content and not covered by the CC license.
- **US-GAAP Taxonomy** material is published by FASB for use without charge;
  consult <https://www.fasb.org> for the current redistribution terms.

## Citation

```bibtex
@misc{herculean_2026,
  title  = {Herculean: An Offline Multi-Skill Evaluation Benchmark for
            LLM Agents in Finance},
  author = {Peng, Xueqing},
  year   = {2026},
  url    = {https://huggingface.co/datasets/TheFinAI/Herculean}
}
```

## Contact

xueqing.peng2024@gmail.com

## DSO 576 Module 6 submission notes

### Branch and commit metadata

- Branch name: cleaning-bella
- Branch URL: not available in this environment because the repository remote is configured as a Hugging Face dataset repo, not a GitHub branch URL for the course project.
- Commit ID: e847c6387a92d9440b28446815ec6d1efaf7e02f

### Data source and version

- Data source: TheFinAI/Herculean public dataset, loaded from the local Parquet file in `data/filings.parquet`.
- Version used: project snapshot for the current workspace, with 73 filing records and 6 columns: `id`, `symbol`, `date`, `document_type`, `mda_content`, and `risk_content`.

### Run instructions

1. Create or activate a Python environment with `pandas` and `pyarrow` installed.
2. Run the notebook in `herculean_cleaning.ipynb` to inspect and validate the raw filings data.
3. Run the cleaning script:

```bash
python3 cleaning_pipeline.py
```

4. Confirm that the output file is generated in `outputs/filings_clean_sample.csv`.

### Expected output files

- `herculean_cleaning.ipynb` — notebook with inspection, cleaning decision log, and validation evidence.
- `cleaning_pipeline.py` — reproducible cleaning script that converts the `date` field to pandas datetime without changing other columns.
- `outputs/filings_clean_sample.csv` — sample cleaned dataset showing up to 50 rows without the long text columns.
- `requirements.txt` — Python dependencies required to reproduce the notebook and script.

### Submission notes

- This assignment keeps the original `data/filings.parquet` file unchanged.
- The cleaning decision is limited to converting the `date` field to pandas datetime using `errors="coerce"` in a copied DataFrame called `filings_clean`.
- No rows were removed, because the inspection found 0 missing values, 0 exact duplicates, 0 repeated IDs, 0 blank text rows, and 0 suspicious records.
