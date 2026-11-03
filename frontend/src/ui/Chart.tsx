import type { LevelLabel } from "../types";
import { formatNumber, UNCALIBRATED_LABEL } from "./Num";

export interface Series {
  name: string;
  values: (number | null)[];
  level: LevelLabel; // weakest level of the series (colours the line; uncalibrated series are dashed)
}

const COLOR: Record<LevelLabel, string> = {
  verified: "var(--lv-verified)", derived: "var(--lv-derived)", estimated: "var(--lv-estimated)",
  literature: "var(--lv-literature)", placeholder: "var(--lv-placeholder)",
};

/** Multi-series line chart. x = quarters; ⚑ marks quarters with scenario events. Pure presentation. */
export function LineChart({ quarters, series, events, title }: {
  quarters: number[]; series: Series[]; events?: (string[] | undefined)[]; title: string;
}) {
  const width = 760, height = 260, padL = 76, padR = 18, padT = 30, padB = 34;
  const all = series.flatMap((s) => s.values.filter((v): v is number => v !== null));
  if (quarters.length === 0 || all.length === 0) return <p className="muted">沒有資料</p>;
  const lo = Math.min(0, ...all), hi = Math.max(1, ...all), span = hi - lo || 1;
  const x = (i: number) => padL + ((width - padL - padR) * i) / Math.max(quarters.length - 1, 1);
  const y = (v: number) => padT + (height - padT - padB) * (1 - (v - lo) / span);
  const ticks = [lo, lo + span / 2, hi];
  return (
    <figure style={{ margin: 0 }}>
      <svg className="chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={title}>
        <text x={padL} y={16} style={{ fontWeight: 600 }}>{title}</text>
        {ticks.map((t) => (
          <g key={t}>
            <line className="axis" x1={padL} x2={width - padR} y1={y(t)} y2={y(t)} />
            <text x={padL - 8} y={y(t) + 4} textAnchor="end">{formatNumber(t, 0)}</text>
          </g>
        ))}
        {quarters.map((q, i) => (
          <g key={q}>
            <text x={x(i)} y={height - 12} textAnchor="middle">Q{q}</text>
            {events?.[i]?.length ? (
              <g>
                <line className="event" x1={x(i)} x2={x(i)} y1={padT - 6} y2={height - padB} />
                <text className="event-label" x={x(i) + 4} y={padT - 8}>⚑ {events[i]!.length}</text>
              </g>
            ) : null}
          </g>
        ))}
        {series.map((s) => {
          const pts = s.values.map((v, i) => (v === null ? null : `${x(i).toFixed(1)},${y(v).toFixed(1)}`)).filter(Boolean);
          const dashed = s.level === "literature" || s.level === "placeholder";
          return (
            <g key={s.name}>
              <polyline points={pts.join(" ")} fill="none" stroke={COLOR[s.level]} strokeWidth={2.5}
                strokeDasharray={dashed ? "6 4" : undefined} />
              {s.values.map((v, i) => (v === null ? null : <circle key={i} cx={x(i)} cy={y(v)} r={3.5} fill={COLOR[s.level]} />))}
            </g>
          );
        })}
      </svg>
      <figcaption className="legend">
        {series.map((s) => (
          <span key={s.name}>
            <svg width="26" height="8" aria-hidden="true"><line x1="0" x2="26" y1="4" y2="4" stroke={COLOR[s.level]} strokeWidth="3"
              strokeDasharray={s.level === "literature" || s.level === "placeholder" ? "6 4" : undefined} /></svg>
            {s.name}（{s.level}{s.level === "literature" || s.level === "placeholder" ? ` · ${UNCALIBRATED_LABEL}` : ""}）
          </span>
        ))}
        {events?.some((e) => e && e.length) ? <span>⚑ = 該季有情境事件</span> : null}
      </figcaption>
    </figure>
  );
}

export function weakest(levels: LevelLabel[]): LevelLabel {
  const order: LevelLabel[] = ["placeholder", "literature", "estimated", "derived", "verified"];
  return levels.reduce<LevelLabel>((w, l) => (order.indexOf(l) < order.indexOf(w) ? l : w), "verified");
}

export function BarChart({ items, title }: { items: { label: string; value: number }[]; title: string }) {
  const width = 760, row = 28, padL = 190, height = items.length * row + 30;
  const max = Math.max(1, ...items.map((i) => Math.abs(i.value)));
  return (
    <svg className="chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={title}>
      {items.map((item, i) => {
        const w = ((width - padL - 120) * Math.abs(item.value)) / max;
        return (
          <g key={item.label}>
            <text x={padL - 8} y={20 + i * row + 12} textAnchor="end">{item.label}</text>
            <rect className="bar" x={padL} y={20 + i * row} width={w} height={row - 10} rx={4} />
            <text x={padL + w + 6} y={20 + i * row + 12}>{formatNumber(item.value, 0)}</text>
          </g>
        );
      })}
    </svg>
  );
}
