# Step-level agent evaluation

**Question:** which steps of the XBRL audit job can an agent take over, for each DQC rule type?
**Answer format:** a grid of step × rule type. Each cell says AI, AI + human review, human or too few cases, and cites the score, its 95% interval and n.

## The steps

| Step | What the agent must do | How it is scored |
|---|---|---|
| S1 locate | find the failing fact (concept, period) and not flag anything else | recall on flagged cases, precision of findings, specificity on clean tasks |
| S2+S3 relate and compute | read the reported value; sum the children or members (117, 126) | both values equal the key (relative tolerance 1e-9), given the case was found |
| S4 diagnose | name the cause | only sign flips have a label (9 rows), so this step reports "too few cases" |
| S5 explain | cite the numbers used | every number cited is a fact value in the instance, or the finding's own reported value, calculated value or their difference |
| S6 decide | materiality and sign-off | no ground truth: human by definition |

S2 and S3 are scored together because the key holds the calculated sum but not the list of components.

## Tasks

One task is one filing folder × one rule type: 157 × 3 = 471 tasks. 158 tasks have flagged cases (362 in total). The other 313 are **assumed clean**: the agent should report nothing. False alarms are measured on these.

The prompt describes the rule in plain words and lists the filing files. It never contains the DQC message.

Filings are split by a hash of the folder name: 20% go to **dev**, for trying out prompts, and 80% to **test**, for the reported numbers. A filing is never in both splits.

## Decision rule (fix it before the first test run)

- **AI** if the lower 95% Wilson bound of every gate metric is at least 95%.
- **AI + human review** if it is at least 80%.
- **Human** otherwise.
- **Too few cases** when a gate metric has fewer than 30 cases, unless another metric already fails.
- Run one agent + model 2–3 times; the worst run decides. Comparing models is out of scope.
- Change the thresholds with `--ai`, `--review` and `--min-n`, but only before you look at test results.

**Power limit:** with these defaults, a perfect agent needs at least 73 cases to reach the 95% bar. On the test split, rule 126 has 72 clean tasks, so even a perfect run gets "AI + human review" for S1 there. Either accept that, or decide now to score `--split all` (more cases, but dev tasks then count toward the result) or to use a 90% bar.

## How to run

```bash
python eval/build_tasks.py                      # writes eval/tasks/tasks.jsonl and answer_key.csv
```

Run your agent on each task's `prompt` (the files are under `herculean_data/`). Write one line per task to `eval/runs/<agent>_<model>_<repeat>.jsonl`:

```json
{"task_id": "10k-cyca-20210930__126", "findings": [ ... ], "model": "...", "agent_framework": "...", "cost_usd": 0.12, "latency_s": 40}
```

Then score the runs:

```bash
python eval/score_runs.py eval/runs/*.jsonl --export-agent-runs data/runs/agent_runs.csv
```

This prints the grid and writes `eval/results/{step_metrics,verdicts,cases}.csv`.

`--export-agent-runs` writes per-case rows in the dashboard's runs schema (BUILD_SPEC section 8), so tab 4 can show the same runs. In that export:
- a case the agent did not find is `structural`;
- a wrong reported value is `extraction`;
- a wrong sum is `calculation`.

Only export real runs.

## Dashboard

```bash
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app/main.py
```

The **Agent evaluation** tab shows the tasks, the measured verdicts (once `eval/results/` exists) with every metric's 95% interval, and the best a perfect agent could get with these case counts. The best-case grid is faded and labelled "at most".

## Limitations

- **The clean tasks are assumed clean.** The Hugging Face card lists 4,959 assertions, but our file has 362. If the file is a subset, some "false alarms" are real errors, so precision and specificity are lower bounds.
- **There is no label for causes other than sign flip,** and none for materiality.
- **The S5 check is mechanical.** It shows the cited numbers exist in the filing, not that the reasoning is right.

## Checks

`tests/test_evaluation.py` covers three cases:
- a perfect run built from the key scores 100% on every metric;
- an empty run scores 0 recall and gets "human";
- one wrong sum, one number that is not in the filing and one false alarm are each caught, and the dashboard's `score_runs` agrees with the export.
