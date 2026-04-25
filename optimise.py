import pandas as pd

df = pd.read_csv('marketing_campaign_estimations.csv', sep='\t')

# --- Baseline: greedy by revenue-per-dollar ---
df['revenue_per_spend'] = df.revenue / df.marketing_spending
df = df.sort_values('revenue_per_spend', ascending=False)
df['spend_cumulative'] = df.marketing_spending.cumsum()
selected_df = df[df.spend_cumulative <= 30_000_000]

total_spend = selected_df.marketing_spending.sum()
revenue_millions = selected_df.revenue.sum() / 1_000_000

assert total_spend <= 30_000_000, f"Budget violated: {total_spend}"

print(f"METRIC revenue_millions={revenue_millions:.4f}")
print(f"# segments={len(selected_df)} spend={total_spend/1e6:.2f}M")