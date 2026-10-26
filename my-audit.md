# My Module 9 audit

## Context

- Name: Ling Zhong
- Team app and version or commit checked: DSO 576 Just Vibes, XBRL Audit-Agent Dashboard, commit `45939a9` on branch `Ling_Zhong_part`. The Phase 3 Streamlit app (`app/main.py`) has not been built yet, so I audited the committed Phase 2 analysis backend that BUILD_SPEC says the app must use for every number on the Configuration Shortlist page (`src/analysis/published.py`), against the team's one-shot prompt `BUILD_SPEC.md`.
- Intended user and decision: a finance-operations / audit-technology manager deciding which 2–3 agent framework + model setups to shortlist for an XBRL auditing pilot (BUILD_SPEC §1, decision 1; use case UC1).

## 1. Feature audit

- Feature and intended behavior: Configuration Shortlist (BUILD_SPEC §3 UC1, §4 page 1). The user sets min ACC, max SER, frameworks and models; the page shows a KPI row, the 20 published setups ranked by ACC with 95% intervals, and a marker on setups whose interval overlaps the leader's, with the note "Marked setups' intervals overlap the leader's, so they are not statistically separated". The README and BUILD_SPEC §1 tell the user that "the top five are statistically tied".
- Inputs and steps to reproduce: from the repo root, `python checks/audit_m6_wilson.py` (Part C calls `rank_configs`, `shortlist` and `shortlist_kpis` with the default controls, with max SER = 0, with max SER = 0 + min ACC = 60, and with frameworks = Hermes only). Data: `data/clean/published_auditing_results.csv`.
- Expected behavior: BUILD_SPEC §9 items 2–3 (three-way tie at 66.15% with rank 1, next two at rank 4; 10 then 5 setups after the filters), ranks stay global when filtering, and the marker should help the manager tell which setups are really as good as the best one.
- Actual behavior and evidence:
  - Works: ranks are competition ranks (1, 1, 1, 4, 4); max SER = 0 leaves 10 setups and adding min ACC = 60 leaves 5; the default KPI row is 20 setups, best 66.15% (43/65), 3 tied; filtering to Hermes keeps global ranks (13, 13, 13, 18).
  - Misleading: the marker covers 9 setups, not the "top five" the README and BUILD_SPEC §1 describe. Read with the planned note, it tells the manager that setups at 44.62% and 43.08% are "not statistically separated" from 66.15%, but a two-proportion test separates them (p = 0.014 and 0.008). A manager could keep a clearly weaker setup on the shortlist.
  - Minor: with frameworks = Hermes only, the KPI says "3 tied at best ACC" (all at 20%). "Tied" here means equal published ACC, not the statistical tie of the marker; the page uses the same word for both.
  - Missing: the existing test (`tests/test_real_data.py` line 27) only checks that the first five rows are marked, so it passes while the claim and the code disagree.
- Conclusion and any recommended change: ranking and filtering work as specified. The tie marker and its wording are misleading for the decision it is meant to support. Requested in AUDIT-01: base the marker on a test against the leader, or reword it as "intervals overlap (not a significance test)", and make the README and BUILD_SPEC match what is marked.

## 2. Number audit

