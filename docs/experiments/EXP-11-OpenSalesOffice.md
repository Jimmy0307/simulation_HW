# EXP-11 · OpenSalesOffice.change (open a store): verified

2026-11-03 · Quarter 1 · autonomous run (operator-authorised) in a REA MCP session (`capture_browser_scenario` +
`export_evidence_bundle`) behind guard v5. The experiment tier allowed only OpenSalesOffice. Teammate presence check
before the run: 0 others online. Private Evidence: `evidence/private/auto/` (working name `exp03_oso`).

## Design

One decision field (`change`, a checkbox per city, 4 unopened cities in one region). OFAT: for each city, click on →
read `calculate` → click off → read. All other cities stayed at baseline (unchanged). Clicks were scoped to
`#soTable_1`; each target's id, value attribute and row label were logged before the run. Edit mode was re-confirmed
after every click.

## Method sequence

`view → modify → calculate ×8 → cancel → view → (re-navigate) TacticStrategyLinksSalesChannel.view → view`.
No `save`; 0 blocked requests; no dialog; URL unchanged during edit; all steps completed. A separate reload afterwards
showed no stored change, Modify enabled, Save/Cancel disabled and no lock text.

## Result

| Toggle | Δ totalSetup | Δ totalLease | Δ totalClose | Δ total |
|---|---|---|---|---|
| city k on (k = 1…4, each alone) | = `setupCost` of city k (view) | 0 | 0 | = Δ totalSetup |
| city k off | back to 0 | 0 | 0 | 0 |

**Relation:** opening unopened stores costs `Σ setupCost` in the decision quarter. `leaseCost` (also in the view) is
**not** part of this quarter's `calculate`. `total = totalSetup + totalLease + totalClose`. `totalFactorySetup` stayed
null. Residual 0 on 8 points. **Evidence strength: strong** for opening.

**Not determined:** whether the lease is charged from the next quarter, the closing cost (`totalClose`), and whether
opening several cities at once is additive (only one city was on at a time; additivity is assumed in
`cost_model.store_opening_cost`).
