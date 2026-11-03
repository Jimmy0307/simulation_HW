# REA pivot: from a self-built MCP to REA-based reverse engineering

Branch `rea/full-reconstruction`, started 2026-11-03 from `codex/marketplace-sim-mcp` @ `c731c7c`.

## 1. Why the previous round drifted

The goal was to use [REA](https://github.com/morluto/rea) (`rea-agents` on npm) to
reverse engineer Marketplace Simulation. The machine's Node.js was v24.18.0, below
REA's minimum on the Node 24 line (>= 24.22.1). REA never ran. Instead, round one
re-implemented parts of REA in Python (HAR parser, HTML parser, a regex JavaScript
symbol scanner, a "calculation finder"). It then wrapped those results in a
22-tool MCP server. That was a detour: REA is already an MCP server, and it has
better provenance, coverage accounting and limits than the Python copies.

That code is now in [`legacy/`](../legacy/README.md). It is not installed, linted, typed or tested.

## 2. Environment (Phase 0)

| Item | Value |
|---|---|
| System Node | v24.18.0, unchanged |
| REA Node | v24.22.2 (official `node-v24.22.2-win-x64.zip`, SHA-256 checked against `SHASUMS256.txt`), unpacked to `D:\tools\node24`, used only by absolute path |
| REA | `rea-agents@6.8.0`, installed with `npm install --global` under prefix `D:\tools\node24` |
| REA catalog | 175 CLI commands, 229 MCP tools, 6 prompts, skill v49 (from `rea doctor`) |
| `rea doctor` | Node/host healthy. Native engines (Hopper, Ghidra, IDA, JADX, Kuna) are absent. None is needed for web/JS work. |
| `rea setup --client codex --yes` | Applied. Adds `[mcp_servers.rea]` to `~/.codex/config.toml` (backup `config.toml.rea.backup`) and installs the REA skill under `~/.agents/skills/`. Codex must be restarted to see the tools. |
| Mode used in this run | **REA CLI `--format json`** for single operations. A private stdio MCP client ran multi-step sessions (`import_evidence_bundle` → `trace_*` / `inspect_analysis_view`), because retained Evidence references only resolve inside one server session. This run was driven from Claude Code, where the Codex registration is not visible. |
| Heap note | Importing the 194 MB application Evidence bundle needs about 3.2 GB of V8 headroom. The MCP server was started with `--max-old-space-size=12288`. |

## 3. New architecture

```
Browser exports (HAR / DevTools, saved HTML+JS)  ──►  evidence/private/  (ignored)
                                                        │
                       REA (reverse engineering + Evidence layer, MCP or CLI)
   inspect_web_network_capture · analyze_javascript_application · inspect_analysis_view
   trace_javascript_semantics · environment_build · (live) list_browser_targets,
   inspect_web_page, observe_web_session, compare_web_captures
                                                        │  Evidence JSON (private)
                                                        ▼
 this repo ── marketplace_sysid.rea_ingest  (thin reader of REA Evidence JSON)
          ├─ security/ + scripts/publication_gate.py   (publication boundary)
          ├─ experiments/ (specification, runbook dry-run, sensitivity, interactions, surrogate)
          ├─ model/      (record types)
          └─ docs/ + data/*.json (de-identified catalogs only)
```

* **REA** owns parsing, module inventory, endpoint discovery, semantic tracing,
  coverage and Evidence identity. It is the MCP surface. This repo ships no MCP server.
* **This repo** owns the safety gate, the system-identification planning layer,
  the documentation, and one thin adapter, `src/marketplace_sysid/rea_ingest.py`.

## 4. Where REA was not enough, and what the thin layer does

`rea_ingest.py` reads REA Evidence JSON. For each webpack module, it slices the
bytes at the exact source range REA recorded and keeps the slice only if its SHA-256
equals REA's `source_sha256` (253/253 sampled modules matched; every class
registration is attributed to a REA module key). It then applies literal patterns
for this application's conventions. It does not parse JavaScript, build graphs or
decode HAR files.

