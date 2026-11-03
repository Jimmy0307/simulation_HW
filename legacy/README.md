# Legacy: self-built Python discovery + MCP server (deprecated)

**Deprecated since `rea/full-reconstruction` (2026-11-03).** Kept for history and comparison only.

This directory holds the first-round toolkit from branch `codex/marketplace-sim-mcp`
(commit `c731c7c`). Because the local Node.js could not run REA at the time, that
round re-implemented parts of REA in Python (HAR parsing, HTML parsing, a regex
JavaScript symbol scanner) and wrapped the results in a 22-tool stdio MCP server.

The project now uses [REA](https://github.com/morluto/rea) itself as the reverse
engineering and Evidence layer, and REA is already an MCP server. See
[`docs/rea-pivot.md`](../docs/rea-pivot.md).

| Path | What it was | Replaced by |
|---|---|---|
| `marketplace_mcp/discovery/` | HAR/HTML/JS parsers, calculation finder, CLI | REA `inspect_web_network_capture`, `analyze_javascript_application`, `inspect_analysis_view` + `marketplace_sysid.rea_ingest` |
| `marketplace_mcp/server.py` | 22-tool MCP server over local JSON | REA MCP server (`rea mcp`) |
| `marketplace_mcp/adapter/` | Optional read-only live RPC client | Not replaced; live access is out of scope (REA passive observation only) |
| `marketplace_mcp/graph/` | Observed data-flow graph | REA semantic graph + `data/decision_catalog.json` |
| `data/` | Artifacts produced by the Python pipeline | `data/decision_catalog.json`, `data/metric_catalog.json`, `data/rpc_catalog.json` |
| `tests/` | Tests of the code above | `tests/` at the repository root |

The code imports the old package name `marketplace_mcp`, is excluded from mypy and
ruff, is not installed by `pyproject.toml`, and is not exercised by the test suite.
