import { useEffect, useRef } from "react";
import type { GameSetupDoc, Line, Report } from "../../types";
import { lineLabel } from "../../ui/common";
import { isUncalibrated } from "../../ui/Num";
import { APPROX, Figure } from "./Figure";

export const MARKET = new Set(["units_demanded", "units_sold", "market_units_total", "market_share", "revenue"]);
export const RESULT = new Set(["operating_profit_before_tax", "income_tax", "net_income", "emergency_loan", "cash_end"]);
export const base = (key: string) => key.split("[")[0];

/** One line for the whole card, instead of a mark on every cell. */
export function summaryNote(report: Report): string | null {
  const levels = new Set(Object.values(report.lines).filter((l) => isUncalibrated(l)).map((l) => l.level));
  if (!levels.size) return null;
  const parts: string[] = [];
  if (levels.has("literature")) parts.push("銷量、營收與市佔來自文獻假設，Q2 數據校準後變實際");
  if (levels.has("placeholder")) parts.push("單位成本、租金、稅與現金用的是佔位規則，驗證實驗完成後變實際");
  const practice = levels.has("heuristic")
    ? "標「練習」的數字用了暫定的練習規則（業務團隊或廣告分配）：練習用 · 規則暫定 · 真實關係待 Q2，只能看方向。"
    : "";
  const estimates = parts.length ? `標 ${APPROX} 的是預估，不是本局預測：${parts.join("；")}。` : "";
  return [practice, estimates].filter(Boolean).join(" ");
}

export function SummaryNote({ report }: { report: Report }) {
  const text = summaryNote(report);
  return text ? <p className="summary-note" role="note" data-testid="literature-notice">{text}</p> : null;
}

export function group(lines: Report["lines"], keep: (key: string) => boolean): [string, Line][] {
  const rows = Object.entries(lines).filter(([key]) => keep(key));
  // trusted numbers first, estimates after: the reliable part is read first, never the other way round
  return [...rows.filter(([, l]) => !isUncalibrated(l)), ...rows.filter(([, l]) => isUncalibrated(l))];
}

const SHARES = new Set(["market_share", "rival_share"]);

/** Readable names in the game view: per-product lines as "銷量 · name", rival lines by opponent number. */
export function gameLabel(setup: GameSetupDoc, key: string): string {
  const b = base(key);
  const inner = key.includes("[") ? key.slice(key.indexOf("[") + 1, -1) : "";
  if (b === "rival_units") return `${rivalLabel(setup, inner)} 銷量`;
  if (b === "rival_share") return `${rivalLabel(setup, inner)} 市佔`;
  if (b === "market_share") return "我們的市佔";
  return inner ? `${lineLabel(b)} · ${inner}` : lineLabel(key);
}

