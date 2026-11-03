import { useEffect, useRef, useState } from "react";
import type { GameSetupDoc, Report } from "../../types";
import { formatNumber } from "../../ui/Num";
import type { Draft, ProductDraft } from "./draft";
import { chooseComponent } from "./draft";
import { Estimate } from "./Estimate";
import { ProductIcon } from "./icons";

interface Props {
  setup: GameSetupDoc;
  draft: Draft;
  preview: Report | null;
  readOnly: boolean;
  onChange: (draft: Draft) => void;
}

const ADVERTISING_MAX = 200000;

/** Price slider range: up to 1.5x the highest willingness to pay in the data (a UI bound, not a result). */
function priceMax(setup: GameSetupDoc): number {
  const wtps = setup.regions.flatMap((r) => r.cities.flatMap((c) => c.segments.map((s) => s.wtp.value)));
  return Math.max(100, Math.ceil((Math.max(0, ...wtps) * 1.5) / 10) * 10);
}

function firstWtp(setup: GameSetupDoc, segment: string | null): number {
  for (const region of setup.regions) for (const city of region.cities) {
    const found = city.segments.find((s) => s.id === segment);
    if (found) return found.wtp.value;
  }
  return 0;
}

function Slider({ label, value, max, step, disabled, onChange, unit }: {
  label: string; value: number; max: number; step: number; disabled: boolean; onChange: (v: number) => void; unit?: string;
}) {
  return (
    <label className="slider">
      <span className="slider-head"><span>{label}</span><b className="slider-value">{formatNumber(value)}{unit ?? ""}</b></span>
      <input type="range" min={0} max={max} step={step} value={Math.min(value, max)} disabled={disabled} aria-label={label}
        onChange={(e) => onChange(Number(e.target.value))} />
    </label>
  );
}

function Card({ setup, product, preview, readOnly, onChange, onRemove, capacity }: {
  setup: GameSetupDoc; product: ProductDraft; preview: Report | null; readOnly: boolean; capacity: number;
  onChange: (p: ProductDraft) => void; onRemove: () => void;
}) {
  const type = setup.brand_types.find((t) => t.code === product.brand_type);
  const unitCost = preview?.lines[`unit_cost[${product.name}]`];
  const sold = preview?.lines[`units_sold[${product.name}]`];
  // Restrained feedback: a short highlight when an input changes, then back to rest.
  const [bump, setBump] = useState(false);
  const first = useRef(true);
  const signature = JSON.stringify(product);
  useEffect(() => {
    if (first.current) { first.current = false; return undefined; }
    setBump(true);
    const t = setTimeout(() => setBump(false), 450);
    return () => clearTimeout(t);
  }, [signature]);
  const locked = product.locked || readOnly;
  return (
    <article className={`product-card${bump ? " bump" : ""}`} data-testid="product-card">
      <header className="product-head">
        <span className="product-icon"><ProductIcon icon={setup.theme.icon} /></span>
        <input className="product-name" value={product.name} disabled={locked} aria-label="產品名稱"
          onChange={(e) => onChange({ ...product, name: e.target.value })} />
        {!readOnly ? <button type="button" className="icon-btn" aria-label={`移除 ${product.name}`} onClick={onRemove}>×</button> : null}
      </header>
      <div className="row">
        <label className="field">類型
          <select value={product.brand_type} disabled={locked}
            onChange={(e) => {
              const next = setup.brand_types.find((t) => t.code === e.target.value);
              onChange({ ...product, brand_type: e.target.value, components: next?.default_components ?? [] });
            }}>
            {setup.brand_types.map((t) => <option key={t.code} value={t.code}>{t.name}</option>)}
          </select>
        </label>
        <span className="pill">目標區隔：{type?.segment_name || "—"}</span>
        {product.locked ? <span className="pill" title="引擎沿用第一次設計時的類型與配置">已設計 · 配置鎖定</span> : null}
      </div>
      <div className="config">
        {setup.component_groups.map((group) => {
          const options = setup.components.filter((c) => c.group === group.id && type?.components.includes(c.id));
          if (!options.length) return null;
          return (
            <div key={group.id} className="config-group">
              <span className="config-name">{group.name}{group.required ? "" : "（選配）"}</span>
              <div className="seg">
                {options.map((c) => (
                  <button key={c.id} type="button" className="seg-btn" aria-pressed={product.components.includes(c.id)}
                    disabled={locked} onClick={() => onChange({ ...product, components: chooseComponent(setup, product.components, c.id) })}>
                    {c.name}{c.available_quarter ? <small> · Q{c.available_quarter}</small> : null}
                  </button>
                ))}
              </div>
            </div>
          );
        })}
      </div>
      <Slider label="價格" value={product.price} max={priceMax(setup)} step={1} disabled={readOnly}
        onChange={(price) => onChange({ ...product, price })} />
      <Slider label={`生產量（${setup.theme.unit}）`} value={product.production} max={capacity} step={1}
        disabled={readOnly || capacity <= 0} onChange={(production) => onChange({ ...product, production })} />
      {capacity <= 0 ? <p className="note">本季產能為 0：先在「工廠產能」購買，下季才能生產。</p> : null}
      <Slider label="廣告" value={product.advertising} max={ADVERTISING_MAX} step={1000} disabled={readOnly}
        onChange={(advertising) => onChange({ ...product, advertising })} />
      <footer className="product-foot">
        <span className="foot-item"><span className="hud-label">單位成本</span>
          {unitCost ? <Estimate line={unitCost} label={`單位成本 ${product.name}`} /> : <span className="muted">試算後顯示</span>}
        </span>
        {sold ? <span className="foot-item"><span className="hud-label">本季銷量</span><Estimate line={sold} label={`銷量 ${product.name}`} /></span> : null}
      </footer>
    </article>
  );
}

