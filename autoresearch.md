# Autoresearch: maximize marketing campaign revenue under budget and CS capacity limits

## Objective
Improve `optimise.py` so it selects a set of campaign segments with **maximum total revenue** while respecting all business constraints:
- marketing budget **<= 30,000,000**
- additional CS contacts **<= 5,000**
- contact rate **<= 0.042** (`cs_contacts / users`)

The workload is tiny (62 rows), so exact combinatorial optimization is practical and preferable to fragile heuristics. The added contact-rate constraint is linear when rewritten as `500 * cs_contacts - 21 * users <= 0`, so an exact mixed-integer or exact search formulation should stay simple and fast.

## Metrics
- **Primary**: `revenue_millions` (millions, higher is better) — total selected revenue divided by 1,000,000
- **Secondary**:
  - `spend_millions` — total selected spend divided by 1,000,000
  - `budget_slack_millions` — unused budget in millions
  - `segment_count` — number of selected segments
  - `cs_contacts` — total additional CS contacts selected
  - `cs_headroom` — remaining CS-contact capacity under the 5,000 cap
  - `contact_rate` — selected `cs_contacts / users`
  - `rate_headroom` — remaining room under the 0.042 rate cap

## How to Run
`./autoresearch.sh` — runs a quick syntax pre-check, then `optimise.py`, which must emit `METRIC name=number` lines.

## Files in Scope
- `optimise.py` — campaign-selection logic and metric output
- `autoresearch.sh` — benchmark harness and pre-checks
- `autoresearch.md` — session memory / findings
- `autoresearch.ideas.md` — backlog for promising deferred ideas

## Off Limits
- `marketing_campaign_estimations.csv` — input data; do not edit
- Git history / branch structure outside the autoresearch workflow

## Constraints
- Must keep spend `<= 30_000_000`
- Must keep additional CS contacts `<= 5_000`
- Must keep contact rate `<= 0.042`
- Must keep the script runnable with `python3 optimise.py`
- No dataset changes
- Keep the solution simple and explainable unless extra complexity yields materially better revenue
- Runtime should remain fast enough for many autoresearch iterations

## What's Been Tried
- Original baseline sorted by `revenue / marketing_spending`, computed cumulative spend, and kept only the sorted prefix under budget.
- That prefix heuristic is structurally weak: if one high-ranked row would overflow the budget, the algorithm stops considering all later feasible/profitable rows.
- Repository inspection: 62 total segments across 31 countries and 2 channels, so exact search is practical.
- Replaced the prefix heuristic with an exact branch-and-bound 0/1 knapsack search using a fractional-knapsack upper bound and a greedy feasible seed. Under the old single-budget objective, revenue improved from **107.9158M** to **110.1627M**.
- New user constraint update: the old best budget-only solution is **not feasible** anymore. It stayed below the 5,000 CS-contact cap (3,639) but violated the contact-rate cap with **0.04463 > 0.042**.
- The new rate constraint can be rewritten exactly as `500 * cs_contacts - 21 * users <= 0`, which makes the problem a small binary linear program with three linear constraints (budget, CS contacts, rate).
- `scipy.optimize.milp` solves this exact formulation essentially instantly on the current dataset, making it a strong candidate over maintaining a custom multi-constraint branch-and-bound.
- Simplified the implementation further by removing the fallback search path and solving directly with SciPy MILP; revenue stayed at the exact optimum while the code became much shorter and the script runtime dropped from about 1.1s to about 0.7s.
- Replaced the tiny pandas-based data-loading/summing path with `csv.DictReader` plus NumPy arrays. Revenue stayed optimal, the code got slightly leaner, and end-to-end script runtime fell again to about 0.5s.
- Simplified once more by loading only the four numeric columns via `np.loadtxt(usecols=...)`. That preserved the exact optimum and trimmed end-to-end runtime to about 0.4s.
- Minor cleanup: `milp(..., integrality=1)` broadcasts the binary integrality requirement, and `result.x > 0.5` is a clear way to recover the chosen mask. Same optimum, slightly less code.
- SciPy's `milp` interface also accepts raw `(A, b_l, b_u)` constraints and tuple bounds, so `Bounds`/`LinearConstraint` imports can be removed entirely without changing the exact solution.
- Offline tie-break checks suggest this constrained optimum is also unique in practice on the current dataset: minimizing CS contacts or spend subject to the best revenue returned the same 42-segment plan.
- If portability ever becomes a requirement, reintroduce a fallback separately. The old warning about unsafe pairwise dominance pruning still applies: in 0/1 selection, a dominated row can still be useful alongside its dominator.
