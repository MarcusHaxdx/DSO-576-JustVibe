## Project Objective

A financial institution's model-risk or finance-operations team must decide which financial tasks can be delegated to AI agents and which require human or deterministic review. Your team will use Herculean as an experimental environment, run several model and create a new relational dataset of tasks, runs, steps, tool calls, cost, latency, outputs, scores, and manually classified errors. Your results will support model routing, review thresholds, early stopping, and cost-reliability comparisons.

## Phase 1. Cleaning

Please refer to the [Data Cleaning Report](cleaning_report.md).

## Phase 2. Analysis

| File          | Description |
|---------------|-------------|
| [BUILD_SPEC.md](BUILD_SPEC.md) | Approved build prompt for the Streamlit dashboard: use cases, views, metrics, interactions, architecture, build order, and acceptance checks. |
| [analysis.py](src/project/analysis.py) | Reusable pandas analysis: validated source loading, configuration rankings/comparisons and threshold shortlists, independent DQC filters and summaries, record selection, CSV exports, and provenance reconciliation. Published rates are included from the documented transcription; no notebook execution or dashboard UI is required. |
