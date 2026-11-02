# Security and private evidence

This project analyzes only files exported from a browser session the operator is authorized to use. It does not bypass authentication, discover endpoints by probing, call unobserved methods, modify decisions, or submit a quarter.

Keep raw HTML, JavaScript bundles, HAR/DevTools captures, screenshots, response values, cookies, tokens, and account/team identifiers under `evidence/private/`. That directory is ignored by Git. Do not open an issue or pull request containing such material. Report software vulnerabilities without including session material.

The local RPC adapter requires runtime-only environment variables, an explicitly configured HTTPS Marketplace host, and a locally observed `READ` service/method with a matching observed request shape. It suppresses request details in errors, rejects redirects, and has no write or finalization interface. Do not put credentials in `.env` files, command arguments, logs, fixtures, or MCP outputs.

Before publishing, run `python scripts/publication_gate.py` and inspect `git status` and the complete staged diff. The gate checks the staged JSON blobs as well as the working tree, enforces an allowlist of public paths, and verifies the evidence/capture ignore patterns. A clean automated scan is a useful check, not a substitute for reviewing generated data.
