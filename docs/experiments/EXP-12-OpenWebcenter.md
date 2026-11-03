# EXP-12 · OpenWebcenter.change (open a web sales center): verified

2026-11-03 · Quarter 1 · autonomous run in a REA MCP session behind guard v5. The experiment tier allowed only
OpenWebcenter. Presence check before the run: 0 others online. Private Evidence: `evidence/private/auto/` (working name
`exp04_owc`).

## Design

One decision field (`change`, one checkbox for the single region). Click on → read → click off → read. Clicks were
scoped to `#wscTable` (the live pro-forma gadget's checkboxes lie outside it). Edit mode was re-confirmed after each click.

## Method sequence

`view → modify → calculate ×2 → cancel → view → TacticStrategyLinksSalesChannel.view → view`. No `save`; 0 blocked
requests; no dialog; URL unchanged in edit mode. A reload afterwards showed no stored change and view mode.

## Result

Opening: `Δ totalSetup = setupCost(region)`, `Δ totalLease = 0`, `Δ totalClose = 0`, `Δ total = Δ totalSetup`.
Turning it off returns all totals to 0. Same rule as EXP-11 (store opening). Residual 0 on 2 points.
**Evidence strength: moderate** (one region, but the identical rule on a second screen).
