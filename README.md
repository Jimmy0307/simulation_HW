# Marketplace Simulation: REA-based reconstruction and system-identification prep

> **Deprecated:** the self-built "Marketplace Simulation MCP" (22 tools, Python HAR/JS parsers)
> from branch `codex/marketplace-sim-mcp` now lives in [`legacy/`](legacy/README.md). Reverse
> engineering is done with [REA](https://github.com/morluto/rea), which is itself an MCP server.
> See [docs/rea-pivot.md](docs/rea-pivot.md).

This repository holds:

1. **Publication boundary**: `src/marketplace_sysid/security/` and `scripts/publication_gate.py`.
   Raw HAR/HTML/JS, REA Evidence and REA environment bundles stay in ignored `evidence/private/`.
2. **REA ingest**: `src/marketplace_sysid/rea_ingest.py` reads REA Evidence JSON
   (`inspect_web_network_capture`, `analyze_javascript_application`) and produces
   de-identified catalogs in `data/`.
3. **System-identification planning**: `src/marketplace_sysid/experiments/` (OFAT specification,
   runbook dry-run, finite differences, interaction pairs, held-out surrogate fitting).
4. **Documentation** of what is known, how strongly, and what to measure next.

## Headline findings (static, REA-attributed)

* Every screen is a `Decision` subclass whose RPC service equals its class name. 310 class
  registrations: **123 editable decision screens, 1 finalization screen (`WrapUp`, menu label "Submit"), 128 reports**.
* The shared base class exposes `view`, `modify` (server lock), **`calculate` (draft decisions → server-computed
  results + validation, no save)**, `save`, `cancel`, `removeLock`, `validateLock`, `prolongLock`.
* **What-if channel: present by static evidence, not yet verified at runtime.** It needs the
  `modify` lock (visible to teammates) and ends with `cancel`. See
  [docs/reconstruction-report.md](docs/reconstruction-report.md) §E and the
  [experiment runbook](docs/experiment-runbook.md).

## Use

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
# REA (Node >= 24.22.1) produced the private Evidence bundles; see docs/rea-pivot.md for the exact commands.
.\.venv\Scripts\marketplace-rea-ingest.exe --capture-bundle evidence\private\rea\01_capture\capture.bundle.json `
  --app-bundle evidence\private\rea\02_js_full\app.bundle.json --source-root evidence\private\rea\02_js\app `
  --html-dir evidence\private\extracted\customer_needs --private-out evidence\private\rea\04_ingest --public-out data
.\.venv\Scripts\python.exe -m marketplace_sysid.experiments.runbook        # dry-run only
.\.venv\Scripts\python.exe scripts\publication_gate.py
```

## Documents

| Document | Content |
|---|---|
| [docs/rea-pivot.md](docs/rea-pivot.md) | Why we pivoted, environment, architecture, REA gaps, offline environment |
| [docs/reconstruction-report.md](docs/reconstruction-report.md) | Current reconstruction (v2, REA-based) |
| [docs/rea-reconciliation.md](docs/rea-reconciliation.md) | REA results compared with the round-one Python results |
| [docs/rpc-contract.md](docs/rpc-contract.md) | RPC contracts incl. statically inferred write candidates (never called) |
| [docs/decision-catalog.md](docs/decision-catalog.md), [docs/metric-catalog.md](docs/metric-catalog.md) | Generated from `data/*.json` |
| [docs/identifiability-matrix.md](docs/identifiability-matrix.md) | How each decision → output pair can be observed |
| [docs/experiment-runbook.md](docs/experiment-runbook.md) | Human-run experiments ranked by information gain |

See [SECURITY.md](SECURITY.md) and [docs/legal-scope.md](docs/legal-scope.md) before contributing.
