import numpy as np
import pandas as pd

BUDGET = 30_000_000.0
MAX_CS_CONTACTS = 5_000
CONTACT_RATE_NUMERATOR = 21
CONTACT_RATE_DENOMINATOR = 500
MAX_CONTACT_RATE = CONTACT_RATE_NUMERATOR / CONTACT_RATE_DENOMINATOR


def solve_with_milp(df: pd.DataFrame) -> list[bool]:
    from scipy.optimize import Bounds, LinearConstraint, milp

    spend = df.marketing_spending.to_numpy(dtype=float)
    revenue = df.revenue.to_numpy(dtype=float)
    cs_contacts = df.cs_contacts.to_numpy(dtype=float)
    users = df.users.to_numpy(dtype=float)

    constraints = LinearConstraint(
        np.vstack(
            [
                spend,
                cs_contacts,
                CONTACT_RATE_DENOMINATOR * cs_contacts
                - CONTACT_RATE_NUMERATOR * users,
            ]
        ),
        -np.inf,
        [BUDGET, MAX_CS_CONTACTS, 0],
    )

    result = milp(
        c=-revenue,
        constraints=constraints,
        bounds=Bounds(0, 1),
        integrality=np.ones(len(df), dtype=int),
    )
    if not result.success:
        raise RuntimeError(f"MILP solver failed: {result.message}")

    return np.rint(result.x).astype(bool).tolist()


def solve_with_branch_and_bound(df: pd.DataFrame) -> list[bool]:
    spends = df.marketing_spending.tolist()
    revenues = df.revenue.tolist()
    cs_contacts = df.cs_contacts.astype(int).tolist()
    excess_contacts = (
        CONTACT_RATE_DENOMINATOR * df.cs_contacts
        - CONTACT_RATE_NUMERATOR * df.users
    ).astype(int).tolist()
    item_count = len(df)

    suffix_negative_excess = [0] * (item_count + 1)
    for index in range(item_count - 1, -1, -1):
        suffix_negative_excess[index] = (
            suffix_negative_excess[index + 1] + min(0, excess_contacts[index])
        )

    remaining_budget = BUDGET
    running_cs_contacts = 0
    running_excess = 0
    seed_take = [False] * item_count
    best_revenue = 0.0
    for index, spend in enumerate(spends):
        next_cs_contacts = running_cs_contacts + cs_contacts[index]
        next_excess = running_excess + excess_contacts[index]
        if (
            spend <= remaining_budget
            and next_cs_contacts <= MAX_CS_CONTACTS
            and next_excess <= 0
        ):
            remaining_budget -= spend
            running_cs_contacts = next_cs_contacts
            running_excess = next_excess
            seed_take[index] = True
            best_revenue += revenues[index]

    best_take = seed_take.copy()
    current_take = [False] * item_count

    def upper_bound(start_index: int, remaining: float, revenue_so_far: float) -> float:
        bound = revenue_so_far
        for candidate_index in range(start_index, item_count):
            spend = spends[candidate_index]
            revenue = revenues[candidate_index]
            if spend <= remaining:
                remaining -= spend
                bound += revenue
            else:
                bound += revenue * (remaining / spend)
                break
        return bound

    def search(
        index: int,
        remaining: float,
        current_cs_contacts: int,
        current_excess: int,
        revenue_so_far: float,
    ) -> None:
        nonlocal best_revenue, best_take

        if current_excess + suffix_negative_excess[index] > 0:
            return

        if index == item_count:
            if current_excess <= 0 and revenue_so_far > best_revenue:
                best_revenue = revenue_so_far
                best_take = current_take.copy()
            return

        if upper_bound(index, remaining, revenue_so_far) <= best_revenue:
            return

        spend = spends[index]
        next_cs_contacts = current_cs_contacts + cs_contacts[index]
        if spend <= remaining and next_cs_contacts <= MAX_CS_CONTACTS:
            current_take[index] = True
            search(
                index + 1,
                remaining - spend,
                next_cs_contacts,
                current_excess + excess_contacts[index],
                revenue_so_far + revenues[index],
            )
            current_take[index] = False

        search(index + 1, remaining, current_cs_contacts, current_excess, revenue_so_far)

    search(0, BUDGET, 0, 0, 0.0)
    return best_take


df = pd.read_csv('marketing_campaign_estimations.csv', sep='\t').copy()
df['revenue_per_spend'] = df.revenue / df.marketing_spending
df = df.sort_values('revenue_per_spend', ascending=False).reset_index(drop=True)

try:
    best_take = solve_with_milp(df)
    solver_name = 'scipy_milp'
except ImportError:
    best_take = solve_with_branch_and_bound(df)
    solver_name = 'branch_and_bound_fallback'

selected_df = df.loc[best_take]

total_spend = float(selected_df.marketing_spending.sum())
total_revenue = float(selected_df.revenue.sum())
total_cs_contacts = int(selected_df.cs_contacts.sum())
total_users = int(selected_df.users.sum())
revenue_millions = total_revenue / 1_000_000
budget_slack_millions = (BUDGET - total_spend) / 1_000_000
contact_rate = total_cs_contacts / total_users
rate_headroom = MAX_CONTACT_RATE - contact_rate

assert total_spend <= BUDGET + 1e-6, f"Budget violated: {total_spend}"
assert total_cs_contacts <= MAX_CS_CONTACTS, f"CS contacts violated: {total_cs_contacts}"
assert (
    CONTACT_RATE_DENOMINATOR * total_cs_contacts
    <= CONTACT_RATE_NUMERATOR * total_users
), f"Contact rate violated: {contact_rate}"

print(f"METRIC revenue_millions={revenue_millions:.4f}")
print(f"METRIC spend_millions={total_spend/1_000_000:.4f}")
print(f"METRIC budget_slack_millions={budget_slack_millions:.4f}")
print(f"METRIC segment_count={len(selected_df)}")
print(f"METRIC cs_contacts={total_cs_contacts}")
print(f"METRIC cs_headroom={MAX_CS_CONTACTS - total_cs_contacts}")
print(f"METRIC contact_rate={contact_rate:.6f}")
print(f"METRIC rate_headroom={rate_headroom:.6f}")
print(
    f"# solver={solver_name} segments={len(selected_df)} spend={total_spend/1e6:.2f}M "
    f"cs={total_cs_contacts} rate={contact_rate:.4%}"
)
