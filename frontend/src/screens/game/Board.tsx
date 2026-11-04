import type { KeyboardEvent, ReactNode } from "react";
import type { GameSetupDoc } from "../../types";
import type { Draft } from "./draft";

// The town board: a schematic isometric map (no real geography). One plate per region, one lot per city,
// a radio tower per regional web center, and the factory on its own plate. Lit buildings = open; dashed ghost
// buildings = opening this quarter; dark empty lot = not open. Clicking anything opens the side panel.

export type Selection =
  | { kind: "city"; key: string }
  | { kind: "web"; key: string }
  | { kind: "factory" }
  | { kind: "product"; index: number }
  | { kind: "preview" }
  | { kind: "modules" };

/** Open outlets: the engine state is the source of truth (the demo replay only carries the state per quarter). */
export function storeOpen(setup: GameSetupDoc, key: string): boolean {
  const city = setup.regions.flatMap((r) => r.cities).find((c) => c.key === key);
  return Boolean(city?.store?.open) || (setup.state?.stores_open ?? []).includes(key);
}
export function webOpen(setup: GameSetupDoc, key: string): boolean {
  const web = setup.regions.find((r) => r.web_center?.key === key)?.web_center;
  return Boolean(web?.open) || (setup.state?.web_centers_open ?? []).includes(key);
}

const HW = 60; // half tile width (px)
const HH = 30; // half tile height (px)
const SP = 1.6; // lot pitch in grid units (lots are 1 unit; the gap leaves room for names)
const GAP = 1.2; // grid units between plates
const SKIRT = 12;

type Pt = [number, number];
const iso = (i: number, j: number): Pt => [(i - j) * HW, (i + j) * HH];
const pts = (list: Pt[]) => list.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
const up = ([x, y]: Pt, h: number): Pt => [x, y - h];

/** An isometric box standing on the grid point (ci, cj), half-sizes si × sj (grid units), height h (px). */
function Box({ ci, cj, si, sj, h, bands = 0 }: { ci: number; cj: number; si: number; sj: number; h: number; bands?: number }) {
  const n = iso(ci - si, cj - sj);
  const e = iso(ci + si, cj - sj);
  const s = iso(ci + si, cj + sj);
  const w = iso(ci - si, cj + sj);
  const rows = Array.from({ length: bands }, (_, k) => h * (k + 1) / (bands + 1));
  return (
    <g className="box">
      <polygon className="wall-l" points={pts([w, s, up(s, h), up(w, h)])} />
      <polygon className="wall-r" points={pts([s, e, up(e, h), up(s, h)])} />
      <polygon className="roof" points={pts([up(n, h), up(e, h), up(s, h), up(w, h)])} />
      {rows.map((y) => (
        <g key={y} className="windows">
          <line x1={w[0] + 3} y1={w[1] - y + 1.5} x2={s[0] - 3} y2={s[1] - y - 1.5} />
          <line x1={s[0] + 3} y1={s[1] - y - 1.5} x2={e[0] - 3} y2={e[1] - y + 1.5} />
        </g>
      ))}
    </g>
  );
}

function Lot({ i, j }: { i: number; j: number }) {
  return <polygon className="lot" points={pts([iso(i + 0.08, j + 0.08), iso(i + 0.92, j + 0.08), iso(i + 0.92, j + 0.92), iso(i + 0.08, j + 0.92)])} />;
}

function Trees({ i, j }: { i: number; j: number }) {
  return (
    <g className="trees" aria-hidden="true">
      {[[0.28, 0.62], [0.7, 0.3], [0.62, 0.7]].map(([a, b]) => {
        const [x, y] = iso(i + a, j + b);
        return <g key={`${a}-${b}`}><line x1={x} y1={y} x2={x} y2={y - 6} /><circle cx={x} cy={y - 9} r={5} /></g>;
      })}
    </g>
  );
}

function Glow({ i, j }: { i: number; j: number }) {
  const [x, y] = iso(i + 0.5, j + 0.5);
  return <ellipse className="glow" cx={x} cy={y} rx={HW * 1.15} ry={HH * 1.15} />;
}

