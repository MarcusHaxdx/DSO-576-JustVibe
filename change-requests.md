# Team change requests

Copy this template into the top folder of your team's app repository if `change-requests.md` is missing. If it already exists, add to it; do not replace your teammates' work. Keep your individual evidence and conclusions in `my-audit.md`.

## Claims

Add your name and what you will audit. Choose a different scope from your teammates, or explain the new evidence you will contribute.

| Author | Feature | Number | Distinct scope or new evidence |
| --- | --- | --- | --- |
| Jinyang Yuan | Review Queue (tab 3, UC3) | Sign-flip rate, 9 / 246 = 3.66 % (Overview, "Flags (M2)") | Review Queue checked on the real 362-row data with a headless walk-through and in the browser; sign-flip rate recomputed independently, by hand for two cases, and re-parsed from the original message text for all 110 rule-type-126 rows. Details in `my-audit.md`. |
| | | | |

## Requests

Copy this block for each actionable finding and choose a unique ID. Reference that ID in your individual audit. A check that finds no defect belongs in your audit; do not invent a bug to fill a request.

### AUDIT-JY-01 Tied ranks look like a ranking

- Author: Jinyang Yuan
- Status: open
- App version or commit checked: `app/main.py` sha256 `883c3d4caad2d34225bc3106d9ecddf85f861d81058196f38a575ce509d6ebdf`, built from the 14,549-byte `BUILD_SPEC.md`; data `data/clean/auditing_clean.csv` sha256 `90cd52929c401be12a62091c99fe8ea7f4f9a370c5c1b335d4a043e3925f27d9`. (`fresh_agent_test` is not a git repository, so there is no commit.)
- Feature or number and its intended behavior or definition: Review Queue (UC3, "which cases go to human review first"). Spec M5: one point per rule triggered; rank by points, then `rel_diff` descending, then filing date descending.
- Inputs and steps to reproduce: start the app; Review Queue tab; turn off every rule except "sign flip".
- Expected result: ranks that say something about review priority, or a visible sign that the order has no basis.
- Actual result: "9 cases in the queue", all with 1 point and `rel_diff` 200 %; ranks 1–9 follow filing date exactly, from 2024-11-14 (rank 1) to 2022-01-12 (rank 9). The table shows consecutive ranks with nothing marking them as tied.
- Evidence (including file, function, and relevant lines if code was checked): `src/analysis/triage.py` `rank_cases`, line 56 `d.sort_values(["points", "rel_diff", "report.filing-date", "case_id"], ...)`; CSV `review_queue.csv` rows 1 and 2 both have points 1 and `rel_diff` 2.0 (Kenilworth 2024-11-14, Kingfish 2024-02-14); `audit_feature_check.py` output "only sign_flip -> 9 cases".
- Likely cause, if established, and remaining uncertainty: the spec's tie-break works as written, so this is not a bug against the spec. Uncertain how real users read "rank 1".
- Requested change: show ties (for example a "tied" marker or a note under the table when the top ranks share points and `rel_diff`).
- Verification check and expected result: repeat the steps; the nine rows are marked as tied, and with all five rules on the 20 two-point cases are not all marked as tied.
- Implementation commit and verification result, if resolved:

### AUDIT-JY-02 "sign flip" is not explained and is not the rule-type-15 sign check

- Author: Jinyang Yuan
- Status: open
- App version or commit checked: same as AUDIT-JY-01.
- Feature or number and its intended behavior or definition: flag `sign_flip` = recomputed value equals the negative of the reported value and the reported value is not 0; shown as the "sign flip" toggle in the Review Queue and as the sign-flip rate in the Overview.
- Inputs and steps to reproduce: `python audit_signflip_check.py`; then `python -c "import pandas as pd; d=pd.read_csv('data/clean/auditing_clean.csv'); print(d.loc[d.sign_flip,'assertion.code'].value_counts())"`.
- Expected result: a user reading "sign flip" can tell what it means.
- Actual result: the toggle has no explanation: `app/main.py` passes no help text to any widget (`grep -n "help=" app/main.py` returns nothing). The Overview flag table was not checked. Of the 9 flagged cases 8 are rule `DQC.US.0126.9590`, 1 is `DQC.US.0117.9574`, none is from rule type 15 (the 116 sign checks, which cannot be flagged because their `calculated_value` is empty).
- Evidence (including file, function, and relevant lines if code was checked): `clean_auditing.py` line 219 `clean["sign_flip"] = (clean["calculated_value"] == -clean["reported_value"]) & (clean["reported_value"] != 0)`; `src/analysis/triage.py` line 9 `"sign_flip": "sign flip"`; `app/main.py` line 324 `c.toggle(RULE_LABELS[r], key=...)`.
- Likely cause, if established, and remaining uncertainty: naming only; the calculation itself checks out (9 flagged rows reproduced independently).
- Requested change: add help text to the toggle and to the Overview flag, for example "recomputed value is exactly the negative of the reported value; not the same as a failed sign-check rule".
- Verification check and expected result: the toggle shows the help text on hover.
- Implementation commit and verification result, if resolved:

