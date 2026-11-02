# Marketplace Simulation MCP

A local-first toolkit for turning a user's own browser exports into a sanitized map of the Marketplace Simulation client, observed RPC contracts, and visible data flow. It keeps private evidence local and labels server-side behavior as opaque when the browser evidence does not show its formula.

## Current reconstruction

The current private capture yields six Quarter 1 HTML pages, 31 observed backend services/methods, 9,435 named JavaScript function symbols, two pure arithmetic client formula records, and seven numeric server-opaque metric fields. The observed RPC methods are 29 `READ` methods and two `UNKNOWN` methods; no write contract was established. See [the reconstruction report](docs/reconstruction-report.md) for scope, evidence limits, and unknowns.

The report describes this specific capture, not a complete map of every Marketplace screen or simulation behavior. Public JSON artifacts contain sanitized schemas and structural metadata only. Raw evidence remains in the ignored `evidence/private/` directory.

## Install and use

Requires Python 3.11 or later.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m marketplace_mcp.discovery.cli --input evidence\private\extracted --output evidence\private\staging_public
.\.venv\Scripts\python.exe scripts\publication_gate.py
```

Review the sanitized staging artifacts and run the publication gate before regenerating the reviewed artifacts under `data/` with `--output data`. The CLI never writes the original request/response values to its output. To start the stdio MCP server after the public data is present, run:

```powershell
.\.venv\Scripts\marketplace-mcp.exe
```

The MCP layer answers from local structural data. Optional runtime RPC access is read-only and requires explicit runtime environment configuration; it is disabled by default and is not used by the MCP tools in this repository.

## What is and is not established

- Browser HTML and JavaScript show UI controllers, route construction, and the browser-side transport flow.
- Captured `POST` requests to `backend-json.php?<service>` carry JSON-RPC-like method/parameter envelopes.
- The visible JavaScript contains a pure arithmetic `quarterlyCapacity(s)` expression. It does not prove how the server calculates simulation outputs.
- The capture contains no demonstrated editable-decision response pairs, so the decision graph records observed protocol data flow rather than causal effects.
- `GameInfo.studentsOnline` and generic `ServiceStatus.gs` are left unknown and are never callable by the adapter.

See [security](SECURITY.md), [legal scope](docs/legal-scope.md), and [provenance rules](docs/provenance.md) before contributing or publishing.

## Method reference

The analysis workflow was informed by [morluto/rea](https://github.com/morluto/rea), especially its local evidence, coverage, and provenance practices. No REA source files or Marketplace assets are redistributed here. This implementation uses the official [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) for its local stdio server.
