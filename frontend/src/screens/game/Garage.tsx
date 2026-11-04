import { useEffect, useRef, useState } from "react";
import type { GameSetupDoc, Line, Report } from "../../types";
import { formatNumber } from "../../ui/Num";
import type { Selection } from "./Board";
import type { Draft, ProductDraft } from "./draft";
import { Figure } from "./Figure";
import { frameColor, ProductIcon } from "./icons";

/** Willingness to pay of the product's target segment across the cities (published values, as given). */
export function wtpRange(setup: GameSetupDoc, segment: string | null): { low: Line; high: Line } | null {
  const lines = setup.regions.flatMap((r) => r.cities.flatMap((c) => c.segments.filter((s) => s.id === segment).map((s) => s.wtp)));
  if (!lines.length) return null;
  const sorted = [...lines].sort((a, b) => a.value - b.value);
  return { low: sorted[0], high: sorted[sorted.length - 1] };
}

/**
 * Price against cost and willingness to pay, drawn on one track. Positions only (no margin is computed):
 * the band is the target segment's willingness to pay, the tick is the engine's unit cost, the dot is your price.
 */
export function PriceGauge({ price, cost, wtp }: { price: number; cost?: Line; wtp: { low: Line; high: Line } | null }) {
  const top = Math.max(price, cost?.value ?? 0, wtp?.high.value ?? 0, 1) * 1.15;
  const at = (v: number) => `${Math.max(0, Math.min(100, (v / top) * 100)).toFixed(1)}%`;
  const describe = [`定價 ${formatNumber(price)}`,
    cost ? `單位成本約 ${formatNumber(cost.value)}（預估）` : "單位成本試算後顯示",
    wtp ? `目標客群願付 ${formatNumber(wtp.low.value)} 到 ${formatNumber(wtp.high.value)}` : ""].filter(Boolean).join("，");
  return (
    <div className="gauge" role="img" aria-label={describe} data-testid="price-gauge">
      <div className="gauge-track">
        {wtp ? <span className="gauge-band" style={{ left: at(wtp.low.value), width: `calc(${at(wtp.high.value)} - ${at(wtp.low.value)} + 4px)` }} /> : null}
        {cost ? <span className="gauge-cost" style={{ left: at(cost.value) }} /> : null}
        <span className="gauge-price" style={{ left: at(price) }} />
      </div>
      <div className="gauge-legend">
        <span className="g-cost">成本 {cost ? <Figure line={cost} label="單位成本" /> : <span className="muted">試算後顯示</span>}</span>
        {wtp ? (
          <span className="g-wtp">願付 <Figure line={wtp.low} label="最低願付價格" />–<Figure line={wtp.high} label="最高願付價格" /></span>
        ) : null}
      </div>
    </div>
  );
}

function BikeCard({ setup, product, index, preview, selected, onOpen }: {
  setup: GameSetupDoc; product: ProductDraft; index: number; preview: Report | null; selected: boolean; onOpen: () => void;
}) {
  const typeIndex = setup.brand_types.findIndex((t) => t.code === product.brand_type);
  const type = setup.brand_types[typeIndex];
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
  return (
    <article className={`bike-card${bump ? " bump" : ""}${selected ? " selected" : ""}`} data-testid="product-card"
      aria-label={`${product.name}，定價 ${formatNumber(product.price)}`}>
      <div className="bike-stage"><ProductIcon icon={setup.theme.icon} size={150} color={frameColor(typeIndex)} /></div>
      <div className="bike-title">
        <h3>{product.name}</h3>
        <span className="muted">{type?.name}{type?.segment_name ? `，給 ${type.segment_name}` : ""}</span>
      </div>
      <p className="bike-price"><span className="bike-price-v">{formatNumber(product.price)}</span><span className="muted">定價</span></p>
      <PriceGauge price={product.price} cost={preview?.lines[`unit_cost[${product.name}]`]} wtp={wtpRange(setup, type?.segment_id ?? null)} />
      <button type="button" className="btn tune" aria-expanded={selected} onClick={onOpen} data-index={index}>調整</button>
    </article>
  );
}

/** The product row under the map: one bicycle card per product; all settings live behind "調整". */
export function Garage({ setup, draft, preview, readOnly, selection, onSelect, onChange }: {
  setup: GameSetupDoc; draft: Draft; preview: Report | null; readOnly: boolean; selection: Selection | null;
  onSelect: (s: Selection) => void; onChange: (d: Draft) => void;
}) {
  const add = () => {
    const type = setup.brand_types[0];
    if (!type) return;
    let n = draft.products.length + 1;
    while (draft.products.some((p) => p.name === `${setup.theme.product}-${n}`)) n += 1;
    const wtp = wtpRange(setup, type.segment_id);
    onChange({ ...draft, products: [...draft.products, {
      name: `${setup.theme.product}-${n}`, brand_type: type.code, components: [...type.default_components],
      price: wtp?.low.value ?? 0, production: 0, advertising: 0, locked: false }] });
    onSelect({ kind: "product", index: draft.products.length });
  };
  return (
    <section className="garage" aria-label={`${setup.theme.product}`}>
      {draft.products.map((product, i) => (
        <BikeCard key={i} setup={setup} product={product} index={i} preview={preview}
          selected={selection?.kind === "product" && selection.index === i}
          onOpen={() => onSelect({ kind: "product", index: i })} />
      ))}
      {!readOnly ? (
        <button type="button" className="bike-add" onClick={add}>
          <span aria-hidden="true" className="bike-add-plus">＋</span>新增{setup.theme.product}
        </button>
      ) : null}
      {draft.products.length === 0 && readOnly ? <p className="muted">這一季沒有產品。</p> : null}
    </section>
  );
}
