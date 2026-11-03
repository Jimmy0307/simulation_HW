# Security and private evidence

This project analyzes only files exported from a browser session the operator is authorized to use, through REA. It does not bypass authentication, discover endpoints by probing, call any Marketplace RPC, modify decisions, or submit a quarter. No code in `src/` sends network requests to Marketplace. The round-one read-only RPC adapter is archived in `legacy/` and is not installed.

Keep raw HTML, JavaScript bundles, HAR/DevTools captures, screenshots, response values, cookies, tokens, and account/team identifiers under `evidence/private/`. That directory is ignored by Git. This includes all REA outputs: Evidence bundles, `experiment_values.json`, and the REA AgentEnv bundle `evidence/private/rea-env/`. REA warns that the env bundle contains recorded `x-xsrf-token` header values, so never copy it elsewhere. Don't open an issue or pull request containing such material. Report software vulnerabilities without including session material.

Operator experiments (`docs/experiment-runbook.md`) are performed by a person in their own logged-in browser, with teammate consent. Agents may only observe through REA's passive tools and must never log in, handle credentials, or press Save/Submit-type controls.

Before publishing, run `python scripts/publication_gate.py` and inspect `git status` and the complete staged diff. The gate checks the staged JSON blobs as well as the working tree, enforces an allowlist of public paths, and verifies the evidence/capture ignore patterns. A clean automated scan is a useful check, not a substitute for reviewing generated data.