export function Rows({ rows, setup }: { rows: [string, Line][]; setup: GameSetupDoc }) {
  return (
    <table className="detail-table">
      <tbody>
        {rows.map(([key, line]) => (
          <tr key={key} data-uncalibrated={isUncalibrated(line) ? "true" : "false"}>
            <td>{gameLabel(setup, key)}</td>
            <td><Figure line={line} label={gameLabel(setup, key)} format={SHARES.has(base(key)) ? "percent" : "number"} /></td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/** Every line of the report, one click away. */
export function Details({ report, setup }: { report: Report; setup: GameSetupDoc }) {
  const rival = (k: string) => k.startsWith("rival_");
  const cost = group(report.lines, (k) => !MARKET.has(base(k)) && !RESULT.has(base(k)) && !rival(k));
  const market = group(report.lines, (k) => MARKET.has(base(k)) || rival(k));
  const result = group(report.lines, (k) => RESULT.has(base(k)));
  return (
    <details className="details" data-testid="details">
      <summary>完整明細</summary>
      <div className="detail-grid">
        <section><h4>投資與費用</h4><Rows rows={cost} setup={setup} /></section>
        <section><h4>銷售與市佔</h4><Rows rows={market} setup={setup} /></section>
        <section><h4>損益與現金</h4><Rows rows={result} setup={setup} /></section>
      </div>
      {report.notes.length ? (
        <><h4>引擎註記</h4><ul className="engine-notes">{report.notes.map((n) => <li key={n}>{n}</li>)}</ul></>
      ) : null}
    </details>
  );
}

const KEY_RESULTS = ["revenue", "net_income", "cash_end"];
const SPENDING = ["capex_capacity", "store_setup", "web_center_setup", "advertising"];

/** The few numbers a player reads first: units per product, revenue, profit, cash, and what was invested. */
export function KeyResults({ report, setup }: { report: Report; setup: GameSetupDoc }) {
  const sold = Object.entries(report.lines).filter(([k]) => k.startsWith("units_sold["));
  const spend = SPENDING.map((k) => [k, report.lines[k]] as const).filter(([, l]) => l && l.value !== 0);
  return (
    <dl className="key-results" data-testid="key-results">
      {sold.map(([k, l]) => (
        <div key={k} className="kr"><dt>{gameLabel(setup, k)}</dt><dd><Figure line={l} label={lineLabel(k)} unit={` ${setup.theme.unit}`} /></dd></div>
      ))}
      {KEY_RESULTS.filter((k) => report.lines[k]).map((k) => (
        <div key={k} className="kr"><dt>{lineLabel(k)}</dt><dd><Figure line={report.lines[k]} label={lineLabel(k)} /></dd></div>
      ))}
      {spend.map(([k, l]) => (
        <div key={k} className="kr spend"><dt>{lineLabel(k)}</dt><dd><Figure line={l} label={lineLabel(k)} /></dd></div>
      ))}
    </dl>
  );
}

export function rivalLabel(setup: GameSetupDoc, firm: string): string {
  const index = setup.game?.opponents.findIndex((o) => o.name === firm) ?? -1;
  const opponent = index >= 0 ? setup.game?.opponents[index] : undefined;
  return opponent ? `對手 ${index + 1} · ${opponent.label}` : firm;
}

/** Market share, you against each rival: one bar each, labelled directly (bar length is position only). */
export function ShareChart({ report, setup }: { report: Report; setup: GameSetupDoc }) {
  const firms = Object.keys(report.lines).filter((k) => k.startsWith("rival_share[")).map((k) => k.slice(12, -1));
  const ours = report.lines.market_share;
  const rows: { key: string; name: string; line: Line; us: boolean }[] = [
    ...(ours ? [{ key: "us", name: "我們", line: ours, us: true }] : []),
    ...firms.map((f) => ({ key: f, name: rivalLabel(setup, f), line: report.lines[`rival_share[${f}]`], us: false })),
  ];
  const top = Math.max(0.0001, ...rows.map((r) => r.line.value));
  return (
    <figure className="share-chart" data-testid="rival-table" aria-label="市佔比較">
      <figcaption>市佔</figcaption>
      <ol>
        {rows.map((r) => (
          <li key={r.key} className={r.us ? "us" : "rival"} data-testid={r.us ? "share-us" : "rival-row"}>
            <span className="share-name">{r.name}</span>
            <span className="share-track" title={`${r.name} 市佔`}>
              <span className="share-bar" style={{ width: `${Math.max(1, (r.line.value / top) * 100).toFixed(1)}%` }} />
            </span>
            <span className="share-value"><Figure line={r.line} label={`${r.name} 市佔`} format="percent" /></span>
          </li>
        ))}
      </ol>
    </figure>
  );
}

/** End of a quarter: a clean report card. Share chart and key results first; every line one click away. */
export function SettlementCard({ report, setup, onClose }: { report: Report; setup: GameSetupDoc; onClose: () => void }) {
  const closeRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <div className="settle-backdrop" role="presentation" onClick={onClose}>
      <div className="report-card" role="dialog" aria-modal="true" aria-label={`第 ${report.quarter} 季結算`}
        data-testid="settlement" onClick={(e) => e.stopPropagation()}>
        <header className="report-head">
          <p className="report-q"><span>第</span><b>{report.quarter}</b><span>季成績單</span></p>
          <button ref={closeRef} type="button" className="btn primary" onClick={onClose}>回到下一季</button>
        </header>
        <div className="report-body">
          <ShareChart report={report} setup={setup} />
          <section aria-label="本季關鍵結果"><h3 className="report-sub">本季結果</h3><KeyResults report={report} setup={setup} /></section>
        </div>
        <SummaryNote report={report} />
        <Details report={report} setup={setup} />
      </div>
    </div>
  );
}

/** Played quarters as small chips; each reopens its report card. */
export function Timeline({ history, onOpen }: { history: Report[]; onOpen: (r: Report) => void }) {
  if (!history.length) return null;
  return (
    <nav className="timeline" aria-label="成績單">
      <span className="muted">成績單</span>
      <ol data-testid="timeline">
        {history.map((r) => (
          <li key={r.quarter}><button type="button" className="q-chip" onClick={() => onOpen(r)}>Q{r.quarter}</button></li>
        ))}
      </ol>
    </nav>
  );
}
