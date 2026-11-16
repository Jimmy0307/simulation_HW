# Q2 demand/bootstrap forecasting — conditional, not empirical

This adds a **parametric assumption-based bootstrap** to the reconstructed
Marketplace Simulation planning toolkit. The actual game's PHP demand model
is **not** available, and Q2 actual sales observations are not yet available.

## Workflow

1. Sales provides a *brand-specific* baseline forecast, staffing, prices, and
   store/web configuration. These are not filled from simulated demand.
2. Run an offline scenario bootstrap to test sensitivity and rough ranges.
3. Manufacturing chooses an indicative operating capacity, then verifies
   in the **official Factory Simulation**. Installed printer capacity and
   expected utilization are not interchangeable.
4. Finance reruns the **official Pro Forma Cash Flow** after each factory
   scenario at 100%, 50%, and 25% of Sales' demand. For the class's current
   Q2 decision rule: base cash >=500,000; 50% demand cash >=300,000;
   examine survivability at 25%.
5. Replace priors with empirical, market/quarter-blocked bootstrap after
   enough Q2+ real transactions exist. Hold out a future quarter.

## Method

- Sales per storefront worker: 30 + 40*Beta(2,6), a subjective distribution
  bounded 30–70 and with expectation 40, inspired by the teacher's sales
  guideline rather than fitted to game sales.
- Common macro shock: lognormal with log-SD 0.20 and mean one.
- Segment share: Beta with mean supplied from observed annual market potential
  and total pseudo-concentration 24. Within-segment brand share: Beta(6,6)
  when two brands are offered. **No brand-choice causal effects inferred**.
- Optional speculative online throughput: 70% chance active per online
  salesperson with Uniform(0,30) output. **The base case excludes online
  throughput** because there are no observed game sales for this channel.
- Costs: interpolate the server's own CostOfProduction **estimates** between
  observed quantity breakpoints on a log-volume scale. When fewer units per
  brand are forecast than the first observed break, extrapolate explicitly
  and apply a larger hypothetical lognormal model-risk multiplier (log-SD
  0.18 vs 0.08 at known-quote levels). Do not present extrapolated costs as
  verified Marketplace costs.
- Finance: current starting bank + **draft**, unconfirmed Q2 financing +
  current interest estimate - separately modeled fixed expenses + revenue -
  estimated production cost. **Not official Pro Forma and not an actual cash
  forecast validated by the backend.**
- Each result reports 20,000 reproducible conditional samples by default:
  P05, P50 and P95. **These are not empirical 90% confidence intervals**.
- Always compare financing with and without Q2 draft equity; an equity field
  visible in Q2 does not mean that cash is already settled.

## Execution (private data only)

Install NumPy without making it a dependency of the regular REA/MCP tools:

    python -m pip install -e ".[bootstrap,dev]"

Prepare private operator inputs at
`evidence/private/q2_bootstrap_inputs.json` with these fields:

- `plans`: array; each plan has `name`, `store_staff`,
  `web_staff`, and `brands`.
- Each brand in a plan has `name`, `type` (`M` or `S`), and
  `price`. Each segment must contain one or two offered brands.
- `cost_quotes`: mapping each offered brand name to server-estimate points
  `[[units, unit_cost], ...]` in ascending quantity order.
- `segment_mountain_weight`: value strictly between 0 and 1.
- `q1_bank_cash`, `q2_draft_equity`, `q2_interest_income`,
  `q2_fixed_cash_by_plan`: model inputs (not protected game state).
- Keep the raw game captures and values out of Git.

    python scripts/q2_bootstrap_forecast.py --inputs evidence/private/q2_bootstrap_inputs.json --output evidence/private/q2_bootstrap_results.json

The script writes only to a private directory; it never accesses the live
Marketplace website, edits decisions, or advances the simulation.

## Evidence boundary and review gates

- Official game estimates: quote table at multiple volumes and Q1 statements.
- Generated values: assumed bootstrap model, not independently observed demand.
- Missing evidence: brand-by-brand demand, price elasticity, ad effects, online
  productivity, quantity below the first server quote, and Q2 settlement.
- Check production feasibility at the **brand** level: splitting the same
  forecast across four brands can move each below quote support even if total
  quarterly factory volume appears sufficient.
- Compare the two-vs-four brand strategy at the **same sales staff and
  advertising levels**, otherwise volume differences are confounded.
- Full pytest, publication gate, and the actual post-Sales factory/pro forma
  refresh are required before recommending a merge or Q2 submission.

No private user-specific values or captured secrets are present in this file.
