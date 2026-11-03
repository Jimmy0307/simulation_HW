# Open business-simulation toolkit: evidence-based reconstruction + local planning simulator

> **Disclaimer.** This is an unofficial, independent project. It is **not affiliated with, endorsed by, or connected to
> Marketplace Simulations / Innovative Learning Solutions** or any course provider. The repository contains **no game
> content**: no parameters, market data, fitted models, text, screenshots or assets. Every number shipped here is
> invented (`examples/`). Users must obtain any data **themselves, legitimately, from their own account**, and keep it
> private. See [docs/legal-scope.md](docs/legal-scope.md).

## Architecture: open engine, bring your own data

```
src/marketplace_sim/        open, generic planning engine (mpsim CLI); data enters only through a parameter pack
examples/synthetic/         invented parameter pack (same schema as a real pack)
examples/demo/              3-quarter demo plans + alternative plans for `mpsim compare`
src/marketplace_sim/api/    local FastAPI (loopback only) over the engine + synthetic demo export for the UI
frontend/                   Vite + React + TypeScript UI (StaticProvider for the demo, ApiProvider for live use)
src/marketplace_sim/control/ control plane: scenarios, events, competitors, sweeps, param diff, HTML, optional MCP
examples/scenarios/         synthetic scenario templates (baseline, cost rise, demand decline, price war, combined)
examples/demo-control/      reproducible control-plane demo (scenario -> sweep -> worst cases -> param diff)
src/marketplace_sysid/      evidence tooling: REA Evidence ingest, parameter extraction, verified cost rules, gate
evidence/private/           YOUR data (git-ignored): REA Evidence, real pack (model/pack.json), saves, briefs
```

* The **engine** is public. A **parameter pack** (`pack.json`, schema `marketplace-sim/param-pack@1`) supplies all
  numbers: `--params examples/synthetic` or, privately, `--params evidence/private/model`.
* The **publication gate** (`scripts/publication_gate.py`) refuses any commit that contains your private values: runs of
  real table values, real parameter values next to their field names, real values reused in `examples/`, or real names.