/** "Make products": one card per product; type and components come from the data source, never hard-coded. */
export function ProductCards({ setup, draft, preview, readOnly, onChange }: Props) {
  const capacity = setup.capacity_units_per_quarter.value;
  const update = (i: number, product: ProductDraft) =>
    onChange({ ...draft, products: draft.products.map((p, j) => (j === i ? product : p)) });
  const add = () => {
    const type = setup.brand_types[0];
    if (!type) return;
    let n = draft.products.length + 1;
    while (draft.products.some((p) => p.name === `${setup.theme.product}-${n}`)) n += 1;
    onChange({ ...draft, products: [...draft.products, {
      name: `${setup.theme.product}-${n}`, brand_type: type.code, components: [...type.default_components],
      price: firstWtp(setup, type.segment_id), production: 0, advertising: 0, locked: false }] });
  };
  return (
    <section className="card" aria-label="做產品">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h2 style={{ margin: 0 }}>做{setup.theme.product}</h2>
        {!readOnly ? <button type="button" className="btn" onClick={add}>＋ 新增{setup.theme.product}</button> : null}
      </div>
      {draft.products.length === 0 ? <p className="muted">還沒有產品。按「新增」設計第一款{setup.theme.product}。</p> : null}
      <div className="product-grid">
        {draft.products.map((product, i) => (
          <Card key={i} setup={setup} product={product} preview={preview} readOnly={readOnly} capacity={capacity}
            onChange={(p) => update(i, p)} onRemove={() => onChange({ ...draft, products: draft.products.filter((_, j) => j !== i) })} />
        ))}
      </div>
      <div className="factory">
        <label className="field">工廠產能（本季購買，下季可用）
          <select value={draft.capacity_increase} disabled={readOnly} aria-label="購買產能"
            onChange={(e) => onChange({ ...draft, capacity_increase: Number(e.target.value) })}>
            {setup.capacity_options.map((o) => (
              <option key={o.units} value={o.units}>{o.units === 0 ? "不購買" : `+${formatNumber(o.units)} ${setup.theme.unit}/天`}</option>
            ))}
          </select>
        </label>
        {(() => {
          const option = setup.capacity_options.find((o) => o.units === draft.capacity_increase);
          return option && option.units > 0
            ? <span className="foot-item"><span className="hud-label">產能投資</span><Estimate line={option.cost} label="產能投資" /></span> : null;
        })()}
      </div>
      {Object.keys(draft.finance).length ? (
        <p className="note">本季另含起始方案的財務決策：{draft.finance.stock_issue ? "增資" : ""}{draft.finance.stock_issue && draft.finance.cd ? "、" : ""}
          {draft.finance.cd ? "CD 存提" : ""}（調整請用「決策編輯」畫面）。</p>
      ) : null}
    </section>
  );
}
