# Private play guide (public; contains no data)

Everything below writes **only** under `evidence/private/` (git-ignored). Never copy those files elsewhere.

## 1. Build your private parameter pack

After REA captures exist in `evidence/private/` (see [quarterly-runbook.md](quarterly-runbook.md)):

```powershell
.\.venv\Scripts\mpsim.exe build-pack --out evidence/private/model
```

The builder reads your captured `view` responses and maps them onto the pack schema; each field's origin is listed
in `marketplace_sim.pack.SOURCE_MAP`. It refuses to write outside a `private` directory.

## 2. Start a save at the current quarter

```powershell
.\.venv\Scripts\mpsim.exe new --params evidence/private/model --out evidence/private/saves/q1.json --quarter 1
```

## 3. Write plans

Plans are YAML. Keys: `capacity_increase` (must equal an offered option), `open_stores` / `open_web_centers` (pack keys),
`cd: {deposit, withdraw}`, `stock_issue: [{shares, price}]`, and `brands: [{name, brand_type, price, production,
advertising, components}]`. Keep plans in `evidence/private/plans/`.

## 4. Compare and play

```powershell
.\.venv\Scripts\mpsim.exe compare evidence/private/saves/q1.json "evidence/private/plans/*.yaml"
.\.venv\Scripts\mpsim.exe play evidence/private/saves/q1.json --decisions evidence/private/plans/B.yaml
.\.venv\Scripts\mpsim.exe explain capex_capacity
```

`compare` never modifies the save; `play` advances it one quarter. Every number carries `[V]`, `[D]`, `[E]` or `[P]`.
Treat `[P]` lines (demand, revenue, production cost, tax, profit) as illustrations, not forecasts.

## 5. Keep the save honest

At the end of each real quarter, the per-quarter run resets the private save to the actual company state, so
simulated drift never accumulates.
