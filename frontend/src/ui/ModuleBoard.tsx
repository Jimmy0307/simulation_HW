import { useState, type ReactNode } from "react";
import type { LedgerRow, Line, Lines, Maturity, ModuleDecisions, ModuleField, ModulesDoc } from "../types";
import { formatNumber } from "./Num";
import { APPROX_TEXT, captureLabel, LiteratureBanner, MATURITY_ORDER, MATURITY_TEXT, MaturityPill, PracticeBadge, PracticeBanner } from "./Practice";

// Every business module, grouped by maturity. A module with an implementation appears with its levers in the group of
// its main part; each lever carries the badge of the part behind it (≈ literature, 練習 heuristic). Verified and
// literature rows without levers point to where they are decided; not-modeled ones are locked and explain why.
// No number is computed here: levers only edit the plan, results come back from the engine.

/** Where a lever already lives on the other screens (presentation only). */
const LEVER_HOME: Record<string, string> = {
  "marketing.segment_targeting": "產品類型（目標客群）",
  "marketing.brand_design": "產品類型與元件",
  "rnd.product_line": "新增 / 移除產品",
  "marketing.pricing": "產品售價",
  "marketing.ad_budget": "產品廣告預算",
  "channel.store_opening": "開店",
  "channel.web_center_opening": "網路中心",
  "channel.distribution_coverage": "開店與網路中心",
  "production.fixed_capacity": "產能",
  "finance.cd": "定存",
  "finance.stock": "增資",
  "market.rival_behaviour": "開局時選對手",
};

const MEDIA_LABEL: Record<string, string> = { local: "地方媒體", regional: "區域媒體", social: "社群", search: "搜尋" };

/** The editable modules: one per implementation, shown in the maturity group of its main part (``primary``). */
const editorsOf = (catalog: ModulesDoc) => catalog.modules.filter((r) => r.decidable && r.primary && r.module);

type Render = (line: Line, label: string, format?: "number" | "percent") => ReactNode;
type Part = "literature" | "heuristic";

function Badge({ part }: { part: Part }) {
  return part === "heuristic" ? <PracticeBadge /> : <span className="lit-mark" title={APPROX_TEXT}>≈ 文獻</span>;
}

function Range({ label, value, max, step, disabled, onChange, unit, part, min = 0 }: {
  label: string; value: number; max: number; step: number; disabled: boolean; onChange: (v: number) => void; unit?: string; part: Part;
  min?: number;
}) {
  return (
    <label className={`slider lever-${part}`}>
      <span className="slider-head"><span>{label} <Badge part={part} /></span><b className="slider-value">{formatNumber(value)}{unit ?? ""}</b></span>
      <input type="range" min={min} max={max} step={step} value={Math.max(min, Math.min(value, max))} disabled={disabled} aria-label={label}
        onChange={(e) => onChange(Number(e.target.value))} />
    </label>
  );
}

const num = (v: unknown, fallback: number): number => (typeof v === "number" && Number.isFinite(v) ? v : fallback);

function Results({ lines, keys, render }: { lines?: Lines | null; keys: [string, string, ("number" | "percent")?][]; render: Render }) {
  const shown = keys.filter(([k]) => lines?.[k]);
  if (!lines || !shown.length) return <p className="muted mod-wait">結果在試算後顯示（引擎計算）。</p>;
  return (
    <dl className="mod-results">
      {shown.map(([k, label, format]) => <div key={k}><dt>{label}</dt><dd>{render(lines[k], label, format)}</dd></div>)}
    </dl>
  );
}

interface EditorProps {
  catalog: ModulesDoc; decisions: ModuleDecisions; onChange?: (d: ModuleDecisions) => void; lines?: Lines | null; render: Render;
  brands: { name: string; advertising: number; inventory?: number }[]; carried?: Record<string, Record<string, number>>;
}

const coefficientsOf = (catalog: ModulesDoc, module: string) =>
  (catalog.modules.find((r) => r.module === module)?.coefficients ?? {}) as Record<string, unknown>;

function drop(decisions: ModuleDecisions, key: string): ModuleDecisions {
  const { [key]: _drop, ...rest } = decisions;
  return rest;
}

