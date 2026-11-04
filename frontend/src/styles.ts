// All styles live here (injected once by main.tsx). The repository's publication gate does not allow .css files.

export const CSS = `
:root {
  --bg: #f6f6f3; --surface: #ffffff; --surface-2: #f0f1ee; --text: #1b1f24; --muted: #5d6670; --border: #e1e3e6;
  --accent: #2f5bea; --accent-ink: #ffffff; --warn-bg: #fff4d6; --warn-ink: #6b4a00; --danger: #c4231a;
  --private-bg: #b42318; --synthetic-bg: #1f6f43;
  --lv-verified: #1a7f37; --lv-derived: #0b62c4; --lv-estimated: #9a6700; --lv-literature: #8250df; --lv-placeholder: #c4231a;
  --shadow: 0 1px 2px rgba(16, 24, 40, .06), 0 1px 3px rgba(16, 24, 40, .08);
  --radius: 12px; --mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  color-scheme: light;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #0e1116; --surface: #161b22; --surface-2: #1d232c; --text: #e6e9ed; --muted: #9aa4af; --border: #2a313b;
    --accent: #7aa2ff; --accent-ink: #0e1116; --warn-bg: #3a2f10; --warn-ink: #f5d27a; --danger: #ff7b72;
    --private-bg: #d1242f; --synthetic-bg: #2d8a57;
    --lv-verified: #4ac26b; --lv-derived: #58a6ff; --lv-estimated: #e3b341; --lv-literature: #c297ff; --lv-placeholder: #ff7b72;
    --shadow: none; color-scheme: dark;
  }
}
:root[data-theme="dark"] {
  --bg: #0e1116; --surface: #161b22; --surface-2: #1d232c; --text: #e6e9ed; --muted: #9aa4af; --border: #2a313b;
  --accent: #7aa2ff; --accent-ink: #0e1116; --warn-bg: #3a2f10; --warn-ink: #f5d27a; --danger: #ff7b72;
  --private-bg: #d1242f; --synthetic-bg: #2d8a57;
  --lv-verified: #4ac26b; --lv-derived: #58a6ff; --lv-estimated: #e3b341; --lv-literature: #c297ff; --lv-placeholder: #ff7b72;
  --shadow: none; color-scheme: dark;
}
* { box-sizing: border-box; }
html, body { margin: 0; background: var(--bg); color: var(--text); }
body { font: 14px/1.5 "Inter", system-ui, -apple-system, "Segoe UI", "Noto Sans TC", "Microsoft JhengHei", sans-serif; }
button, input, select { font: inherit; color: inherit; }
a { color: var(--accent); }
.shell { display: grid; grid-template-columns: 232px 1fr; min-height: 100vh; }
.side { border-right: 1px solid var(--border); padding: 20px 14px; position: sticky; top: 0; height: 100vh; background: var(--surface); }
.brand { font-weight: 700; font-size: 16px; margin: 0 6px 4px; }
.brand small { display: block; font-weight: 400; color: var(--muted); font-size: 12px; }
.nav { display: flex; flex-direction: column; gap: 2px; margin-top: 18px; }
.nav a { text-decoration: none; color: var(--text); padding: 8px 10px; border-radius: 8px; display: flex; gap: 10px; align-items: center; }
.nav a:hover { background: var(--surface-2); }
.nav a[aria-current="page"] { background: var(--accent); color: var(--accent-ink); }
.nav .num { font-variant-numeric: tabular-nums; opacity: .7; width: 16px; }
.main { padding: 22px 28px 60px; min-width: 0; }
.topbar { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; justify-content: space-between; margin-bottom: 18px; }
.topbar h1 { font-size: 22px; margin: 0; letter-spacing: -.01em; }
.badges { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.pill { display: inline-flex; align-items: center; gap: 6px; border-radius: 999px; padding: 3px 10px; font-size: 12px; font-weight: 600; border: 1px solid var(--border); background: var(--surface); }
.pack-synthetic { background: var(--synthetic-bg); color: #fff; border-color: transparent; }
.pack-private { background: var(--private-bg); color: #fff; border-color: transparent; animation: pulse 2.4s ease-in-out infinite; }
@keyframes pulse { 50% { filter: brightness(1.15); } }
@media (prefers-reduced-motion: reduce) { .pack-private { animation: none; } }
.card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); box-shadow: var(--shadow); padding: 16px 18px; margin-bottom: 16px; min-width: 0; }
.card h2 { font-size: 15px; margin: 0 0 12px; }
.card h3 { font-size: 13px; margin: 14px 0 8px; color: var(--muted); text-transform: uppercase; letter-spacing: .04em; }
.grid { display: grid; gap: 16px; }
.grid.cols-4 { grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); }
.grid.cols-2 { grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); }
.stat .label { color: var(--muted); font-size: 12px; }
.stat .value { font-size: 22px; font-weight: 650; font-variant-numeric: tabular-nums; }
.muted { color: var(--muted); }
.banner { border-radius: var(--radius); padding: 12px 16px; margin-bottom: 16px; display: flex; gap: 10px; align-items: flex-start; border: 1px solid transparent; }
.banner.warn { background: var(--warn-bg); color: var(--warn-ink); border-color: color-mix(in srgb, var(--warn-ink) 30%, transparent); }
.banner.danger { background: color-mix(in srgb, var(--danger) 14%, var(--surface)); color: var(--text); border-color: var(--danger); }
.banner.info { background: var(--surface-2); }
.banner b { white-space: nowrap; }
.table-wrap { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; }
th, td { padding: 7px 10px; border-bottom: 1px solid var(--border); text-align: right; white-space: nowrap; vertical-align: top; }
th { font-size: 12px; color: var(--muted); font-weight: 600; position: sticky; top: 0; background: var(--surface); }
th:first-child, td:first-child { text-align: left; }
tr.diff-row td { background: color-mix(in srgb, var(--accent) 7%, transparent); }
td.changed { box-shadow: inset 3px 0 0 var(--accent); }
tr.reverify td { background: color-mix(in srgb, var(--danger) 10%, transparent); }
tr.worst td { background: color-mix(in srgb, var(--danger) 8%, transparent); }
.mono { font-family: var(--mono); font-size: 12px; }
.btn { border: 1px solid var(--border); background: var(--surface); border-radius: 8px; padding: 7px 14px; cursor: pointer; font-weight: 600; }
.btn:hover:not(:disabled) { background: var(--surface-2); }
.btn.primary { background: var(--accent); color: var(--accent-ink); border-color: transparent; }
.btn:disabled { opacity: .5; cursor: not-allowed; }
.row { display: flex; gap: 10px; flex-wrap: wrap; align-items: end; }
.field { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--muted); }
.field input, .field select { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 6px 8px; min-width: 90px; color: var(--text); }
.field input[type="checkbox"] { min-width: 0; }
.checks { display: flex; gap: 12px; flex-wrap: wrap; }
.checks label { display: inline-flex; gap: 6px; align-items: center; font-size: 13px; color: var(--text); }
.error { color: var(--danger); font-weight: 600; }
.note { color: var(--muted); font-size: 12px; }

/* --- source levels ------------------------------------------------------------------------------------------- */
.lv { --lv: var(--lv-placeholder); }
.lv-verified { --lv: var(--lv-verified); } .lv-derived { --lv: var(--lv-derived); } .lv-estimated { --lv: var(--lv-estimated); }
.lv-literature { --lv: var(--lv-literature); } .lv-placeholder { --lv: var(--lv-placeholder); }
.num { position: relative; display: inline-flex; align-items: center; gap: 6px; justify-content: flex-end; outline: none; }
.num .v { color: var(--lv); font-weight: 600; }
.num.uncal .v { text-decoration: underline dotted var(--lv); text-underline-offset: 3px; }
.mark { display: inline-grid; place-items: center; min-width: 18px; height: 18px; border-radius: 5px; font-size: 10.5px; font-weight: 800; color: #fff; background: var(--lv); }
.uncal-chip { font-size: 10.5px; font-weight: 800; letter-spacing: .02em; padding: 1px 6px; border-radius: 5px; border: 1.5px solid var(--lv); color: var(--lv);
  background: repeating-linear-gradient(135deg, color-mix(in srgb, var(--lv) 16%, transparent) 0 4px, transparent 4px 8px); white-space: nowrap; }
.tip { display: none; position: absolute; z-index: 30; top: calc(100% + 6px); right: 0; width: min(440px, 80vw); text-align: left; white-space: normal;
  background: var(--surface); color: var(--text); border: 1px solid var(--border); border-left: 4px solid var(--lv); border-radius: 10px; padding: 10px 12px;
  box-shadow: 0 8px 28px rgba(0, 0, 0, .18); font-weight: 400; font-size: 12.5px; }
.num:hover .tip, .num:focus .tip, .num:focus-within .tip { display: block; }
.tip .tip-title { font-weight: 700; margin-bottom: 4px; }
.tip ol { margin: 6px 0 0; padding-left: 18px; }
.tip li { margin: 2px 0; }
.tip code { font-family: var(--mono); font-size: 11.5px; }
.legend { display: flex; gap: 14px; flex-wrap: wrap; align-items: center; font-size: 12px; }
.legend span { display: inline-flex; gap: 6px; align-items: center; }
.chart { width: 100%; height: auto; }
.chart text { fill: var(--muted); font-size: 11px; }
.chart .axis { stroke: var(--border); }
.chart .event { stroke: var(--danger); stroke-dasharray: 3 3; }
.chart .event-label { fill: var(--danger); font-weight: 700; }
.bar { fill: var(--accent); opacity: .85; }
/* --- game mode ------------------------------------------------------------------------------------------------ */
/* A town at dusk: the board is the one bold element (lit buildings for open outlets); everything around it stays quiet. */
.game, .game-setup {
  --g-board: #d6e3e9; --g-land: #e7eddd; --g-edge-l: #b9c6aa; --g-edge-r: #a3b195; --g-lot: #ced7c3; --g-lot-line: #adb8a2;
  --g-paved: #e2e5e8; --g-tree: #8cad83; --g-trunk: #7c6b56; --g-wall-l: #6d899f; --g-wall-r: #526d84; --g-roof: #aabdcc;
  --g-lit: #ffbf3f; --g-accent: #00788f; --g-accent-ink: #ffffff; --g-rival: #a7b0b9; --g-est: #8a929b; --g-ok: #5c9a48;
  --g-frame-1: #00788f; --g-frame-2: #8a3f8f; --g-frame-3: #b88700; --g-frame-4: #3e5fa8;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) .game, :root:not([data-theme="light"]) .game-setup {
    --g-board: #0f1b24; --g-land: #1c2b27; --g-edge-l: #14211d; --g-edge-r: #0e1814; --g-lot: #25342e; --g-lot-line: #34463e;
    --g-paved: #2c3a42; --g-tree: #2f5b3f; --g-trunk: #4b4137; --g-wall-l: #3b546a; --g-wall-r: #2a3f53; --g-roof: #5d7589;
    --g-lit: #ffc24a; --g-accent: #22a6bd; --g-accent-ink: #0e1116; --g-rival: #4b545d; --g-est: #7d8792; --g-ok: #6fb35a;
    --g-frame-1: #2bb3c9; --g-frame-2: #c27cc7; --g-frame-3: #e0b32e; --g-frame-4: #7f9ae0;
  }
}
:root[data-theme="dark"] .game, :root[data-theme="dark"] .game-setup {
  --g-board: #0f1b24; --g-land: #1c2b27; --g-edge-l: #14211d; --g-edge-r: #0e1814; --g-lot: #25342e; --g-lot-line: #34463e;
  --g-paved: #2c3a42; --g-tree: #2f5b3f; --g-trunk: #4b4137; --g-wall-l: #3b546a; --g-wall-r: #2a3f53; --g-roof: #5d7589;
  --g-lit: #ffc24a; --g-accent: #22a6bd; --g-accent-ink: #0e1116; --g-rival: #4b545d; --g-est: #7d8792; --g-ok: #6fb35a;
  --g-frame-1: #2bb3c9; --g-frame-2: #c27cc7; --g-frame-3: #e0b32e; --g-frame-4: #7f9ae0;
}
.game { display: flex; flex-direction: column; padding-bottom: 8px; }
.game .btn.primary, .game-setup .btn.primary { background: var(--g-accent); color: var(--g-accent-ink); }
.game :focus-visible { outline: 2px solid var(--g-accent); outline-offset: 2px; }
/* setup screen */
.game-setup .setup-hero { display: flex; gap: 22px; align-items: center; }
.setup-icon { flex: none; }
.choice-row { display: flex; gap: 8px; flex-wrap: wrap; }
.choice { display: inline-flex; gap: 8px; align-items: center; border: 1px solid var(--border); border-radius: 10px; padding: 8px 12px; cursor: pointer; }
.choice.on { border-color: var(--g-accent); box-shadow: inset 0 0 0 1px var(--g-accent); }
.choice.off { opacity: .55; cursor: not-allowed; }
.count-readout { font-weight: 700; margin: 4px 0 8px; }
.opponents { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 8px; }
.btn.big { padding: 11px 22px; font-size: 15px; }
.btn.small { padding: 3px 10px; font-size: 12px; }
/* top strip */
.strip { display: flex; flex-wrap: wrap; gap: 10px 18px; align-items: center; margin-bottom: 14px; }
.source-tag { display: inline-flex; align-items: baseline; gap: 8px; padding: 5px 13px; border-radius: 999px; color: #fff; font-weight: 700; font-size: 13px; }
.source-tag small { font-weight: 500; opacity: .88; font-size: 12px; }
.source-tag.synthetic { background: var(--synthetic-bg); }
.source-tag.private { background: var(--private-bg); }
.rivals { display: inline-flex; gap: 4px; align-items: center; font-size: 12.5px; }
.rival-dot { width: 22px; height: 22px; border-radius: 50%; display: grid; place-items: center; font-size: 11.5px; font-weight: 700;
  background: var(--surface-2); color: var(--text); box-shadow: inset 0 0 0 1.5px var(--g-rival); }
.rival-dot.d-aggressive { background: var(--text); color: var(--surface); box-shadow: none; }
.rival-dot.d-conservative { background: transparent; box-shadow: inset 0 0 0 1.5px var(--g-rival); border: 1.5px dashed transparent; }
.rivals .muted { margin-left: 4px; }
.timeline { display: inline-flex; gap: 6px; align-items: center; font-size: 12.5px; }
.timeline ol { list-style: none; display: flex; gap: 4px; margin: 0; padding: 0; }
.q-chip { border: 1px solid var(--border); background: var(--surface); border-radius: 999px; padding: 2px 10px; font-weight: 650; cursor: pointer; font-size: 12.5px; }
.q-chip:hover { border-color: var(--g-accent); }
.levels-switch { margin-left: auto; display: inline-flex; align-items: center; gap: 8px; background: none; border: 0; cursor: pointer; font-size: 12.5px; color: var(--muted); padding: 4px; }
.switch-knob { width: 30px; height: 18px; border-radius: 9px; background: var(--border); position: relative; transition: background .2s; }
.switch-knob::after { content: ""; position: absolute; top: 2px; left: 2px; width: 14px; height: 14px; border-radius: 50%; background: var(--surface); transition: transform .2s; }
.levels-switch[aria-checked="true"] { color: var(--text); }
.levels-switch[aria-checked="true"] .switch-knob { background: var(--g-accent); }
.levels-switch[aria-checked="true"] .switch-knob::after { transform: translateX(12px); }
.demo-line { margin: -4px 0 12px; font-size: 12.5px; color: var(--muted); }
/* stage: board + bikes, and the side panel when something is selected */
.stage { display: grid; grid-template-columns: minmax(0, 1fr); gap: 16px; align-items: start; }
.stage.with-sheet { grid-template-columns: minmax(0, 1fr) 360px; }
.board { margin: 0; background: var(--g-board); border-radius: 20px; padding: 6px 10px 8px; }
.board svg { display: block; width: 100%; height: auto; max-height: 54vh; }
.board-key { display: flex; gap: 16px; flex-wrap: wrap; justify-content: center; font-size: 12px; color: var(--muted); padding: 2px 0 4px; }
.board-key span { display: inline-flex; gap: 6px; align-items: center; }
.key { display: inline-block; width: 12px; height: 12px; border-radius: 3px; }
.key.open { background: var(--g-lit); box-shadow: 0 0 6px var(--g-lit); }
.key.planned { border: 1.5px dashed var(--g-accent); }
.key.closed { background: var(--g-lot); border: 1px solid var(--g-lot-line); }
.board .land { fill: var(--g-land); }
.board .skirt-l { fill: var(--g-edge-l); }
.board .skirt-r { fill: var(--g-edge-r); }
.board .plate-name { fill: var(--muted); font-size: 13px; font-weight: 600; }
.plot { cursor: pointer; outline: none; }
.plot .lot { fill: var(--g-lot); stroke: var(--g-lot-line); stroke-width: 1; transition: fill .3s ease-out, stroke .15s; }
.plot.open .lot, .plot.planned .lot { fill: var(--g-paved); }
.plot:hover .lot { stroke: var(--g-accent); stroke-width: 2; }
.plot.selected .lot, .plot:focus-visible .lot { stroke: var(--g-accent); stroke-width: 3.5; }
.plot-name { fill: var(--text); font-size: 13px; font-weight: 650; paint-order: stroke; stroke: var(--g-land); stroke-width: 4px; stroke-linejoin: round; pointer-events: none; }
.plot.closed .plot-name { fill: var(--muted); font-weight: 500; }
.plot.selected .plot-name { fill: var(--g-accent); }
.wall-l { fill: var(--g-wall-l); } .wall-r { fill: var(--g-wall-r); } .roof { fill: var(--g-roof); }
.windows line { stroke: var(--g-lit); stroke-width: 2.2; stroke-dasharray: 3 3.5; }
.glow { fill: url(#g-glow); }
.trees line { stroke: var(--g-trunk); stroke-width: 2; }
.trees circle { fill: var(--g-tree); }
.mast { stroke: var(--g-wall-r); stroke-width: 2; }
.signal { stroke: var(--g-lit); stroke-width: 2; fill: none; stroke-linecap: round; }
.ghost .wall-l, .ghost .wall-r, .ghost .roof { fill: color-mix(in srgb, var(--g-accent) 12%, transparent); stroke: var(--g-accent); stroke-width: 1.2; stroke-dasharray: 4 3; }
.ghost .windows { display: none; }
.ghost .mast, .ghost .signal { stroke: var(--g-accent); stroke-dasharray: 3 3; }
.town { transform-box: fill-box; transform-origin: 50% 100%; animation: rise .38s ease-out; }
@keyframes rise { from { opacity: 0; transform: scaleY(.25); } to { opacity: 1; transform: none; } }
/* bikes */
.garage { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 14px; margin-top: 16px; }
.bike-card { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 12px 16px 16px; display: flex; flex-direction: column; gap: 6px;
  transition: box-shadow .25s ease-out, border-color .25s ease-out; }
.bike-card.selected { border-color: var(--g-accent); box-shadow: 0 0 0 2px color-mix(in srgb, var(--g-accent) 30%, transparent); }
.bike-card.bump { box-shadow: 0 0 0 4px color-mix(in srgb, var(--g-accent) 18%, transparent); }
.bike-stage { display: grid; place-items: center; padding: 4px 0 0; }
.bike-title h3 { margin: 0; font-size: 16px; }
.bike-title .muted { font-size: 12.5px; }
.bike-price { margin: 4px 0 0; display: flex; align-items: baseline; gap: 8px; }
.bike-price-v { font-size: 28px; font-weight: 750; font-variant-numeric: tabular-nums; letter-spacing: -.01em; line-height: 1.1; }
.bike-price .muted { font-size: 12.5px; }
.btn.tune { align-self: flex-start; margin-top: 6px; }
.bike-add { border: 1.5px dashed var(--border); background: transparent; border-radius: 16px; min-height: 220px; color: var(--muted); font-size: 15px; font-weight: 600;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px; cursor: pointer; }
.bike-add:hover { border-color: var(--g-accent); color: var(--text); }
.bike-add-plus { font-size: 28px; line-height: 1; }
.bike { display: block; max-width: 100%; height: auto; }
.bike-tyre { fill: none; stroke: var(--text); stroke-width: 5; }
.bike-rim { fill: none; stroke: var(--muted); stroke-width: 1.2; }
.bike-spokes { stroke: var(--muted); stroke-width: .9; opacity: .55; }
.bike-hub { fill: var(--text); }
.bike-saddle, .bike-bars { stroke: var(--text); stroke-width: 5; stroke-linecap: round; fill: none; }
.bike-crank { fill: var(--surface); stroke: var(--text); stroke-width: 2.5; }
.bike-shadow { fill: var(--text); opacity: .08; }
/* price against cost and willingness to pay */
.gauge { margin-top: 2px; }
.gauge-track { position: relative; height: 8px; border-radius: 4px; background: var(--surface-2); margin: 12px 8px 8px; }
.gauge-band { position: absolute; top: 0; bottom: 0; background: color-mix(in srgb, var(--g-ok) 38%, transparent); border-radius: 4px; }
.gauge-cost { position: absolute; top: -5px; width: 2px; height: 18px; background: var(--g-est); transform: translateX(-1px); border-radius: 1px; }
.gauge-price { position: absolute; top: 50%; width: 16px; height: 16px; border-radius: 50%; background: var(--g-accent); border: 3px solid var(--surface);
  box-shadow: 0 0 0 1px var(--g-accent); transform: translate(-50%, -50%); transition: left .25s ease-out; }
.gauge-legend { display: flex; justify-content: space-between; gap: 8px; font-size: 12px; color: var(--muted); }
.gauge-legend .fig { color: var(--text); font-weight: 600; }
/* numbers: trusted plain; uncalibrated with a quiet ≈ and a hover note */
.fig { font-variant-numeric: tabular-nums; font-weight: 600; border-radius: 4px; transition: background-color .6s ease-out; }
.fig.tick { background: color-mix(in srgb, var(--g-accent) 20%, transparent); transition: none; }
.fig.est { position: relative; font-weight: 500; cursor: help; outline: none; }
.fig-approx { color: var(--g-est); font-weight: 400; margin-right: 2px; }
.fig-tip { display: none; position: absolute; z-index: 40; top: calc(100% + 6px); right: 0; width: max-content; max-width: 240px; background: var(--text); color: var(--bg);
  font-size: 12px; font-weight: 400; padding: 7px 10px; border-radius: 8px; text-align: left; white-space: normal; line-height: 1.45; }
.fig-tip b { display: block; font-weight: 650; }
.fig.est:hover .fig-tip, .fig.est:focus .fig-tip { display: block; }
.status-bar .fig-tip { top: auto; bottom: calc(100% + 6px); left: 0; right: auto; }
.fig.full { display: inline-flex; }
/* side panel */
.sheet { background: var(--surface); border: 1px solid var(--border); border-radius: 18px; padding: 14px 18px 18px; position: sticky; top: 12px;
  max-height: calc(100vh - 130px); overflow: auto; animation: sheet-in .22s ease-out; }
@keyframes sheet-in { from { opacity: 0; transform: translateX(14px); } to { opacity: 1; transform: none; } }
.sheet-head { display: flex; justify-content: space-between; align-items: center; gap: 10px; }
.sheet-head h2 { margin: 0; font-size: 20px; outline: none; }
.sheet-status { color: var(--muted); font-size: 13px; margin: 4px 0 10px; }
.sheet-sub { font-size: 13.5px; margin: 18px 0 6px; font-weight: 650; }
.sheet-bike { display: grid; place-items: center; background: var(--surface-2); border-radius: 14px; padding: 8px 0; margin-bottom: 12px; }
.sheet .field { margin-bottom: 8px; }
.sheet .field input, .sheet .field select { width: 100%; }
.btn.wide { width: 100%; padding: 10px; margin: 2px 0 10px; }
.btn.quiet-danger { margin-top: 18px; color: var(--danger); background: transparent; }
.icon-btn { border: 1px solid var(--border); background: var(--surface); border-radius: 8px; width: 30px; height: 30px; cursor: pointer; font-size: 16px; flex: none; }
.stats { display: grid; margin: 8px 0; }
.stat-line { display: flex; justify-content: space-between; gap: 12px; border-bottom: 1px solid var(--border); padding: 6px 0; }
.stat-line dt { color: var(--muted); }
.stat-line dd { margin: 0; }
.seg-table th, .seg-table td { padding: 5px 6px; white-space: normal; }
.seg-needs { display: block; font-size: 11.5px; }
.config-group { display: flex; flex-direction: column; gap: 4px; margin: 8px 0; }
.config-name { font-size: 12px; color: var(--muted); }
.seg { display: flex; flex-wrap: wrap; gap: 4px; }
.seg-btn { border: 1px solid var(--border); background: var(--surface); border-radius: 8px; padding: 4px 10px; font-size: 12.5px; cursor: pointer; }
.seg-btn[aria-pressed="true"], .seg-btn[aria-checked="true"] { background: var(--g-accent); color: var(--g-accent-ink); border-color: transparent; }
.seg-btn:disabled { cursor: not-allowed; opacity: .75; }
.slider { display: flex; flex-direction: column; gap: 2px; margin: 8px 0; }
.slider-head { display: flex; justify-content: space-between; font-size: 12.5px; color: var(--muted); }
.slider-value { color: var(--text); font-variant-numeric: tabular-nums; }
.slider input { width: 100%; accent-color: var(--g-accent); }
/* bottom status bar */
.status-bar { position: sticky; bottom: 0; z-index: 25; display: flex; align-items: center; gap: 10px 24px; flex-wrap: wrap; margin-top: 16px;
  background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 10px 14px 10px 18px; box-shadow: 0 -6px 24px rgba(0, 0, 0, .08); }
.status-q { display: flex; align-items: baseline; gap: 3px; }
.status-q b { font-size: 30px; line-height: 1; font-weight: 800; font-variant-numeric: tabular-nums; }
.status-q small { color: var(--muted); font-size: 13px; }
.status-item { display: flex; flex-direction: column; line-height: 1.3; }
.status-item > span:first-child { font-size: 12px; color: var(--muted); }
.status-item .fig { font-size: 16px; }
.goal-text { font-weight: 600; max-width: 260px; }
.status-actions { margin-left: auto; display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.status-problem { color: var(--danger); font-size: 13px; }
/* report card */
.settle-backdrop { position: fixed; inset: 0; background: rgba(10, 14, 20, .5); display: grid; place-items: center; z-index: 50; padding: 16px; }
.report-card { background: var(--surface); border-radius: 20px; width: min(820px, 100%); max-height: 90vh; overflow: auto; padding: 22px 26px;
  box-shadow: 0 24px 60px rgba(0, 0, 0, .3); animation: card-in .32s ease-out; }
@keyframes card-in { from { opacity: 0; transform: translateY(12px) scale(.98); } to { opacity: 1; transform: none; } }
.report-head { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.report-q { margin: 0; display: flex; align-items: baseline; gap: 6px; font-size: 18px; font-weight: 600; }
.report-q b { font-size: 46px; line-height: 1; font-weight: 800; color: var(--g-accent); font-variant-numeric: tabular-nums; }
.report-body { display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr); gap: 28px; margin: 20px 0 6px; }
.report-sub, .share-chart figcaption { font-size: 13.5px; font-weight: 650; margin: 0 0 10px; }
.share-chart { margin: 0; }
.share-chart ol { list-style: none; padding: 0; margin: 0; display: grid; gap: 9px; }
.share-chart li { display: grid; grid-template-columns: 104px minmax(0, 1fr) 70px; gap: 10px; align-items: center; font-size: 13px; }
.share-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.share-track { height: 14px; display: block; }
.share-bar { display: block; height: 100%; background: var(--g-rival); border-radius: 0 4px 4px 0; transition: width .5s ease-out; }
.share-chart li.us .share-bar { background: var(--g-accent); }
.share-chart li.us .share-name { font-weight: 700; }
.share-value { text-align: right; }
.key-results { margin: 0; }
.kr { display: flex; justify-content: space-between; gap: 12px; padding: 7px 0; border-bottom: 1px solid var(--border); }
.kr dt { color: var(--muted); }
.kr dd { margin: 0; font-size: 15px; }
.summary-note { font-size: 12.5px; color: var(--muted); margin: 14px 0 6px; }
.details { margin-top: 6px; }
.details summary { cursor: pointer; font-weight: 600; padding: 6px 0; }
.detail-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 6px 18px; }
.details h4 { font-size: 13px; margin: 10px 0 4px; }
.detail-table td { padding: 4px 6px; white-space: normal; }
.detail-table td:first-child { color: var(--muted); }
.engine-notes { color: var(--muted); font-size: 12px; margin: 4px 0 0; padding-left: 18px; }
@media (prefers-reduced-motion: reduce) {
  .town, .sheet, .report-card { animation: none; }
  .bike-card, .gauge-price, .share-bar, .fig, .plot .lot, .switch-knob, .switch-knob::after { transition: none; }
}
@media (max-width: 1100px) {
  .stage.with-sheet { grid-template-columns: minmax(0, 1fr); }
  .sheet { position: static; max-height: none; }
  .report-body { grid-template-columns: minmax(0, 1fr); }
}
@media (max-width: 860px) {
  .shell { grid-template-columns: 1fr; }
  .side { position: static; height: auto; border-right: 0; border-bottom: 1px solid var(--border); }
  .nav { flex-direction: row; flex-wrap: wrap; }
  .main { padding: 16px; }
}
/* --- business modules: practice badge, maturity, module board, ledger overview ----------------------------------- */
/* ladder / tile colours: validated with the dataviz palette checker (CVD and normal-vision separation, contrast) */
:root { --lv-heuristic: #a34f00; --practice-bg: #ffb02e; --practice-ink: #241500; --m-none: #8a929b;
  --m-verified: #1a7f37; --m-literature: #8250df; --m-heuristic: #c27a00; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --lv-heuristic: #ffa94d; --practice-bg: #f0a020; --practice-ink: #1a1000; --m-none: #6b747e;
  --m-verified: #2f9a52; --m-literature: #9670e0; --m-heuristic: #c98410; } }
:root[data-theme="dark"] { --lv-heuristic: #ffa94d; --practice-bg: #f0a020; --practice-ink: #1a1000; --m-none: #6b747e;
  --m-verified: #2f9a52; --m-literature: #9670e0; --m-heuristic: #c98410; }
.lv-heuristic { --lv: var(--lv-heuristic); }
.practice-badge { position: relative; display: inline-flex; align-items: center; gap: 3px; font-size: 11px; font-weight: 800; line-height: 1;
  letter-spacing: .04em; padding: 3px 6px; border-radius: 5px; color: var(--practice-ink); border: 1.5px solid var(--practice-ink);
  background: repeating-linear-gradient(135deg, var(--practice-bg) 0 6px, color-mix(in srgb, var(--practice-bg) 70%, #fff) 6px 9px);
  white-space: nowrap; vertical-align: middle; cursor: help; }
.practice-badge.lg { font-size: 13px; padding: 5px 9px; }
.practice-tip { display: none; position: absolute; left: 0; top: calc(100% + 6px); z-index: 30; width: 260px; padding: 9px 11px;
  font-size: 12px; font-weight: 500; letter-spacing: 0; line-height: 1.5; color: var(--text); background: var(--surface);
  border: 1px solid var(--border); border-left: 4px solid var(--practice-bg); border-radius: 10px; box-shadow: 0 6px 18px rgba(0,0,0,.18); white-space: normal; }
.practice-tip b { display: block; margin-bottom: 3px; }
.practice-badge:hover .practice-tip, .practice-badge:focus-visible .practice-tip { display: block; }
.practice-banner { display: flex; gap: 10px; align-items: flex-start; margin: 8px 0 10px; padding: 9px 11px; border-radius: 10px;
  background: color-mix(in srgb, var(--practice-bg) 16%, var(--surface)); border: 1.5px solid var(--practice-bg); font-size: 13px; line-height: 1.5; }
.fig.practice { display: inline-flex; align-items: center; gap: 5px; }
.fig.practice .fig-v { font-weight: 650; text-decoration: underline wavy var(--practice-bg); text-underline-offset: 4px; }
.num .practice-badge { margin-left: 4px; }
.maturity-pill { display: inline-block; font-size: 11.5px; font-weight: 750; padding: 2px 8px; border-radius: 999px; border: 1.5px solid; white-space: nowrap; }
.maturity-pill.m-verified { color: var(--lv-verified); border-color: var(--lv-verified); }
.maturity-pill.m-literature { color: var(--lv-literature); border-color: var(--lv-literature); }
.maturity-pill.m-heuristic { color: var(--practice-ink); background: var(--practice-bg); border-color: var(--practice-ink); }
.maturity-pill.m-not-modeled { color: var(--muted); border-color: var(--m-none); border-style: dashed; }
.module-board { display: flex; flex-direction: column; gap: 16px; }
.mod-group-head { display: flex; align-items: center; gap: 10px; font-size: 14px; margin: 0 0 8px; flex-wrap: wrap; }
.mod-group-head small { font-weight: 400; }
.mod-editor { border: 1.5px solid var(--practice-bg); border-radius: 12px; padding: 10px 14px 12px; margin-bottom: 10px; background: var(--surface); }
.mod-editor-head { display: flex; justify-content: space-between; align-items: center; gap: 10px; flex-wrap: wrap; }
.mod-editor-head h4 { margin: 0; font-size: 14.5px; }
.mod-toggle { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; }
.mod-levers { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); column-gap: 16px; }
.mod-brand { border-top: 1px dashed var(--border); padding-top: 8px; margin-top: 8px; }
.mod-results { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 6px 14px; margin: 8px 0 0; padding: 8px 10px;
  border-radius: 8px; background: var(--surface-2); }
.mod-results dt { font-size: 12px; color: var(--muted); }
.mod-results dd { margin: 0; }
.mod-wait { font-size: 12.5px; margin: 8px 0 0; }
.mod-grid { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 8px; }
.mod-tile { display: flex; flex-direction: column; gap: 2px; padding: 8px 10px; border-radius: 9px; border: 1px solid var(--border);
  border-left: 4px solid var(--m-none); background: var(--surface); font-size: 13px; }
.mod-tile.m-verified { border-left-color: var(--m-verified); } .mod-tile.m-literature { border-left-color: var(--m-literature); }
.mod-tile.m-heuristic { border-left-color: var(--m-heuristic); }
.mod-name { font-weight: 650; }
.mod-meta { font-size: 12px; color: var(--muted); }
.mod-tile.locked { padding: 0; border-style: dashed; border-left: 4px dashed var(--m-none); background: transparent; }
.mod-tile.locked.open { grid-column: 1 / -1; }
.mod-lock { all: unset; box-sizing: border-box; display: flex; flex-direction: column; gap: 2px; width: 100%; padding: 8px 10px; cursor: pointer; color: var(--muted); }
.mod-lock:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 8px; }
.mod-lock .mod-name { color: var(--text); opacity: .75; }
.lock-reason { padding: 4px 12px 10px; font-size: 12.5px; line-height: 1.55; }
.lock-reason p { margin: 4px 0; }
.module-shelf { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 12px; }
.shelf-card { display: flex; flex-direction: column; align-items: flex-start; gap: 4px; min-width: 170px; padding: 10px 12px; border-radius: 12px;
  border: 1.5px solid var(--practice-bg); background: var(--surface); color: var(--text); cursor: pointer; font: inherit; text-align: left; }
.shelf-card.selected { box-shadow: inset 0 0 0 2px var(--g-accent, var(--accent)); }
.shelf-card.locked { border: 1.5px dashed var(--m-none); color: var(--muted); }
.shelf-title { display: inline-flex; align-items: center; gap: 6px; font-weight: 700; font-size: 13.5px; }
.shelf-meta { font-size: 12px; color: var(--muted); }
.ladder { margin: 12px 0 4px; }
.ladder-bar { display: flex; gap: 2px; height: 22px; border-radius: 6px; overflow: hidden; }
.ladder-seg { min-width: 4px; }
.ladder-seg.m-verified, .key.m-verified { background: var(--m-verified); }
.ladder-seg.m-literature, .key.m-literature { background: var(--m-literature); }
.ladder-seg.m-heuristic, .key.m-heuristic { background: var(--m-heuristic); }
.ladder-seg.m-not-modeled, .key.m-not-modeled { background: repeating-linear-gradient(135deg, var(--m-none) 0 4px, transparent 4px 8px); border: 1px solid var(--m-none); }
.ladder-legend { display: flex; flex-wrap: wrap; gap: 6px 18px; margin-top: 8px; font-size: 13px; }
.ladder-legend .key { display: inline-block; width: 12px; height: 12px; border-radius: 3px; margin-right: 6px; vertical-align: -1px; }
.ledger-gap { margin: 10px 0 0; }
.ledger-filters { display: flex; flex-wrap: wrap; gap: 6px; margin: 4px 0 14px; }
.chip { font: inherit; font-size: 12.5px; padding: 4px 11px; border-radius: 999px; border: 1px solid var(--border); background: var(--surface); color: var(--text); cursor: pointer; }
.chip.on { background: var(--text); color: var(--bg); border-color: var(--text); }
.ledger-layout { display: grid; grid-template-columns: 1fr; gap: 16px; align-items: start; }
.ledger-layout.with-detail { grid-template-columns: minmax(0, 1fr) minmax(280px, 380px); }
.ledger-areas { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 14px; }
.ledger-area h3 { font-size: 13.5px; margin: 0 0 6px; }
.ledger-area ul { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 5px; }
.ledger-area li.dim { opacity: .28; }
.ledger-tile { width: 100%; display: flex; flex-direction: column; gap: 2px; text-align: left; font: inherit; color: var(--text); cursor: pointer;
  padding: 7px 10px; border-radius: 8px; border: 1px solid var(--border); border-left: 5px solid var(--m-none); background: var(--surface); }
.ledger-tile.m-verified { border-left-color: var(--m-verified); } .ledger-tile.m-literature { border-left-color: var(--m-literature); }
.ledger-tile.m-heuristic { border-left-color: var(--m-heuristic); background: color-mix(in srgb, var(--practice-bg) 10%, var(--surface)); }
.ledger-tile.m-not-modeled { border-style: dashed; border-left-style: dashed; background: transparent; color: var(--muted); }
.ledger-tile.selected { box-shadow: inset 0 0 0 2px var(--accent); }
.tile-name { font-size: 13px; font-weight: 650; }
.tile-meta { display: flex; align-items: center; gap: 6px; font-size: 11.5px; color: var(--muted); }
.ledger-detail { position: sticky; top: 12px; background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 12px 14px; }
.ledger-tags { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin: 4px 0 8px; font-size: 12.5px; }
.ledger-fields { display: grid; grid-template-columns: 6.5em 1fr; gap: 6px 10px; font-size: 13px; margin: 0; }
.ledger-fields dt { color: var(--muted); }
.ledger-fields dd { margin: 0; line-height: 1.5; }
.ledger-fields code { margin-right: 6px; font-size: 11.5px; }
.ledger-sources { font-size: 12px; line-height: 1.5; padding-left: 18px; color: var(--muted); }
.ledger-sources b { color: var(--text); }
.ledger-legend { display: grid; gap: 8px; margin: 0; }
.ledger-legend div { display: grid; grid-template-columns: 7em 1fr; gap: 10px; align-items: start; font-size: 13px; }
.ledger-legend dd { margin: 0; }
@media (max-width: 900px) { .ledger-layout.with-detail { grid-template-columns: 1fr; } .ledger-detail { position: static; } }
@media (prefers-reduced-motion: reduce) { .practice-tip { transition: none; } }
`;
