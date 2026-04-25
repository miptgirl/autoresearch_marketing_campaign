import pandas as pd

BUDGET = 30_000_000.0

df = pd.read_csv('marketing_campaign_estimations.csv', sep='\t').copy()
df['revenue_per_spend'] = df.revenue / df.marketing_spending
df = df.sort_values('revenue_per_spend', ascending=False).reset_index(drop=True)

spends = df.marketing_spending.tolist()
revenues = df.revenue.tolist()
item_count = len(df)

# Seed the search with a greedy pass that keeps scanning after an item does
# not fit. This gives branch-and-bound a strong initial lower bound.
remaining_budget = BUDGET
seed_take = [False] * item_count
best_revenue = 0.0
for index, spend in enumerate(spends):
    if spend <= remaining_budget:
        remaining_budget -= spend
        seed_take[index] = True
        best_revenue += revenues[index]

best_take = seed_take.copy()
current_take = [False] * item_count


def upper_bound(start_index: int, remaining: float, revenue_so_far: float) -> float:
    """Fractional-knapsack upper bound for pruning."""
    bound = revenue_so_far
    for index in range(start_index, item_count):
        spend = spends[index]
        revenue = revenues[index]
        if spend <= remaining:
            remaining -= spend
            bound += revenue
        else:
            bound += revenue * (remaining / spend)
            break
    return bound


def search(index: int, remaining: float, revenue_so_far: float) -> None:
    global best_revenue, best_take

    if index == item_count:
        if revenue_so_far > best_revenue:
            best_revenue = revenue_so_far
            best_take = current_take.copy()
        return

    if upper_bound(index, remaining, revenue_so_far) <= best_revenue:
        return

    spend = spends[index]
    revenue = revenues[index]

    if spend <= remaining:
        current_take[index] = True
        search(index + 1, remaining - spend, revenue_so_far + revenue)
        current_take[index] = False

    search(index + 1, remaining, revenue_so_far)


search(0, BUDGET, 0.0)
selected_df = df.loc[best_take]

total_spend = float(selected_df.marketing_spending.sum())
revenue_millions = float(selected_df.revenue.sum() / 1_000_000)
budget_slack_millions = (BUDGET - total_spend) / 1_000_000

assert total_spend <= BUDGET, f"Budget violated: {total_spend}"

print(f"METRIC revenue_millions={revenue_millions:.4f}")
print(f"METRIC spend_millions={total_spend/1_000_000:.4f}")
print(f"METRIC budget_slack_millions={budget_slack_millions:.4f}")
print(f"METRIC segment_count={len(selected_df)}")
print(f"# segments={len(selected_df)} spend={total_spend/1e6:.2f}M")