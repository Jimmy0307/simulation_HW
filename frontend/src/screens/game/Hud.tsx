import type { ReactNode } from "react";
import type { GameSetupDoc, Line } from "../../types";
import { Figure } from "./Figure";

/** Top strip: which data this game runs on (always visible), the opponents, report cards, and the levels switch. */
export function SourceStrip({ setup, mode, showLevels, onShowLevels, children }: {
  setup: GameSetupDoc; mode: "static" | "api"; showLevels: boolean; onShowLevels: (on: boolean) => void; children?: ReactNode;
}) {
  return (
    <header className="strip" aria-label="資料源與對手">
      <span className={`source-tag ${setup.is_private ? "private" : "synthetic"}`} data-testid="game-source">
        {setup.is_private ? "PRIVATE 實戰資料" : "SYNTHETIC 虛構資料"}
        <small>{mode === "api" ? "本機引擎即時計算" : "Demo：預錄的一局"}</small>
      </span>
      {setup.game ? (
        <span className="rivals" aria-label={`${setup.game.opponents.length} 個對手`}>
          {setup.game.opponents.map((o, i) => (
            <span key={o.name} className={`rival-dot d-${o.difficulty}`} title={`對手 ${i + 1}：${o.label}`}>{i + 1}</span>
          ))}
          <span className="muted">{setup.game.opponents.length} 個對手</span>
        </span>
      ) : null}
      {children}
      <button type="button" role="switch" aria-checked={showLevels} className="levels-switch" data-testid="levels-switch"
        onClick={() => onShowLevels(!showLevels)}>
        <span className="switch-knob" aria-hidden="true" />顯示所有來源等級
      </button>
    </header>
  );
}

/** Bottom bar: quarter, cash, capacity, objective, and the two turn actions. Everything else lives in panels. */
export function StatusBar({ setup, problem, children }: { setup: GameSetupDoc; problem: string | null; children: ReactNode }) {
  const state = setup.state;
  const cash: Line | null = state
    ? { value: state.cash.value, level: state.cash.level, source: "cash carried from the previous quarter (engine state)",
        uncalibrated: state.cash.uncalibrated }
    : null;
  return (
    <div className="status-bar" role="toolbar" aria-label="回合狀態與動作">
      <div className="status-q" aria-label={`第 ${state?.quarter ?? 1} 季`}><small>第</small><b>{state?.quarter ?? 1}</b><small>季</small></div>
      <div className="status-item"><span>現金</span>{cash ? <Figure line={cash} label="期初現金" /> : "—"}</div>
      <div className="status-item"><span>產能</span><Figure line={setup.capacity_units_per_quarter} label="本季產能" unit={` ${setup.theme.unit}`} /></div>
      {setup.game?.objective ? <div className="status-item goal"><span>目標</span><b className="goal-text">{setup.game.objective}</b></div> : null}
      <div className="status-actions">
        {problem ? <span className="status-problem" role="status">{problem}</span> : null}
        {children}
      </div>
    </div>
  );
}