- Number audited and its meaning: the leader's 95% ACC interval, 43/65 = 66.15% → 54.0–76.5% (BUILD_SPEC §9 item 2, README "Key facts"). It should mean: if the 65 audit instances are a sample from similar XBRL audit tasks, the setup's true accuracy is plausibly between 54.0% and 76.5%. Derived from it: `overlaps_leader`, the count of setups whose interval reaches the leader's lower bound.
- Formula, units, population, and time window: Wilson score interval, z = 1.96, on k = `acc_instances` correct out of n = `audit_instances` = 65; output in percent (0–100). Population: the 65 HERCULEAN Auditing instances per setup, published aggregates from Table 2 (arXiv:2605.14355v3, p. 9); one published run per setup, no time dimension.
- Relevant data assumptions: (1) `acc_instances` = round(ACC × 65) recovers the true count; checked: k/65 reproduces every published ACC to 2 decimals. (2) n = 65 for every setup. (3) The 65 outcomes are independent Bernoulli trials (needed for the interval). (4) The overlap rule implicitly treats setups as independent samples, but all setups ran on the same 65 instances.
- Code checked: `src/analysis/published.py` at `45939a9`:
  - `wilson_ci`, lines 44–52: `p = k / n`; `centre = (p + z*z/(2n)) / (1 + z*z/n)`; `half = z*sqrt(p(1-p)/n + z*z/(4n²)) / (1 + z*z/n)`; returns `100*max(0, centre-half), 100*min(1, centre+half)`.
  - `rank_configs`, lines 62–64 apply it per setup; lines 70–71: `leader_low = out.loc[out["accuracy_pct"].idxmax(), "acc_ci_low"]`; `out["overlaps_leader"] = out["acc_ci_high"] >= leader_low`.
- What this code computes, in my own words: for each setup it turns "43 of 65 right" into a range of plausible true accuracies, which is pulled slightly toward 50% and is never outside 0–100%. It then marks any setup whose range reaches up to the bottom of the leader's range.
- Small test case and expected result: k = 43, n = 65, z = 1.96. Step by step: p = 0.6615; z²/n = 0.0591; centre = (0.6615 + 0.0296)/1.0591 = 0.6525; half = 1.96 × √(0.003445 + 0.000227)/1.0591 = 0.1121; interval = 54.0% to 76.5%. Range check: lower < 66.15% < upper, both within 0–100.
- Actual result: `wilson_ci(43, 65)` = (54.04, 76.47); matches.
- Independent calculation or check of a specific assumption/code line:
  - Computed another way: `checks/audit_m6_wilson.py` Part A writes the Wilson formula from scratch with the standard library and reads the CSV directly (no team code). All 20 intervals match the team's `rank_configs` to 7e-15 percentage points (B1), and the marked set is the same 9 setups (B2).
  - Went deeper into lines 70–71: the overlap rule is the assumption behind "not statistically separated". Two 95% intervals can overlap even when the difference between two proportions is significant, so the rule is more generous than a test. A pooled two-proportion test against 43/65 gives p = 0.71 (63.08%), 0.051 (49.23%), 0.0135 (44.62%) and 0.0082 (43.08%, two setups). So the rule marks 9 setups where a test supports at most 6 and the README states 5.
- What the evidence establishes and what remains uncertain: established: the interval number and its code are correct; the marker's count (9) disagrees with the stated claim (5); 3 marked setups are significantly below the leader under an unpaired test. Uncertain: the setups share the same 65 instances, so a paired McNemar test would be correct, but the paper publishes no case-level results; the p-values near 0.05 (49.23%) could go either way. With one run per setup, run-to-run variation is also unknown, so the intervals may be too narrow. Not tested: the Streamlit display itself (not built), M7 and M8.
- Recommended change, if any: AUDIT-01 (see the team's `change-requests.md`).

## My contribution

- What I personally checked and concluded: I checked the team repository and the professor's Module 9 repository with the AI and confirmed that no Phase 3 app exists yet, so I decided to audit the committed backend against BUILD_SPEC. I confirmed with my team that no one else had claimed an audit scope, and I accepted the Configuration Shortlist and M6 because they support the dashboard's headline "top five tied" claim. I reviewed the check output, this audit and AUDIT-01 before anything was committed. I reran the check and got the same output," or "Gemini gave the same interval, 54.0–76.5%. My conclusion: the interval is correct, but the "not statistically separated" marker would mislead a manager choosing pilot setups.
- How AI helped, if used: Claude Code (Opus 5.5) read the repository, suggested the feature and number, wrote and ran `checks/audit_m6_wilson.py` (the hand-formula check and the two-proportion tests), and drafted this file and AUDIT-01. The calculations in sections 1–2 come from that script, which anyone can rerun.
- Related change-request IDs in the team's `change-requests.md`, if any: AUDIT-01.
