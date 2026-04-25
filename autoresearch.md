# Autoresearch: maximize marketing campaign revenue under budget

## Objective
Improve `optimise.py` so it selects a set of campaign segments with **maximum total revenue** while respecting the fixed marketing budget of **30,000,000**. The current implementation is a greedy heuristic: it sorts by revenue-per-spend, takes a cumulative prefix, and stops once the next item would exceed budget. That means it can leave budget unused and never consider cheaper profitable items later in the sorted list.

The workload is tiny (62 rows), so higher-quality combinatorial optimization strategies are likely practical. We should favor exact or near-exact selection logic over fragile heuristics when the runtime stays fast.

## Metrics
- **Primary**: `revenue_millions` (millions, higher is better) — total selected revenue divided by 1,000,000
- **Secondary**:
  - `spend_millions` — total selected spend divided by 1,000,000
  - `budget_slack_millions` — unused budget in millions
  - `segment_count` — number of selected segments

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
- Must keep the script runnable with `python3 optimise.py`
- No dataset changes
- Keep the solution simple and explainable unless extra complexity yields materially better revenue
- Runtime should remain fast enough for many autoresearch iterations

## What's Been Tried
- Baseline code sorts by `revenue / marketing_spending`, computes cumulative spend, and keeps only the sorted prefix under budget.
- This baseline is structurally weak: if one high-ranked row would overflow the budget, the algorithm stops considering all later rows even if several of them would fit and increase revenue.
- Repository inspection: 62 total segments across 31 countries and 2 channels, so exact search may be feasible with careful pruning.