function SalesForceEditor({ catalog, decisions, carried, onChange, lines, render }: EditorProps) {
  const coeff = coefficientsOf(catalog, "sales_force");
  const block = decisions.sales_force as Record<string, unknown> | undefined;
  const team = carried?.sales_force;
  const employed = num(team?.headcount, 0) > 0;
  const on = Boolean(block) || employed;
  const ref = num(coeff.reference_salary, 1);
  const values = {
    headcount: num(block?.headcount, Math.round(num(team?.headcount, 0))),
    salary: num(block?.salary, num(team?.salary, ref)),
    commission_pct: num(block?.commission_pct, num(team?.commission_pct, num(coeff.reference_commission_pct, 0))),
    training: num(block?.training, 0),
    web_headcount: num(block?.web_headcount, Math.round(num(team?.web_headcount, 0))),
  };
  const set = (patch: Partial<typeof values>) => onChange?.({ ...decisions, sales_force: { ...values, ...patch } });
  const toggle = () => {
    if (!onChange) return;
    if (on && !employed) onChange(drop(decisions, "sales_force")); else set({});
  };
  const disabled = !onChange || !on;
  return (
    <section className="mod-editor lit" data-testid="sales-force-editor" aria-label="業務人力與薪酬">
      <header className="mod-editor-head">
        <h4>業務人力與薪酬</h4>
        <label className="mod-toggle">
          <input type="checkbox" checked={on} disabled={!onChange || employed} onChange={toggle} />
          {employed ? "團隊在職中（把人數設為 0 才會解散）" : "啟用業務團隊"}
        </label>
      </header>
      <LiteratureBanner>業務人數對銷售力的影響用文獻的固定彈性形式（報酬遞減），彈性在後設分析的範圍內。</LiteratureBanner>
      <PracticeBanner>底薪、佣金、訓練對留任和技能的影響，以及各項成本，仍是練習規則；用到訓練或沿用上季留下的人數時，需求鏈也會變成練習。</PracticeBanner>
      <div className="mod-levers">
        <Range part="literature" label="業務人數" value={values.headcount} max={60} step={1} disabled={disabled} unit=" 人" onChange={(v) => set({ headcount: v })} />
        <Range part="heuristic" label="每人每季底薪" value={values.salary} max={Math.round(ref * 3)} step={100} disabled={disabled} onChange={(v) => set({ salary: v })} />
        <Range part="heuristic" label="佣金（營收的 %）" value={values.commission_pct} max={15} step={0.5} disabled={disabled} unit=" %" onChange={(v) => set({ commission_pct: v })} />
        <Range part="heuristic" label="每人訓練費" value={values.training} max={Math.round(num(coeff.training_scale, 1000) * 3)} step={100} disabled={disabled}
          onChange={(v) => set({ training: v })} />
        <Range part="heuristic" label="網路業務人數" value={values.web_headcount} max={30} step={1} disabled={disabled} unit=" 人"
          onChange={(v) => set({ web_headcount: v })} />
      </div>
      <Results lines={lines} render={render} keys={[
        ["selling_effort", "銷售力倍數"], ["sales_force_quit_rate", "本季離職率", "percent"],
        ["sales_force_departures", "預計離職人數"], ["sales_force_salaries", "薪資"], ["sales_force_commission", "佣金"],
        ["sales_force_training", "訓練費"], ["sales_force_hiring", "招募與資遣"], ["web_sales_effort", "網路業務倍數"],
        ["web_sales_salaries", "網路業務薪資"]]} />
    </section>
  );
}

function MediaMixEditor({ catalog, decisions, brands, onChange, lines, render }: EditorProps) {
  const weights = (coefficientsOf(catalog, "marketing.media_mix").media_weights ?? {}) as Record<string, number>;
  const media = Object.keys(weights);
  const block = (decisions["marketing.media_mix"] as { mix?: Record<string, Record<string, number>> } | undefined) ?? {};
  const mix = block.mix ?? {};
  const write = (next: Record<string, Record<string, number>>) => {
    if (!onChange) return;
    onChange(Object.keys(next).length ? { ...decisions, "marketing.media_mix": { mix: next } } : drop(decisions, "marketing.media_mix"));
  };
  return (
    <section className="mod-editor lit" data-testid="media-mix-editor" aria-label="廣告媒體分配">
      <header className="mod-editor-head"><h4>廣告媒體分配</h4></header>
      <LiteratureBanner>每種媒體各自報酬遞減（MCI 形式），預算的總效果沿用需求面的文獻彈性；各媒體的權重是中性預設（相等），Q2 起才能估計。</LiteratureBanner>
      {!brands.length ? <p className="muted">先新增產品，才有廣告可以分配。</p> : null}
      {brands.map((brand) => {
        const shares = mix[brand.name];
        const on = Boolean(shares);
        const toggle = () => {
          const { [brand.name]: _drop, ...rest } = mix;
          write(on ? rest : { ...mix, [brand.name]: Object.fromEntries(media.map((m) => [m, 25])) });
        };
        return (
          <div key={brand.name} className="mod-brand" data-testid={`media-mix-${brand.name}`}>
            <label className="mod-toggle">
              <input type="checkbox" checked={on} disabled={!onChange} onChange={toggle} />
              分配「{brand.name}」的廣告（預算 {formatNumber(brand.advertising)}）
            </label>
            {on ? (
              <>
                <div className="mod-levers four">
                  {media.map((m) => (
                    <Range key={m} part="literature" label={MEDIA_LABEL[m] ?? m} value={num(shares?.[m], 0)} max={100} step={5} disabled={!onChange}
                      unit=" 份" onChange={(v) => write({ ...mix, [brand.name]: { ...shares, [m]: v } })} />
                  ))}
                </div>
                <Results lines={lines} render={render} keys={[[`media_mix_index[${brand.name}]`, "配比指數（1 = 最佳配比）"]]} />
              </>
            ) : null}
          </div>
        );
      })}
    </section>
  );
}

