"""Independent check of the sign-flip rate. Does not import anything from src/analysis.
Run from the repo top folder:  python audit_signflip_check.py
"""
import pandas as pd

df = pd.read_csv("data/clean/auditing_clean.csv")
rep, calc = df["reported_value"], df["calculated_value"]

both = rep.notna() & calc.notna()            # rows where a comparison is possible
flip = both & (rep != 0) & (calc == -rep)    # my own definition, not the file's sign_flip column
flip_col = df["sign_flip"].astype(bool)

print("rows in file:                        ", len(df))
print("rows with both values (denominator): ", int(both.sum()))
print("sign flips, my definition:           ", int(flip.sum()))
print("sign flips, file's sign_flip column: ", int(flip_col.sum()))
print("same rows flagged?                   ", bool((flip == flip_col).all()))
print("rate, comparison rows as denominator:", round(100 * flip.sum() / both.sum(), 2), "%")
print("rate, all rows as denominator:       ", round(100 * flip.sum() / len(df), 2), "%")
rel = ((calc - rep).abs() / rep.abs())[flip]
print("relative gap on flagged rows (should all be 2.0):", sorted(set(rel.round(6))))
print()
cols = [c for c in ["report.accession", "assertion.code", "reported_value", "calculated_value", "assertion.detail"] if c in df]
print(df.loc[flip, cols].to_string())
