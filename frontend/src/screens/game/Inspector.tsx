import { useEffect, useRef, type ReactNode } from "react";
import type { GameSetupDoc, Report } from "../../types";
import { formatNumber } from "../../ui/Num";
import { storeOpen, webOpen, type Selection } from "./Board";
import { chooseComponent, type Draft, type ProductDraft } from "./draft";
import { Figure } from "./Figure";
import { PriceGauge, wtpRange } from "./Garage";
import { frameColor, ProductIcon } from "./icons";
import { Details, KeyResults, SummaryNote } from "./Settlement";

const ADVERTISING_MAX = 200000;

interface Common {
  setup: GameSetupDoc;
  draft: Draft;
  preview: Report | null;
  readOnly: boolean;
  onChange: (draft: Draft) => void;
}

function toggle(list: string[], key: string): string[] {
  return list.includes(key) ? list.filter((k) => k !== key) : [...list, key];
}

/** Price slider range: up to 1.5x the highest willingness to pay in the data (a UI bound, not a result). */
function priceMax(setup: GameSetupDoc): number {
  const wtps = setup.regions.flatMap((r) => r.cities.flatMap((c) => c.segments.map((s) => s.wtp.value)));
  return Math.max(100, Math.ceil((Math.max(0, ...wtps) * 1.5) / 10) * 10);
}

function Slider({ label, value, max, step, disabled, onChange, unit }: {
  label: string; value: number; max: number; step: number; disabled: boolean; onChange: (v: number) => void; unit?: string;
}) {
  return (
    <label className="slider">
      <span className="slider-head"><span>{label}</span><b className="slider-value">{formatNumber(value)}{unit ? ` ${unit}` : ""}</b></span>
      <input type="range" min={0} max={max} step={step} value={Math.min(value, max)} disabled={disabled} aria-label={label}
        onChange={(e) => onChange(Number(e.target.value))} />
    </label>
  );
}

function Stat({ label, children }: { label: string; children: ReactNode }) {
  return <div className="stat-line"><dt>{label}</dt><dd>{children}</dd></div>;
}

