# RPC contract (v2, REA-based)

The previous Python-derived version is preserved as `legacy/docs/rpc-contract-v1.md`.

## Transport (verified in client code)

`core.js:5:7918` (REA module `57080`). Every RPC is jQuery `ajax` `POST` to
`<servicePoint>backend-json.php?<Service>` with body `{"method": <m>, "parameters": [...]}`,
header `X-<csrfTokenName>`. The response is `{error, errorMessage, errorDetail, result}`, and
`error != 0` is raised as an API error. `sendBeacon(method, params)` uses `fetch(... keepalive)`
for page-exit calls. The service name is chosen at runtime:

* Screens: `DecisionFactory.getDecision(name)` → `new window[name](name)` → `this.service = name`
  (`sstudent.js:1:182053`, `:1:188141`, REA module `8939`). **Service = class name.**
* Infrastructure: `serviceFactory.getService("<Name>")`.

## Inventory: referenced in JS vs. observed in the capture

| Group | Referenced in client JS (static) | Observed in Q1 capture |
|---|---|---|
| Screen services (`window.X = ….extend`) | **252** (124 decision/finalization screens + 128 reports; 58 helpers excluded) | 29 |
| Infrastructure services | 11: `AccountingDetails`, `Chat`, `Email`, `GameInfo`, `LeftMenu`, `MarketResults`, `Resource`, `ServiceStatus`, `Settings`, `StudentInit`, `TokenProvider` | 2 (`GameInfo`, `ServiceStatus`) |
| Literal-service view calls | `DesignAd`, `DevelopBrand`, `ModifyAd`, `ModifyBrand` (`.fetch("X","view")`) | 1 (`ModifyBrand`) |
| Distinct methods | 8 base-class methods + 30 literal methods found by REA endpoint discovery + 5 class-scoped (`fillCategory`, `createChatSession`, `getChatSessions`, `createResponse`, `getResponse`) + `deleteRefreshToken`, `getRequestToken` | `view`, `gs`, `studentsOnline` |
| Service/method pairs | ≥ 252 × `view` + 124 × 7 decision methods + ~40 infrastructure pairs (upper bound; the server decides which pairs it accepts) | **31** |

The capture shows 70 recognized RPC records (31 pairs) out of 102 entries. REA capture
Evidence: `ev_579388377fcb78fcf4b2c20d9a117f3cbb2778bf3cbf51c8d49379fd879671c4`.

## Base-class methods (every screen service)

Source: `sstudent.js` line 1, REA module `8939`.

| Method | Parameters | Class | Location | Notes |
|---|---|---|---|---|
| `view` | `[user, sendStatic, sendDynamic, sendErrors, sendCalculate]` | READ | `:1:188378` | Returns `{staticData, dynamicData, decisions, errors, calculate, commonData, shareContent}`. Observed. |
| `modify` | `[user, 0]` | STATE_TRACKING (lock) | `:1:188860` | Acquires a server-side edit lock. Returns `{modifyResult, lock{token, lockDuration, lockedByMe, playerName, timeLocked}, dynamicData, decisions, errors, calculate}`. Teammates see "locked by PLAYER". |
| `calculate` | `[user, decisions, 0]` | CALCULATION_TRIGGER | `:1:192346` | Sends **draft** decisions. Returns `{checkResult{ok, errors}, calculateResult}`. Called only while `inModifyMode`. No lock token is sent. |
| `save` | `[user, decisions, 0, lockToken]` | **WRITE** | `:1:193364` | Persists. On `saveResult` the client reloads `view`. |
| `cancel` | `[user, 0, lockToken]` | STATE_TRACKING (unlock) | `:1:194103` | Discards drafts and releases the lock. |
| `removeLock` | `[user, 0]` | STATE_TRACKING | | Offered when the caller already holds the lock in another window. |
| `validateLock` / `prolongLock` | `[user, 0, lockToken]` | STATE_TRACKING | | Timer: prompts 900 s before lock expiry; 3 attempts × 120 s. |

## Statically inferred write contract candidates (never called)

Evidence level: **S** = literal call site in REA-located module text; **R** = also a REA
`discover-static-endpoint` node; **O** = observed in the capture. Only the parameter shape is recorded.

| Service.method | Parameter shape | Effect (inferred from client code) | Evidence |
|---|---|---|---|
| `<every decision screen>.save` | `[user, decisions, 0, lockToken]` | Persists the team's decision for the quarter | S |
| `<every decision screen>.modify` / `cancel` / `removeLock` / `prolongLock` | see above | Lock state (shared with teammates) | S |
| `WrapUp.save` with `decisions={wrapped:true, targetSegments}` | via `wrap()`; `unwrap` saves `{wrapped:false}` | **FINALIZATION**: submits the quarter (menu label "Submit") | S |
| `Settings.saveQuarterScreenSettings` | `[user, quarter, [], [], [{number, message, detail}]]` | Stores screen settings / client error log | S, R |
| `StudentInit.runFinish` (beacon) | `[user, [{service, method, parameters}...]]` | Flushes bundled settings writes on page exit | S, R |
| `StudentInit.runInit` | `[user]` | Session/quarter initialisation (may write) | S, R |
| `Chat.postMessage`, `Chat.joinChannel` | `[user, channel, text, lastId]`, `[user, definition]` | Team chat | S, R |
| `Email.setEmailRead` | `[user, emailId]` | Marks mail read | S, R |
| `saveInstructorSettings`, `saveOverlays` (core.js) | not traced | Instructor/overlay preferences | R |
| `<assistant screen>.createChatSession`, `.createResponse` | `[user, …]` | Creates assistant sessions/responses | S |
| `TokenProvider.deleteRefreshToken` (beacon) | `[refreshToken]` | Auth token lifecycle. Out of scope; never touch. | S |

## Read-type methods (statically referenced)

`GameInfo`: `basicInfo`, `checkSession`, `teamMonitor`, `wrapupStatus`, `liveProForma`, `schedule`,
`studentsOnline` (O), `yourTurnContracts`; `LeftMenu.leftMenuItems`; `Resource.resourceList`;
`AccountingDetails.getDetails([user, item, quarter, proforma])`; `MarketResults.resolve`;
`Chat.getChannels/getMessages/getHistoryMessages`; `Email.getEmails/getNewEmailsCount`;
`StudentInit.welcome`; `ServiceStatus.gs` (O); `<screen>.fillCategory`.
`TokenProvider.getCode/getHeaderToken/getRequestToken` are authentication. They are excluded from all analysis and never called.

## Safety classification used by this repo

Only `view` on screen services and the read-type infrastructure methods above may ever be
*observed* (passively) during operator sessions. `calculate` is a calculation trigger that needs
the `modify` lock. It is listed in the runbook only as an operator-run step that needs teammate
consent. Nothing in this repository sends any RPC.
