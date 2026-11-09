"""Sensitivity of the sign-flip definition: how many cases are *almost* exact negations?
Run from the repo top folder:  python audit_nearflip_check.py
"""
import pandas as pd

df = pd.read_csv("data/clean/auditing_clean.csv")
r, c = df["reported_value"], df["calculated_value"]
opp = (r * c < 0) & ~df["sign_flip"].astype(bool)          # opposite signs, not exactly negated
gap = (c + r).abs() / r.abs()                              # distance from exact negation, relative to |reported|

print("rows with opposite signs (incl. flagged):", int((r * c < 0).sum()), "| exactly negated:", int(df["sign_flip"].sum()))
for t in (0.001, 0.01, 0.05):
    print(f"opposite signs, not flagged, within {t:.1%} of negation:", int((opp & (gap < t)).sum()))

near = df.loc[opp & (gap < 0.01)]
print()
print(near[["report.accession", "assertion.code", "reported_value", "calculated_value"]].to_string())
print("reported + calculated:", (near["reported_value"] + near["calculated_value"]).tolist())
print("gap relative to |reported|:", gap[near.index].round(5).tolist())
print("rate if these were counted:", round(100 * (df["sign_flip"].sum() + len(near)) / c.notna().sum(), 2), "%")
