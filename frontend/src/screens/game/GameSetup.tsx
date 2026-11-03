import { useEffect, useRef, useState } from "react";
import type { GameScript, GameSetupDoc, GameStartConfig } from "../../types";
import { Banner } from "../../ui/common";
import { ProductIcon } from "./icons";

interface Props {
  setup: GameSetupDoc;
  canCompute: boolean;
  script: GameScript | null;
  busy: boolean;
  onStart: (config: GameStartConfig) => void;
}

/** Opening screen: data source, opponents (count + difficulty), starting plan and the one-line objective. */
export function GameSetup({ setup, canCompute, script, busy, onStart }: Props) {
  const fixed = !canCompute && script !== null; // the static demo replays one pre-recorded configuration
  const [source, setSource] = useState<"synthetic" | "private">(setup.is_private ? "private" : "synthetic");
  const [difficulties, setDifficulties] = useState<string[]>(
    script ? script.config.opponents.map((o) => o.difficulty) : ["normal", "normal", "normal"]);
  const [replay, setReplay] = useState(false);
  const [preset, setPreset] = useState<string>("");
  const [objective, setObjective] = useState<string>(script?.config.objective ?? setup.objectives[0]?.text ?? "");
  const startRef = useRef<HTMLButtonElement>(null);
  useEffect(() => startRef.current?.focus(), []); // initial focus on the main action

  const setCount = (count: number) =>
    setDifficulties((d) => Array.from({ length: count }, (_, i) => d[i] ?? "normal"));
  const start = () => onStart({
    source, replay, objective, preset: preset || null,
    opponents: replay ? [] : difficulties.map((difficulty) => ({ difficulty })),
  });

  return (
    <div className="game-setup">
      <section className="card setup-hero">
        <div className="setup-icon"><ProductIcon icon={setup.theme.icon} size={72} /></div>
        <div>
          <h2>開一局：{setup.theme.product}經營</h2>
          <p className="muted">一季 = 一回合。每回合做{setup.theme.product}、鋪貨、定價，先「試算」再「結束這一季」。
            所有數字都由本機引擎計算；未校準的數字會以「？ 預估」顯示。</p>
        </div>
      </section>
      {fixed ? (
        <Banner kind="info" title="Demo 模式">
          這是預先算好的一局（synthetic 虛構資料、{script?.config.opponents.length} 個對手），只能逐季重播。
          要自由設定對手與決策，請啟動本機 API（tools\bat\start-ui.bat）。
        </Banner>
      ) : null}
      <div className="grid cols-2">
        <section className="card">
          <h2>1. 資料源</h2>
          <div className="choice-row" role="radiogroup" aria-label="資料源">
            {(["synthetic", "private"] as const).map((s) => (
              <label key={s} className={`choice${source === s ? " on" : ""}${!canCompute && s === "private" ? " off" : ""}`}>
                <input type="radio" name="source" value={s} checked={source === s} disabled={fixed || (!canCompute && s === "private")}
                  onChange={() => setSource(s)} />
                {s === "synthetic" ? "synthetic（虛構練習）" : "private（實戰：真實參數）"}
              </label>
            ))}
          </div>
          {!canCompute ? <p className="note">private 只能在本機 API 模式使用。</p> : null}
          <h2 style={{ marginTop: 16 }}>2. 對手</h2>
          <label className="field">對手數量（1–{setup.max_opponents}）
            <input type="range" min={1} max={setup.max_opponents} value={difficulties.length} disabled={fixed || replay}
              aria-label="對手數量" onChange={(e) => setCount(Number(e.target.value))} />
          </label>
          <p className="count-readout" data-testid="opponent-count">{replay ? "真實對手" : `${difficulties.length} 個對手`}</p>
          <div className="opponents">
            {difficulties.map((d, i) => (
              <label key={i} className="field">對手 {i + 1}
                <select value={d} disabled={fixed || replay} aria-label={`對手 ${i + 1} 難度`}
                  onChange={(e) => setDifficulties((all) => all.map((x, j) => (j === i ? e.target.value : x)))}>
                  {setup.difficulties.map((opt) => <option key={opt.id} value={opt.id}>{opt.label}</option>)}
                </select>
              </label>
            ))}
          </div>
          <details className="note">
            <summary>難度代表什麼？（對應現有的 bot 參數）</summary>
            <ul>{setup.difficulties.map((d) => <li key={d.id}><b>{d.label}</b>：{d.description}</li>)}</ul>
          </details>
          <label className={`choice${setup.replay.available ? "" : " off"}`} style={{ marginTop: 10 }}>
            <input type="checkbox" checked={replay} disabled={fixed || !setup.replay.available}
              onChange={(e) => setReplay(e.target.checked)} />
            用真實對手（replay）
          </label>
          {!setup.replay.available ? <p className="note" data-testid="replay-reason">尚不可用：{setup.replay.reason}</p> : null}
        </section>
        <section className="card">
          <h2>3. 起始方案</h2>
          <label className="field">從預設方案帶入產品與鋪貨
            <select value={preset} disabled={fixed} onChange={(e) => setPreset(e.target.value)}>
              <option value="">從零開始</option>
              {setup.presets.map((p) => <option key={p.id} value={p.id}>{p.id}</option>)}
            </select>
          </label>
          <h2 style={{ marginTop: 16 }}>4. 目標（一句話）</h2>
          <div className="choice-row">
            {setup.objectives.map((o) => (
              <button key={o.id} type="button" className={`btn${objective === o.text ? " primary" : ""}`} disabled={fixed}
                onClick={() => setObjective(o.text)}>{o.text}</button>
            ))}
          </div>
          <label className="field" style={{ marginTop: 8 }}>或自己寫
            <input value={objective} disabled={fixed} onChange={(e) => setObjective(e.target.value)} />
          </label>
          <div className="row" style={{ marginTop: 18 }}>
            <button ref={startRef} className="btn primary big" disabled={busy || (!replay && difficulties.length < 1)}
              onClick={start}>開始第一季</button>
          </div>
        </section>
      </div>
    </div>
  );
}
