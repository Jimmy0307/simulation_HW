# Calculate-screen triage (Phase 2)

Updated 2026-11-03 after the Phase 3 read-only capture and the Phase 4 experiments. Scope: the 48 screens with a
what-if path (`data/decision_catalog.json`) plus `Stock`, whose `view` also returns a `calculate` block.

* **A**: the `calculate` result follows from parameters already in the screen's own `view` (plus the decision).
  No further experiment is needed; the formula is in `src/marketplace_sysid/cost_model.py`.
* **B**: the result contains quantities absent from `view`, or interacting fields, so an experiment is needed.
* **C**: no `view` captured yet (screen not in this quarter's menu), or no allowed UI path.

## Summary

| Class | Count | Screens |
|---|---|---|
| A (verified) | 5 | CD, FixedCapacity, OpenSalesOffice*, OpenWebcenter*, Stock |
| B (open) | 0 | The two Q1 B screens (OpenSalesOffice, OpenWebcenter) were resolved by EXP-11/EXP-12 and are now A, for the opening case |
| C, no UI path | 1 | ProFormaCashFlow (`autoCalculated = true` → client removes Modify) |
| C, not in Q1 menu | 41 | see ranking below |
| not applicable | 1 | CompanyName (text field; `calculate` returns no numeric output) |

\* Opening an unopened outlet only. Closing (`totalClose`), the recurring lease of opened outlets and
`totalFactorySetup` stay **unverified**; they need a quarter in which an outlet is already open.

## A: derivations and evidence

| Screen | Derivation from `view` | Evidence | Strength |
|---|---|---|---|
| CD | `cd = staticData.cd + deposit − withdraw`; `interest = cd × staticData.rate / 4 / 100`; negative input → `checkResult.ok=false` | EXP-01, 4 points, residual 0 | moderate (deposit term only) |
| FixedCapacity | `expansion = total = capacityOptions[units = increase].cost`; `acquirement = 0` (no supplier choice); display `units × 65` | EXP-02, 9 points, residual 0 | strong |
| OpenSalesOffice | opening: `totalSetup = Σ cities[change ∧ ¬opened].setupCost`; `totalLease = totalClose = 0`; `total = Σ` | EXP-11, 8 points, residual 0 | strong for opening |
| OpenWebcenter | same rule over `regions[*]` | EXP-12, 2 points, residual 0 | moderate (1 region) |
| Stock | `stockIncrease = Σ shares × price`; `sharesIncrease = Σ shares`; `stockTotal/sharesTotal = staticData.* + increase` | `view` identity, 1 point, residual 0 | moderate |

## C, no UI path: ProFormaCashFlow

The `view` exposes the finance rates (`taxRate`, `cdRate`, `inventoryTax`, `ltRate5yr`, `slRateMin/Max`,
`elRateMin/Inc`) and the statement structure: rows with `sign` and `calculated` flags, subtotals `e_nocf`, `e_tia`,
`e_tfa` and end `cash`. The subtotals are sign-weighted sums of their section rows (accounting identity, A). The
server-calculated rows (`income_taxes`, `interest_income`, `interest`, emergency loan borrow/repay) cannot be probed:
with `autoCalculated = true` the client hides Modify, so no allowed action reaches `calculate`. They become observable
through ProForma projections after saved decisions (P in the matrix) or in later quarters.

## C, not in the Q1 menu: ranked by expected information value

These screens are registered in the client but not offered in Quarter 1. "Expected" is the likely class once their
`view` is captured, judged from the `writeCalculate` outputs versus what a view of that kind usually carries.

| Rank | Screen | Inputs | `calculate` outputs (examples) | Expected | Why it matters |
|---|---|---|---|---|---|
| 1 | FactorySimulation / ...Regional | estimatedDemand, estimatedPrice (Calculate button) | per brand material, labor, overhead, prodCost, avgCost; changeover, excess capacity | B | Unit production cost, the largest opaque cost block |
| 2 | ExtFactorySimulation / ...Regional | OC, productivity, hours, planned production, … | the above plus overtime and OC needed | B | Labor/overtime cost structure |
| 3 | OperatingCapacity / ...Regional | operatingCapacity, projectedWorkersProductivity | directLaborCPU, overheadCPU, costToChangeOperatingCapacity | B | Cost per unit vs capacity utilisation |
| 4 | ProFormaDivisionProfitability | estimatedDemand, estimatedPrice (Calculate button) | division P&L items | B | Accounting from price × volume to profit |
| 5 | HireSalesPeople / HireWebSalesPeople | sf, support | hire, employ and layoff cost | B or A | Sales-force cost |
| 6 | LocalMedia / RegionalMedia | inserts | adsCost, mediaCost, regionCost | A likely (published price lists) | Advertising cost |
| 7 | ShortTermLoan / LongTermLoan | borrow, repay | interest and the applied loan charges | B (charge may depend on amount; ProForma view lists short-loan bounds) | Financing cost |
| 8 | SpecialPrograms | contest, demoKit, training | budgets, sales force totals | A likely | Sales promotion cost |
| 9 | Overtime / ...Regional | hours | overtime cost and capacity | B | Short-run capacity cost |
| 10 | SearchEngineMarketing / SimpleInternetMarketing / DesignWebPage | budget, maxBid, keywords | totalBudget, adsCost | B (auction) | Internet marketing cost |

Others (C): DemandProjection* (operator's own estimates, not a server model), Promotions, Dividends, FeatureRD,
ImproveChangeover, ImprovementActions, InspectQuality, InvestInActions, ProductionControlSystem, SellUnwantedInventory,
PaymentToPartners, SupplyChainInformationSystem, WarehouseLocationRegional, FactoryLocationRegional, WebProductivity,
WebTraffic, SocialMedia, BuyMarketResearch, SourceStudy, VarianceStudy.

**For the next quarter:** capture each newly visible screen's `view` (read-only), re-run
`python -m marketplace_sysid.parameters`, and re-triage. Many C items may turn out to be A once their rate tables show up.