function InventoryEditor({ decisions, brands, onChange, lines, render }: EditorProps) {
  const block = decisions["supply.inventory"] as { sell_off?: Record<string, number> } | undefined;
  const on = Boolean(block);
  const sell = block?.sell_off ?? {};
  const write = (next: Record<string, number>) => onChange?.({ ...decisions, "supply.inventory": Object.keys(next).length ? { sell_off: next } : {} });
  const carried = brands.filter((b) => (b.inventory ?? 0) > 0);
  return (
    <section className="mod-editor lit" data-testid="inventory-editor" aria-label="庫存持有成本與出清">
      <header className="mod-editor-head">
        <h4>庫存持有成本與出清</h4>
        <label className="mod-toggle">
          <input type="checkbox" checked={on} disabled={!onChange}
            onChange={() => onChange?.(on ? drop(decisions, "supply.inventory") : { ...decisions, "supply.inventory": {} })} />
          計入庫存持有成本
        </label>
      </header>
      <LiteratureBanner>季末沒賣掉的庫存，按年持有成本率（文獻範圍內）÷ 4 乘以單位成本計費；單位成本仍是佔位規則，所以這筆費用顯示為佔位。</LiteratureBanner>
      {on ? (
        <>
          <PracticeBanner>出清：季初把上季留下的庫存賣掉，回收單位成本的一個暫定比例（沒有可用的文獻比例）。</PracticeBanner>
          {!carried.length ? <p className="muted">目前沒有上季留下的庫存可以出清。</p> : (
            <div className="mod-levers">
              {carried.map((b) => (
                <Range key={b.name} part="heuristic" label={`出清 ${b.name}`} value={num(sell[b.name], 0)} max={Math.floor(b.inventory ?? 0)} step={1}
                  disabled={!onChange} unit=" 件" onChange={(v) => {
                    const { [b.name]: _drop, ...rest } = sell;
                    write(v > 0 ? { ...rest, [b.name]: v } : rest);
                  }} />
              ))}
            </div>
          )}
        </>
      ) : null}
      <Results lines={lines} render={render} keys={[["inventory_holding_cost", "庫存持有成本"], ["inventory_selloff_proceeds", "出清收入"]]} />
    </section>
  );
}

function PurchasingEditor({ catalog, decisions, onChange, lines, render }: EditorProps) {
  const coeff = coefficientsOf(catalog, "supply.purchasing");
  const tiers = (coeff.discount_tiers ?? []) as [number, number][];
  const top = Math.max(1000, ...tiers.map(([u]) => u * 1.5));
  const block = decisions["supply.purchasing"] as { contract_units?: number } | undefined;
  const on = Boolean(block);
  return (
    <section className="mod-editor" data-testid="purchasing-editor" aria-label="採購合約與數量折扣">
      <header className="mod-editor-head">
        <h4>採購合約與數量折扣</h4>
        <label className="mod-toggle">
          <input type="checkbox" checked={on} disabled={!onChange}
            onChange={() => onChange?.(on ? drop(decisions, "supply.purchasing") : { ...decisions, "supply.purchasing": { contract_units: 0 } })} />
          簽採購合約
        </label>
      </header>
      <PracticeBanner>承諾的元件數量越多，材料成本折扣越大；沒生產到承諾量要付差額費。折扣級距與費用都是暫定值。</PracticeBanner>
      {on ? (
        <div className="mod-levers">
          <Range part="heuristic" label="每季承諾採購量（件）" value={num(block?.contract_units, 0)} max={Math.round(top)} step={50} disabled={!onChange}
            onChange={(v) => onChange?.({ ...decisions, "supply.purchasing": { contract_units: v } })} />
        </div>
      ) : null}
      {tiers.length ? <p className="muted mod-tiers">級距（暫定）：{tiers.map(([u, d]) => `${formatNumber(u)} 件起 ${Math.round(d * 100)}%`).join("、")}</p> : null}
      <Results lines={lines} render={render} keys={[["purchasing_discount", "折扣", "percent"], ["material_cost_factor", "材料成本倍數"],
        ["purchasing_shortfall_fee", "差額費"]]} />
    </section>
  );
}

