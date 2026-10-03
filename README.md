# DSO 576 Module 6: Project Data Cleaning

## Project question

Based on HERCULEAN's published Auditing results, which agent-framework and backbone-model configurations should a financial-technology manager shortlist when considering overall accuracy and the types of errors they make? The primary comparison is ACC; SER, EER, and CER describe the reported error profile.

## Data sources and row definitions

- `data/mathematical_reasoning.csv` is the original TheFinAI/Herculean `auditing_env/XBRL/mathematical_reasoning.csv` DQC assertion file. The inspected snapshot was accessed 2026-10-01 from [TheFinAI/Herculean](https://huggingface.co/datasets/TheFinAI/Herculean). SHA-256: `fa52ccea5b80ea8ff1b27e5e38b5510caf74a82682858e1cc53641bbd1f7fdf2`. It has 4,959 physical lines but parses to 362 CSV records and 20 columns because quoted assertion details contain embedded line breaks. One record is one assertion occurrence; `report.id` is not a unique row key. This original file is not modified by the pipeline.
- `data/benchmark_results.csv` is the existing 20-row structured transcription of the Auditing block in Table 2. It has no provenance fields, so the values were checked against Table 2 of HERCULEAN, arXiv:2605.14355v3 (2026-05-29), page 9.
- `data/published_auditing_results.csv` is a sourced derivative of those aggregate results. Every row is explicitly labeled as published aggregate results, not a case-level prediction. The paper reports 65 audit instances per configuration.
- `data/cleaned_sample.csv` contains 47 cleaned DQC rows (no more than the assignment's 50-row maximum), with a `source_record_number` provenance field. Five targeted difficult records are included along with evenly spaced records from the full source.

The DQC assertions and the paper's aggregate results are kept separate. They have different row units and there is no verified case-level key connecting the 362 assertions to the paper's 65 audit instances. No join is performed.

## Cleaning rules and evidence

Read [`cleaning_decision_log.md`](cleaning_decision_log.md) before running the transformation. It records the proposed rules, reasons, checks, and five expected record outcomes before the pipeline was applied. The pipeline retains identifiers as strings, preserves assertion-detail newlines, converts only numeric analysis fields, validates date strings without rewriting them, reports missingness and duplicates, and does not impute or drop rows.

Default pandas inference reads `entity.cik`, `report.id`, and `report.sic-code` as `int64`; the cleaning pipeline keeps these identifier/code fields as strings. `assertion.type` and `report.filing-year` remain `int64` analysis fields. All full-file numeric conversion and date parsing checks reported zero failures.

Full-data verification is in `outputs/cleaning_summary.json` and `outputs/checklist_evidence.md`. The five individual record checks, with original values, expected results, actual results, and reasons, are in `outputs/record_checks.csv`. The source had 0 exact duplicate rows, 0 missing values, 0 conversion failures, and 0 date-parse failures. It had 86 repeated `report.id` groups (290 rows in those groups; 204 excess occurrences), all retained. All five record checks passed. The full-file cleaned record count remains 362; the shareable cleaned sample has 47 rows.

The highest published ACC is a three-way tie at 66.15% (43/65): Claude Code + Claude Sonnet 4.6, OpenClaw + Claude Sonnet 4.6, and OpenClaw + GPT-5.4. Their published rates tie at SER 0.00%, EER 6.15%, and CER 27.69%. Codex + GPT-5.4 and Codex + Claude Sonnet 4.6 are next at 63.08% (41/65), with SER 0.00%, EER 6.15%, CER 30.77%. These are candidates for further evaluation, not statistically established winners or evidence of deployment safety.

Codex suggested: “One filing can have multiple assertion occurrences, so do not deduplicate on `report.id`.” Original records 1 and 2 share `report.id` 411725 but have different assertion details. The source has 0 exact full-row duplicate rows, 86 repeated `report.id` groups (290 rows; 204 excess occurrences). Repeated IDs were retained because rows are assertion occurrences. The user reviewed the examples and agreed both should be retained, and checked `362 - 158 = 204` excess occurrences. See the decision log and PDF for the two source-record details.

## Reproduction

From the repository root, with the two original CSVs in `data/`:

```powershell
python -m pip install -r requirements.txt
python clean_project_data.py
```

Expected outputs:

- `data/cleaned_sample.csv`
- `data/published_auditing_results.csv`
- `outputs/cleaning_summary.json`
- `outputs/checklist_evidence.md`
- `outputs/record_checks.csv`
- `outputs/ranked_configurations.csv`
- `outputs/module6_cleaning_draft.pdf`

For the notebook, restart the kernel in `notebooks/phase1_exploration.ipynb` and choose **Run All**. It invokes the same pipeline and reloads these output files.

## Limitations

The HERCULEAN numbers are published aggregate results across 65 auditing instances per configuration. The available files do not provide case-level model outputs, a mapping to the DQC assertions, repeated runs, uncertainty estimates, cost, latency, or agent tool traces. Percentage totals vary from 99.99% to 100.01% due to rounding. Do not interpret these results as a per-case evaluation or deployment recommendation.

## GitHub review metadata

- Active local branch: `Ling_Zhong_part`.
- Existing branch URL: https://github.com/MarcusHaxdx/DSO-576-JustVibe/tree/Ling_Zhong_part
- Assignment commit ID: `04c0c81` (full ID: `04c0c81b15cfe928305772533b6ecb601b0cc391`). This commit contains the staged assignment files; this README records the ID in a follow-up metadata commit.
