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
.game { display: flex; flex-direction: column; gap: 0; padding-bottom: 76px; }
.game-setup .setup-hero { display: flex; gap: 18px; align-items: center; }
.setup-icon { color: var(--accent); }
.choice-row { display: flex; gap: 8px; flex-wrap: wrap; }
.choice { display: inline-flex; gap: 8px; align-items: center; border: 1px solid var(--border); border-radius: 10px; padding: 8px 12px; cursor: pointer; }
.choice.on { border-color: var(--accent); box-shadow: inset 0 0 0 1px var(--accent); }
.choice.off { opacity: .55; cursor: not-allowed; }
.count-readout { font-weight: 700; margin: 4px 0 8px; }
.opponents { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 8px; }
.btn.big { padding: 11px 22px; font-size: 15px; }
.btn.small { padding: 3px 10px; font-size: 12px; }
.hud { display: flex; flex-wrap: wrap; gap: 10px 22px; align-items: center; background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 10px 16px; margin-bottom: 16px; position: sticky; top: 0; z-index: 20; box-shadow: var(--shadow); }
.hud-source { border-radius: 10px; padding: 6px 12px; color: #fff; font-weight: 750; display: flex; flex-direction: column; line-height: 1.25; }
.hud-source small { font-weight: 500; opacity: .9; font-size: 11px; }
.hud-source.synthetic { background: var(--synthetic-bg); }
.hud-source.private { background: var(--private-bg); }
.hud-item { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.hud-label { color: var(--muted); font-size: 11.5px; }
.hud-quarter { font-size: 18px; }
.hud-goal { max-width: 240px; }
.hud-rivals { display: flex; gap: 4px; flex-wrap: wrap; }
.rival-chip { font-size: 11.5px; border-radius: 6px; padding: 1px 7px; border: 1px solid var(--border); background: var(--surface-2); }
.rival-chip.d-aggressive { border-color: var(--danger); }
.game-grid { display: grid; grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr); gap: 16px; align-items: start; }
.product-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; margin-top: 12px; }
.product-card { border: 1px solid var(--border); border-radius: 12px; padding: 12px; background: var(--surface-2);
  display: flex; flex-direction: column; gap: 10px; transition: box-shadow .25s ease-out, border-color .25s ease-out; }
.product-card.bump { border-color: var(--accent); box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 22%, transparent); }
.product-head { display: flex; gap: 8px; align-items: center; }
.product-icon { color: var(--accent); flex: none; }
.product-name { flex: 1; min-width: 0; font-weight: 700; border: 1px solid var(--border); border-radius: 8px; padding: 5px 8px; background: var(--surface); }
.icon-btn { border: 1px solid var(--border); background: var(--surface); border-radius: 8px; width: 30px; height: 30px; cursor: pointer; font-size: 16px; }
.config { display: flex; flex-direction: column; gap: 6px; }
.config-name { font-size: 12px; color: var(--muted); }
.seg { display: flex; flex-wrap: wrap; gap: 4px; }
.seg-btn { border: 1px solid var(--border); background: var(--surface); border-radius: 8px; padding: 4px 9px; font-size: 12.5px; cursor: pointer; }
.seg-btn[aria-pressed="true"] { background: var(--accent); color: var(--accent-ink); border-color: transparent; }
.seg-btn:disabled { cursor: not-allowed; opacity: .75; }
.slider { display: flex; flex-direction: column; gap: 2px; }
.slider-head { display: flex; justify-content: space-between; font-size: 12.5px; color: var(--muted); }
.slider-value { color: var(--text); font-variant-numeric: tabular-nums; }
.slider input { width: 100%; accent-color: var(--accent); }
.product-foot, .cost-row, .factory { display: flex; flex-wrap: wrap; gap: 14px; align-items: end; }
.factory { margin-top: 14px; padding-top: 12px; border-top: 1px dashed var(--border); }
.foot-item { display: flex; flex-direction: column; gap: 2px; }
.map { width: 100%; height: auto; max-height: 220px; margin-top: 10px; }
.map .region { fill: var(--surface-2); stroke: var(--border); }
.map .region.web-on { stroke: var(--accent); stroke-dasharray: 6 4; }
.map .region-label { fill: var(--muted); font-size: 12px; font-weight: 700; }
.map .city { cursor: pointer; outline: none; }
.map .city circle { fill: var(--surface); stroke: var(--muted); stroke-width: 2; transition: r .15s ease-out; }
.map .city.open circle { fill: var(--accent); stroke: var(--accent); }
.map .city.planned circle { fill: color-mix(in srgb, var(--accent) 25%, var(--surface)); stroke: var(--accent); stroke-dasharray: 4 3; }
.map .city.selected circle, .map .city:focus circle { stroke-width: 4; }
.map .city-label { fill: var(--text); font-size: 12px; }
.legend .dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; border: 2px solid var(--muted); }
.legend .dot.open { background: var(--accent); border-color: var(--accent); }
.legend .dot.planned { border-color: var(--accent); border-style: dashed; }
.region-web { display: flex; flex-wrap: wrap; gap: 12px; align-items: end; margin: 10px 0; padding: 8px 10px; border-radius: 10px; background: var(--surface-2); }
.city-panel { border: 1px solid var(--border); border-radius: 12px; padding: 12px; margin-top: 10px; }
.seg-table th, .seg-table td, .settle-table td { padding: 5px 8px; }
/* the estimate state: faded, dashed, behind a click; never styled as a headline result */
.estimate { display: inline-flex; flex-direction: column; align-items: flex-end; gap: 2px; }
.estimate-btn { font: inherit; font-size: 12px; font-weight: 700; color: var(--lv); background: transparent; cursor: pointer;
  border: 1.5px dashed var(--lv); border-radius: 7px; padding: 1px 8px; opacity: .6; }
