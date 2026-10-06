## Goal

A model-risk or financial-technology manager must choose an agent-framework and backbone-model configuration for AI-assisted XBRL auditing. The manager compares accuracy and error patterns across configurations, explores the underlying DQC assertions, and opens relevant SEC filings for further investigation. The output is a configuration comparison and a set of cases for human review.

## Sources

We use the HERCULEAN mathematical_reasoning.csv file and the Auditing results from Table 2 of the official paper. The CSV opened in pandas contains 362 rows and 20 columns, covering 125 entities and 158 SEC reports from 2022–2024. One row represents one DQC assertion occurrence associated with an XBRL filing. Table 2 provides ACC, SER, EER, and CER for 20 configurations formed by five agent frameworks and four backbone models.

## Exploration

The DQC file contains 61 assertion codes and three numeric assertion types, with no missing values. It includes 217 assertion occurrences from 10-Q filings and 145 from 10-K filings. Framework choice materially affects performance: with Claude Sonnet 4.6, ReAct Agent achieves 20.00% ACC and 80.00% SER, while Claude Code and OpenClaw each achieve 66.15% ACC and 0.00% SER.

**What this supports**: We can compare model-framework configurations, visualize their error composition, summarize DQC cases by filing and assertion characteristics, and link users to source filings.

**What is missing**: The public data do not include case-level agent predictions, configuration-level cost, latency, or tool-call traces. Therefore, the initial dashboard cannot identify which specific cases each configuration failed or compare cost and latency. These remain future extensions requiring controlled agent runs.