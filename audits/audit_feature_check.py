"""Headless walk-through of the Review Queue tab with Streamlit's AppTest (no browser).
Run from the app's top folder:  .venv/bin/python audit_feature_check.py
"""
from streamlit.testing.v1 import AppTest

RULES = ["sign_flip", "period_after_filing", "non_usd", "non_us_gaap_prefix", "large_gap"]


def queue_count(at):
    for m in at.markdown:
        if "cases in the queue" in m.value:
            return int(m.value.split("**")[1].split()[0])
    return 0          # the "No cases in the queue" info box is shown instead


def fresh():
    return AppTest.from_file("app/main.py", default_timeout=90).run()


at = fresh()
assert not at.exception, at.exception
print("start view: all rules on, threshold", at.session_state["q_threshold_pct"], "% ->", queue_count(at), "cases")

for only in RULES:
    at = fresh()
    for r in RULES:
        at.session_state[f"q_{r}"] = (r == only)
    at.run()
    assert not at.exception, at.exception
    slider = [s for s in at.slider if "threshold" in s.label][0]
    print(f"only {only:20s} -> {queue_count(at):3d} cases | threshold slider disabled: {slider.disabled}")

at = fresh()
for r in RULES:
    at.session_state[f"q_{r}"] = False
at.run()
print("no rule on            ->", queue_count(at), "cases;", [i.value[:60] for i in at.info if "No cases" in i.value])

at = fresh()
at.session_state["q_threshold_pct"] = 100
at.run()
print("all rules, threshold 100% ->", queue_count(at), "cases")
