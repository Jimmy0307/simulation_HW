# Quarterly runbook (public; contains no data)

## When to run

Each quarter, **after the new quarter opens and before the team makes its decisions**. Running it later still works,
but its main value is decision support.

## What the operator does

1. Ask Claude Code to run the per-quarter command (`/quarter <N>`, a local command file kept out of the repository).
2. When a browser window opens, **log in yourself** and go to the company's main screen. That is the only manual step:
   the agent never types credentials and never saves or submits.
3. Wait for the report. If it shows a red block (a hard stop), follow its instructions; locks expire on their own and
   cancel, never save.

## What the run does (summary)

* Confirms the actual quarter from the page (the actual quarter wins over the argument).
* Starts the network guard ([data/guard_policy.json](../data/guard_policy.json)) and runs its two-phase self-test.
* Captures newly opened screens **read-only** (especially competitor, market-share, scorecard and standings reports).
  It never enters Submit.
* Re-extracts parameters, re-triages calculate screens, and runs what-if experiments on screens that need them, with
  teammate-presence checks and Cancel-only restore.
* Appends whatever competitor/market data is available to the **private demand panel**. After 2 quarters it assesses
  identifiability; after 3 it fits a demand model, validates it on a held-out quarter, and only then promotes demand from
  `literature` to `estimated` (until then demand runs at `literature` level: published forms, uncalibrated
  coefficients; upgrade path in `docs/demand-model-spec.md` §6).
* Rebuilds the private pack with `mpsim build-pack --out evidence/private/model --quarter-label Q<N>`, which snapshots it,
  diffs it against the previous quarter (value-free summary on screen, full diff in `evidence/private/model/diffs/`)
  and raises red flags for verified modules whose parameters changed. Those modules are re-verified before their
  `[V]` lines are trusted again.
* Updates the private save to the real state and writes a private brief for the quarter.

## How to read the report

| Field | Meaning |
|---|---|
| QUARTER | Actual quarter detected |
| NEW_PAGES | Screens captured for the first time this quarter |
| DEMAND_PANEL | Quarters of market/competitor data collected so far |
| MODEL_STATUS | Source level of each engine module (verified / derived / estimated / placeholder) |
| EXPERIMENTS | What-if experiments: status, relation found, evidence strength |
| PARAM_DIFF | Parameter changes vs last quarter (count, red flags, verified modules to re-verify; no values) |
| BLOCKED_REQUESTS | Anything the guard blocked (expected: self-test only) |

Use `mpsim compare` on the private save to compare candidate plans, and always read the source-level marks: only `[V]`
and `[D]` numbers are measured or exact.

## Fallback: a quarter saved with the browser (plain HAR)

When the team saved the screens with the browser's DevTools instead of an REA run:

```powershell
# keep the HAR under evidence/private/ (git-ignored)
.\.venv\Scripts\mpsim.exe build-pack --out evidence/private/model --har evidence/private/har/qN.har --base evidence/private/model --quarter-label QN
.\.venv\Scripts\mpsim.exe cost-curve --params evidence/private/model          # leave-one-out check of the cost table
.\.venv\Scripts\mpsim.exe reconcile --params evidence/private/model --har evidence/private/har/qN.har `
    --quarter N-1 --plan evidence/private/plans/qN-1-actual.yaml [--save evidence/private/saves/start-qN-1.json] `
    --out evidence/private/reconcile/qN-1-values.json                              # statuses on screen, values private
```

Open at least: the three statements (last quarter), CostOfProduction, ModifyBrand, OpenSalesOffice, OpenWebcenter,
HireSalesPeople, HireWebSalesPeople, RegionalMedia, CD, Stock, FixedCapacity, ProFormaCashFlow.