.estimate-btn:hover, .estimate-btn:focus-visible { opacity: .9; }
.estimate.open .num .v { font-weight: 500; opacity: .8; }
.estimate-note { color: var(--muted); font-size: 11px; max-width: 220px; text-align: right; white-space: normal; }
.turn-bar { position: sticky; bottom: 0; z-index: 25; display: flex; gap: 10px; align-items: center; justify-content: flex-end; flex-wrap: wrap;
  background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 10px 14px; box-shadow: 0 -2px 12px rgba(0, 0, 0, .08); }
.turn-label { margin-right: auto; font-weight: 700; }
.settle-backdrop { position: fixed; inset: 0; background: rgba(10, 14, 20, .45); display: grid; place-items: center; z-index: 50; padding: 16px; }
.settle-card { background: var(--surface); border-radius: 16px; border: 1px solid var(--border); width: min(900px, 100%); max-height: 90vh; overflow: auto;
  padding: 18px 20px; box-shadow: 0 18px 50px rgba(0, 0, 0, .3); animation: flip-in .32s ease-out; transform-origin: 50% 0; }
@keyframes flip-in { from { opacity: 0; transform: perspective(900px) rotateX(-12deg) translateY(8px); } to { opacity: 1; transform: none; } }
@media (prefers-reduced-motion: reduce) { .settle-card { animation: none; } .product-card, .map .city circle { transition: none; } }
.settle-head { display: flex; justify-content: space-between; align-items: center; gap: 10px; }
.settle-head h2 { margin: 0; font-size: 18px; }
.settle-notice { background: var(--warn-bg); color: var(--warn-ink); border-radius: 10px; padding: 8px 12px; font-size: 13px; margin: 10px 0; }
.settle-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 18px; }
.settle-table { width: 100%; }
.settle-card .settle-table td, .settle-card .settle-table th { white-space: normal; }
.settle-table td:first-child { color: var(--muted); }
.rivals tr.us td { font-weight: 700; }
.settle-notes { color: var(--muted); font-size: 12.5px; margin: 10px 0 0; }
.timeline { list-style: none; display: flex; gap: 10px; flex-wrap: wrap; padding: 0; margin: 0; }
.timeline li { display: flex; gap: 10px; align-items: center; border: 1px solid var(--border); border-radius: 12px; padding: 6px 10px; }
.timeline-btn { border: 0; background: transparent; cursor: pointer; display: flex; gap: 6px; align-items: baseline; padding: 0; }
.timeline-goal { display: flex; flex-direction: column; }
@media (max-width: 1100px) { .game-grid { grid-template-columns: 1fr; } }
@media (max-width: 860px) {
  .shell { grid-template-columns: 1fr; }
  .side { position: static; height: auto; border-right: 0; border-bottom: 1px solid var(--border); }
  .nav { flex-direction: row; flex-wrap: wrap; }
  .main { padding: 16px; }
}
`;
