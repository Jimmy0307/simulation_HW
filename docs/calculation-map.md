# Calculation map (v2, REA-based)

v1 (one formula, `quarterlyCapacity`) is in `legacy/docs/calculation-map-v1.md`.

Sources: REA application Evidence `ev_7131e083513834ff…`. Each expression comes from the text
of a REA webpack module whose bytes match REA's `source_sha256`. `rea_ingest` extracted
219 multiplicative/divisive expressions in 47 classes. Most of them are chart and animation
geometry. The business-relevant expressions are below (`file:line:col` is the class registration).

## Exact client-side arithmetic (EXACT_CLIENT_FORMULA)

| # | Formula | Where | REA module |
|---|---|---|---|
| 1 | `quarterlyCapacity(s) = s × maxDays`; `dailyCapacity(s) = s / maxDays` | `OperatingCapacity` `sstudent.js:4:743870`, `OperatingCapacityRegional` `:4:758665` | 84654, 33031 |
| 2 | `effectiveCapacity(OC, productivity) = OC × productivity / 100` | same two classes; `ExtFactorySimulation(Regional)` | 84654, 33031, 36161, 52772 |
| 3 | The quarter has **65** production days (literal `65` in `FixedCapacity`, `OperatingCapacity`, `ExtFactorySimulation`, `DemandProjection*`; `maxDays` elsewhere) | `FixedCapacity` `:4:429360` | 63171 |
| 4 | Fixed capacity: units/quarter = units/day × 65; capacity cost per unit = option cost / units; projected demand per day = `projectDemandNextQuarter / 65` | `FixedCapacity` | 63171 |
| 5 | Planned production capacity = `plannedProduction × 65 × projectedWorkersProductivity / 100` | `ExtFactorySimulation` `:4:298040` | 36161 |
| 6 | Demand projection per day = `brandDemand / 65`; operating capacity needed per day = `operatingCapacityNeeded / 65` | `DemandProjection` `:4:211744`, `DemandProjectionRegional` `:4:228727` | 31191, 4594 |
| 7 | Regional demand share % = `demand × 100 / lqTotalDemand` | `DemandProjectionRegional` | 4594 |
| 8 | Market share % = `segment demand × 100 / segment total demand`; overall `f × 100 / total` | `MarketShare` `:4:586525` | 23142 |
| 9 | Supplier market share % = `demand / totalDemand × 100` | `MarketShareSupplier` `:4:591565` | 72122 |
| 10 | Channel share % = `soDemand × 100 / total`, `webDemand × 100 / total` | `ChannelDemand` `:4:42713` | 38869 |
| 11 | Capacity utilisation % = `operatingCapacity × 100 / fixedCapacity` | `FactoryLocations` `:4:365190` | 16235 |
| 12 | Web commission cost (last quarter) = `lqCommission × unitsSold` | `WebTraffic` `:4:1084026` | 58010 |
| 13 | Quarterly CD rate = `annual rate / 4` (display) | `CD` `:4:38786` | 14146 |
| 14 | Two-quarter R&D cost display = `twoQuarterCost × 2` | `FeatureRD` `:4:400758` | 77969 |

These are client expressions only. They do not prove the server uses the same arithmetic,
although items 1–6 are shown next to server values in the same tables and are good candidates for
an equality check during EXP-02.

## Server-computed, reachable before save (what-if, `calculate`)

48 decision screens can request `<Service>.calculate(user, draftDecisions, 0)`. They return
`checkResult` (validation) and `calculateResult`. Examples, with output names from `writeCalculate` and the capture:

| Screen | Inputs | Server outputs |
|---|---|---|
| `CD` | `deposit`, `withdraw` | `cd`, `interest` |
| `ShortTermLoan` | `borrow`, `repay` | `shortTermLoan`, `interest`, `quarterlyRate`, `annualRate` |
| `FixedCapacity` | capacity option, `supplier` | `acquirement`, `expansion`, `total` |
| `OpenSalesOffice` / `OpenWebcenter` | `change` per city | `total`, `totalSetup`, `totalLease`, `totalClose`, `totalFactorySetup` |
| `FactorySimulation(Regional)` (Calculate button) | `estimatedDemand`, `estimatedPrice` | per brand `unitsProduced`, `material`, `labor`, `overhead`, `prodCost`, `avgCost`, `endCost`; `chover*`, `excess*`, `production*`, `total*` |
| `ExtFactorySimulation(Regional)` | OC, productivity, hours, planned production, … | the above plus `overtime*`, `plannedOC`, `operatingCapacityNeeded` |
| `ProFormaDivisionProfitability` | `estimatedDemand`, `estimatedPrice`, `demandMultiplier` | `items` (division P&L lines), `brandsForSale` |
| `OperatingCapacity` | `operatingCapacity`, `projectedWorkersProductivity` | `directLaborCPU`, `overheadCPU`, `costToChangeOperatingCapacity`, … |
| `HireSalesPeople` / `HireWebSalesPeople` | `sf`, `support` | `total`, `hireCost`, `employCost`, `layOffCost` |
| `LocalMedia` / `RegionalMedia` | `inserts` | `adsCost`, `mediaCost`, `regionCost` |
| `SpecialPrograms` | `contest`, `demoKit`, `training` | budgets, `newSalesForce`, `totalSalesForce` |
| `ProFormaCashFlow` | projection cells | `items` (calculated rows) |

Full list: `docs/metric-catalog.md` (source `calculate`).

## Server-opaque outputs (no client formula, no what-if path)

* Demand / unit sales / market share inputs: `Sales.staticData.*Sales`, `MarketShare.staticData.demand`.
* Income statement, balance sheet and cash flow rows: `FinanceReport` / `ProFormaFinance` `staticData.sections[].items[]`.
  Row names come from the server, and ProForma `fill` columns are labelled "projection".
* `FixedCapacity.dynamicData.projectDemandNextQuarter`, `averageProductivity`, `minimumOperatingCapacity`.
* Cash fields in the Q1 capture: `CD.view → dynamicData.projectedCash`, `FinancialResources.view →
  staticData.totalCash / cash`, `CD.view → staticData.cash`.
* `warnMinPrice` / `warnMaxPrice` come from `Stock.view → staticData` (Closely Held Stock), so they
  bound the **stock issue price**, not product prices. They are **not referenced anywhere in the
  client JavaScript** (0 occurrences in `sstudent.js` and `core.js`). Any warning is produced
  server-side (returned through `checkResult.errors`) or by a template outside these bundles.