| Need | Why REA 6.8.0 could not answer it directly | Thin-layer answer |
|---|---|---|
| Service names of RPC calls | The client sends every RPC through jQuery `ajax` to `backend-json.php?<Service>` with a service name computed at runtime (`this.serviceName()` → `this.service` → the class name). REA's request extractor covers `fetch`/WebSocket/`node:http`. It records `.fetch("<literal>")` first arguments as endpoint candidates, which captures 30 method names, but not the dynamic service. | Class registrations `window.X = Base.extend({...})` inside REA-verified modules; `DecisionFactory.getDecision(name)` instantiates `window[name]` and sets `service = name` (`sstudent.js:1:182053`, `:1:188141`). |
| String-literal call arguments (`"calculate"`, `"save"`) | `trace_javascript_semantics` literal seeds had no matches. Property seeds matched only `core.js`: `sstudent.js` is "limited" in REA's semantic coverage even after raising limits (the analysis is bounded by the parent result budget). | Literal patterns over the verified module text. |
| Route/menu tree | REA's `javascript-routes` view is empty because this app routes by resource name through `engine.php`, not URL paths. | Rendered task-list tree parsed from the saved (private) HTML, joined to class names. |
| Value-level experiment data | Passive live captures keep value-free body shapes by design. | `experiment_value_rows()` reads bodies from a REA `inspect_web_network_capture` record of an operator's HAR and writes **only** to `evidence/private`. |

## 5. REA runs in this pass (all outputs in `evidence/private/rea/`)

| Step | Command | Evidence |
|---|---|---|
| 01 capture | `rea inspect-web-network-capture <download.devtools> har --detail summary` + 3 `capture` preview pages | parent `ev_579388377fcb…`, 102/102 records |
| 02 JS (default limits) | `rea analyze-javascript-application app/ --detail summary` | `ev_a30fcf315cea…`, 4 files, 883 webpack modules, semantic node ceiling hit |
| 02 JS (raised limits) | same, with `--max-semantic-nodes 600000 --max-semantic-nodes-per-file 400000 --max-semantic-unknowns 300000 --max-semantic-unknowns-per-file 200000 --max-heap-mb 8192` | **`ev_7131e083513834ff…`** (primary), 1,422 module nodes, 39 endpoint nodes, 105k data-flow relations, semantic status partial (result-budget bound) |
| routes view | `inspect-analysis-view` kind `javascript-routes` | empty (see §4) |
| semantic trace | `trace_javascript_semantics` property seed `calculate` | `ev_75f5ad0fa962…` (2 `core.js` matches) |
| live | `rea list-browser-targets http://127.0.0.1:9222` | `endpoint_unreachable`. **Live phase skipped.** |
| env | `rea environment-build marketplace-q1.har evidence/private/rea-env --name marketplace-replay` | capture `ev_5ca070c9…`, manifest `ev_fa72646a…`, state `ev_9ee5c318…` |

## 6. The REA offline environment (replaces our MCP)

`evidence/private/rea-env/` is an AgentEnv bundle (`envs/marketplace-replay/`
Dockerfile, `manifest.json`, `evidence.json`, a smoke task). `rea environment-serve`
can serve it as an MCP agent environment that answers from the capture. This
replaces the 22 hand-written MCP tools. **It contains real captured data**,
including recorded `x-xsrf-token` request-header values (REA warning
`credential-named-members`, 70 pointers). It must never leave `evidence/private`.

What it can and cannot do today:

* It **can** replay the 70 recorded `backend-json.php` exchanges, citing record
  ordinals and Evidence IDs, so an agent can query the Q1 screens offline.
* REA projected **one** tool (`post_mpl_web7_backend_json`), because every RPC is a
  `POST` to the same path and the service only differs in the query string. It served
  **0** tools from derived state (29 static-asset groups excluded). It withheld the
  write with reason `no-state-target`.
* It **cannot** answer any screen or method not in the capture, emulate validation,
  or compute what-if results. It is not a simulator.
* It was **built, not run**. Docker 29.6.2 is installed, but the `agent-env` runner is not.

## 6b. Operator-experiment network guard (safety mechanism, not REA functionality)

`tools/guard/guard.mjs` (local-only; `tools/` is git-ignored) attaches to the operator's page over CDP and intercepts
`backend-json.php` requests with `Fetch.enable`. It continues only whitelisted methods
(`view`, `calculate`, `modify`, `cancel`, plus `TokenProvider.getHeaderToken`, which is
continue-only, with no response or header access). Blocked `ServiceStatus.gs` polls use
`failRequest(BlockedByClient)`. Every other blocked request gets a local
`{"error":-10}` reply instead of `failRequest`. **Reason:** the engine's `errorHandler`
shows a native `alert()` for network failures (codes −4/−5/−6), and the operator rules
forbid dialogs. Code −10 is the client's own "aborted" code and is handled silently. With
either mechanism, nothing reaches the server. The guard logs only service, method, decision and time.