function Town({ i, j }: { i: number; j: number }) {
  return (
    <g className="town">
      <Box ci={i + 0.34} cj={j + 0.34} si={0.17} sj={0.17} h={38} bands={3} />
      <Box ci={i + 0.68} cj={j + 0.36} si={0.14} sj={0.14} h={24} bands={2} />
      <Box ci={i + 0.4} cj={j + 0.7} si={0.14} sj={0.14} h={17} bands={1} />
    </g>
  );
}

function Tower({ i, j }: { i: number; j: number }) {
  const [x, y] = iso(i + 0.5, j + 0.5);
  return (
    <g className="town">
      <Box ci={i + 0.5} cj={j + 0.5} si={0.11} sj={0.11} h={50} bands={4} />
      <line className="mast" x1={x} y1={y - 50} x2={x} y2={y - 72} />
      <path className="signal" d={`M${x - 9} ${y - 74} q9 -9 18 0 M${x - 15} ${y - 79} q15 -14 30 0`} />
    </g>
  );
}

function Plot({ label, state, selected, testId, name, onSelect, children, labelAt }: {
  label: string; state: "open" | "planned" | "closed"; selected: boolean; testId: string; name: string;
  onSelect: () => void; children: ReactNode; labelAt: Pt;
}) {
  const onKey = (e: KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onSelect(); }
  };
  return (
    <g className={`plot ${state}${selected ? " selected" : ""}`} role="button" tabIndex={0} aria-label={label}
      aria-pressed={selected} data-testid={testId} onClick={onSelect} onKeyDown={onKey}>
      {children}
      <text className="plot-name" x={labelAt[0]} y={labelAt[1] + 18} textAnchor="middle">{name}</text>
    </g>
  );
}

const STATE_TEXT = { open: "營業中", planned: "本季開設", closed: "未開設" } as const;

