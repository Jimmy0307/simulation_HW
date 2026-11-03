import { useCallback, useEffect, useState, type ReactNode } from "react";
import type { Line, Lines, PackInfo } from "../types";
import { formatNumber, Num } from "./Num";

export function Card({ title, children, actions }: { title?: string; children: ReactNode; actions?: ReactNode }) {
  return (
    <section className="card">
      {title || actions ? (
        <div className="row" style={{ justifyContent: "space-between", marginBottom: 8 }}>
          {title ? <h2 style={{ margin: 0 }}>{title}</h2> : <span />}
          {actions}
        </div>
      ) : null}
      {children}
    </section>
  );
}

export function Banner({ kind, title, children }: { kind: "warn" | "danger" | "info"; title?: string; children: ReactNode }) {
  return (
    <div className={`banner ${kind}`} role={kind === "info" ? "status" : "alert"}>
      {title ? <b>{title}</b> : null}
      <div>{children}</div>
    </div>
  );
}

export function PackBadge({ pack, mode }: { pack: PackInfo | null; mode: "static" | "api" }) {
  if (!pack) return <span className="pill">載入中…</span>;
  return (
    <span className="badges">
      <span className={`pill ${pack.is_private ? "pack-private" : "pack-synthetic"}`} data-testid="pack-badge">
        {pack.is_private ? "PRIVATE 真實資料" : "SYNTHETIC 虛構資料"} · {pack.name}
      </span>
      <span className="pill">{mode === "api" ? "實戰模式 · 本機 API" : "Demo 模式 · 靜態唯讀"}</span>
      <span className="pill">需求模型：{pack.demand_model}</span>
    </span>
  );
}

export interface AsyncState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  reload: () => void;
}

export function useAsync<T>(fn: () => Promise<T>, deps: unknown[]): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  const reload = useCallback(() => setTick((t) => t + 1), []);
  useEffect(() => {
    let alive = true;
    setLoading(true);
    fn().then((value) => { if (alive) { setData(value); setError(null); } })
      .catch((e: unknown) => { if (alive) setError(e instanceof Error ? e.message : String(e)); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);
  return { data, error, loading, reload };
}

export function Status({ state }: { state: { loading: boolean; error: string | null } }) {
  if (state.error) return <p className="error">{state.error}</p>;
  if (state.loading) return <p className="muted">載入中…</p>;
  return null;
}

const LINE_LABELS: Record<string, string> = {
  cash_start: "期初現金", cash_end: "期末現金", revenue: "營收", net_income: "淨利", market_share: "市佔",
  market_units_total: "市場總銷量", capex_capacity: "產能投資", capacity_units_per_quarter: "每季產能",
  production_cost: "生產成本", advertising: "廣告", income_tax: "所得稅", operating_profit_before_tax: "稅前營業利益",
  cd_balance: "CD 餘額", cd_interest: "CD 利息", stock_raised: "增資", store_setup: "開店費用", web_center_setup: "網路中心開設",
  outlet_lease: "通路租金", design_cost: "設計費", emergency_loan: "緊急貸款", fixed_capacity_next_quarter: "下季固定產能",
};

export function lineLabel(key: string): string {
  const base = key.split("[")[0];
  const brand = key.includes("[") ? key.slice(key.indexOf("[")) : "";
  const names: Record<string, string> = { units_sold: "銷量", units_demanded: "需求量", unit_cost: "單位成本" };
  return (LINE_LABELS[key] ?? names[base] ?? base) + brand;
}

export function LinesTable({ lines }: { lines: Lines }) {
  return (
    <div className="table-wrap">
      <table>
        <thead><tr><th>項目</th><th>數值（顏色 = 來源等級；滑鼠移上看來源鏈）</th></tr></thead>
        <tbody>
          {Object.entries(lines).map(([key, line]) => (
            <tr key={key}><td>{lineLabel(key)} <span className="muted mono">{key}</span></td><td><Num line={line} label={key} /></td></tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ValueCell({ line, label }: { line: Line | undefined; label: string }) {
  return line ? <Num line={line} label={label} /> : <span className="muted">—</span>;
}

export function plain(value: unknown): string {
  if (typeof value === "number") return formatNumber(value);
  if (value === null || value === undefined) return "—";
  return typeof value === "object" ? JSON.stringify(value) : String(value);
}
