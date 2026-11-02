# Observable architecture

## Evidence map

| Claim | Status | Evidence |
|---|---|---|
| Rendered pages load browser JavaScript assets including `core.js` and `sstudent.js` | `VERIFIED_RENDERED_HTML` | Six local HTML exports; asset names only are published |
| The UI controller routes resources and loads view content | `VERIFIED_CLIENT_CODE` | Static call graph includes `menuClickCallback`, `changeResource`, `play`, `setContent`, and `doLoad` |
| The client transport sends JSON requests through `core.js` functions resembling `fetch`, `ajax`, and `send` | `VERIFIED_CLIENT_CODE` | Static symbols and call edges, with one captured request initiator stack |
| Service requests use `POST /mpl/web7/backend-json.php?<Service>` and JSON envelopes with a `method` and `parameters` | `VERIFIED_NETWORK_TRACE` | Sanitized HAR schemas and endpoint aliases |
| `engine.php` is the application shell/resource router | `INFERRED_FROM_MULTIPLE_OBSERVATIONS` | HTML pages, client route strings, and resource-loading call flow; server PHP source was not present |
| `backend-json.php` dispatches requests to service handlers | `INFERRED_FROM_MULTIPLE_OBSERVATIONS` | Service query names and repeated JSON request/response patterns; server implementation was not present |
| Server-side simulation formulas and persistent-state implementation | `UNKNOWN` | Not delivered in browser evidence |

```mermaid
flowchart TD
    B[Browser] -->|rendered shell and resource route| E[engine.php]
    E -->|HTML references client assets| U[sstudent.js UI controller]
    U -->|view and resource flow| C[core.js transport]
    C -->|POST JSON RPC: service, method, parameters| J[backend-json.php?Service]
    J -->|opaque service processing| S[Marketplace service and simulation state]
    S -->|JSON response| C
```

The diagram distinguishes what the browser shows from what is inferred about the server. Neither PHP implementation was acquired, and no attempt was made to obtain it.

## Analysis workflow reference

The local evidence-first approach was informed by [REA](https://github.com/morluto/rea): keep coverage visible, preserve provenance, and record unknowns. Its CLI was not run here because installed Node v24.18.0 is below REA's current v24.22.1 minimum for the Node 24 line. This project uses its own Python parsers on local evidence.
