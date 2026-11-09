"""Check how calculated_value was parsed, for rule type 126 (total vs sum of child concepts).
For every type-126 row, re-read the addend lines in the original message (assertion.detail),
add them up with their + / - weights, and compare with calculated_value.
Does not use clean_auditing.py or src/analysis. Run from the repo top folder:  python audit_parse_check.py
"""
import re
import pandas as pd

df = pd.read_csv("data/clean/auditing_clean.csv")
rows = df[df["assertion.type"] == 126]

line = re.compile(r"^([+-])\s+(\w+)\s+(-?[\d,]+)\s*$", re.MULTILINE)   # e.g. "-  \tInterestExpense      4,675 "

ok, bad, none_found = 0, [], 0
for idx, r in rows.iterrows():
    addends = line.findall(r["assertion.detail"])
    if not addends:
        none_found += 1
        continue
    mine = sum((1 if sign == "+" else -1) * int(val.replace(",", "")) for sign, _, val in addends)
    if abs(mine - r["calculated_value"]) < 0.5:
        ok += 1
    else:
        bad.append((idx, r["report.accession"], r["calculated_value"], mine, len(addends)))

print("type-126 rows:                         ", len(rows))
print("my sum equals calculated_value:        ", ok)
print("my sum differs from calculated_value:  ", len(bad))
print("no addend lines found by my pattern:   ", none_found)
for b in bad[:10]:
    print("  row", b[0], b[1], "calculated_value", b[2], "my sum", b[3], "addends", b[4])
