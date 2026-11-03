# EXP-01 · CD.deposit what-if channel: verified

Date 2026-11-03 · Quarter 1 · operator-run with teammate consent · REA `capture_browser_scenario` (connect
mode) on the operator's logged-in browser, behind a local network guard. Private Evidence:
`evidence/private/exp-01/` (scenario `rea/s3_exp01.json`, guard log, `experiment_values.json`).
Nothing below contains team values except the trivial zero baseline.

## Result

**The what-if channel works and does not persist.** `CD.calculate` returned server-computed
results for draft deposits, and after `Cancel` the stored decision was unchanged.

| Step | RPC (in order) | Notes |
|---|---|---|
| navigate | `CD.view` | baseline deposit = B |
| Modify | `CD.modify` | `modifyResult=true`, lock held by us, `lockDuration` = 3600 s |
| fill B → Shift | `CD.calculate` | ok, outputs at baseline |
| fill B − S → Shift | `CD.calculate` | `checkResult.ok=false`, 1 input error on `deposit` (negative not allowed), no result |
| fill B + S → Shift | `CD.calculate` | ok, Δcd = +S, Δinterest = +S × (displayed quarterly rate) |
| fill B → Shift | `CD.calculate` | ok, back to the baseline outputs |
| Cancel | `CD.cancel` | edit mode left; Modify enabled; Save/Cancel/inputs disabled |
| re-navigate (Stock → CD) | `Stock.view`, `CD.view` | stored deposit = B (restored); no lock text |

S = 10 000 currency units. Full method sequence:
`view → modify → calculate ×4 → cancel → view → Stock.view → view`. No `save` was sent. The
guard blocked 0 requests during the experiment.

## Findings

1. **No auto-calculate on value change.** A programmatic fill (input event) did not trigger `calculate`
   within 1.5 s. The `keyup` binding fires it: one Shift press led to `calculate` within the 500 ms debounce. A
   real user typing triggers it on every key release.
2. **Interest is linear in the deposit, at the displayed quarterly rate:** observed `Δcd = Δdeposit` and
   `Δinterest = Δdeposit × rate_annual / 4 / 100`. The observed slope Δinterest/Δdeposit exactly equals the displayed `rate/4` (%) (value kept private).
   Working hypothesis (only the deposit term was tested; `cd_prior` and `withdraw` were 0):
   `cd = cd_prior + deposit − withdraw`, `interest = cd × rate_annual / 4 / 100`.
   **Evidence strength: moderate.** Two valid points (Δ = 0, Δ = +S) and an exact match to the client-displayed
   rate. Tiered rates for large deposits and the `withdraw`/`cd_prior` terms were not varied.
3. **Server validation is reachable without saving:** a negative deposit comes back as
   `checkResult.ok=false` with a field-level input error, and no result.
4. **Lock:** `modify` grants a 3600 s lock (`validateLock` would be called at 2700 s, which was not reached). `cancel`
   released it immediately; the re-entered page showed Modify enabled and no lock notice.
5. **Side effects:** none observed. The stored decision was identical before and after (`CD.view` after Cancel and
   after re-navigation). REA `compare_web_captures` (`ev_f546fa59…`) reported only coarse DOM/AX "modified".
   A node-level accessibility diff shows the only difference is the menu state of the item clicked during re-navigation.

## Conditions and caveats

* The REA scenario reloads the page at the start. The page's own baseline calls on load (`TokenProvider.getHeaderToken/
  deleteRefreshToken`, `StudentInit.runInit/runFinish`, `ServiceStatus.gs`, `Email.getNewEmailsCount`) were allowed by
  the guard's baseline tier (`docs/rea-pivot.md` §6b).
* Static analysis cannot prove `calculate` writes nothing server-side. This experiment shows that **no persistent change is
  visible to the client** after Cancel.

## Implication for EXP-02+

The channel is usable for cost-function identification with the same pattern (Modify → fill → Shift → read → … →
restore → Cancel), provided each screen's input binding event is known (`keyup`, `click` or `change`; see
`docs/decision-catalog.md`). Screens with a Calculate button (FactorySimulation*, ProFormaDivisionProfitability)
need that button added to the guard's per-screen allow list and the click allow list.
