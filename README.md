# DQC Audit Dashboard: which XBRL audit steps can AI take over? (DSO 576)

- **Live app:** https://dso-576-justvibe-ld8a8lxfww5t8ipaowvfpf.streamlit.app/ (opens without sign-in)
- **Repository:** https://github.com/MarcusHaxdx/DSO-576-JustVibe
- **Team:** Ling Zhong · Man To Ho · Bella Xue · Jinyang Yuan · Lingxiao He

## Intended user and decision

**User:** a trading-technology manager at an asset manager who is deciding how far to trust AI agents with XBRL filing checks.

**Decision:** which kinds of DQC (Data Quality Committee) error cases can be handed to an agent and which must stay with a human reviewer. The manager also decides which cases a human reviews first.

**Scope:** the evaluation uses one agent + model, run 2–3 times; the worst run counts. Choosing between models (accuracy against cost) is out of scope.

**Why not just read the raw file:** each case is a ~2 KB free-text message with the reported and calculated values buried in a sentence. The app turns them into comparable numbers, groups cases by rule type, flags oddities, ranks cases for review, and shows what an agent evaluation on these cases can and cannot prove.

## What the app does

The sidebar filters (rule type, filing year, concept prefix, unit, period kind, flags, company) apply to Ground truth, Case Explorer and Review Queue.

| Tab | Question it answers |
|---|---|
| **Project** | What is the question, where is each stage of the pipeline, and what is the answer so far? |
| **Ground truth** | Which rule types and years have the most cases? How big are the gaps between reported and calculated values (relative gap in %, absolute gap in USD)? How many sign flips? |
| **Case Explorer** | For one case: the original DQC message next to the values extracted from it, the gap, the flags, and a link to the filing on SEC. Is this a clear pattern or does it need human judgment? |
| **Review Queue** | Which cases go to a human first? Turn triage rules on or off and set the large-gap threshold; one point per rule triggered. Download the queue as CSV. |
| **Agent evaluation** | The decision rule (AI / AI + human review / human, based on the lower 95% Wilson bound), the 471 filing × rule tasks, and what a perfect agent could earn with these case counts. |
Every empty selection explains itself. For example, 0 matching cases names the filters that caused it and offers a reset button, and a type-15-only filter explains why there is no gap histogram.

## Run locally

Python 3.12 (numpy 1.26.4 has no wheels for 3.13).

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app/main.py
```

Tests: `.venv/bin/python -m pytest -q`

**Deploy (Streamlit Community Cloud):** New app → this repo, branch, main file `app/main.py`, Advanced settings → Python 3.12. Everything the app reads is in the repo: `data/clean/auditing_clean.csv`, `eval/tasks/`, `output/cleaning_report.txt`.

## Data scope (disclosure)

| Item | Details |
|---|---|
| Source | Hugging Face `TheFinAI/Herculean`, `auditing_env/XBRL/mathematical_reasoning.csv`, dataset commit `52d3ecb`, downloaded 2026-09-30, CC BY 4.0 |
| Used in the app | **all 362 rows** of that file after cleaning (`data/clean/auditing_clean.csv`, 34 columns): 158 filings, 125 companies, rule types 15 / 117 / 126 (116 / 136 / 110 rows), 0 rows dropped |
| Subset note | The dataset card lists 4,959 assertions; the downloaded file has 362. The app covers only these 362. Filings without a case are *assumed* clean. |
| Not used in the app | `output/sample_50.csv` (a 50-row review sample from Module 6) and the raw XBRL filings in `herculean_data/` (git-ignored, needed only to run agents) |

**The three DQC rule types** (one row of the data = one rule that fired on one filing):

| Rule type | What it checks | Example from the data | Cases | Calculated value? |
|---|---|---|---|---|
| **15 · sign check** | A concept that should never be negative (payments, share counts, rates) is reported as negative | ESG Inc. reports `PaymentsToAcquirePropertyPlantAndEquipment` as −1,284 | 116 (USD 84, shares 15, pure 12, bbl 4, USD/bbl 1) | No, so no gap |
| **117 · total vs dimensional breakdown** | A total does not equal the sum of its members along one axis (product, segment, region) | StoneX Group: revenue 255,500,000 vs its two product/service members summing to 142,400,000 | 136 (all USD) | Yes |
| **126 · total vs sum of child components** | A parent concept does not equal the sum of its children in the calculation linkbase | CYTTA Corp.: operating cash flow −1,313,536 vs child components summing to −1,212,736 | 110 (all USD) | Yes |

Only types 117 and 126 have a calculated value, so the 246 gap and sign-flip figures in the app come from them. A **sign flip** (9 cases) means the calculated value equals the reported value with the opposite sign.

Cleaning: `src/cleaning/clean_auditing.py` (and `clean_auditing.py` / `cleaning_auditing.ipynb` from Module 6) parses each DQC message into concept, period, unit, reported value and calculated value. It flags 9 sign flips and 2 periods ending after the filing date, and never edits a value. The counts are in `output/cleaning_report.txt`. Agent evaluation design: `eval/README.md`. Dashboard spec: `BUILD_SPEC.md`.

## Current limitations

- **No agent has been run yet.** The measured verdict grid is empty by design, so no numbers are made up. The "what the design can prove" grid is the most a *perfect* agent could earn. It is a ceiling, not a result.
- Every row is a DQC error (severity ERROR). There are no labelled clean cases, so false alarms are measured on assumed-clean filing × rule pairs. That makes the measured false-alarm rate an upper bound.
- The review queue is rule-based (one point per rule). It is not a model and has not been validated against reviewer decisions.
- Diagnosis (S4) has only 9 labelled causes (sign flips), too few to test. Sign-off (S6) has no label at all and stays human.
- Type 15 (sign check) cases have no calculated value, so they have no gap.
- Only one agent + model is evaluated, so the verdicts apply to that model. They do not say whether a cheaper model would do as well.

## AI assistance

AI tools (Claude and Codex) helped us plan the project and draft the cleaning code, the dashboard and this README. We ran all code on the real data, checked the cleaned values against the original DQC messages, and fixed the errors we found. Codex's separate cleaning script (`clean_codex.py`) was used only to double-check our own cleaning.
