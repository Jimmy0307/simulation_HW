# Quarterly runbook (public; contains no data)

## When to run

Each quarter, **after the new quarter opens and before the team makes its decisions**. Running it later still works,
but its main value is decision support.

## What the operator does

1. Ask Claude Code to run the per-quarter command (`/quarter <N>`, a local command file kept out of the repository).
2. When a browser window opens, **log in yourself** and go to the company's main screen. That is the only manual step:
   the agent never types credentials and never saves or submits.
3. Wait for the report. If it shows a red block (a hard stop), follow its instructions; locks expire on their own and
   cancel, never save.

## What the run does (summary)

* Confirms the actual quarter from the page (the actual quarter wins over the argument).
* Starts the network guard ([data/guard_policy.json](../data/guard_policy.json)) and runs its two-phase self-test.
* Captures newly opened screens **read-only** (especially competitor, market-share, scorecard and standings reports).
  It never enters Submit.
* Re-extracts parameters, re-triages calculate screens, and runs what-if experiments on screens that need them, with
  teammate-presence checks and Cancel-only restore.
* Appends whatever competitor/market data is available to the **private demand panel**. After 2 quarters it assesses
  identifiability; after 3 it fits a demand model, validates it on a held-out quarter, and only then promotes demand from
  `placeholder` to `estimated`.
* Diffs this quarter's parameters against last quarter's and flags any change that may require re-verifying a module.
* Updates the private save to the real state and writes a private brief for the quarter.

## How to read the report

| Field | Meaning |
|---|---|
| QUARTER | Actual quarter detected |
| NEW_PAGES | Screens captured for the first time this quarter |
| DEMAND_PANEL | Quarters of market/competitor data collected so far |
| MODEL_STATUS | Source level of each engine module (verified / derived / estimated / placeholder) |
| EXPERIMENTS | What-if experiments: status, relation found, evidence strength |
| BLOCKED_REQUESTS | Anything the guard blocked (expected: self-test only) |

Use `mpsim compare` on the private save to compare candidate plans, and always read the source-level marks: only `[V]`
and `[D]` numbers are measured or exact.
