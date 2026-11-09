# Guesses and choices not fixed by BUILD_SPEC.md

- Spec says app/ must not count anything, but no metrics function gives "rel_diff cases", "above 500%" or "comparison cases without rel_diff" for the histogram caption; src/analysis/ is frozen, so the app takes len() of `metrics.discrepancy` output for these three numbers. Suggested change (not made): add a `histogram_counts(df, max_rel)` helper to metrics.py.
- `runs.load_runs` docstring says "the app then hides tab 4", but spec section 4 says tab 4 is always present with an empty state; followed the spec. Suggested change (not made): fix that docstring.
- How to switch tabs from the "Open these cases" button: used `st.tabs(key="active_tab", on_change="rerun")` (supported in Streamlit 1.66) and set that key in the button callback.
- "Malformed runs file": treated any exception from `load_runs` or `score_runs` (missing columns, unknown case_id, unparsable CSV) as malformed and show the error plus "No agent runs loaded".
- Runs file loading cached with `st.cache_data` keyed by modified time, same as the clean CSV (spec only says this for the clean CSV).
- When filters leave no runs on the filtered cases, tab 4 shows "No agent runs on the currently filtered cases." (spec does not define this state).
- Filing-year and unit filter options are taken from the values present in the loaded data; rule-type options are the three spec labels.
- Histogram: x axis in percent, 50 bins of 10% from 0 to 500% inclusive; sign-flip and other cases are stacked as two colors (red highlight vs blue).
- Histogram caption also lists median/max abs_diff (USD) next to median/max rel_diff from `discrepancy_summary`.
- Flag summary table shows the four counts from `flag_summary` (sign flip, period after filing, non-USD, non-us-gaap prefix) with the sign-flip rate as "x% (n / m ...)" beneath.
- Case Explorer "filing date" shown as a date (no time); reported/calculated use localized number format; empty calculated cells are blank (`placeholder=""`).
- Detail panel: original message in a read-only text area; parsed fields as a two-column table; "—" for missing values; a note explains why a discrepancy is missing (type 15, non-USD, missing value, or reported 0).
- Queue status line format: "rank R of N, P point(s): reasons".
- Review Queue table shows all `triage.QUEUE_COLUMNS` (including `case_id`) and the CSV is `queue.to_csv` of that same DataFrame; the "why" column is `reasons` relabeled "why (reasons)" on screen only (CSV header stays `reasons`).
- Triage toggles default to all five rules on, threshold 10%; they persist across reruns via session state but are not cleared by "Reset filters" (they are not global filters).
- Rule toggles shown as `st.toggle` labeled with `triage.RULE_LABELS`.
- Scatter in tab 4 labels each point "agent_framework / model"; accuracy axis as percent.
- Bars, KPIs and charts use Plotly with fixed colors #4C78A8 (base) and #E45756 (highlight); page uses Streamlit wide layout.
