# Module 6: cleaning the auditing ground-truth data (DSO 576)

**Student:** Jinyang Yuan
**Branch:** `Jinyang-Yuan`
**Branch URL:** https://github.com/MarcusHaxdx/DSO-576-JustVibe/tree/Jinyang-Yuan
**Commit ID:** [submitted commit]

## Project question

A trading-technology manager must decide which agent and model to trust for XBRL auditing. This assignment cleans the ground-truth file used to score the agents: which DQC assertion types and error patterns can an agent be checked on reliably, and which should go to a human?

## Data source and version

| | |
|---|---|
| Dataset | `TheFinAI/Herculean` on Hugging Face, license CC BY 4.0 |
| File | `auditing_env/XBRL/mathematical_reasoning.csv` (362 rows, 20 columns, 669,724 bytes) |
| Version | dataset commit `52d3ecb`, downloaded 2026-09-30 |
| One row | one DQC (Data Quality Committee) rule that fired on one XBRL filing; the rule's message is in the text column `assertion.detail` |

The data is not committed (`herculean_data/` is git-ignored). To get the file:

- Browser: open the dataset page on Hugging Face, go to *Files and versions*, open `auditing_env/XBRL/`, download `mathematical_reasoning.csv`, and save it as `herculean_data/auditing_env/XBRL/mathematical_reasoning.csv`.
- Or: `python -c "from huggingface_hub import hf_hub_download; hf_hub_download('TheFinAI/Herculean', 'auditing_env/XBRL/mathematical_reasoning.csv', repo_type='dataset', local_dir='herculean_data')"`

The original file is only read. It is never modified.

## How to run

From the project root (the folder that contains `herculean_data/`):

```bash
pip install -r requirements.txt
python clean_auditing.py
```

The notebook gives the same result with the evidence for each checklist item: open `cleaning_auditing.ipynb` from the project root, then **Restart, Run All**. It reads the original CSV and writes `output/auditing_clean.csv`.

Optional second implementation (written by Codex, used only to check mine): `python clean_codex.py` writes `output_codex/`. The last cell of the notebook compares the two outputs and skips itself if `output_codex/` is missing.

## Expected output files

| File | What | In Git |
|---|---|---|
| `output/auditing_clean.csv` | cleaned data, 362 rows, 34 columns (20 original + 14 derived) | no, generated |
| `output/sample_50.csv` | 50 rows with a `sample_reason` column | yes |
| `output/cleaning_report.txt` | counts and checks printed by the script | yes |
| `output_codex/mathematical_reasoning_clean.csv` | Codex version, 31 columns | no, generated |

`sample_50.csv` keeps all 9 sign-flip rows, the 2 rows whose period ends after the filing date, the rows used in the record checks, and a random fill (seed 42) split evenly by `assertion.type`, up to 50 rows. The reason for each row is in `sample_reason`.

## What the script and notebook should print

- 362 rows in, 362 out, 0 dropped. Rows by `assertion.type` (15 / 117 / 126): 116 / 136 / 110, before and after.
- Failed type conversions: 0.
- Periods: 237 ranges, 125 single dates (instants).
- Exact duplicate rows: 0. Repeated `report.id`: 204. Repeats on the short key: 18 (kept, the message text differs). Repeats on the final row key: 0.
- Missing: only type 15 has no `rule_element_id` and no `calculated_value` (116 each, left empty by design). `period_start` is empty for the 125 single dates. Unexpected missing values: 0.
- Flags: `sign_flip` 9, `period_after_filing` 2. No value is changed.
- `sign_flip` rate: 9 of 246 rows that have a calculated value (3.7%).
- Units: USD 330, shares 15, pure 12, bbl 4, USD/bbl 1. All 32 non-USD rows are type 15.
- `entity.name`: 7 rows changed (non-breaking space), 125 names, 125 CIKs, 1 name per CIK.

## Files

| File | Purpose |
|---|---|
| `clean_auditing.py` | the cleaning script (reads the CSV, writes `output/`) |
| `cleaning_auditing.ipynb` | the same cleaning step by step, with the checks for the 14-item checklist |
| `clean_codex.py` | Codex's independent version, kept for the comparison |
| `requirements.txt` | dependencies |

## AI assistance

- Codex wrote `clean_codex.py` from a prompt that listed the rules but no expected numbers. I searched it for destructive steps, ran it, and compared its output with mine column by column (31 shared columns, 29 identical). The 2 differences were checked against the raw message text: `unit` for row 103 (my pattern cut `USD/bbl` to `USD`; fixed) and `period_start` for single-date periods (a design choice, mine kept).
- Claude (claude.ai) helped me plan the cleaning rules and draft clean_auditing.py and cleaning_auditing.ipynb. I ran both on the real file, checked the output against the raw message text, and found and fixed one bug in the unit pattern (USD/bbl).

## Known limitations

- The number at the end of `rule_version` (for example `crk-20211231.htm 4`) is kept as text and not parsed.
- The 9 sign-flip rows are flagged, not checked against the filings.
- The `period_after_filing` explanation (a rate assumption for a later year) is an inference.
- Every row has severity ERROR, so the file has no clean examples to compare against.
- Extraction covers the three message templates seen (types 15, 117, 126). A new template would show up as unexpected missing values.
