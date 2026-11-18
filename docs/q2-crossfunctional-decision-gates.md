# Q2 cross-functional decision gates

This release adds pure, synthetic-testable input guards to the factory-calibrated Marketplace simulator, without publishing any team's private captures, demand values, costs, or HAR.

## Boundary

The functions in `src/marketplace_sim/q2_decision_gates.py` are **decision-support utilities**, not a replacement for the game PHP, its ad/price demand response, Production Simulation, or Pro Forma.

- `sales_equivalent_forecast`: compares full sellers versus fractionally selling support staff. It does **not** infer game staffing productivity.
- `ad_budget`: tests the conservative **combined ad-design + media-placement cap**. Validate which specific fee categories count in the game.
- `price_change_break_even_uplift` and `incremental_units_to_cover_spend`: calculate thresholds; they do not predict a marketing response.
- `proforma_cash_gates`: requires 100%, 50%, 25% scenario cash before returning a pass; even provided values retain a source-not-verified marker.

## Procedure

1. Read brand-level prices and forecast from Sales. **Do not** treat as realized demand.
2. Use `mpsim factory` and the latest captured private pack for the manufacturing calculation. Record if the inputs are **observed**, **interpolated**, or **assumed**.
3. Compare several capacity and authorized overtime options using the **same demand draws**. Any bootstrap over simulated data is conditional on priors, not a confidence interval from real market sales.
4. Calculate the advertising cap, price-change break-even, HR salary uplift break-even, and web-investment uplift threshold. Do not invent price/ad elasticities.
5. Enter approved team decisions in the official game. Re-run Production Simulation and **Pro Forma Cash Flow** with 100%, 50%, and 25% demand, recording bank cash separately from certificates of deposit.
6. Do not approve next-quarter site/machine commitments on the strength of a model's unverified cash estimates.

The team-specific complete scenario report, results, and code with game numbers should stay in the user's private working environment, never a public repository.

## Safety, merge gates and limitations

Run: `pytest -q tests/test_q2_decision_gates.py`; then full `pytest`, publication/secrets gate, and inspect diff before merge. No live game writes.

Historical Q1 bank cash may be a verified starting balance. Any Q2 equity field must be explicitly verified as available cash. The absence of a Q2 sales observation prevents an empirical demand bootstrap and prevents confirmation of the correct ad/price/HR causal response. Only official game simulations can close the operating-capacity, overtime and cash validation gates.
