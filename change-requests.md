# Team change requests

Copy this template into the top folder of your team's app repository if `change-requests.md` is missing. If it already exists, add to it; do not replace your teammates' work. Keep your individual evidence and conclusions in `my-audit.md`.

## Claims

Add your name and what you will audit. Choose a different scope from your teammates, or explain the new evidence you will contribute.

| Author | Feature | Number | Distinct scope or new evidence |
| --- | --- | --- | --- |
| Ling Zhong | Configuration Shortlist (UC1): ranked setups, 95% intervals and the "not statistically separated" marker (`src/analysis/published.py`: `rank_configs`, `shortlist`, `shortlist_kpis`) | M6: the leader's Wilson 95% ACC interval, 43/65 = 66.15% → 54.0–76.5%, and the `overlaps_leader` count | First claim on the Shortlist and M6 |

## Requests

Copy this block for each actionable finding and choose a unique ID. Reference that ID in your individual audit. A check that finds no defect belongs in your audit; do not invent a bug to fill a request.

### AUDIT-XX Short description

- Author:
- Status: open
- App version or commit checked:
- Feature or number and its intended behavior or definition:
- Inputs and steps to reproduce:
- Expected result:
- Actual result:
- Evidence (including file, function, and relevant lines if code was checked):
- Likely cause, if established, and remaining uncertainty:
- Requested change:
- Verification check and expected result:
- Implementation commit and verification result, if resolved:

Record findings without undoing a teammate's work. Mark a request resolved only after verifying the change.

### AUDIT-01 "Not statistically separated" marker covers 9 setups, 3 of them significantly worse than the leader

- Author: Ling Zhong
- Status: open
- App version or commit checked: `45939a9` on branch `Ling_Zhong_part` (Phase 2 backend; the Phase 3 app is not built yet)
- Feature or number and its intended behavior or definition: Configuration Shortlist marker (BUILD_SPEC §4 page 1, §6 M6). `overlaps_leader` = a setup's Wilson 95% ACC high ≥ the leader's low. The app note under the table reads "Marked setups' intervals overlap the leader's, so they are not statistically separated". README and BUILD_SPEC §1 say "the top five are not statistically separated".
- Inputs and steps to reproduce: from the repository root, `python checks/audit_m6_wilson.py` (stdlib only for Part A; Part B imports the team backend).
- Expected result: the marker only covers setups that a test cannot separate from the leader, and the number of marked setups matches the README claim (five).
- Actual result: 9 setups are marked (A3, B2). A pooled two-proportion test against 43/65 gives p = 0.0135 for Claude Code + GPT-5.4 (44.62%) and p = 0.0082 for Claude Code + Qwen3.5-27B and OpenClaw + Qwen3.5-397B-A17B (43.08%), so 3 marked setups are significantly worse at the 5% level. Codex + Qwen3.5-397B-A17B (49.23%) is borderline (p = 0.051). Only the two Codex setups at 63.08% (p = 0.71) clearly match the "top five" claim.
- Evidence (including file, function, and relevant lines if code was checked): `src/analysis/published.py`, `rank_configs`, lines 70–71 (`leader_low = …`; `out["overlaps_leader"] = out["acc_ci_high"] >= leader_low`). The rule is coded exactly as BUILD_SPEC §6 M6 says; the defect is in the rule and its wording. `tests/test_real_data.py` line 27 only asserts `head(5)` are marked, so it does not catch the other 4. The interval itself is correct: my independent Wilson formula matches `wilson_ci` to 7e-15 points for all 20 setups.
- Likely cause, if established, and remaining uncertainty: overlapping 95% intervals do not imply "no significant difference"; two 95% intervals can overlap while the difference is significant. Uncertainty: all setups run on the same 65 instances, so the right test is paired (McNemar), which needs case-level results the paper does not publish. The unpaired test is an approximation; a paired test could move these p-values either way, so which borderline setups are "separated" is untested. The claim that overlapping intervals do not prove a tie holds regardless.
- Requested change: either (a) mark setups by a test against the leader (e.g. two-proportion p ≥ 0.05) and update the note, or (b) keep the overlap rule but reword the note to "intervals overlap the leader's (not a significance test)". In both cases change README "Key facts" and BUILD_SPEC §1 so the stated number matches what the screen marks, and make `test_real_data.py` assert the full marked set, not `head(5)`.
- Verification check and expected result: rerun `python checks/audit_m6_wilson.py` and `python -m pytest`. Under (a) the marked set is the 5 setups at ≥ 63.08% plus Codex + Qwen3.5-397B-A17B (p = 0.051), i.e. 6, and README matches; under (b) 9 marked with the new wording and README says 9.
- Implementation commit and verification result, if resolved:
