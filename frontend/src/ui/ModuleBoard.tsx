import { useState, type ReactNode } from "react";
import type { LedgerRow, Line, Lines, Maturity, ModuleDecisions, ModulesDoc } from "../types";
import { formatNumber } from "./Num";
import { captureLabel, MATURITY_ORDER, MATURITY_TEXT, MaturityPill, PracticeBanner } from "./Practice";

// Every business module, grouped by maturity. Heuristic modules with an implementation get levers (and the practice
// banner); verified / literature modules point to where they are decided; not-modeled ones are locked and explain why.
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

type Render = (line: Line, label: string, format?: "number" | "percent") => ReactNode;

function Range({ label, value, max, step, disabled, onChange, unit }: {
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

function SalesForceEditor({ catalog, decisions, carried, onChange, lines, render }: {
  catalog: ModulesDoc; decisions: ModuleDecisions; carried?: Record<string, number>; onChange?: (d: ModuleDecisions) => void;
  lines?: Lines | null; render: Render;
}) {
  const coeff = catalog.modules.find((r) => r.module === "sales_force")?.coefficients ?? {};
  const block = decisions.sales_force as Record<string, unknown> | undefined;
  const employed = num(carried?.headcount, 0) > 0;
  const on = Boolean(block) || employed;
  const ref = num(coeff.reference_salary, 1);
  const values = {
    headcount: num(block?.headcount, Math.round(num(carried?.headcount, 0))),
    salary: num(block?.salary, num(carried?.salary, ref)),
    commission_pct: num(block?.commission_pct, num(carried?.commission_pct, num(coeff.reference_commission_pct, 0))),
    training: num(block?.training, 0),
  };
  const set = (patch: Partial<typeof values>) => onChange?.({ ...decisions, sales_force: { ...values, ...patch } });
  const toggle = () => {
    if (!onChange) return;
    if (on && !employed) {
      const { sales_force: _drop, ...rest } = decisions;
      onChange(rest);
    } else set({});
  };
  const disabled = !onChange || !on;
  return (
    <section className="mod-editor" data-testid="sales-force-editor" aria-label="業務人力與薪酬">
      <header className="mod-editor-head">
        <h4>業務人力與薪酬</h4>
        <label className="mod-toggle">
          <input type="checkbox" checked={on} disabled={!onChange || employed} onChange={toggle} />
          {employed ? "團隊在職中（把人數設為 0 才會解散）" : "啟用業務團隊"}
        </label>
      </header>
      <PracticeBanner />
      <div className="mod-levers">
        <Range label="業務人數" value={values.headcount} max={60} step={1} disabled={disabled} unit=" 人" onChange={(v) => set({ headcount: v })} />
        <Range label="每人每季底薪" value={values.salary} max={Math.round(ref * 3)} step={100} disabled={disabled} onChange={(v) => set({ salary: v })} />
        <Range label="佣金（營收的 %）" value={values.commission_pct} max={15} step={0.5} disabled={disabled} unit=" %" onChange={(v) => set({ commission_pct: v })} />
        <Range label="每人訓練費" value={values.training} max={Math.round(num(coeff.training_scale, 1000) * 3)} step={100} disabled={disabled}
          onChange={(v) => set({ training: v })} />
      </div>
      <Results lines={lines} render={render} keys={[
        ["selling_effort", "銷售力倍數"], ["sales_force_quit_rate", "本季離職率", "percent"],
        ["sales_force_departures", "預計離職人數"], ["sales_force_salaries", "薪資"], ["sales_force_commission", "佣金"],
        ["sales_force_training", "訓練費"], ["sales_force_hiring", "招募與資遣"]]} />
    </section>
  );
}

function MediaMixEditor({ catalog, decisions, brands, onChange, lines, render }: {
  catalog: ModulesDoc; decisions: ModuleDecisions; brands: { name: string; advertising: number }[];
  onChange?: (d: ModuleDecisions) => void; lines?: Lines | null; render: Render;
}) {
  const weights = (catalog.modules.find((r) => r.module === "marketing.media_mix")?.coefficients?.media_weights ?? {}) as Record<string, number>;
  const media = Object.keys(weights);
  const block = (decisions["marketing.media_mix"] as { mix?: Record<string, Record<string, number>> } | undefined) ?? {};
  const mix = block.mix ?? {};
  const write = (next: Record<string, Record<string, number>>) => {
    if (!onChange) return;
    if (!Object.keys(next).length) {
      const { "marketing.media_mix": _drop, ...rest } = decisions;
      onChange(rest);
    } else onChange({ ...decisions, "marketing.media_mix": { mix: next } });
  };
  return (
    <section className="mod-editor" data-testid="media-mix-editor" aria-label="廣告媒體分配">
      <header className="mod-editor-head"><h4>廣告媒體分配</h4></header>
      <PracticeBanner />
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
                    <Range key={m} label={MEDIA_LABEL[m] ?? m} value={num(shares?.[m], 0)} max={100} step={5} disabled={!onChange}
                      unit=" 份" onChange={(v) => write({ ...mix, [brand.name]: { ...shares, [m]: v } })} />
                  ))}
                </div>
                <Results lines={lines} render={render} keys={[[`ad_efficiency[${brand.name}]`, "分配效率"],
                  [`effective_advertising[${brand.name}]`, "有效廣告量"]]} />
              </>
            ) : null}
          </div>
        );
      })}
    </section>
  );
}

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
          <p><b>為什麼還不能調：</b>引擎還沒有這個模組，送出這類決策會被拒絕。{row.ours !== "None." ? `目前：${row.ours}` : ""}</p>
          <p><b>真實遊戲：</b>{row.real_status === "measured" ? "實測" : row.real_status === "inferred" ? "推斷 · 未證實 · 待擷取" : "未知"}。{row.real_note}</p>
          <p><b>下一步：</b>{row.next_step}</p>
        </div>
      ) : null}
    </li>
  );
}

