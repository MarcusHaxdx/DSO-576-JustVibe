# Project Starting Point

## Team and GitHub

| Team name | GitHub repository |
|---|---|
| Just Vibes | https://github.com/MarcusHaxdx/DSO-576-JustVibe.git |

## Selected project area

5.Financial-Agent Deployment

## Why our team is interested in it

AI agents are increasingly pitched for real financial workflows, but the HERCULEAN benchmark shows large, workflow-dependent gaps in reliability. Especially in the structured-verification tasks (auditing, hedging) that map onto real audit and trade-finance work. Drawing on a team background that includes international-banking and trade-finance/audit work, we're interested in the operational question banks actually face once "agents can technically attempt this" is established: which tasks are safe to hand off, which need a human or a deterministic check, and how you'd defend that line to a regulator.

## Candidate Vision A

A model-risk / finance-operations lead at a bank must decide which of the four HERCULEAN-style financial workflows (trading, hedging, market-insight reporting, XBRL auditing) can run with AI-agent autonomy versus requiring mandatory human or deterministic sign-off, and at what performance/error threshold that boundary should sit. And requires reconciling three incompatible evaluation types (financial-return metrics, subjective rubric scores, and deterministic audit checks) into one cross-workflow risk standard.

## Candidate Vision B

A trading-technology manager at an asset manager must decide which specific agent-framework + backbone-model configuration to deploy for two workflows at opposite ends of the verifiability spectrum which is Auditing (deterministic, checkable against DQC ground-truth assertions) and Trading (outcome-driven, no ground truth). Based primarily on execution reliability, defined per workflow (accuracy against ground truth for Auditing; execution stability and decision consistency across repeated runs for Trading, since no ground truth exists there), with cost and latency tracked as secondary, reported-but-not-optimized factors.

## Side-by-side candidate assessment

| Assessment | Vision A | Vision B |
|---|---|---|
| Evidence found so far | HERCULEAN's Table 2 shows accuracy/error rates are sharply workflow-dependent under identical agents/models. For exmaple, Auditing ranges ~20–66% ACC across configurations while Market Insights rubric scores exceed 9/10 for the same backbones. This result direct support for a per-workflow review-threshold policy. | The same table shows the same backbone (Claude Sonnet 4.6) swings from 20.00% ACC (ReAct Agent) to 66.15% ACC (Claude Code) in Auditing purely from framework choice and this is exactly the evidence a deployment-configuration decision needs. |
| Core-data fit | From strong for outcome metrics (CR/SR/MDD, rubric score, ACC/SER/EER/CER), the paper reports these per workflow already. Weak for the cost/latency/step-level data our schema is supposed to hold: the public dataset ships only the environment (prices, news, filings, XBRL), not agent execution traces. | The paper's footnote repo (github.com/xueqingpeng/trading-analysis) is a useable, working harness, not a placeholder: .claude/skills/ for all five skills, a Claude Agent SDK runner (Docker or native), a proxy that routes to OpenAI/Gemini/Azure so we aren't locked to Claude backbones, and a Python API that returns total_cost_usd and num_errors directly. We can run real tasks against the real environment and get genuine cost and output data without building a harness from scratch. |
| Biggest risk | The paper's own run-level logs (steps, tool calls, cost, latency) aren't public even the GitHub runner repo the dataset card points to is an unfilled placeholder. So the confirmed data access covers environment inputs only, not the granular records our relational schema needs. We'd have to generate an original (smaller) set of runs ourselves. | Smaller than we thought, but not zero: the repo gives real cost and a raw error count for free, but not step-level tool-call logs, latency, or any error classification. Thus, if building that layer is still on us, and is the actual point of our schema. |

## Core data source we confirmed we can access

TheFinAI/Herculean on Hugging Face (https://huggingface.co/datasets/TheFinAI/Herculean). Verified so far: env.duckdb / equivalent Parquet tables for prices (2,656 rows), news (3,888 rows), filings (73 rows) covering 8 mega-cap tickers, 2024-12-01 to 2026-03-31 and auditing_env/ (158 SEC XBRL filings with full linkbases, chunked US-GAAP taxonomy 2021–2024, and a 4,959-row DQC ground-truth CSV).

## Three questions we still need to resolve

1. Do we narrow Vision B down to Auditing only, or keep both Auditing and Trading? Auditing alone gives us clean ground-truth accuracy, a single-shot (not daily-loop) task, and much lower cost/complexity?
2. Which data do we actually pull? Do we pull env.duckdb from the repo's committed copy or download fresh from the official Hugging?
3. What exactly does our reliability metric measurec for trading and aduit or just focus on trading?

## Role-file progress

Use one of these status labels: **Not started**, **In progress**, **Ready for team review**, **Complete**, or **Not applicable**.

| Role file | Owner | Status |
|---|---|---|
| [`objectives.md`](objectives.md) | Man To Ho | In progress |
| [`alternatives.md`](alternatives.md) | Ling Zhong | In progress |
| [`data-fit.md`](data-fit.md) | Jinyang Yuan | In progress |
| [`auxiliary.md`](auxiliary.md) | Jiawei'Bella' Xue | In progress |
| [`technical.md`](technical.md) | Lingxiao He | In progress |


## Team check

- [X] We added our team name and the correct private GitHub repository link.
- [X] We selected the area based first on genuine team interest.
- [X] A and B are distinct candidate Visions within the same area.
- [X] The candidate comparison uses verified evidence rather than unsupported claims.
- [X] At least one data source opened, or we recorded the access blocker.
- [X] We preserved three real questions instead of hiding uncertainty.
- [X] Every active role file has an owner and a current status.
- [X] Every teammate reviewed this provisional starting point.