/** Result lines of a generic editor; {brand}, {segment}, {rival} match any bracketed key. */
function expand(lines: Lines | null | undefined, spec: [string, string, ("number" | "percent")?][]): [string, string, ("number" | "percent")?][] {
  if (!lines) return [];
  return spec.flatMap(([key, label, format]) => {
    if (!key.includes("{")) return lines[key] ? [[key, label, format] as [string, string, ("number" | "percent")?]] : [];
    const head = key.slice(0, key.indexOf("["));
    return Object.keys(lines).filter((k) => k.startsWith(`${head}[`))
      .map((k) => [k, `${label} · ${k.slice(head.length + 1, -1)}`, format] as [string, string, ("number" | "percent")?]);
  });
}

function GenericEditor({ row, catalog, decisions, onChange, lines, render, brands, carried }: EditorProps & { row: LedgerRow }) {
  const key = row.module as string;
  const fields = row.fields ?? [];
  const ui = row.ui ?? {};
  const block = decisions[key] as Record<string, unknown> | undefined;
  const carriedOn = Object.keys(carried?.[key] ?? {}).length > 0;
  const stopped = block?.stop === true;
  const on = !stopped && (Boolean(block) || carriedOn);
  const partOf = (f: ModuleField): Part => (catalog.modules.find((r) => r.key === f.part)?.maturity === "heuristic" ? "heuristic" : "literature");
  const own = block && !stopped ? block : {};
  const write = (next: Record<string, unknown>) => onChange?.({ ...decisions, [key]: next });
  const toggle = () => {
    if (!onChange) return;
    if (on) {
      if (carriedOn) write({ stop: true }); else onChange(drop(decisions, key));
    } else {
      onChange(stopped ? drop(decisions, key) : { ...decisions, [key]: {} });
    }
  };
  const lockedOn = carriedOn && !row.stoppable;
  const value = (f: ModuleField, brand?: string): unknown => {
    const raw = own[f.name];
    if (brand !== undefined) return (raw as Record<string, unknown> | undefined)?.[brand] ?? f.default;
    return raw ?? f.default;
  };
  const set = (f: ModuleField, v: unknown, brand?: string) => write({ ...own, [f.name]: brand !== undefined
    ? { ...((own[f.name] as Record<string, unknown> | undefined) ?? {}), [brand]: v } : v });
  const disabled = !onChange || !on;
  const lever = (f: ModuleField, brand?: string) => {
    const label = brand !== undefined ? `${f.label} · ${brand}` : f.label;
    const id = `${f.name}${brand ?? ""}`;
    if (f.kind === "flag") {
      return (
        <label key={id} className={`mod-toggle lever-${partOf(f)}`}>
          <input type="checkbox" checked={Boolean(value(f, brand))} disabled={disabled} aria-label={label}
            onChange={(e) => set(f, e.target.checked, brand)} />{label} <Badge part={partOf(f)} />
        </label>
      );
    }
    if (f.kind === "choice" || f.kind === "brand_choice") {
      return (
        <label key={id} className={`mod-choice lever-${partOf(f)}`}>
          <span>{label} <Badge part={partOf(f)} /></span>
          <select value={String(value(f, brand))} disabled={disabled} aria-label={label} onChange={(e) => set(f, e.target.value, brand)}>
            {f.options.map(([v, text]) => <option key={v} value={v}>{text}</option>)}
          </select>
        </label>
      );
    }
    return <Range key={id} part={partOf(f)} label={label} value={num(value(f, brand), Number(f.default))} min={f.low} max={f.high} step={f.step}
      unit={f.unit} disabled={disabled} onChange={(v) => set(f, v, brand)} />;
  };
  const perBrand = (f: ModuleField) => f.kind === "brand_number" || f.kind === "brand_choice";
  const main = row.maturity === "literature" ? " lit" : "";
  return (
    <section className={`mod-editor${main}`} data-testid={`module-editor-${key}`} aria-label={row.name}>
      <header className="mod-editor-head">
        <h4>{row.name}</h4>
        <label className="mod-toggle">
          <input type="checkbox" checked={on} disabled={!onChange || lockedOn} onChange={toggle} aria-label={ui.toggle ?? `啟用${row.name}`} />
          {lockedOn ? "進行中（帶到下一季；把投入或餘額調到 0 才會結束）" : ui.toggle ?? `啟用${row.name}`}
        </label>
      </header>
      {ui.literature ? <LiteratureBanner>{ui.literature}</LiteratureBanner> : null}
      {ui.practice ? <PracticeBanner>{ui.practice}</PracticeBanner> : null}
      {on && fields.length ? (
        <div className="mod-levers">
          {fields.flatMap((f) => (perBrand(f) ? (brands.length ? brands.map((b) => lever(f, b.name)) : [<p key={f.name} className="muted">先新增產品。</p>]) : [lever(f)]))}
        </div>
      ) : null}
      <Results lines={lines} render={render} keys={expand(lines, ui.results ?? [])} />
    </section>
  );
}