export function Board({ setup, draft, selection, onSelect }: {
  setup: GameSetupDoc; draft: Draft; selection: Selection | null; onSelect: (s: Selection) => void;
}) {
  // Layout in grid units: factory plate first, then one plate per region along the i axis.
  const plates: { a: number; c: number; d: number; key: string; label: string }[] = [];
  const items: { depth: number; node: ReactNode }[] = [];
  const isSel = (s: Selection) => JSON.stringify(s) === JSON.stringify(selection);

  plates.push({ a: -0.2, c: 1.2, d: 1.2, key: "factory", label: "" });
  {
    const sel: Selection = { kind: "factory" };
    const growing = draft.capacity_increase > 0;
    items.push({
      depth: 1, node: (
        <Plot key="factory" label={`工廠${growing ? "（本季擴產）" : ""}`} state={growing ? "planned" : "open"} selected={isSel(sel)}
          testId="factory" name="工廠" onSelect={() => onSelect(sel)} labelAt={iso(0.92, 0.92)}>
          <Lot i={0} j={0} />
          <g className="town factory">
            <Box ci={0.55} cj={0.42} si={0.3} sj={0.2} h={20} bands={1} />
            <Box ci={0.3} cj={0.3} si={0.06} sj={0.06} h={46} />
            {growing ? <g className="ghost"><Box ci={0.5} cj={0.8} si={0.26} sj={0.1} h={14} /></g> : null}
          </g>
        </Plot>
      ),
    });
  }

  let cursor = 1 + GAP;
  for (const region of setup.regions) {
    const n = region.cities.length;
    const cols = Math.max(1, Math.min(2, n));
    const rows = Math.max(1, Math.ceil(n / cols));
    const columns = cols + (region.web_center ? 1 : 0);
    const i0 = cursor;
    const width = (columns - 1) * SP + 1;
    plates.push({ a: i0 - 0.25, c: i0 + width + 0.25, d: (rows - 1) * SP + 1 + 0.25, key: region.id, label: `區域 ${region.id}` });
    region.cities.forEach((city, k) => {
      const i = i0 + (k % cols) * SP;
      const j = Math.floor(k / cols) * SP;
      const open = storeOpen(setup, city.key);
      const state = open ? "open" : draft.open_stores.includes(city.key) ? "planned" : "closed";
      const sel: Selection = { kind: "city", key: city.key };
      items.push({
        depth: i + j, node: (
          <Plot key={city.key} label={`${city.name}（${STATE_TEXT[state]}）`} state={state} selected={isSel(sel)}
            testId={`city-${city.key}`} name={city.name} onSelect={() => onSelect(sel)} labelAt={iso(i + 0.92, j + 0.92)}>
            {state === "open" ? <Glow i={i} j={j} /> : null}
            <Lot i={i} j={j} />
            {state === "closed" ? <Trees i={i} j={j} /> : state === "planned" ? <g className="ghost"><Town i={i} j={j} /></g> : <Town i={i} j={j} />}
          </Plot>
        ),
      });
    });
    const web = region.web_center;
    if (web) {
      const i = i0 + cols * SP;
      const j = 0;
      const state = webOpen(setup, web.key) ? "open" : draft.open_web_centers.includes(web.key) ? "planned" : "closed";
      const sel: Selection = { kind: "web", key: web.key };
      items.push({
        depth: i + j, node: (
          <Plot key={web.key} label={`${web.name} 網路中心（${STATE_TEXT[state]}）`} state={state} selected={isSel(sel)}
            testId={`web-${web.key}`} name="網路中心" onSelect={() => onSelect(sel)} labelAt={iso(i + 0.92, j + 0.92)}>
            {state === "open" ? <Glow i={i} j={j} /> : null}
            <Lot i={i} j={j} />
            {state === "closed" ? <Trees i={i} j={j} /> : state === "planned" ? <g className="ghost"><Tower i={i} j={j} /></g> : <Tower i={i} j={j} />}
          </Plot>
        ),
      });
    }
    cursor = i0 + width + GAP;
  }

  // Bounds of the drawing (plates, skirts, buildings above, names below).
  const corners = plates.flatMap((p) => [iso(p.a, -0.25), iso(p.c, -0.25), iso(p.c, p.d), iso(p.a, p.d)]);
  const xs = corners.map(([x]) => x);
  const ys = corners.map(([, y]) => y);
  const minX = Math.min(...xs) - 84;
  const maxX = Math.max(...xs) + 24;
  const minY = Math.min(...ys) - 92;
  const maxY = Math.max(...ys) + SKIRT + 34;

  return (
    <figure className="board" aria-label="城市地圖">
      <svg viewBox={`${minX.toFixed(0)} ${minY.toFixed(0)} ${(maxX - minX).toFixed(0)} ${(maxY - minY).toFixed(0)}`}
        role="group" aria-label="城市示意圖（非真實地理）。點城市、網路中心或工廠打開側欄。">
        <defs>
          <radialGradient id="g-glow">
            <stop offset="0%" stopColor="var(--g-lit)" stopOpacity="0.55" />
            <stop offset="100%" stopColor="var(--g-lit)" stopOpacity="0" />
          </radialGradient>
        </defs>
        {plates.map((p) => {
          const b = -0.25;
          const [nw, ne, se, sw] = [iso(p.a, b), iso(p.c, b), iso(p.c, p.d), iso(p.a, p.d)];
          const left = iso(p.a, p.d);
          return (
            <g key={p.key} className="plate">
              <polygon className="skirt-r" points={pts([ne, se, [se[0], se[1] + SKIRT], [ne[0], ne[1] + SKIRT]])} />
              <polygon className="skirt-l" points={pts([se, sw, [sw[0], sw[1] + SKIRT], [se[0], se[1] + SKIRT]])} />
              <polygon className="land" points={pts([nw, ne, se, sw])} />
              {p.label ? <text className="plate-name" x={left[0] - 10} y={left[1] + 4} textAnchor="end">{p.label}</text> : null}
            </g>
          );
        })}
        {items.sort((x, y) => x.depth - y.depth).map((item) => item.node)}
      </svg>
      <figcaption className="board-key">
        <span><i className="key open" />亮燈：營業中</span>
        <span><i className="key planned" />虛線：本季開設</span>
        <span><i className="key closed" />空地：未開設</span>
      </figcaption>
    </figure>
  );
}
