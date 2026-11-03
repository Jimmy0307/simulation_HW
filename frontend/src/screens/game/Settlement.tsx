import { useEffect, useRef, useState } from "react";
import type { GameSetupDoc, Line, Report } from "../../types";
import { lineLabel } from "../../ui/common";
import { isUncalibrated } from "../../ui/Num";
import { becomesActual, Estimate } from "./Estimate";

export const MARKET = new Set(["units_demanded", "units_sold", "market_units_total", "market_share", "revenue"]);
export const RESULT = new Set(["operating_profit_before_tax", "income_tax", "net_income", "emergency_loan", "cash_end"]);
export const base = (key: string) => key.split("[")[0];

export const LITERATURE_NOTICE = "本季銷量、營收為文獻假設下的預估，非本局預測；Q2 校準後轉為實際。";

export function group(lines: Report["lines"], keep: (key: string) => boolean): [string, Line][] {
  const rows = Object.entries(lines).filter(([key]) => keep(key));
  // trusted numbers first, estimates after: the reliable part is read first, never the other way round
  return [...rows.filter(([, l]) => !isUncalibrated(l)), ...rows.filter(([, l]) => isUncalibrated(l))];
}

export function Rows({ rows, open }: { rows: [string, Line][]; open?: boolean }) {
  return (
    <table className="settle-table">
      <tbody>
        {rows.map(([key, line]) => (
          <tr key={key} data-uncalibrated={isUncalibrated(line) ? "true" : "false"}>
            <td>{lineLabel(key)}</td>
            <td><Estimate line={line} label={lineLabel(key)} open={open} /></td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function rivalLabel(setup: GameSetupDoc, firm: string): string {
  const index = setup.game?.opponents.findIndex((o) => o.name === firm) ?? -1;
  const opponent = index >= 0 ? setup.game?.opponents[index] : undefined;
  return opponent ? `對手 ${index + 1} · ${opponent.label}` : firm;
}

function Rivals({ report, setup }: { report: Report; setup: GameSetupDoc }) {
  const [open, setOpen] = useState(false);
  const firms = Object.keys(report.lines).filter((k) => k.startsWith("rival_share[")).map((k) => k.slice(12, -1));
  const ours = report.lines.market_share;
  return (
    <div className="rivals" data-testid="rival-table">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h3>市佔比較（全部為預估）</h3>
        <button type="button" className="btn small" onClick={() => setOpen((o) => !o)}>{open ? "收合" : "全部展開"}</button>
      </div>
      <table className="settle-table">
        <thead><tr><th>公司</th><th>市佔</th><th>銷量</th></tr></thead>
        <tbody>
          {ours ? (
            <tr className="us"><td>我們</td><td><Estimate line={ours} label="我們的市佔" open={open} note={false} /></td>
              <td>{Object.entries(report.lines).filter(([k]) => k.startsWith("units_sold[")).length ? "見上方各產品" : "—"}</td></tr>
          ) : null}
          {firms.map((firm) => (
            <tr key={firm} data-testid="rival-row">
              <td>{rivalLabel(setup, firm)}</td>
              <td><Estimate line={report.lines[`rival_share[${firm}]`]} label={`${firm} 市佔`} open={open} note={false} /></td>
              <td>{report.lines[`rival_units[${firm}]`]
                ? <Estimate line={report.lines[`rival_units[${firm}]`]} label={`${firm} 銷量`} open={open} note={false} /> : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {ours ? <p className="note">市佔為 0 到 1 的比例。整張表都是預估：{becomesActual(ours.level)}。</p> : null}
    </div>
  );
}

/** End-of-quarter card: trusted cost side shown plainly; sales, revenue, share and profit in the estimate state. */
export function SettlementCard({ report, setup, onClose }: { report: Report; setup: GameSetupDoc; onClose: () => void }) {
  const closeRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  const literature = Object.values(report.lines).some((l) => l.level === "literature");
  const rival = (k: string) => k.startsWith("rival_");
  const cost = group(report.lines, (k) => !MARKET.has(base(k)) && !RESULT.has(base(k)) && !rival(k));
  const market = group(report.lines, (k) => MARKET.has(base(k)) && k !== "market_share");
  const result = group(report.lines, (k) => RESULT.has(base(k)));
  return (
    <div className="settle-backdrop" role="presentation" onClick={onClose}>
      <div className="settle-card" role="dialog" aria-modal="true" aria-label={`第 ${report.quarter} 季結算`}
        data-testid="settlement" onClick={(e) => e.stopPropagation()}>
        <header className="settle-head">
          <h2>第 {report.quarter} 季結算</h2>
          <button ref={closeRef} type="button" className="btn" onClick={onClose}>回到下一季</button>
        </header>
        {literature ? <p className="settle-notice" role="note" data-testid="literature-notice">{LITERATURE_NOTICE}</p> : null}
        <div className="settle-grid">
          <section>
            <h3>成本面（可信的直接顯示）</h3>
            <Rows rows={cost} />
          </section>
          <section>
            <h3>銷售（預估）</h3>
            <Rows rows={market} />
            <Rivals report={report} setup={setup} />
            <h3>損益與現金</h3>
            <Rows rows={result} />
          </section>
        </div>
        {report.notes.length ? (
          <ul className="settle-notes">{report.notes.map((n) => <li key={n}>{n}</li>)}</ul>
        ) : null}
      </div>
    </div>
  );
}

/** Played quarters, oldest first; each reopens its settlement card. */
export function Timeline({ history, objectiveMetric, onOpen }: {
  history: Report[]; objectiveMetric: string | null; onOpen: (r: Report) => void;
}) {
  if (!history.length) return null;
  return (
    <section className="card" aria-label="時間軸">
      <h2>時間軸</h2>
      <ol className="timeline" data-testid="timeline">
        {history.map((r) => (
          <li key={r.quarter}>
            <button type="button" className="timeline-btn" onClick={() => onOpen(r)}>
              <b>Q{r.quarter}</b><span className="muted">結算</span>
            </button>
            {objectiveMetric && r.lines[objectiveMetric] ? (
              <span className="timeline-goal"><span className="hud-label">{lineLabel(objectiveMetric)}</span>
                <Estimate line={r.lines[objectiveMetric]} label={`Q${r.quarter} ${lineLabel(objectiveMetric)}`} /></span>
            ) : null}
          </li>
        ))}
      </ol>
    </section>
  );
}