### AUDIT-JY-03 `rel_diff` has different units on screen and in the CSV

- Author: Jinyang Yuan
- Status: open
- App version or commit checked: same as AUDIT-JY-01.
- Feature or number and its intended behavior or definition: Review Queue table and "Download queue (CSV)" ("a CSV download of that same DataFrame", spec section 4); `rel_diff` = absolute difference / |reported value|.
- Inputs and steps to reproduce: only "sign flip" on; read the `rel_diff` column; click "Download queue (CSV)"; `head -3 ~/Downloads/review_queue.csv`.
- Expected result: the same number in the same unit.
- Actual result: screen shows `200%` on all nine rows; the CSV has `2.0` (rank 1 and 2 rows). The screen also shows thousands separators (−252,587), the CSV has `-252587.0`.
- Evidence (including file, function, and relevant lines if code was checked): `app/main.py` line 338 `"rel_diff": st.column_config.NumberColumn(format="percent")`; line 340 `queue.to_csv(index=False)` writes the raw fraction.
- Likely cause, if established, and remaining uncertainty: the percent format is applied only on screen. It follows the spec's wording, so it is not a spec violation; whether it confuses users is not tested.
- Requested change: name the unit in the CSV header (for example `rel_diff_fraction`) or write the CSV in percent.
- Verification check and expected result: the downloaded CSV's header or values make the unit clear; rank 1 reads `200` or `2.0` under a header that says which.
- Implementation commit and verification result, if resolved:

### AUDIT-JY-04 The queue does not show the concept prefix that triggers the "non-us-gaap prefix" rule

- Author: Jinyang Yuan
- Status: open
- App version or commit checked: same as AUDIT-JY-01.
- Feature or number and its intended behavior or definition: rule "non-us-gaap prefix" (concept prefix other than `us-gaap`). Spec asks for `prefix:concept` in the Case Explorer; it does not say how the queue shows it.
- Inputs and steps to reproduce: Review Queue; turn off all rules except "non-us-gaap prefix".
- Expected result: the user can see from the table why a case is flagged.
- Actual result: "12 cases in the queue"; the `why` column says "non-us-gaap prefix" but the `concept` column shows only the bare name (for example `TheaterAccessFees`), never a prefix. Backend check: none of the 12 `concept` values contains ":". Three of the 12 are rule-type-15 cases (Barnwell).
- Evidence (including file, function, and relevant lines if code was checked): `src/analysis/triage.py` line 17 `QUEUE_COLUMNS` contains `concept`, not `concept_prefix`; the data has both columns (`src/analysis/loader.py` line 18).
- Likely cause, if established, and remaining uncertainty: the queue reuses the bare `concept` column. Not a spec violation.
- Requested change: show `prefix:concept` in the queue, or add the `concept_prefix` column.
- Verification check and expected result: with only the prefix rule on, every one of the 12 rows shows a prefix other than `us-gaap`.
- Implementation commit and verification result, if resolved:

### AUDIT-JY-05 `reasons` column header differs from the spec

- Author: Jinyang Yuan
- Status: open
- App version or commit checked: same as AUDIT-JY-01.
- Feature or number and its intended behavior or definition: spec section 4, Tab 3: "`reasons` is labeled 'why' on screen".
- Inputs and steps to reproduce: Review Queue tab; read the header of the fourth column.
- Expected result: header "why".
- Actual result: header "why (reasons)".
- Evidence (including file, function, and relevant lines if code was checked): `app/main.py` line 334 `"reasons": st.column_config.TextColumn("why (reasons)")`. The build agent noted this choice in its own `GUESSES.md`.
- Likely cause, if established, and remaining uncertainty: a deliberate small choice by the build agent. Low impact.
- Requested change: label the column "why", or change the spec to "why (reasons)".
- Verification check and expected result: the header reads as the spec says.
- Implementation commit and verification result, if resolved:

Record findings without undoing a teammate's work. Mark a request resolved only after verifying the change.
