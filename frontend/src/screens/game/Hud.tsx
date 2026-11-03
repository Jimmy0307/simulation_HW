import type { GameSetupDoc, Line } from "../../types";
import { Estimate } from "./Estimate";

/** Top bar of the game screen: which data, which quarter, cash, capacity, outlets, objective, opponents. */
export function Hud({ setup, mode }: { setup: GameSetupDoc; mode: "static" | "api" }) {
  const state = setup.state;
  const cash: Line | null = state
    ? { value: state.cash.value, level: state.cash.level, source: "cash carried from the previous quarter (engine state)",
        uncalibrated: state.cash.uncalibrated }
    : null;
  const outlets = (state?.stores_open.length ?? 0) + (state?.web_centers_open.length ?? 0);
  return (
    <header className="hud" aria-label="遊戲狀態">
      <div className={`hud-source ${setup.is_private ? "private" : "synthetic"}`} data-testid="game-source">
        {setup.is_private ? "PRIVATE 實戰資料" : "SYNTHETIC 虛構資料"}
        <small>{mode === "api" ? "本機引擎即時計算" : "Demo：預錄的一局"}</small>
      </div>
      <div className="hud-item"><span className="hud-label">回合</span><b className="hud-quarter">第 {state?.quarter ?? 1} 季</b></div>
      <div className="hud-item"><span className="hud-label">期初現金</span>{cash ? <Estimate line={cash} label="期初現金" /> : "—"}</div>
      <div className="hud-item"><span className="hud-label">本季產能（{setup.theme.unit}）</span>
        <Estimate line={setup.capacity_units_per_quarter} label="本季產能" /></div>
      <div className="hud-item"><span className="hud-label">營業中的通路</span><b>{outlets}</b></div>
      {setup.game?.objective ? <div className="hud-item hud-goal"><span className="hud-label">目標</span>{setup.game.objective}</div> : null}
      {setup.game ? (
        <div className="hud-item"><span className="hud-label">對手</span>
          <span className="hud-rivals">{setup.game.opponents.map((o) => (
            <span key={o.name} className={`rival-chip d-${o.difficulty}`}>{o.label}</span>))}</span>
        </div>
      ) : null}
    </header>
  );
}
