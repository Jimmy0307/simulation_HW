# Reconstruction report (v2, REA-based)

Branch `rea/full-reconstruction`. Round one is preserved as [`reconstruction-report-v1-python.md`](reconstruction-report-v1-python.md).
Tools: REA `rea-agents@6.8.0` on Node 24.22.2 (see [rea-pivot.md](rea-pivot.md)). All raw inputs and REA
Evidence stay in ignored `evidence/private/`.

> ## ⭐ What-if channel: **PRESENT, runtime-verified on `CD.deposit` (EXP-01, 2026-11-03)**
>
> Operator-run with teammate consent, behind a local network guard: `modify → calculate ×4 → cancel`, no `save`.
> The stored value was unchanged after Cancel and the lock was released. Interest = Δdeposit × displayed rate/4. See
> [experiments/EXP-01.md](experiments/EXP-01.md). Other screens remain static evidence only.
>
> Every decision screen inherits `calculate(user, draftDecisions, 0)` from the shared `Decision` base class
> (`sstudent.js:1:192346`, REA module `8939`). It sends the **unsaved** decisions currently on screen and
> returns `{checkResult{ok, errors}, calculateResult}`. The client renders `calculateResult` with
> `writeCalculate()` and server validation with `writeAllErrors()`. **No `save` is involved.**
>
> * **Trigger:** typing in a bound input (`bindCalculate(id, "keyup"|"click"|"change")` → 500 ms debounce →
>   `onTimerCalculate` → `calculate(true)`, `:1:192874`/`:1:192940`), or the **Calculate** button on planner
>   screens (`FactorySimulation*`, `ExtFactorySimulation*`, `ProFormaDivisionProfitability`). 48 screens.
> * **Precondition:** the screen must be in modify mode. `onTimerCalculate` checks `inModifyMode`, which
>   requires `modify(user, 0)`, which **acquires a server-side edit lock** that teammates see. The lock is
>   released by `cancel(user, 0, lockToken)`.
> * **Still not provable from the client:** server-internal effects of `calculate`/`modify`. EXP-01 found no
>   client-visible persistent change after Cancel. REA coverage was not re-evaluated with EXP-01 as a verifier:
>   REA accepts only canonical Evidence bundles, and producing one would mean repeating the Modify/Cancel run inside an MCP session.
> * **Not draft-sensitive:** ProForma Income Statement / Balance Sheet / Cash Flow `view`, and `GameInfo.liveProForma([user])`,
>   send no decisions, so they can only reflect **saved** state (INFERRED). `projectDemandNextQuarter` is a
>   read-only `FixedCapacity.dynamicData` value, and `projectedCash` a read-only `CD.dynamicData` value, in the capture.

## A. Architecture

Verified in client code: `engine.php` shell → `sstudent.js` UI engine → `core.js` transport → `POST
backend-json.php?<Service>` JSON-RPC (`core.js:5:7918`). Screens are classes on `window`.
`DecisionFactory.getDecision(name)` instantiates `window[name]` and sets `service=name`. Menu and resource
lists come from the server (`LeftMenu.leftMenuItems`, `Resource.resourceList`) per quarter.

## B. Modules (Phase 2b)

310 class registrations in REA-verified webpack modules: **123 decision screens, 1 finalization screen
(`WrapUp`, labelled "Submit"), 128 reports, 58 helpers** (animations/editors). The Q1 rendered tree has 62
items, 27 marked as decision screens. See [module-map.md](module-map.md).

## C. RPC contracts (Phase 2a)

Statically referenced: 252 screen services, 11 infrastructure services, 8 base methods, 30 REA-discovered
literal methods and 5 class-scoped methods. Observed: 31 pairs. Write candidates (never called): every
screen's `save`, the lock methods, `WrapUp` finalization, `Settings.saveQuarterScreenSettings`,
`StudentInit.runFinish`/`runInit`, chat/email/assistant writes, instructor/overlay settings. See [rpc-contract.md](rpc-contract.md).

## D. Decision fields (Phase 2c)

Decision fields come from each screen's `read()` (`<obj>.<field> = this.value("<control>")`), with control types from
`this.com(type, id, …)`. Value types: integer (`iedit`), float (`fedit`), boolean (`checkbox`), enum
(`combobox`/`radio`), text (`memo`/`edit`). **No numeric client-side bounds exist.** Bounds, required
fields, warnings and notes are server-side, returned as `checkResult.errors` by `calculate` and `save`.
That makes them probeable without saving. `warnMinPrice/warnMaxPrice` are Stock issue-price fields, unused
by the client. See [decision-catalog.md](decision-catalog.md).

## E. Client calculations (Phase 2d)

14 business-relevant exact client formulas, all display-level: 65-day quarter, effective capacity =
OC × productivity / 100, capacity cost per unit, market/channel/regional share %, utilisation %, web
commission cost. See [calculation-map.md](calculation-map.md). Everything material (demand, costs,
P&L) is server-computed. 48 screens expose server computation of draft decisions through `calculate`.

## F. Outputs (metrics)

Unit sales (`Sales`), revenue/COGS/operating profit (`IncomeStatement`, `ProFormaIncomeStatement` rows),
market share (`MarketShare`, client %), scorecard (`BalancedScorecard*`, `PlayersStanding`), production
cost (`FactorySimulation` calculate). See [metric-catalog.md](metric-catalog.md).

## G. Identifiability (Phase 4)

[identifiability-matrix.md](identifiability-matrix.md) classifies each (field, output group) as F/W/P/Q/X.
Across 124 screens: W = 87, F = 24, P = 197, Q = 201, X = 57 cells. Cost structure is mostly **W**
(what-if). Demand response is **Q** (next quarter, confounded).

## H. Live observation (Phase 3)

**Skipped.** `rea list-browser-targets http://127.0.0.1:9222` → `endpoint_unreachable` (no CDP browser
running). No navigation, clicks or requests were made against Marketplace in this pass.

## I. REA offline environment (Phase 5)

Built `evidence/private/rea-env` (`marketplace-replay`). It has one projected tool (all RPCs share one path),
replays the 70 recorded exchanges, served 0 tools from state, and withheld the write (`no-state-target`). It was
not run: `agent-env` is not installed. It contains recorded `x-xsrf-token` header values, so it is private only.

## J. Coverage (Phase 6)

REA `evaluate_reconstruction_coverage`, capture-backed surfaces: `rpc-contracts` **unknown** (31 claims),
`decision-catalog` **unknown** (18), `output-catalog` **unknown** (30). Every claim is `verifier-missing`, plus
`package-proof-unknown`. REA's fail-closed model expects runtime verifiers, which do not exist yet.

Hand-written coverage table (static denominator = client registry):

| Boundary | Static (client) | Observed (Q1 capture) | Runtime-verified |
|---|---|---|---|
| Screen services | 252 | 29 | 0 |
| Decision screens with parsed fields | 124 | 18 with decision shapes | 0 |
| What-if screens | 48 | 5 returned `calculate` data on `view` (CD, FixedCapacity, OpenSalesOffice, OpenWebcenter, ProFormaCashFlow); the `Stock` report does too | 0 |
| Client formulas | 14 business-relevant (219 expressions) | n/a | 0 |
| Q1 menu items | 62 | 62 | n/a |

## Limits

Static analysis never observed execution. The server implementation is unavailable and was not sought.
Class registrations, fields and formulas come from REA-located, digest-verified module text, using literal
patterns documented in `rea_ingest.py`. Dynamic constructs can hide additional fields (`possibly_triggers_…` flags).
