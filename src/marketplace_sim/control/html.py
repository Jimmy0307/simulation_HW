"""Self-contained, offline HTML report for scenario results (inline CSS + SVG; no scripts, fonts or images)."""

from __future__ import annotations

import html
from typing import Any

LEVEL_CLASS = {"verified": "lv-v", "derived": "lv-d", "estimated": "lv-e", "placeholder": "lv-p"}
CSS = """
:root{--bg:#fbfaf7;--fg:#1f2328;--muted:#5b6470;--grid:#d9dde3;--card:#ffffff;
--v:#1a7f37;--d:#0b62c4;--e:#a16207;--p:#b42318;--line:#0b62c4;--line2:#7c3aed;--ev:#b42318}
@media (prefers-color-scheme: dark){:root{--bg:#14171c;--fg:#e6e8eb;--muted:#9aa4b2;--grid:#2c323b;--card:#1b1f26;
--v:#4ac26b;--d:#58a6ff;--e:#e3b341;--p:#ff7b72;--line:#58a6ff;--line2:#b392f0;--ev:#ff7b72}}
body{background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif;margin:0;padding:24px;max-width:1200px}
h1{font-size:22px;margin:0 0 4px} h2{font-size:17px;margin:28px 0 8px} .muted{color:var(--muted)}
.card{background:var(--card);border:1px solid var(--grid);border-radius:10px;padding:16px;margin:12px 0;overflow-x:auto}
table{border-collapse:collapse;font-variant-numeric:tabular-nums;width:100%} th,td{padding:4px 8px;border-bottom:1px solid var(--grid);text-align:right;white-space:nowrap}
th:first-child,td:first-child{text-align:left} .lv-v{color:var(--v)} .lv-d{color:var(--d)} .lv-e{color:var(--e)} .lv-p{color:var(--p)}
.tag{display:inline-block;border:1px solid currentColor;border-radius:4px;padding:0 4px;font-size:11px;margin-left:4px}
.legend span{margin-right:14px} .ev{color:var(--ev);font-weight:600}
svg text{fill:var(--muted);font-size:11px} .axis{stroke:var(--grid)} .s1{stroke:var(--line);fill:none;stroke-width:2.5}
.s2{stroke:var(--line2);fill:none;stroke-width:2;stroke-dasharray:5 4} .evl{stroke:var(--ev);stroke-dasharray:3 3}
"""


def _fmt(value: float) -> str:
    return f"{value:,.0f}" if abs(value) >= 100 else f"{value:,.2f}"


def _chart(quarters: list[dict[str, Any]], metric: str, metric2: str | None, title: str) -> str:
    xs = [q["quarter"] for q in quarters]
    ys = [q["lines"].get(metric, {}).get("value", 0.0) for q in quarters]
    ys2 = [q["lines"].get(metric2, {}).get("value", 0.0) for q in quarters] if metric2 else []
    if not xs:
        return ""
    width, height, pad = 720, 220, 48
    lo, hi = min([*ys, *ys2, 0.0]), max([*ys, *ys2, 1.0])
    span = hi - lo or 1.0

    def px(i: int) -> float:
        return pad + (width - 2 * pad) * (i / max(len(xs) - 1, 1))

    def py(v: float) -> float:
        return float(height - pad + (pad - (height - pad)) * ((v - lo) / span))

    def path(values: list[float]) -> str:
        return " ".join(f"{'M' if i == 0 else 'L'}{px(i):.1f},{py(v):.1f}" for i, v in enumerate(values))

    parts = [f'<svg viewBox="0 0 {width} {height}" width="100%" role="img" aria-label="{html.escape(title)}">',
             f'<line class="axis" x1="{pad}" y1="{py(0):.1f}" x2="{width - pad}" y2="{py(0):.1f}"/>',
             f'<text x="{pad}" y="16">{html.escape(title)}</text>',
             f'<text x="4" y="{py(hi) + 4:.1f}">{_fmt(hi)}</text><text x="4" y="{py(lo) + 4:.1f}">{_fmt(lo)}</text>']
    for i, q in enumerate(quarters):
        parts.append(f'<text x="{px(i) - 8:.1f}" y="{height - 18}">Q{q["quarter"]}</text>')
        if q["events"]:
            parts.append(f'<line class="evl" x1="{px(i):.1f}" y1="{pad - 10}" x2="{px(i):.1f}" y2="{height - pad}"/>'
                         f'<text x="{px(i) + 4:.1f}" y="{pad - 12}">⚑ {len(q["events"])}</text>')
    parts.append(f'<path class="s1" d="{path(ys)}"/>')
    if ys2:
        parts.append(f'<path class="s2" d="{path(ys2)}"/>')
    parts.append("</svg>")
    return "".join(parts)


def render_results(results: list[dict[str, Any]], title: str = "Scenario report") -> str:
    body = [f"<h1>{html.escape(title)}</h1>",
            ('<p class="muted legend">Source level: <span class="lv-v">■ verified</span><span class="lv-d">■ derived</span>'
             '<span class="lv-e">■ estimated</span><span class="lv-p">■ placeholder (illustrative, not a forecast)</span></p>')]
    for result in results:
        quarters = result["quarters"]
        summary = result["summary"]
        body.append(f'<h2>{html.escape(result["name"])} <span class="muted">· fingerprint {html.escape(result["fingerprint"])}'
                    f' · seed {result["seed"]}</span></h2>')
        body.append('<div class="card">' + _chart(quarters, "cash_end", "net_income", "cash_end (solid) / net_income (dashed)")
                    + _chart(quarters, "capacity_units_per_quarter", None, "capacity units per quarter") + "</div>")
        events = [(q["quarter"], e) for q in quarters for e in q["events"]]
        if events:
            body.append('<div class="card"><b class="ev">Events</b><ul>' + "".join(
                f"<li>Q{qn}: {html.escape(e)}</li>" for qn, e in events) + "</ul></div>")
        body.append('<div class="card"><table><tr><th>summary</th><th>value</th></tr>' + "".join(
            f"<tr><td>{html.escape(k)}</td><td>{html.escape(_fmt(v) if isinstance(v, (int, float)) else str(v))}</td></tr>"
            for k, v in summary.items()) + "</table></div>")
        metrics: list[str] = []
        for q in quarters:
            metrics += [k for k in q["lines"] if k not in metrics]
        rows = ["<tr><th>metric</th>" + "".join(f"<th>Q{q['quarter']}{' ⚑' if q['events'] else ''}</th>" for q in quarters) + "</tr>"]
        for metric in metrics:
            cells = []
            for q in quarters:
                line = q["lines"].get(metric)
                if line is None:
                    cells.append("<td>-</td>")
                    continue
                cls = LEVEL_CLASS.get(line["level"], "lv-p")
                cells.append(f'<td class="{cls}" title="{html.escape(line["source"])}">{_fmt(line["value"])}'
                             f'<span class="tag">{line["level"][0].upper()}</span></td>')
            rows.append(f"<tr><td>{html.escape(metric)}</td>{''.join(cells)}</tr>")
        body.append('<div class="card"><table>' + "".join(rows) + "</table></div>")
    return (f"<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" "
            f"content=\"width=device-width,initial-scale=1\"><title>{html.escape(title)}</title><style>{CSS}</style>"
            f"</head><body>{''.join(body)}</body></html>")
