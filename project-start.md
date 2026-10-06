# Project Starting Point

## Selected project area

Financial-Agent Deployment

## Why our team is interested in it

AI agents are increasingly pitched for real financial workflows, but the HERCULEAN benchmark shows large, workflow-dependent gaps in reliability. Especially in the structured-verification tasks (auditing, hedging) that map onto real audit and trade-finance work. Drawing on a team background that includes international-banking and trade-finance/audit work, we're interested in the operational question banks actually face once "agents can technically attempt this" is established: which tasks are safe to hand off, which need a human or a deterministic check, and how you'd defend that line to a regulator.

## Project Vision

A trading-technology manager at an asset manager must decide which specific agent-framework + backbone-model configuration to deploy for two workflows at opposite ends of the verifiability spectrum which is Auditing (deterministic, checkable against DQC ground-truth assertions) and Trading (outcome-driven, no ground truth). Based primarily on execution reliability, defined per workflow (accuracy against ground truth for Auditing; execution stability and decision consistency across repeated runs for Trading, since no ground truth exists there), with cost and latency tracked as secondary, reported-but-not-optimized factors.

## Core data source we confirmed we can access

TheFinAI/Herculean on Hugging Face (https://huggingface.co/datasets/TheFinAI/Herculean). Verified so far: env.duckdb / equivalent Parquet tables for prices (2,656 rows), news (3,888 rows), filings (73 rows) covering 8 mega-cap tickers, 2024-12-01 to 2026-03-31 and auditing_env/ (158 SEC XBRL filings with full linkbases, chunked US-GAAP taxonomy 2021–2024, and a 4,959-row DQC ground-truth CSV).

## Instructor suggestion

I like the vision because it gives you a concrete comparison across agent/model configurations. Auditing is especially useful because you have clear ground truth, but you can include Trading as an additional comparison if it remains manageable.

The main priority should be to build a useful decision dashboard backed by meaningful pandas analysis. For example:

compare model/framework performance across tasks;
show accuracy/reliability, cost, latency, and errors;
visualize a cost–performance tradeoff;
let the user filter by workflow/model/framework;
drill into failed cases or DQC assertion types;
optionally show which cases might deserve review.
