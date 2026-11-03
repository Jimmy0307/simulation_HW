# EXP-02 · FixedCapacity.increase option scan: verified

Date 2026-11-03 · Quarter 1 · operator-approved, run with REA `capture_browser_scenario` **inside a REA MCP session**
(connect mode, operator's logged-in browser) behind the local network guard (policy `data/guard_policy.json`,
experiment tier = FixedCapacity only). Private Evidence: `evidence/private/exp-02/` (scenario Evidence
`ev_4d3323cd…`, exported as a canonical REA bundle; guard log; `experiment_values.json`).

## Result

**The what-if channel works on a click-bound screen and does not persist.**

| Step | RPC | Notes |
|---|---|---|
| navigate | `FixedCapacity.view` | baseline option = 0 (no added capacity); no supplier choice on this screen |
| Modify | `FixedCapacity.modify` | lock granted, `lockDuration` = 3600 s |
| click every capacity option in ascending order, then the baseline option again | `FixedCapacity.calculate` ×9 | each fired by the radio `click` binding (500 ms debounce); every result `checkResult.ok=true` |
| Cancel | `FixedCapacity.cancel` | returned `true`; Modify enabled, Save/Cancel disabled |
| re-navigate (Tactic-Strategy Links → Fixed Capacity) | `TacticStrategyLinksManufacturing.view`, `FixedCapacity.view` | stored option = baseline |

No `save` was sent; the guard blocked 0 requests during the experiment. The URL stayed on the Fixed Capacity workspace for
every edit step, and no dialog or popup events occurred. All 45 scenario steps completed.

## Findings

1. **Capital cost of capacity is exactly linear.** `calculate.expansion = calculate.total = c × Δunits_per_day`,
   with one constant marginal cost c for every offered option (all machine counts on the screen). There are no
   economies or diseconomies of scale in this range. `acquirement` stayed 0, which fits a screen without
   supplier/acquisition choices. **Evidence strength: strong** (9 points, including both baseline ends; residual 0).
2. The server's `calculate` totals equal the option-cost column already present in the `view` response's
   `staticData.capacityOptions`. For this screen, the what-if channel confirms the static table rather than revealing
   hidden cost terms.
3. **Client formula confirmed on screen:** units per quarter = units per day × 65 at every option (presence check in the
   accessibility text; weak but consistent with `calculation-map.md` #3–4).
4. `projectDemandNextQuarter`, `averageProductivity` and `minimumOperatingCapacity` are `view` dynamicData, not
   `calculate` outputs. Changing the capacity option does not recompute them.

## REA coverage

`evaluate_reconstruction_coverage`, boundary `whatif-contracts` (claims EXP-01/CD and EXP-02/FixedCapacity), with EXP-02 as a
`controlled-replay` verifier from the exported canonical bundle → **unknown**:
`package-proof-unknown` (no reconstruction package exists); `verifier-missing` for EXP-01 (CLI-produced Evidence
cannot be placed in a canonical bundle without re-running); `verifier-result-incompatible` for EXP-02 (REA accepted the
verifier contract digest, canonical compact-sorted JSON, but its result-to-artifact/owner matching rules are not
exposed in the compact schema; two attempts did not reconcile them).
