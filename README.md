# DSO 576 Just Vibes: XBRL Audit-Agent Dashboard

Phase 2 deliverables:

1. [`BUILD_SPEC.md`](BUILD_SPEC.md): what the Phase 3 dashboard does and how to build it. Start here.
2. Clean team data: `data/clean/auditing_clean.csv` (362 DQC cases × 34 columns) and `data/clean/published_auditing_results.csv` (20 published framework + model setups). Team reconciliation decisions are in BUILD_SPEC §2c.
3. Analysis backend: `src/analysis/` (loader, filters, metrics, triage, published), tested in `tests/`.

## Reproduce

From the repository root:

```powershell
python -m pip install -r requirements.txt
python src/cleaning/clean_project_data.py   # data/raw -> data/clean + outputs/
python -m pytest                             # 33 tests, incl. the BUILD_SPEC acceptance numbers
```

## Layout

| Path | Contents |
|---|---|
| `data/raw/` | `mathematical_reasoning.csv` (TheFinAI/Herculean `auditing_env/XBRL/`, SHA-256 `fa52ccea…7fdf2`, never modified) and `benchmark_results.csv` (Table 2 Auditing block transcription, checked against arXiv:2605.14355v3 p. 9) |
| `data/clean/` | the two canonical files the dashboard reads |
| `src/cleaning/` | `clean_project_data.py` (Ling's Module 6 pipeline) and `parse_detail.py` (Jinyang's parsing of `assertion.detail`) |
| `src/analysis/` | reusable functions that return DataFrames/dicts; the dashboard calls only these |
| `tests/` | unit tests per layer and `test_real_data.py` (acceptance checks on the real files) |
| `outputs/` | Module 6 evidence: `cleaning_summary.json`, `checklist_evidence.md`, `record_checks.csv`, `ranked_configurations.csv`, the 47-row `cleaned_sample.csv` |
| `cleaning_decision_log.md`, `phase1_findings.md`, `notebooks/` | Module 6 and Phase 1 history |

## Key facts

- The DQC file and the published results are never joined: one row is an assertion occurrence vs a setup evaluated on 65 instances, and no case-level key links them.
- The top published ACC is a three-way tie at 66.15% (43/65; 95% interval 54.0–76.5%): Claude Code + Claude Sonnet 4.6, OpenClaw + Claude Sonnet 4.6, OpenClaw + GPT-5.4. The next two (Codex, 63.08%) overlap, so the top five are not statistically separated.
- Limitations: published aggregates only; no case-level predictions, repeated runs, cost, latency or tool traces.

## Module 6 history

Ling Zhong's individual cleaning was submitted at commit `04c0c81` on branch `Ling_Zhong_part` (https://github.com/MarcusHaxdx/DSO-576-JustVibe/tree/Ling_Zhong_part). Its rules and five predeclared record checks are in `cleaning_decision_log.md`; the file paths there predate the Phase 2 move to `data/raw/` and `data/clean/`.
