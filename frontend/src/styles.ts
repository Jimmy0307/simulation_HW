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
@media (max-width: 860px) {
  .shell { grid-template-columns: 1fr; }
  .side { position: static; height: auto; border-right: 0; border-bottom: 1px solid var(--border); }
  .nav { flex-direction: row; flex-wrap: wrap; }
  .main { padding: 16px; }
}
`;
