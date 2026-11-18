# Q2 factory policy decision lab (read-only)

This module extends Q2 forecasting with an offline manufacturing-policy comparison. It is deliberately not a reimplementation of the Marketplace PHP backend.

## Inputs, ownership and evidence

All company/team and financial amounts must come from the operator's local private JSON under the gitignored evidence/private/ directory. Never commit captured HARs, credentials, team IDs, real quotes, or raw simulation responses.

- Sales supplies demand by brand, offered prices and store/web staffing. The policy model never silently substitutes guessed demand for a missing Sales forecast.
- HR supplies projected worker productivity; the game may update it after worker compensation is saved.
- Manufacturing extracts observed OperatingCapacity chart values (daily capacity to labor/overhead per unit), Overtime productivity points, and CostOfProduction quote points.
- Finance supplies Q1 bank cash, financing, certificate-of-deposit withdrawals, operating costs and proposed store/printer capital spending. Draft equity is not settled cash.

The module src/marketplace_sim/factory_policy.py exposes FactoryEvidence, Policy, PolicyAssumptions and simulate. It makes no network requests or writes.

## Correct cost semantics

The CostOfProduction table's x-axis is the TOTAL number of units produced across all brands. Every brand's quote uses the same company total output, while the bike-specific row determines the unit cost.

Natural cubic interpolation in log(volume)-log(cost) matches the existing marketplace_sim.cost_curve family. Predictions below the first observed quote are extrapolations, not validated results.

The game's OperatingCapacity chart supplies labor/overhead curves, but does not reveal exactly how those figures combine with the CostOfProduction quotes. The surrogate adds only a WEIGHTED DIFFERENCE relative to a reference operating capacity, not the complete quoted cost plus complete labor/overhead again. Rerun sensitivity with chart_cost_weight between 0 and 1.

Idle cost, overtime wage exposure and lost-sales goodwill effects are hypotheses, explicitly adjustable. Do not describe them as verified PHP formulas.

## Bootstrap and policy comparison

1. Create candidate daily operating capacities from 8 to the observed fixed daily capacity and maximum authorized overtime from 0 to 4 hours.
2. Use IDENTICAL Sales demand draws for every policy (paired comparison). Evaluate unit sales, lost sales, cash, idle capacity and overtime actually used.
3. Generate demand uncertainty using the existing ASSUMPTION-BASED parameter bootstrap. Resample the synthetic outcomes for Monte Carlo stability, clearly distinguishing it from empirical confidence intervals.
4. Compare scenarios with the staff currently counted by Sales, the sales-only headcount interpretation, a higher-demand case and Q3 growth assumptions. Perform idle-cost, overtime-cost and goodwill-weight sensitivity.
5. Verify the leading policies in the OFFICIAL Marketplace Production Simulation at 25%, 50%, 100%, 150% and an extreme demand case. Record actual production, stock-outs, overtime, per-brand costs, excess-capacity cost and ending bank cash.
6. Verify >=500,000 bank cash at normal demand, >=300,000 at half demand, and worst-case survivability in OFFICIAL Pro Forma. Count a certificate of deposit as bank cash only if a withdrawal was explicitly recorded.
7. Do not commit future printers or stores before cash stress tests pass.

## Synthetic usage example (not real Marketplace figures)

    from marketplace_sim.factory_policy import FactoryEvidence, Policy, PolicyAssumptions, simulate
    evidence = FactoryEvidence(
        fixed_daily=16, workdays=65, productivity_pct=70,
        overtime_hours=(0.,1.,2.,3.,4.),
        overtime_productivity_pct=(70.,69.,68.,66.,64.),
        daily_capacity_chart_x=(1.,8.,14.,16.),
        labor_per_unit_chart_y=(500.,150.,120.,180.),
        overhead_per_unit_chart_y=(500.,80.,50.,40.),
        quotes_by_brand={"Example": ((100.,900.),(500.,600.),(1000.,500.))},
    )
    hypothesis = PolicyAssumptions(
        starting_cash=300000., financing_cash=0., fixed_other_expenses=200000.,
    )
    case = simulate(
        evidence, Policy(14,4), forecast_by_brand={"Example":500},
        prices={"Example":1300.}, assumptions=hypothesis,
    )
    assert case["is_official_factory_result"] is False

Run: pytest -q tests/test_factory_policy_decision_lab.py

Before merging, run the complete pytest suite and python scripts/publication_gate.py. Never commit actual game-derived values or the team's private scenario results.

## Known gaps

- The reconstructed quarterly advance() engine does not establish the full official Q2 factory scheduling / overtime / demand behavior. This is a decision SURROGATE, not a cloned backend.
- The Q2 user HAR recorded the factory before final decisions, so no official scenario validation exists for this policy grid yet.
- Service and support staff may have reduced selling capacity; don't silently assume all support workers sell at the same rate.
- The six-to-one ratio between lost sales and idle slots and any future-sales goodwill penalty are unverified.
- No live game edits or quarter submissions are authorized by this workflow.
