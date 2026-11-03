# Reconstruction report

## A. Architecture

**Verified:** Six rendered HTML pages reference `core.js`, `sstudent.js`, `sstudent-en-us.js`, and `cdn-check.js`; two unique JavaScript bundle contents were locally available. Client code exposes UI/resource controller and transport symbols. A captured session shows JSON request/response shapes.

**Inferred:** `engine.php` serves as the application shell/resource route entry. Client-generated routes and page markup support this interpretation. `backend-json.php?<Service>` dispatches JSON-RPC-like requests to service handlers based on the repeated observed endpoint and envelope pattern.

**Unknown:** PHP implementation, server state transitions, simulation formulas, unobserved routes, and whether any particular captured read endpoint has side effects beyond the returned read data.

## B. `engine.php`

No PHP source was present or requested. From the rendered shell, client route strings, resource names, and `changeResource`/`play`/`setContent` flow, it appears to render the application and route resource/tab/quarter views. This is an inference from multiple client observations, not a claim about its server implementation.

## C. `backend-json.php`

The capture verifies POST requests whose path is `/mpl/web7/backend-json.php` with a service name in the query. Their JSON bodies use a `method` and `parameters` shape. It appears to be the RPC/service dispatcher. Request and response values are not published.

## D. RPC

There are 102 captured network entries: 70 recognized service observations and 32 requests without a recognized service/method. The normalized registry has 31 service/method contracts. Twenty-nine are classified `READ`; two remain `UNKNOWN` (`GameInfo.studentsOnline`, `ServiceStatus.gs`). No `WRITE`, validation, calculation-trigger, or finalization contract was verified in the available capture. See `docs/rpc-contract.md` and `data/service_registry.json`.

## E. Client calculations

Two exact formula records identify the same client method at two source positions: `quarterlyCapacity(s) = s * this.maxDays` in `client_asset_002.js`, line 4, columns 744663 and 759862. This is an exact browser-side arithmetic expression. It does not prove that the server uses the same expression for production or financial outputs. A name-only heuristic adds 118 unresolved candidate records (38 unique names) to the inventory; no full client transformation of server metrics was verified. See `docs/calculation-map.md`.

## F. Server calculations

Seven numeric response fields remain server opaque: `averageProductivity`, `cash`, `projectDemandNextQuarter`, `projectedCash`, `totalCash`, `warnMaxPrice`, and `warnMinPrice`. No server formula was inferred. Revenue, unit sales, market share, COGS, operating profit, and scorecard numeric outputs were not present in these six captured research pages, so they remain unknown for this evidence set. Other visible calculations that rely on lookups, conditions, or calls were not marked exact.

## G. Decision model

The decision graph records observed request/response dataflow fields to service methods, plus exact client formula edges. It contains 1,095 nodes and 1,062 edges from captured schemas. No verified editable-decision contract or controlled before/after pair exists, so there are no causal decision-to-outcome edges. The HTML navigation labels include Marketing Research, Strategic Planning, Marketing, Human Resources, Sales Channel, Manufacturing, Accounting, Finance, and related strategy/report screens. The parent tree is partial and is not filled by inference.

## H. System identification

The highest-value next observation is a legitimate UI screen with a clearly reversible decision and a preview/recalculation output. Capture its schema and validation first. Then hold state and competitors constant and collect baseline, small minus, and small plus observations for one variable. Only after a reversible preview is established should the operator test an evidenced pair such as price × advertising or capacity × demand. These are proposals, not current results; the toolkit does not execute them. Fit a simple held-out surrogate only after enough controlled observations exist.

## I. MCP status

The local MCP server exposes 22 read/intelligence tools: `list_modules`, `get_module`, `list_services`, `get_service`, `get_rpc_method`, `get_decision_graph`, `trace_decision`, `list_metrics`, `explain_metric`, `list_exact_client_formulas`, `get_formula`, `list_server_opaque_metrics`, `get_customer_needs`, `get_market_segments`, `get_market_potential`, `get_price_willing_to_pay`, `list_experiments`, `propose_experiment`, `get_sensitivity`, `get_interactions`, `get_surrogate_model`, and `explain_provenance`. They read sanitized local artifacts and do not expose credentials. `propose_experiment` emits a dry-run design only.

## J. Security and publication

Both input ZIPs and extracted content are under ignored `evidence/private/`. Public artifacts were generated into an ignored staging directory and scanned before being copied. The publication gate enforces an allowlist of public roots and extensions, verifies required ignore patterns, rejects private evidence/raw capture/static media paths, and scans both working and staged JSON/fixture payloads. At report generation, the gate found no forbidden paths or sensitive-pattern matches. Raw HAR, HTML dumps, downloaded Marketplace bundles/assets, session data, account IDs, and private Marketplace response values are excluded.

## Limits and tool reference

The analysis workflow was informed by [morluto/rea](https://github.com/morluto/rea); no REA implementation or Marketplace asset is redistributed. The REA CLI was not run because the installed Node v24.18.0 is below REA's current v24.22.1 minimum for the Node 24 line. Its repository served as a methodology reference only. The MCP server uses the official [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk).
