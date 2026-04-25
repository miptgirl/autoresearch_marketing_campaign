import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

BUDGET = 30_000_000.0
MAX_CS_CONTACTS = 5_000
CONTACT_RATE_NUMERATOR = 21
CONTACT_RATE_DENOMINATOR = 500
MAX_CONTACT_RATE = CONTACT_RATE_NUMERATOR / CONTACT_RATE_DENOMINATOR

users, cs_contacts, spend, revenue = np.loadtxt(
    'marketing_campaign_estimations.csv',
    delimiter='\t',
    skiprows=1,
    usecols=(2, 3, 4, 5),
    unpack=True,
)

constraints = LinearConstraint(
    np.vstack(
        [
            spend,
            cs_contacts,
            CONTACT_RATE_DENOMINATOR * cs_contacts - CONTACT_RATE_NUMERATOR * users,
        ]
    ),
    -np.inf,
    [BUDGET, MAX_CS_CONTACTS, 0],
)

result = milp(
    c=-revenue,
    constraints=constraints,
    bounds=Bounds(0, 1),
    integrality=np.ones(len(revenue), dtype=int),
)
if not result.success:
    raise RuntimeError(f"MILP solver failed: {result.message}")

selected = np.rint(result.x).astype(bool)
total_spend = float(spend[selected].sum())
total_revenue = float(revenue[selected].sum())
total_cs_contacts = int(cs_contacts[selected].sum())
total_users = int(users[selected].sum())
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
print(f"METRIC segment_count={int(selected.sum())}")
print(f"METRIC cs_contacts={total_cs_contacts}")
print(f"METRIC cs_headroom={MAX_CS_CONTACTS - total_cs_contacts}")
print(f"METRIC contact_rate={contact_rate:.6f}")
print(f"METRIC rate_headroom={rate_headroom:.6f}")
print(
    f"# solver=scipy_milp segments={int(selected.sum())} spend={total_spend/1e6:.2f}M "
    f"cs={total_cs_contacts} rate={contact_rate:.4%}"
)