**Policy v3 (tiered), 2026-11-03.** The first two guard versions used a short method
whitelist. They broke the page on every load: REA `capture_browser_scenario` connect mode
always navigates to `start_url`, and a page load needs `TokenProvider.getHeaderToken` and
`StudentInit.runInit`. The guard now applies three tiers. (1) **Baseline**: calls a normal
login/refresh makes anyway (`TokenProvider.getHeaderToken/deleteRefreshToken`,
`StudentInit.runInit/runFinish`, `ServiceStatus.gs`, `Settings.saveSettings/saveQuarterScreenSettings`).
These are allowed because they are not experiment effects, and blocking them only disables the page.
(2) **Experiment**: any `view`; `CD.modify/calculate/cancel/validateLock/prolongLock`.
(3) **Strict**: any `save`, `WrapUp.*`, `Chat.*`, `Email.*`, `createChatSession/createResponse`.
These are blocked and flagged as anomalies. Unknown methods are blocked and logged.
`Email.getNewEmailsCount` (read-only unread counter, fired on every load) was later moved to baseline by operator decision.

**Policy file (v4).** The tiers now live in [`data/guard_policy.json`](../data/guard_policy.json), the single source of truth.
The experiment tier names exactly one screen at a time (EXP-02: `FixedCapacity.view/modify/calculate/cancel/validateLock/prolongLock`;
EXP-01's CD entry is kept under `history`). The script itself stays out of the repository.

**Rebuilding the guard** (about 80 lines of Node ≥ 22; no dependencies):

1. Read `data/guard_policy.json`. Read the mode from a one-line file (`strict` or `selftest-block-view:<Service>`).
2. Open `ws://127.0.0.1:9222/devtools/page/<targetId>` (target from `rea list-browser-targets`); send `Page.enable` and
   `Fetch.enable {patterns:[{urlPattern:"*backend-json.php*", requestStage:"Request"}]}`.
3. On `Fetch.requestPaused`: service = first query token of the URL; method = `JSON.parse(request.postData).method`.
   Classify in the policy's `evaluation_order`: baseline pair → strict (method or service) → selftest → experiment
   (`any_service_methods`, then `service_methods[service]`) → unknown.
4. Allow with `Fetch.continueRequest`. Block with `Fetch.fulfillRequest` (status 200, body `{"error":-10,...}`). Never read
   response bodies or headers.
5. Append one JSON line per request: time, service, method, tier, decision. Log `Page.javascriptDialogOpening` and socket
   close as anomalies. Write a heartbeat status file every 2 s.
6. Before use: an offline table test of the classifier, then the two-phase self-test (block one report `view`, then allow it).

**v5 (hot policy).** The guard re-reads `data/guard_policy.json` whenever its content changes, so the experiment tier
can be switched to the next screen without a restart. `GameInfo.studentsOnline` is in the baseline tier because the
autonomous run checks teammate presence before each screen.

## 6c. Known limitation: REA reconstruction coverage

`evaluate_reconstruction_coverage` was run for the RPC, decision and output boundaries (unknown: `verifier-missing`) and
for the what-if boundary with EXP-02 as a `controlled-replay` verifier (unknown: `package-proof-unknown`,
`verifier-result-incompatible`). REA's fail-closed coverage model targets re-implementations with package proofs and
verifier results matched to artifact/owner digests whose rules are not exposed in the compact schema. This project ships
no re-implementation, so the verdict stays **unknown** by design. The operator chose not to pursue it further; the
evidence for each verified relation is in `docs/experiments/` and `docs/cost-model.md` instead.

## 7. What changed in the repository

* `src/marketplace_mcp` → `src/marketplace_sysid` (security, experiments, model kept; `rea_ingest.py` and `experiments/runbook.py` added).
* `discovery/`, `server.py`, `adapter/`, `graph/`, their tests and the Python-generated `data/*.json` → `legacy/`.
* `pyproject.toml`: no `mcp` dependency, no MCP/discovery entry points. `marketplace-rea-ingest` added. ruff and mypy exclude `legacy/`.
* The publication gate now allows `legacy/` (`.py/.md/.json`) and scans `legacy/data`.
