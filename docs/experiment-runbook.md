# Experiment runbook (operator-run, ranked by information gain)

Machine-readable spec: [`data/experiment_runbook.json`](../data/experiment_runbook.json). Dry-run:
`python -m marketplace_sysid.experiments.runbook` (all 10 items validate against `data/decision_catalog.json`
and expand to baseline/minus/plus OFAT designs; baselines are placeholders until you read the real value).

**Nothing here is automated.** A person on the team performs every UI action. The agent never logs in,
clicks, saves or submits.

## 0. Ground rules (read once)

* **Teammate consent for every item.** `modify` takes a server-side lock on that screen: teammates
  see "locked by <you>" and cannot edit it until you **Cancel**. Agree on a time window and announce it in team chat.
* **Never press Save, Submit (`WrapUp`), Accept, Finalize or Apply** during WHATIF items. Restore is always **Cancel**.
* Write down the **original value** of every field before you change it.
* Keep ≥ 3 s between page navigations. Stay on the Marketplace origin. If the session expires, stop. Don't try to recover it.
* Keep all files under `evidence\private\exp\<ID>\`. Don't commit them.
* **Why two captures?** REA passive captures (`inspect_web_page`, `observe_web_session`) keep only
  value-free body *shapes*. They show which services were hit and whether the screen changed, but not the numbers, and
  not the `method` inside the JSON body. The numbers, and the proof that no `save` was sent, come from a DevTools
  HAR that REA decodes with `inspect_web_network_capture`.

## 1. Common procedure (`<ID>` = EXP-xx, `<M>` = module, `<F>` = field)

```powershell
# one-time: a dedicated Chrome profile with CDP (you log in yourself in this window)
& "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir=D:\tools\chrome-cdp-profile
$env:PATH = "D:\tools\node24;$env:PATH"
$E = "D:\simulationHW\simulation_HW\evidence\private\exp\<ID>"; New-Item -ItemType Directory -Force $E | Out-Null
$O = "https://play.marketplace-simulation.com"

# A. find the tab (open screen <M> in view mode first)
rea list-browser-targets http://127.0.0.1:9222 --allowed-origins $O --format json > $E\targets.json
$T = "<targetId of the Marketplace tab from targets.json>"

# B. BEFORE (passive)
rea inspect-web-page http://127.0.0.1:9222 $T --allowed-origins $O --include-accessibility-text --include-json-body-shapes --observation-ms 1500 --format json --filter-output normalized_result > $E\before.json
rea capture-web-screenshot http://127.0.0.1:9222 $T --allowed-origins $O --format json > $E\before.screenshot.json

# C. open DevTools > Network, tick "Preserve log", clear it. Then start a 3-minute passive window:
rea observe-web-session http://127.0.0.1:9222 $T --allowed-origins $O --observation-ms 180000 --format json > $E\session.json
#    During the window, by hand: Modify → note original <F> → set (original − step) → wait 2 s
#    → set (original + step) → wait 2 s → set original → Cancel.
#    (Live-calc fields refresh 0.5 s after typing; button screens: press "Calculate" after each change.)

# D. AFTER (passive) + compare
rea inspect-web-page http://127.0.0.1:9222 $T --allowed-origins $O --include-accessibility-text --include-json-body-shapes --observation-ms 1500 --format json --filter-output normalized_result > $E\after.json
rea compare-web-captures $E\before.json $E\after.json --format json > $E\compare.json

# E. values: DevTools > Network > "Save all as HAR (with content)" → $E\values.har
rea inspect-web-network-capture $E\values.har har --detail summary --evidence_output $E\values.bundle.json --format json > $E\values.summary.json
cd D:\simulationHW\simulation_HW
.\.venv\Scripts\marketplace-rea-ingest.exe --capture-bundle evidence\private\rea\01_capture\capture.bundle.json `
  --app-bundle evidence\private\rea\02_js_full\app.bundle.json --source-root evidence\private\rea\02_js\app `
  --experiment-capture $E\values.bundle.json --private-out $E
