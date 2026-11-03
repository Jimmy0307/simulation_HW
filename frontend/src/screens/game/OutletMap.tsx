import { useState } from "react";
import type { GameCity, GameRegion, GameSetupDoc, Report } from "../../types";
import type { Draft } from "./draft";
import { Estimate } from "./Estimate";

interface Props {
  setup: GameSetupDoc;
  draft: Draft;
  preview: Report | null;
  readOnly: boolean;
  onChange: (draft: Draft) => void;
}

// Schematic layout (no real geography): one panel per region, cities on a small grid inside it.
const REGION_W = 230;
const CELL_W = 100;
const CELL_H = 74;
const COLS = 2;

function toggle(list: string[], key: string): string[] {
  return list.includes(key) ? list.filter((k) => k !== key) : [...list, key];
}

function CityPanel({ city, setup, draft, readOnly, onChange }: {
  city: GameCity; setup: GameSetupDoc; draft: Draft; readOnly: boolean; onChange: (d: Draft) => void;
}) {
  const open = city.store?.open ?? false;
  const planned = draft.open_stores.includes(city.key);
  return (
    <div className="city-panel" data-testid="city-panel">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h3 style={{ margin: 0 }}>{city.name}</h3>
        {city.store ? (
          <button type="button" className={`btn${planned ? "" : " primary"}`} disabled={readOnly || open}
            onClick={() => onChange({ ...draft, open_stores: toggle(draft.open_stores, city.key) })}>
            {open ? "已開店" : planned ? "取消本季開店" : "本季在這裡開店"}
          </button>
        ) : <span className="muted">此城市沒有店面選項</span>}
      </div>
      {city.store ? (
        <div className="cost-row">
          <span className="foot-item"><span className="hud-label">開店成本</span><Estimate line={city.store.setup_cost} label={`開店成本 ${city.name}`} /></span>
          <span className="foot-item"><span className="hud-label">租金</span><Estimate line={city.store.lease_cost} label={`租金 ${city.name}`} /></span>
        </div>
      ) : null}
      <p className="note">新開的店從下一季開始銷售。</p>
      <table className="seg-table">
        <thead><tr><th>區隔</th><th>12 個月市場規模</th><th>願付價格</th></tr></thead>
        <tbody>
          {city.segments.map((s) => (
            <tr key={s.id}>
              <td>{s.name}<span className="muted"> · {setup.segments.find((x) => x.id === s.id)?.needs.slice(0, 2).join("、")}</span></td>
              <td><Estimate line={s.size_12m} label={`市場規模 ${city.name} ${s.name}`} /></td>
              <td><Estimate line={s.wtp} label={`願付價格 ${city.name} ${s.name}`} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RegionPanel({ region, draft, readOnly, onChange }: {
  region: GameRegion; draft: Draft; readOnly: boolean; onChange: (d: Draft) => void;
}) {
  const web = region.web_center;
  if (!web) return null;
  const planned = draft.open_web_centers.includes(web.key);
  return (
    <div className="region-web">
      <span><b>{web.name}</b> 網路中心（涵蓋整區）</span>
      <span className="foot-item"><span className="hud-label">開設成本</span><Estimate line={web.setup_cost} label={`網路中心 ${web.name}`} /></span>
      <button type="button" className="btn" disabled={readOnly || web.open}
        onClick={() => onChange({ ...draft, open_web_centers: toggle(draft.open_web_centers, web.key) })}>
        {web.open ? "已開設" : planned ? "取消本季開設" : "本季開設"}
      </button>
    </div>
  );
}

/** "Distribution": click a city to see its segments and willingness to pay, then open a store there. */
export function OutletMap({ setup, draft, preview, readOnly, onChange }: Props) {
  const [selected, setSelected] = useState<string | null>(setup.regions[0]?.cities[0]?.key ?? null);
  const rows = Math.max(1, ...setup.regions.map((r) => Math.ceil(r.cities.length / COLS)));
  const width = setup.regions.length * (REGION_W + 16) + 16;
  const height = rows * CELL_H + 56;
  const city = setup.regions.flatMap((r) => r.cities).find((c) => c.key === selected) ?? null;
  const region = setup.regions.find((r) => r.cities.some((c) => c.key === selected)) ?? null;
  const storeSetup = preview?.lines.store_setup;
  const webSetup = preview?.lines.web_center_setup;
  return (
    <section className="card" aria-label="鋪貨">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h2 style={{ margin: 0 }}>鋪貨</h2>
        <span className="legend">
          <span><i className="dot open" />營業中</span><span><i className="dot planned" />本季開設</span><span><i className="dot" />未開設</span>
        </span>
      </div>
      <svg className="map" viewBox={`0 0 ${width} ${height}`} role="group" aria-label="城市示意圖（非真實地理）">
        {setup.regions.map((r, ri) => {
          const x0 = 16 + ri * (REGION_W + 16);
          const web = r.web_center;
          const webOn = web && (web.open || draft.open_web_centers.includes(web.key));
          return (
            <g key={r.id}>
              <rect x={x0} y={8} width={REGION_W} height={height - 16} rx={14}
                className={`region${webOn ? " web-on" : ""}`} />
              <text x={x0 + 14} y={30} className="region-label">區域 {r.id}{webOn ? " · 網路中心" : ""}</text>
              {r.cities.map((c, ci) => {
                const cx = x0 + 22 + (ci % COLS) * CELL_W + CELL_W / 2 - 12;
                const cy = 44 + Math.floor(ci / COLS) * CELL_H + 22;
                const open = c.store?.open ?? false;
                const planned = draft.open_stores.includes(c.key);
                const state = open ? "open" : planned ? "planned" : "closed";
                return (
                  <g key={c.key} className={`city ${state}${selected === c.key ? " selected" : ""}`} role="button" tabIndex={0}
                    aria-label={`${c.name}（${open ? "營業中" : planned ? "本季開設" : "未開設"}）`} aria-pressed={selected === c.key}
                    data-testid={`city-${c.key}`}
                    onClick={() => setSelected(c.key)}
                    onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setSelected(c.key); } }}>
                    <circle cx={cx} cy={cy} r={16} />
                    <text x={cx} y={cy + 32} textAnchor="middle" className="city-label">{c.name}</text>
                  </g>
                );
              })}
            </g>
          );
        })}
      </svg>
      {region ? <RegionPanel region={region} draft={draft} readOnly={readOnly} onChange={onChange} /> : null}
      {city ? <CityPanel city={city} setup={setup} draft={draft} readOnly={readOnly} onChange={onChange} /> : null}
      {storeSetup || webSetup ? (
        <div className="cost-row">
          <span className="hud-label">本季開設費用（引擎試算）</span>
          {storeSetup ? <Estimate line={storeSetup} label="開店費用" /> : null}
          {webSetup ? <Estimate line={webSetup} label="網路中心開設" /> : null}
        </div>
      ) : null}
    </section>
  );
}
