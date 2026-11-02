# Provenance model

Every public assertion should use one of these statuses:

| Status | Meaning |
|---|---|
| `VERIFIED_CLIENT_CODE` | A browser-delivered client bundle contains the symbol or expression |
| `VERIFIED_NETWORK_TRACE` | A local authenticated-session capture contains the request/response structure |
| `VERIFIED_RENDERED_HTML` | A rendered page export contains the safe structural element |
| `VERIFIED_RUNTIME_OBSERVATION` | A controlled, repeatable observation was made while operating the authorized UI |
| `INFERRED_FROM_MULTIPLE_OBSERVATIONS` | Multiple evidence items support a cautious architectural interpretation |
| `SURROGATE_MODEL` | A fitted approximation to collected observations |
| `PUBLIC_EXTERNAL_SOURCE` | A public source supports a methodology or dependency statement |
| `UNKNOWN` | Evidence is absent, conflicting, or insufficient |

Edges also carry a relation class: `DIRECT_FORMULA`, `OBSERVED_DEPENDENCY`, `LIKELY_DEPENDENCY`, `CORRELATION_ONLY`, or `UNKNOWN`. Confidence is about the stated evidence-backed relation, not the hidden server implementation. A request field adjacent to a response field is not proof of business causality.

Private evidence is mapped to generated aliases such as `page_001.html`, `capture_001:entry_1`, and `client_asset_002.js`. The mapping file remains under ignored `evidence/private/`. Public artifacts contain aliases and shapes, not raw paths, headers, request values, response values, or identifiers.