## Install and run the synthetic demo

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\mpsim.exe new --params examples/synthetic --out demo-save.json
.\.venv\Scripts\mpsim.exe play demo-save.json --decisions examples/demo/q1.yaml
.\.venv\Scripts\mpsim.exe play demo-save.json --decisions examples/demo/q2.yaml
.\.venv\Scripts\mpsim.exe compare demo-save.json "examples/demo/plans/*.yaml"
.\.venv\Scripts\mpsim.exe explain cd_interest
```

## Control plane: game master and agent interfaces

```powershell
.\.venv\Scripts\mpsim.exe scenario run examples/scenarios/combined-shock.yaml --out outputs/scenarios   # + offline HTML
.\.venv\Scripts\mpsim.exe sweep run examples/demo-control/sweep.yaml --out outputs/sweeps
.\.venv\Scripts\mpsim.exe sweep worst outputs/sweeps/demo-stress.sweep.json --top 10
.\.venv\Scripts\mpsim.exe params diff examples/synthetic examples/demo-control/pack-v2
```

* Scenarios set parameter overrides per quarter, composable events and competitor behaviour (baseline, random, private
  replay). Runs are deterministic (same spec + seed => same result and fingerprint).
* Game master guide (Chinese): [docs/gamemaster-guide.md](docs/gamemaster-guide.md).
* Agent harness: [docs/agent-harness.md](docs/agent-harness.md).
* `outputs/` is git-ignored. Results built from a private pack must be written under `evidence/private/`.
* **Optional MCP layer** (`python -m marketplace_sim.control.mcp_server`): wraps only this local engine (run_scenario,
  run_sweep, list_scenarios, explain_result). It is **unrelated to the REA MCP server** used for reverse engineering and
  never contacts the game or any online service.

## Web UI (static synthetic demo or live local API)

```powershell
python scriptsuild_demo.py                         # export synthetic demo -> test -> build -> gate-check frontend/dist
cd frontend; npm run preview                         # static demo (read-only, synthetic data)
.\.venv\Scripts\python.exe -m marketplace_sim.api --pack synthetic   # live mode: local API (127.0.0.1 only) ...
cd frontend; npm run dev:api                         # ... and the UI talking to it
```

The UI never computes numbers. It renders what the Python engine returns, every number shows its source level, and
anything with a literature or placeholder input carries an "uncalibrated · not a forecast" mark with a hover source
chain. See [docs/ui-guide.md](docs/ui-guide.md) (Chinese). The GitHub Pages workflow is manual and must not be run
before the history cleanup ([docs/history-cleanup-plan.md](docs/history-cleanup-plan.md), open TODO:
[docs/TODO-history-cleanup.md](docs/TODO-history-cleanup.md); the workflow refuses to run until it is marked cleaned).

**Game mode** (8th entry; the seven analysis screens are unchanged) is a turn-based view of the same engine: one
quarter = one turn, with 1–6 opponents built from the control plane's existing bots. Trusted numbers (verified /
derived) show directly; anything literature- or placeholder-level stays behind a faded "? 預估" (estimate) chip until
clicked. The static demo replays one pre-recorded synthetic game. See [docs/ui-guide.md §6a](docs/ui-guide.md).

## Load your own data (private)

1. Capture your own sessions with [REA](https://github.com/morluto/rea) into `evidence/private/` (see
   [docs/rea-pivot.md](docs/rea-pivot.md) and [docs/quarterly-runbook.md](docs/quarterly-runbook.md)).
2. `mpsim build-pack --out evidence/private/model` turns your captured `view` responses into a private pack.
3. Play and compare with `--params evidence/private/model`. See [docs/private-play-guide.md](docs/private-play-guide.md).

## Source levels (shown on every number)

| Mark | Level | Meaning |
|---|---|---|
| `[V]` | verified | Reproduced against measured server results with zero residual (operator what-if experiments) |
| `[D]` | derived | Follows directly from published parameters (exact identities) |
| `[E]` | estimated | Fitted to observed data and validated on a held-out quarter (future demand model) |
| `[L]` | literature | Functional form backed by published literature; coefficients **not** calibrated on this game's data; never read as a forecast |
| `[P]` | placeholder | Illustrative and uncalibrated; never read as a forecast |

Order: verified > derived > estimated > literature > placeholder. A combined number takes the **weakest** level of its
inputs. Today:
* verified: capacity investment, outlet opening cost, CD balance and interest;
* derived: stock raise;
* literature: demand, units sold, market share and revenue, from
  [docs/demand-model-spec.md](docs/demand-model-spec.md) and [docs/demand-literature.md](docs/demand-literature.md);
* placeholder: production cost, tax and therefore profit and cash.

## Method summary

* **Reverse engineering with REA:** captures and shipped JavaScript are analysed with REA (Evidence IDs, coverage,
  limits). Repo code only reads REA Evidence ([docs/rea-pivot.md](docs/rea-pivot.md)).
* **Network guard:** live observation runs behind a local CDP guard with a tiered allow-list
  ([data/guard_policy.json](data/guard_policy.json)). Writes such as `save` and submission are always blocked.
* **What-if verification:** the client's no-save `calculate` path is used in operator-approved experiments, each
  restored with Cancel ([docs/experiments/](docs/experiments/)).
* **Evidence grades:** every claim states its evidence and strength
  ([docs/reconstruction-report.md](docs/reconstruction-report.md), [docs/cost-model.md](docs/cost-model.md)).

## Documents

| Document | Content |
|---|---|
| [docs/private-play-guide.md](docs/private-play-guide.md) | Build a private save, play, compare plans |
| [docs/gamemaster-guide.md](docs/gamemaster-guide.md) | 主持端：情境、事件、對手、what-if、HTML 報告（中文） |
| [docs/agent-harness.md](docs/agent-harness.md) | Sweeps, worst cases, sensitivity, JSON formats, optional local MCP |
| [docs/ui-guide.md](docs/ui-guide.md) | Web UI：兩種模式、切換參數包、來源等級標記（中文） |
| [docs/history-cleanup-plan.md](docs/history-cleanup-plan.md) | Git history leak investigation and cleanup plan (Chinese) |
| [docs/TODO-history-cleanup.md](docs/TODO-history-cleanup.md) | **Open TODO**: history not cleaned yet; hard rules and the automatic reminder (Chinese) |
| [docs/dev-diary.md](docs/dev-diary.md) | Development diary: how the project evolved (Chinese) |
| [docs/demand-literature.md](docs/demand-literature.md) | Public literature on demand forms, parameter ranges and fit grades |
| [docs/demand-model-spec.md](docs/demand-model-spec.md) | Literature-level demand chain, coefficients, mapped vs placeholder, upgrade path |
| [docs/quarterly-runbook.md](docs/quarterly-runbook.md) | What happens each quarter, what the operator does, how to read the report |
| [docs/reconstruction-report.md](docs/reconstruction-report.md) | Reconstruction findings (REA-based) |
| [docs/cost-model.md](docs/cost-model.md) | Verified cost rules and what is not covered |
| [docs/calculate-screen-triage.md](docs/calculate-screen-triage.md) | Which screens are derived, need experiments, or are pending |
| [docs/parameter-catalog.md](docs/parameter-catalog.md) | Parameter structure (value-free) |
| [docs/experiment-runbook.md](docs/experiment-runbook.md), [docs/experiments/](docs/experiments/) | Experiment designs and results |
| [docs/decisions-log.md](docs/decisions-log.md) | Autonomous-run decisions |
| [legacy/](legacy/README.md) | Deprecated round-one Python MCP toolkit |

See [SECURITY.md](SECURITY.md) before contributing.
