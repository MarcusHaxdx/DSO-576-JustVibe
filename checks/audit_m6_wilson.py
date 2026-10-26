"""Module 9 audit check (Ling Zhong): M6 Wilson interval and the Shortlist "not statistically separated" marker.

Run from the repository root:  python checks/audit_m6_wilson.py

Part A recomputes everything from the CSV with the standard library only (no team code).
Part B calls the team's backend and compares. Part C checks the feature's claims.
"""
from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "clean" / "published_auditing_results.csv"
Z = 1.96


def wilson(k: int, n: int, z: float = Z) -> tuple[float, float]:
    """Wilson score interval in percent, written from the textbook formula."""
    p = k / n
    centre = (p + z**2 / (2 * n)) / (1 + z**2 / n)
    half = (z / (1 + z**2 / n)) * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))
    return 100 * (centre - half), 100 * (centre + half)


def two_prop_p(k1: int, k2: int, n: int) -> float:
    """Two-sided pooled two-proportion z-test p-value (treats the two setups as independent samples)."""
    pooled = (k1 + k2) / (2 * n)
    se = math.sqrt(pooled * (1 - pooled) * 2 / n)
    return math.erfc(abs((k1 - k2) / n / se) / math.sqrt(2)) if se else 1.0


rows = list(csv.DictReader(DATA.open(encoding="utf-8")))
for r in rows:
    r["k"], r["n"] = int(r["acc_instances"]), int(r["audit_instances"])
    r["setup"] = f'{r["framework"]} + {r["model_name"]}'

# ---- Part A: independent recomputation --------------------------------------------------------
print("A1. Small case by hand: 43/65")
lo, hi = wilson(43, 65)
print(f"    p = {43/65:.4%}; Wilson 95% = {lo:.2f}% to {hi:.2f}%  (BUILD_SPEC says ~54.0-76.5%)")
assert round(lo, 1) == 54.0 and round(hi, 1) == 76.5

print("A2. Sanity: k/n reproduces each published ACC, n is 65 everywhere, interval contains p")
for r in rows:
    assert r["n"] == 65
    assert abs(100 * r["k"] / r["n"] - float(r["accuracy_pct"])) < 0.005, r["setup"]
    l, h = wilson(r["k"], r["n"])
    assert 0 <= l <= 100 * r["k"] / r["n"] <= h <= 100
print("    ok for all 20 setups")

leader_k = max(r["k"] for r in rows)
leader_lo, _ = wilson(leader_k, 65)
print(f"A3. Setups whose interval high >= leader's low ({leader_lo:.2f}%), with a test against {leader_k}/65")
print(f"    {'setup':36} {'ACC':>7} {'95% interval':>15} {'overlap':>8} {'p vs leader':>12}")
marked = []
for r in sorted(rows, key=lambda r: (-r["k"], r["setup"])):
    l, h = wilson(r["k"], 65)
    if h < leader_lo:
        continue
    marked.append(r)
    p = two_prop_p(leader_k, r["k"], 65)
    flag = "  <-- p < 0.05" if p < 0.05 else ""
    print(f"    {r['setup']:36} {100*r['k']/65:6.2f}% [{l:5.1f}, {h:5.1f}] {'yes':>8} {p:12.4f}{flag}")
print(f"    marked by the overlap rule: {len(marked)} setups (README/BUILD_SPEC say 'the top five')")

# ---- Part B: compare with the team's code ---------------------------------------------------
sys.path.insert(0, str(ROOT / "src"))
from analysis.published import load_published, rank_configs, shortlist, shortlist_kpis  # noqa: E402

ranked = rank_configs(load_published(DATA))
print("B1. Team rank_configs vs my intervals (max abs difference, percentage points)")
mine = {r["setup"]: wilson(r["k"], 65) for r in rows}
diff = max(max(abs(a - b) for a, b in zip(mine[s], (lo_, hi_)))
           for s, lo_, hi_ in zip(ranked["setup"], ranked["acc_ci_low"], ranked["acc_ci_high"]))
print(f"    {diff:.2e}")
assert diff < 1e-9
team_marked = set(ranked.loc[ranked["overlaps_leader"], "setup"])
print(f"B2. Team overlaps_leader count: {len(team_marked)}; same set as mine: {team_marked == {r['setup'] for r in marked}}")

# ---- Part C: feature behaviour (Shortlist controls, BUILD_SPEC section 9 items 2-3) ----------
print("C1. Ranks of the top five:", list(zip(ranked["setup"].head(5), ranked["rank"].head(5))))
print("C2. Max SER = 0 ->", len(shortlist(ranked, max_ser=0)), "setups; plus min ACC = 60 ->",
      len(shortlist(ranked, min_acc=60, max_ser=0)), "setups (spec: 10 and 5)")
print("C3. Default KPI row:", shortlist_kpis(shortlist(ranked)))
herm = shortlist(ranked, frameworks=["Hermes"])
print("C4. Frameworks = Hermes only: KPI", shortlist_kpis(herm),
      "| ranks", herm["rank"].tolist(), "| overlaps_leader", herm["overlaps_leader"].tolist())
