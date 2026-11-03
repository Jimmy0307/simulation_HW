# Cost-side model (Phase 5)

`src/marketplace_sysid/cost_model.py` reproduces server `calculate` outputs from decision inputs plus parameters
published in each screen's own `view` (`data/parameter_catalog.json`). It contains **only relations verified against
the server**.

## Covered outputs and residuals

Residuals are computed privately (`evidence/private/parameters/cost_model_residuals.json`) against every measured
server result. The repository tests use synthetic numbers only.

| Function | Server output | Verified by | Points | Max abs residual |
|---|---|---|---|---|
| `cd_projection` | `CD.calculate.cd`, `.interest` (and rejection of negative deposits) | EXP-01 | 4 | 0 |
| `capacity_investment` | `FixedCapacity.calculate.expansion`, `.acquirement`, `.total` | EXP-02 | 9 | 0 |
| `quarterly_units` | displayed units/quarter (= units/day × 65) | EXP-02 + client code | 9 | 0 (on-screen check) |
| `store_opening_cost` | `OpenSalesOffice.calculate.totalSetup/totalLease/totalClose/total` (opening) | EXP-11 | 8 | 0 |
| `web_center_opening_cost` | `OpenWebcenter.calculate.*` (opening) | EXP-12 | 2 | 0 |
| `stock_issue` | `Stock.calculate.stockIncrease/sharesIncrease/stockTotal/sharesTotal` | `view` identity | 1 | 0 |

Total: 24 measured points (33 compared output values), all residuals exactly 0.

## Not yet covered (unverified, deliberately not modelled)

* **Outlets:** recurring lease of opened stores/web centers (`leaseCost` is in the view but was 0 in the opening
  quarter's `calculate`), closing cost (`totalClose`), `totalFactorySetup`, and additivity across several cities at once.
* **CD:** the `cd_prior` and `withdraw` terms (hypothesis `cd = prior + deposit − withdraw`); tiered rates.
* **Capacity with suppliers:** `acquirement` and supplier-specific costs (no supplier choice in Q1).
* **Production cost:** material, labor, overhead, changeover, excess capacity, overtime (FactorySimulation,
  ExtFactorySimulation, OperatingCapacity are not in the Q1 menu).
* **Finance:** income tax, interest charges, emergency loans, short/long-term loan interest. The rates are in the
  ProForma `view` (`taxRate`, `slRateMin/Max`, `ltRate5yr`, `elRateMin/Inc`, `inventoryTax`), but no UI path reaches
  their `calculate` (`autoCalculated`).
* **Marketing and sales force:** media, internet marketing, promotions, sales-force hiring and compensation.
* **Demand side:** entirely outside this model (needs later-quarter market-result screens; see `docs/parameter-catalog.md`).