function InfoTile({ row }: { row: LedgerRow }) {
  const home = LEVER_HOME[row.key];
  return (
    <li className={`mod-tile m-${row.maturity}`} title={row.ours}>
      <span className="mod-name">{row.name}</span>
      <span className="mod-meta">{home ? `在「${home}」調整` : row.kind === "accounting" ? "自動計算，沒有可調的杆" : "沒有可調的杆"}</span>
    </li>
  );
}

/** All modules, grouped by maturity. `onChange` absent = read-only (demo). */
export function ModuleBoard({ catalog, decisions, onChange, brands, carried, lines, render, only }: {
  catalog: ModulesDoc; decisions: ModuleDecisions; onChange?: (d: ModuleDecisions) => void;
  brands: { name: string; advertising: number }[]; carried?: Record<string, Record<string, number>>;
  lines?: Lines | null; render: Render; only?: Maturity[];
}) {
  const groups = (only ?? MATURITY_ORDER).map((m) => ({ maturity: m, rows: catalog.modules.filter((r) => r.maturity === m) }));
  return (
    <div className="module-board" data-testid="module-board">
      {groups.map(({ maturity, rows }) => {
        const editable = maturity === "heuristic" ? [...new Set(rows.filter((r) => r.decidable).map((r) => r.module))] : [];
        const rest = rows.filter((r) => !(r.decidable && maturity === "heuristic"));
        return (
          <section key={maturity} className={`mod-group g-${maturity}`} data-testid={`module-group-${maturity}`}>
            <h3 className="mod-group-head"><MaturityPill maturity={maturity} /><span>{rows.length} 個</span>
              <small className="muted">{MATURITY_TEXT[maturity].short}</small></h3>
            {editable.includes("sales_force") ? (
              <SalesForceEditor catalog={catalog} decisions={decisions} carried={carried?.sales_force} onChange={onChange} lines={lines} render={render} />
            ) : null}
            {editable.includes("marketing.media_mix") ? (
              <MediaMixEditor catalog={catalog} decisions={decisions} brands={brands} onChange={onChange} lines={lines} render={render} />
            ) : null}
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
