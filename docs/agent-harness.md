# Agent harness: batch scenarios, sweeps and machine-readable results

The agent interface drives the same local engine as the game-master CLI, but in bulk and with JSON outputs. Everything is
offline and deterministic: the same scenario + seed always gives the same result and the same `fingerprint`.

## 1. Sweep definition

```yaml
name: demo-stress
base_scenario: scenario.yaml        # a normal scenario file, relative to this sweep file
mode: grid                          # grid = full product; sample = `samples` distinct combinations drawn with `seed`
samples: 20
seed: 7
objective: min_cash                 # final_cash | min_cash | cumulative_net_income  (lower = worse)
variables:
  - {name: capacity_cost, path: "capacity_options[*].cost", op: scale, values: [0.9, 1.0, 1.25], base: 1.0}
  - {name: demand_q2, event: {type: demand_shock, from_quarter: 2, target: "*", duration: 3}, values: [-0.3, 0.0, 0.1], base: 0.0}
  - name: rivals
    competitors:
      calm: [{name: a, strategy: baseline}]
      aggressive: [{name: a, strategy: baseline, params: {price_factor: 0.8}}, {name: b, strategy: random}]
  - name: plan
    policies:
      cautious: {type: fixed, default: ../demo/plans/a-cautious.yaml}
      bold: {type: fixed, default: ../demo/plans/c-aggressive.yaml}
  - {name: seed, seeds: [0, 1, 2]}
```

Variable kinds:
* `override`: a parameter path with `set`, `scale` or `add`.
* `event`: an event template; the value is its magnitude.
* `competitors`: named rival sets.
* `policies`: named policies. Paths are relative to the sweep file and are rewritten relative to the base scenario, so fingerprints do not depend on the checkout location.
* `seeds`

Runs are named `<sweep>-NNN` in expansion order.

## 2. Commands

```bash
mpsim sweep run examples/demo-control/sweep.yaml --out outputs/sweeps
mpsim sweep worst outputs/sweeps/demo-stress.sweep.json --top 10
mpsim scenario run examples/scenarios/price-war.yaml --out outputs/scenarios
mpsim params diff OLD_PACK_DIR NEW_PACK_DIR
```

Outputs built from a non-synthetic pack are refused unless the output directory is under a `private` directory.

## 3. Result formats

**Scenario result** (`<name>.result.json`, schema `marketplace-sim/scenario-result@1`):
* `name`, `fingerprint` (sha256 of the canonical spec + pack text, 16 hex chars) and `seed`.
* `quarters[]`, each with:
  * `quarter`, `plan`, `events[]` (labels) and `overrides[]` (applied paths with counts);
  * `lines{metric: {value, level, source}}`;
  * `notes[]` and `state`.
* `summary`:
  * `final_cash`, `min_cash`, `cumulative_net_income`, `total_capex`, `emergency_loans`;
  * `weakest_level{metric: level}`;
  * `quarters_with_events[]`.

**Sweep result** (`<name>.sweep.json`, schema `marketplace-sim/sweep-result@1`) plus a Markdown table:
* `name`, `objective`, `mode`, `demand_level` and `caveat` (non-empty while demand is below `estimated`).
* `rows[]`, each with `id`, `fingerprint`, `assignment{variable: value}`, `objective` and `summary`.
* `worst[]`: the bottom 5 by objective.
* `sensitivity[]`, sorted by effect size. Each entry has:
  * `variable`, `kind`;
  * `mean_objective_by_value`;
  * `main_effect_range`;
  * `local_slope`, for numeric variables, from `marketplace_sysid.experiments.sensitivity.finite_difference`.

Every metric has a level: `verified`, `derived`, `estimated`, `literature` or `placeholder`. An agent must not rank
decisions on `literature` or `placeholder` metrics as if they were forecasts. Use `weakest_level` to know what a
conclusion rests on.

**Stress tests before demand is estimated.**
* Demand, units, market share and revenue are at `literature` level: published functional forms whose coefficients are
  literature midpoints or labelled defaults ([demand-model-spec.md](demand-model-spec.md)).
* Until `FittedDemand` passes hold-out validation, a sweep's "worst cases" reflect those **literature assumptions**,
  not a forecast of this game.
* Sweep results carry `demand_level` and a `caveat` field. The Markdown report and `mpsim sweep worst` print the caveat.
  Agents must repeat it when reporting.
* To see how much a conclusion depends on the assumptions, sweep the coefficients themselves (`path:
  demand.coefficients.price_sensitivity`, …); see `examples/demo-control/sweep-demand.yaml`.

## 4. Optional MCP layer (local engine only)

`python -m marketplace_sim.control.mcp_server` starts a stdio MCP server with four tools:

| tool | input | output |
|---|---|---|
| `run_scenario` | `path`, `save_to_outputs?` | name, fingerprint, summary, per-quarter events and key lines |
| `run_sweep` | `path`, `top?` | runs, worst N, sensitivity; writes the sweep files |
| `list_scenarios` | `directory?` | scenario files with name and description |
| `explain_result` | `result_path`, `metric` | metric level, formula, evidence, per-quarter values, levels and events |

* Paths must stay inside the working directory.
* Results from non-synthetic packs are written to `evidence/private/outputs/`, never to `outputs/`.
* It needs the optional `mcp` package (`pip install "mcp>=2,<3"`).

> **This server is unrelated to the REA MCP server** used for reverse engineering. It only wraps the local planning
> engine and never contacts the game or any online service.

Example client configuration (Claude Code `.mcp.json`):

```json
{"mcpServers": {"marketplace-sim-local": {"command": ".venv/Scripts/python.exe",
  "args": ["-m", "marketplace_sim.control.mcp_server"]}}}
```

## 5. Python API

```python
from marketplace_sim.control.spec import load_spec
from marketplace_sim.control.runner import run_scenario
from marketplace_sim.control.sweep import load_sweep, run_sweep, worst

result = run_scenario(load_spec(Path("examples/scenarios/cost-rise.yaml")))
print(result.summary(), result.fingerprint)
sweep = run_sweep(load_sweep(Path("examples/demo-control/sweep.yaml")))
print(worst(sweep["rows"], 3))
```

## 6. Recommended agent loop

1. `list_scenarios`, then pick or write a base scenario. Use a synthetic pack for public work and a private pack only
   under `evidence/private/`.
2. Write a small sweep over the decision you care about (`policies`) crossed with the risks (`event` and `override`).
3. Read `worst` and `sensitivity`. Report results together with their `weakest_level` and `fingerprint`.
4. Each quarter, after `build-pack --quarter-label QN`, check the red flags: if a verified module's parameters
   changed, re-run its experiment before trusting `[V]` lines again.