# → $E\experiment_values.json : one row per RPC with method, decisions_sent, calculate_result, check_ok
```

**Pass/abort checks**

1. `experiment_values.json` methods must be exactly `modify → calculate… → cancel` (plus `view`).
   **Any `save` row means abort.** Tell the team and re-enter the original values.
2. `compare.json` should show no persistent change in the decision field after Cancel. Reload the screen
   (≥ 3 s later) and confirm the original value is shown.
3. `check_ok=false` rows are useful: they reveal server-side bounds. Record them; don't save.

## 2. The experiments

| Rank | ID | Module.field | Change (OFAT) | Read | No-submit? | Restore | Consent |
|---|---|---|---|---|---|---|---|
| 1 | EXP-01 | `CD.deposit` | baseline, −10 000, +10 000 (stay ≥ 0) | `calculate.cd`, `calculate.interest`, `check_ok` | ✅ what-if | Cancel | yes (locks CD) |
| 2 | EXP-02 | `FixedCapacity.increase` (+ `supplier` if shown) | each capacity option in turn (radio), one at a time | `calculate.acquirement/expansion/total`; on-screen units/quarter vs units/day × 65 | ✅ what-if | Cancel | yes (locks Fixed Capacity) |
| 3 | EXP-03 | `FactorySimulation.estimatedDemand` (fallback `OpenSalesOffice.change`) | baseline, −500, +500 units, press **Calculate** each time | per-brand `material/labor/overhead/prodCost/avgCost`, `chover*/excess*/total*` | ✅ what-if | Cancel | yes |
| 4 | EXP-04 | `ProFormaDivisionProfitability.estimatedPrice` | baseline, −50, +50, **Calculate** | `calculate.items` (division P&L lines) | ✅ what-if | Cancel | yes |
| 5 | EXP-05 | `OperatingCapacity.operatingCapacity` | ±10 units/day | `directLaborCPU`, `overheadCPU`, `costToChangeOperatingCapacity` | ✅ what-if | Cancel | yes |
| 6 | EXP-06 | `HireSalesPeople.sf` | ±1 person, one region | `total`, per-region hire/employ/layoff cost | ✅ what-if | Cancel | yes |
| 7 | EXP-07 | `LocalMedia.inserts` | ±1 insert | `adsCost`, `mediaCost`, `regionCost` | ✅ what-if | Cancel | yes |
| 8 | EXP-08 | `ShortTermLoan.borrow` | ±10 000 | `interest`, `quarterlyRate`, `annualRate` | ✅ what-if | Cancel | yes |
| 9 | EXP-09 | `HireSalesPeople.sf` → ProForma | +1 then Save; read ProForma Income/Cash; restore | ProForma projection columns | ❌ needs Save | Modify → original → Save | **team decision** |
| 10 | EXP-10 | `Pricing.price` | ±10 on one brand/region as part of the real quarter plan | next-quarter `Sales`, `MarketShare`, `IncomeStatement` | ❌ needs Submit | not reversible | **team decision** |

Why this order: EXP-01 proves the channel is safe (no persistence, lock released) and must pass before anything else.
EXP-02/03/04 identify the large server-opaque cost blocks (capacity capital, production cost, division P&L) with
many cheap, reversible points. EXP-05…08 fill in the cost side of each lever. EXP-09 tests the *inferred*
ProForma recomputation but writes. EXP-10 is the demand model: one confounded observation per quarter.

### EXP-01 · CD.deposit (validate the what-if channel)

> **Status: ✅ VERIFIED 2026-11-03.** See [experiments/EXP-01.md](experiments/EXP-01.md). It ran via REA
> `capture_browser_scenario` behind the tiered network guard. Method sequence `modify → calculate ×4 → cancel`, no
> `save`, 0 blocked requests, stored value restored, lock released. Lessons for the next items: a programmatic
> `fill` does not trigger `calculate`, so one Shift press (keyup) is needed; a negative input returns `checkResult.ok=false`;
> the lock lasts 3600 s.

* **Before:** Finance → Certificate of Deposit in view mode. Steps A, B. Note `deposit` and `withdraw`.
* **Change:** Modify, then deposit = original − 10 000 (if ≥ 0), wait 2 s; original + 10 000, wait 2 s; original. Cancel.
* **After:** steps D, E. Expect 3+ `calculate` rows in which only `deposit` changes, `calculate.interest`
  moves with the deposit, `cancel` is present, and there is no `save`. Re-open CD (≥ 3 s): the original deposit is shown.
* **Learns:** that the channel exists and is non-persistent, the lock duration (`modify` response), and the interest function.

### EXP-02 · FixedCapacity.increase

> **Status: ✅ VERIFIED 2026-11-03.** See [experiments/EXP-02.md](experiments/EXP-02.md). Run in a REA MCP session;
> `modify → calculate ×9 → cancel`, no `save`, 0 blocked requests. Capital cost is exactly linear in units/day, and the
> stored option was restored. Radios are clicked by `#fcTable input[name=capOption]#capOption_<units>`.

* **Before:** Manufacturing → Fixed Capacity. Note the selected capacity option and supplier.
* **Change:** Modify, then click each capacity option radio once (wait 2 s each) and return to the original option. Cancel.
* **After:** D, E. Fit `total` against option size (step shape, per-unit cost). Check that the on-screen
  "units per quarter" equals "units per day × 65" (client formula) and compare it with `projectDemandNextQuarter/65`.

### EXP-03 · FactorySimulation.estimatedDemand (fallback: OpenSalesOffice.change)

* Available only in quarters where the planner screen is in the menu. If it is missing, run the fallback: toggle
  `change` for one city in Open Stores, wait 2 s, toggle back, Cancel. That reads `total/totalSetup/totalLease`.
* **Change:** Modify, then estimatedDemand for one brand = original, −500, +500 (press **Calculate** after each), then original. Cancel.
* **Learns:** per-unit material/labor/overhead and changeover/excess-capacity cost as a function of volume.

## 3. After the experiments

`experiment_values.json` rows feed `marketplace_sysid.experiments.sensitivity.finite_difference` (local slopes)
and, once ≥ 10 points per variable exist, `experiments.surrogate.fit_surrogate` (held-out). Results stay private.
Only the fitted structure (functional form, not team values) may be published after the gate.