const EDITOR_VIEW: Record<string, (p: EditorProps) => ReactNode> = {
  "marketing.media_mix": MediaMixEditor,
  sales_force: SalesForceEditor,
  "supply.inventory": InventoryEditor,
  "supply.purchasing": PurchasingEditor,
};

function LockedTile({ row }: { row: LedgerRow }) {
  const [open, setOpen] = useState(false);
  return (
    <li className={`mod-tile locked${open ? " open" : ""}`}>
      <button type="button" className="mod-lock" aria-expanded={open} data-testid={`locked-${row.key}`} onClick={() => setOpen(!open)}>
        <span className="mod-name">{row.name}</span>
        <span className="mod-meta">待建 · {captureLabel(row.capture)}</span>
      </button>
      {open ? (
        <div className="lock-reason" data-testid="lock-reason" role="note">
          <p><b>為什麼還不能調：</b>引擎還沒有這個模組，送出這類決策會被拒絕。{row.ours.startsWith("None") ? "" : `目前：${row.ours}`}</p>
          <p><b>真實遊戲：</b>{row.real_status === "measured" ? "實測" : row.real_status === "inferred" ? "推斷 · 未證實 · 待擷取" : "未知"}。{row.real_note}</p>
          <p><b>下一步：</b>{row.next_step}</p>
        </div>
      ) : null}
    </li>
  );
}

function InfoTile({ row }: { row: LedgerRow }) {
  const home = LEVER_HOME[row.key];
  const covered = Boolean(row.module && row.decidable);
  return (
    <li className={`mod-tile m-${row.maturity}`} title={row.ours}>
      <span className="mod-name">{row.name}</span>
      <span className="mod-meta">{covered ? "在上面的模組裡調整" : home ? `在「${home}」調整` : row.kind === "accounting" ? "自動計算，沒有可調的杆" : "沒有可調的杆"}</span>
    </li>
  );
}

/** All modules, grouped by maturity. `onChange` absent = read-only (demo). */
export function ModuleBoard({ catalog, decisions, onChange, brands, carried, lines, render, only }: {
  catalog: ModulesDoc; decisions: ModuleDecisions; onChange?: (d: ModuleDecisions) => void;
  brands: { name: string; advertising: number; inventory?: number }[]; carried?: Record<string, Record<string, number>>;
  lines?: Lines | null; render: Render; only?: Maturity[];
}) {
  const props: EditorProps = { catalog, decisions, onChange, lines, render, brands, carried };
  const groups = (only ?? MATURITY_ORDER).map((m) => ({ maturity: m, rows: catalog.modules.filter((r) => r.maturity === m) }));
  return (
    <div className="module-board" data-testid="module-board">
      {groups.map(({ maturity, rows }) => {
        const editors = editorsOf(catalog).filter((r) => r.maturity === maturity);
        const shown = new Set(editors.map((r) => r.key));
        const rest = rows.filter((r) => !shown.has(r.key));
        return (
          <section key={maturity} className={`mod-group g-${maturity}`} data-testid={`module-group-${maturity}`}>
            <h3 className="mod-group-head"><MaturityPill maturity={maturity} /><span>{rows.length} 個</span>
              <small className="muted">{MATURITY_TEXT[maturity].short}</small></h3>
            {editors.map((r) => {
              const view = EDITOR_VIEW[r.module as string];
              return <div key={r.key}>{view ? view(props) : <GenericEditor {...props} row={r} />}</div>;
            })}
            {rest.length ? (
              <ul className="mod-grid">
                {rest.map((row) => (maturity === "not-modeled" ? <LockedTile key={row.key} row={row} /> : <InfoTile key={row.key} row={row} />))}
              </ul>
            ) : null}
          </section>
        );
      })}
    </div>
  );
}
