# Reconciliation: REA pass vs. round-one Python pass

Round one: `docs/reconstruction-report-v1-python.md`, `legacy/docs/*-v1.md`, `legacy/data/*.json`.
REA pass: capture Evidence `ev_579388377fcb…`, application Evidence `ev_7131e083513834ff…` (and
`ev_a30fcf315cea…` at default limits), environment `ev_5ca070c9…`/`ev_fa72646a…`/`ev_9ee5c318…`,
coverage verdicts in `evidence/private/rea/07_coverage/`.

## ✅ Confirmed

| Round-one claim | REA-pass evidence |
|---|---|
| 102 network entries, 70 recognized service records, 31 service/method pairs | `inspect_web_network_capture`: 102/102 records retained; ingest finds the same 70 records and 31 pairs |
| Transport is `POST /mpl/web7/backend-json.php?<Service>` with `{method, parameters}` | Now located in code: `core.js:5:7918` (`JSON.stringify({method:F,parameters:Y})`), `core.js:5:8575` (`backend-json.php?`), REA module `57080` |
| `quarterlyCapacity(s) = s × maxDays` is exact client arithmetic | `sstudent.js:4:744662`, REA module `84654` (round one: col 744663 1-based) |
| `averageProductivity`, `cash`, `projectDemandNextQuarter`, `projectedCash`, `totalCash`, `warnMinPrice`, `warnMaxPrice` are server-opaque | Still no client formula; none is computed client-side |
| No write/finalization request was *observed* in the capture | REA capture: all 70 RPC records are `view`, `gs` or `studentsOnline` |
| Revenue, unit sales, market share, COGS, operating profit and scorecard are absent from the six Q1 pages | Confirmed; their screens (`Sales`, `MarketShare`, `IncomeStatement`, `BalancedScorecard`, …) are registered but were not captured |

## 🆕 New findings

| Finding | Evidence |
|---|---|
| **Service name = screen class name.** 310 class registrations → 252 screen services (124 decision incl. 1 finalization, 128 reports) | `DecisionFactory.getDecision` `sstudent.js:1:182053`; `service=u` `:1:188141`; REA module `8939` |
| Base-class contracts for every decision screen: `view`, `modify` (lock), **`calculate`**, `save`, `cancel`, `removeLock`, `validateLock`, `prolongLock` with exact parameter shapes | `sstudent.js:1:188378…194103`, module `8939` |
| **What-if channel**: `calculate(user, draftDecisions, 0)` returns `checkResult` + `calculateResult` without saving. Triggered by a 500 ms debounced input binding or a Calculate button, and only in modify mode. 48 screens | `:1:192346`, `:1:192874`, `:1:192940`; 97 `bindCalculate` sites; planner `modifyModeButtons` include `calculate` |
| `WrapUp` (menu "Submit") is the finalization path: `wrap()` → `calculate` → `save {wrapped:true, targetSegments}`; `unwrap` saves `{wrapped:false}` | `WrapUp` class, REA module `68220` |
| 30 literal RPC methods via REA endpoint discovery, incl. `GameInfo.liveProForma`, `wrapupStatus`, `teamMonitor`, `Settings.saveQuarterScreenSettings`, `StudentInit.runFinish` (exit beacon) | REA `discover-static-endpoint` nodes |
| 14 business-relevant client formulas (65-day quarter, effective capacity, share %, utilisation, commission) | `docs/calculation-map.md` |
| Full Q1 menu tree with parents (62 items, 27 marked decision screens) | aria-level structure in the saved HTML; joined to class names |
| `warnMinPrice/warnMaxPrice` come from `Stock.view` (stock issue price) and are **never referenced** in client JS | 0 occurrences in both bundles; round-one entry 94 = `Stock` |
| No numeric client-side bounds on any input; all validation is server `checkResult` | control option survey (`size`, `rows`, `maxlength` only) |
| Production cost model is reachable before save: `FactorySimulation` per-brand material/labor/overhead/prodCost | `writeCalculate` of module `19060` |
| REA AgentEnv bundle of the Q1 capture (replay) | `evidence/private/rea-env` |

## ⚠️ Contradictions with round one

| Round one said | REA pass shows | Resolution |
|---|---|---|
| `dailyCapacity`, `effectiveCapacity` are "UNKNOWN review candidates" | Both are exact pure arithmetic (`s/maxDays`, `s×e/100`) | Round-one heuristic under-classified them; now EXACT_CLIENT_FORMULA |
| Repeated `writeCalculate` handlers were "calculation candidates" | They **render** server `calculate` results. They compute nothing (apart from `/65` display conversions) | Reframed as calculate outputs in the metric catalog |
| "No WRITE, validation, calculation-trigger, or finalization contract was verified" (read as: no known write surface) | Statically, every decision screen has `save`/`modify`/`cancel` plus `WrapUp` finalization and a `calculate` trigger | Not *observed* (still true), but the write surface is known: see `docs/rpc-contract.md` |
| "The HTML navigation parent tree is partial and is not filled by inference" | Parents are recoverable exactly from `aria-level` order in the rendered tree | Now complete for Q1 (not inferred) |
| `GameInfo.studentsOnline` is UNKNOWN | Client uses it for the chat presence indicator (`updateOnline`) | READ_CANDIDATE (still never called by us) |
| Six resources / modules | 310 registered screens; six were *captured pages* | Different denominators |

## ❓ REA cannot decide (needs runtime evidence or is out of reach)

| Question | Why |
|---|---|
| Does `calculate` persist anything server-side? Does `modify` change anything besides the lock? | Static code can't show server effects. Test in EXP-01. |
| Do ProForma projections recompute from *saved* current-quarter decisions? | INFERRED: `view` sends no decisions and drafts are client-only. Test in EXP-09. |
| Which registered screens appear in which quarter/course | Server-driven `leftMenuItems`; only Q1 captured |
| Any server formula (demand, cost, finance) | No server code is delivered; only behavioural identification is possible |
| Semantic data flow inside `sstudent.js` | REA semantic coverage for that file is "limited" even with raised limits (parent result budget). Literal/property seeds matched only `core.js`. |
| URL routes | REA `javascript-routes` is empty: the app routes by resource name, not URL |
| Reconstruction coverage | REA `evaluate_reconstruction_coverage` → **unknown** for `rpc-contracts` (31 claims), `decision-catalog` (18), `output-catalog` (30): `verifier-missing` on every claim + `package-proof-unknown`. Needs runtime verifiers, which this inventory-only project doesn't have |