function CityPanel({ setup, draft, preview, readOnly, onChange, cityKey }: Common & { cityKey: string }) {
  const city = setup.regions.flatMap((r) => r.cities).find((c) => c.key === cityKey);
  if (!city) return null;
  const open = storeOpen(setup, city.key);
  const planned = draft.open_stores.includes(city.key);
  const setupLine = preview?.lines.store_setup;
  return (
    <div data-testid="city-panel">
      <p className="sheet-status">{open ? "營業中" : planned ? "本季開設，下一季開始銷售" : "還沒有店面"}</p>
      {city.store ? (
        <button type="button" className={`btn${planned ? "" : " primary"} wide`} disabled={readOnly || open}
          onClick={() => onChange({ ...draft, open_stores: toggle(draft.open_stores, city.key) })}>
          {open ? "已開店" : planned ? "取消本季開店" : "本季在這裡開店"}
        </button>
      ) : <p className="muted">這個城市沒有店面選項。</p>}
      {city.store ? (
        <dl className="stats">
          <Stat label="開店成本"><Figure line={city.store.setup_cost} label={`開店成本 ${city.name}`} /></Stat>
          <Stat label="每季租金"><Figure line={city.store.lease_cost} label={`租金 ${city.name}`} /></Stat>
          {planned && setupLine ? <Stat label="本季開店費用合計"><Figure line={setupLine} label="本季開店費用" /></Stat> : null}
        </dl>
      ) : null}
      <h3 className="sheet-sub">這裡的客群</h3>
      <table className="seg-table">
        <thead><tr><th>客群</th><th>一年市場規模</th><th>願付價格</th></tr></thead>
        <tbody>
          {city.segments.map((s) => (
            <tr key={s.id}>
              <td>{s.name}<small className="muted seg-needs">{setup.segments.find((x) => x.id === s.id)?.needs.slice(0, 2).join("、")}</small></td>
              <td><Figure line={s.size_12m} label={`市場規模 ${city.name} ${s.name}`} /></td>
              <td><Figure line={s.wtp} label={`願付價格 ${city.name} ${s.name}`} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function WebPanel({ setup, draft, preview, readOnly, onChange, webKey }: Common & { webKey: string }) {
  const region = setup.regions.find((r) => r.web_center?.key === webKey);
  const web = region?.web_center;
  if (!region || !web) return null;
  const planned = draft.open_web_centers.includes(web.key);
  const isOpen = webOpen(setup, web.key);
  const setupLine = preview?.lines.web_center_setup;
  return (
    <div data-testid="web-panel">
      <p className="sheet-status">{isOpen ? "營業中" : planned ? "本季開設" : "還沒有開設"}：網路銷售涵蓋整個區域 {region.id}。</p>
      <button type="button" className={`btn${planned ? "" : " primary"} wide`} disabled={readOnly || isOpen}
        onClick={() => onChange({ ...draft, open_web_centers: toggle(draft.open_web_centers, web.key) })}>
        {isOpen ? "已開設" : planned ? "取消本季開設" : "本季開設網路中心"}
      </button>
      <dl className="stats">
        <Stat label="開設成本"><Figure line={web.setup_cost} label={`網路中心 ${web.name}`} /></Stat>
        <Stat label="每季租金"><Figure line={web.lease_cost} label={`網路中心租金 ${web.name}`} /></Stat>
        {planned && setupLine ? <Stat label="本季開設費用"><Figure line={setupLine} label="網路中心開設" /></Stat> : null}
      </dl>
    </div>
  );
}

function FactoryPanel({ setup, draft, readOnly, onChange }: Common) {
  const option = setup.capacity_options.find((o) => o.units === draft.capacity_increase);
  return (
    <div data-testid="factory-panel">
      <dl className="stats">
        <Stat label="本季產能"><Figure line={setup.capacity_units_per_quarter} label="本季產能" unit={` ${setup.theme.unit}`} /></Stat>
      </dl>
      <h3 className="sheet-sub">擴充產能（本季購買，下季可用）</h3>
      <div className="seg" role="radiogroup" aria-label="購買產能">
        {setup.capacity_options.map((o) => (
          <button key={o.units} type="button" role="radio" className="seg-btn" aria-checked={draft.capacity_increase === o.units}
            disabled={readOnly} onClick={() => onChange({ ...draft, capacity_increase: o.units })}>
            {o.units === 0 ? "不擴充" : `+${formatNumber(o.units)} ${setup.theme.unit}/天`}
          </button>
        ))}
      </div>
      {option && option.units > 0 ? <dl className="stats"><Stat label="產能投資"><Figure line={option.cost} label="產能投資" /></Stat></dl> : null}
      {Object.keys(draft.finance).length ? (
        <p className="note">本季另含起始方案的財務決策（{[draft.finance.stock_issue ? "增資" : "", draft.finance.cd ? "定存" : ""].filter(Boolean).join("、")}），
          要調整請到「決策編輯」畫面。</p>
      ) : null}
    </div>
  );
}

function ProductPanel({ setup, draft, preview, readOnly, onChange, index, onClose }: Common & { index: number; onClose: () => void }) {
  const product = draft.products[index];
  if (!product) return null;
  const typeIndex = setup.brand_types.findIndex((t) => t.code === product.brand_type);
  const type = setup.brand_types[typeIndex];
  const capacity = setup.capacity_units_per_quarter.value;
  const locked = product.locked || readOnly;
  const set = (p: ProductDraft) => onChange({ ...draft, products: draft.products.map((x, j) => (j === index ? p : x)) });
  const sold = preview?.lines[`units_sold[${product.name}]`];
  return (
    <div data-testid="product-panel">
      <div className="sheet-bike"><ProductIcon icon={setup.theme.icon} size={190} color={frameColor(typeIndex)} /></div>
      <label className="field">名稱
        <input value={product.name} disabled={locked} aria-label="產品名稱" onChange={(e) => set({ ...product, name: e.target.value })} />
      </label>
      <PriceGauge price={product.price} cost={preview?.lines[`unit_cost[${product.name}]`]} wtp={wtpRange(setup, type?.segment_id ?? null)} />
      <Slider label="價格" value={product.price} max={priceMax(setup)} step={1} disabled={readOnly}
        onChange={(price) => set({ ...product, price })} />
      <Slider label="生產量" unit={setup.theme.unit} value={product.production} max={capacity} step={1}
        disabled={readOnly || capacity <= 0} onChange={(production) => set({ ...product, production })} />
      {capacity <= 0 ? <p className="note">本季產能為 0：先點地圖上的工廠擴充產能，下一季才能生產。</p> : null}
      <Slider label="廣告" value={product.advertising} max={ADVERTISING_MAX} step={1000} disabled={readOnly}
        onChange={(advertising) => set({ ...product, advertising })} />
      {sold ? <dl className="stats"><Stat label="本季銷量"><Figure line={sold} label={`銷量 ${product.name}`} unit={` ${setup.theme.unit}`} /></Stat></dl> : null}
      <h3 className="sheet-sub">設計</h3>
      {product.locked ? <p className="note">已經設計過：引擎沿用第一次的類型與配置。</p> : null}
      <label className="field">類型
        <select value={product.brand_type} disabled={locked}
          onChange={(e) => {
            const next = setup.brand_types.find((t) => t.code === e.target.value);
            set({ ...product, brand_type: e.target.value, components: next?.default_components ?? [] });
          }}>
          {setup.brand_types.map((t) => <option key={t.code} value={t.code}>{t.name}{t.segment_name ? `（給 ${t.segment_name}）` : ""}</option>)}
        </select>
      </label>
      {setup.component_groups.map((group) => {
        const options = setup.components.filter((c) => c.group === group.id && type?.components.includes(c.id));
        if (!options.length) return null;
        return (
          <div key={group.id} className="config-group">
            <span className="config-name">{group.name}{group.required ? "" : "（選配）"}</span>
            <div className="seg">
              {options.map((c) => (
                <button key={c.id} type="button" className="seg-btn" aria-pressed={product.components.includes(c.id)}
                  disabled={locked} onClick={() => set({ ...product, components: chooseComponent(setup, product.components, c.id) })}>
                  {c.name}{c.available_quarter ? <small> · Q{c.available_quarter} 起</small> : null}
                </button>
              ))}
            </div>
          </div>
        );
      })}
      {!readOnly ? (
        <button type="button" className="btn quiet-danger" onClick={() => {
          onChange({ ...draft, products: draft.products.filter((_, j) => j !== index) });
          onClose();
        }}>移除 {product.name}</button>
      ) : null}
    </div>
  );
}

function PreviewPanel({ setup, preview }: { setup: GameSetupDoc; preview: Report | null }) {
  if (!preview) return <p className="muted" data-testid="preview-panel">試算中…</p>;
  return (
    <div data-testid="preview-panel">
      <p className="sheet-status">還沒推進，改任何決策都會重新試算。</p>
      <KeyResults report={preview} setup={setup} />
      <SummaryNote report={preview} />
      <Details report={preview} setup={setup} />
    </div>
  );
}

function title(setup: GameSetupDoc, draft: Draft, s: Selection): string {
  if (s.kind === "city") return setup.regions.flatMap((r) => r.cities).find((c) => c.key === s.key)?.name ?? s.key;
  if (s.kind === "web") return `${setup.regions.find((r) => r.web_center?.key === s.key)?.web_center?.name ?? s.key} 網路中心`;
  if (s.kind === "factory") return "工廠";
  if (s.kind === "product") return draft.products[s.index]?.name ?? setup.theme.product;
  return "本季試算";
}

/** Side panel: the depth behind whatever was clicked on the board, a bike card or "試算". */
export function Inspector(props: Common & { selection: Selection; onClose: () => void }) {
  const { selection: s, onClose } = props;
  const headRef = useRef<HTMLHeadingElement>(null);
  const key = JSON.stringify(s);
  useEffect(() => { headRef.current?.focus(); }, [key]);
  return (
    <aside className="sheet" aria-label={`${title(props.setup, props.draft, s)}：詳細`} data-testid="inspector"
      onKeyDown={(e) => { if (e.key === "Escape") { e.stopPropagation(); onClose(); } }}>
      <header className="sheet-head">
        <h2 ref={headRef} tabIndex={-1}>{title(props.setup, props.draft, s)}</h2>
        <button type="button" className="icon-btn" aria-label="關閉側欄" onClick={onClose}>×</button>
      </header>
      <div className="sheet-body" key={key}>
        {s.kind === "city" ? <CityPanel {...props} cityKey={s.key} /> : null}
        {s.kind === "web" ? <WebPanel {...props} webKey={s.key} /> : null}
        {s.kind === "factory" ? <FactoryPanel {...props} /> : null}
        {s.kind === "product" ? <ProductPanel {...props} index={s.index} onClose={onClose} /> : null}
        {s.kind === "preview" ? <PreviewPanel setup={props.setup} preview={props.preview} /> : null}
      </div>
    </aside>
  );
}
