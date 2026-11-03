# Calculation map

## Exact client arithmetic

The static analyzer found two exact records for the same `quarterlyCapacity(s)` client function in `client_asset_002.js`:

| Expression | Source location | Classification |
|---|---|---|
| `s*this.maxDays` | line 4, column 744663 | `EXACT_CLIENT_FORMULA` |
| `s*this.maxDays` | line 4, column 759862 | `EXACT_CLIENT_FORMULA` |

These are two source occurrences from one delivered client asset. The expression is pure arithmetic in the client body. It establishes a client-side quarterly capacity calculation only; it does not establish the server's production, utilization, or financial formula. Source references are local evidence aliases, and no downloaded JavaScript bundle is published.

## Unresolved client function candidates

The static name heuristic generated 118 review records across 38 unique function names. It includes functions such as `getDemandMultiplier`, `getProductivityTable`, `getRFPIndex`, `dailyCapacity`, `effectiveCapacity`, and repeated `writeCalculate` handlers. These are `UNKNOWN` candidates, not verified calculations: a name can describe a handler or table lookup, and the public inventory intentionally contains no candidate bodies. No candidate is classified as a complete client transformation of server data from the current static pass. The records and source offsets are in `data/client_calculations.json` under `review_candidates`.

## Server opaque numeric outputs

Seven numeric response fields match the metric vocabulary but have no identified decision variable in their captured request schemas: `averageProductivity`, `cash`, `projectDemandNextQuarter`, `projectedCash`, `totalCash`, `warnMaxPrice`, and `warnMinPrice`. They are classified `SERVER_OPAQUE`; no formula is asserted. Their response paths and RPC evidence aliases appear in `data/calculation_map.json`.

Common business outcomes such as revenue, unit sales, market share, COGS, operating profit, and scorecard fields were not observed as numeric responses in these six Quarter 1 pages. For this evidence set they remain `UNKNOWN`, rather than being marked opaque as if they had been observed.

Other complex client functions that resemble calculations were not treated as exact formulas because they depend on lookup tables, branches, or calls. The public calculation record contains only the two pure arithmetic expressions. It does not equate accounting identities such as revenue to any observed Marketplace implementation.
