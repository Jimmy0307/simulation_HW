import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { DataProvider } from "../data/provider";
import type { GameScript, GameSetupDoc, GameStartConfig, ModulesDoc, PackInfo, PlanDoc, Report } from "../types";
import { Banner } from "../ui/common";
import { Board, type Selection } from "./game/Board";
import { carryOver, emptyDraft, fromPlan, toPlan, validate, type Draft } from "./game/draft";
import { LevelsContext } from "./game/Figure";
import { GameSetup } from "./game/GameSetup";
import { Garage } from "./game/Garage";
import { SourceStrip, StatusBar } from "./game/Hud";
import { Inspector } from "./game/Inspector";
import { ModuleShelf } from "./game/ModuleShelf";
import { SettlementCard, Timeline } from "./game/Settlement";

const PREVIEW_DELAY_MS = 350;
const LEVELS_KEY = "mpsim.game.showLevels";

function packOf(doc: GameSetupDoc): PackInfo {
  return { name: doc.name, provenance: doc.provenance, is_private: doc.is_private, source: doc.source,
    demand_model: doc.demand_model, quarter: doc.quarter };
}

/** Per-viewer convenience only; the page works the same without storage. */
function storedLevels(): boolean {
  try { return window.localStorage.getItem(LEVELS_KEY) === "1"; } catch { return false; }
}
function storeLevels(on: boolean) {
  try { window.localStorage.setItem(LEVELS_KEY, on ? "1" : "0"); } catch { /* storage unavailable */ }
}

/**
 * Game mode: one quarter = one turn, on top of the same engine calls as the analysis screens.
 * The screen only collects inputs and shows engine results; nothing is computed here.
 */
export function GameMode({ provider, onPack }: { provider: DataProvider; onPack?: (pack: PackInfo) => void }) {
  const [setup, setSetup] = useState<GameSetupDoc | null>(null);
  const [script, setScript] = useState<GameScript | null>(null);
  const [catalog, setCatalog] = useState<ModulesDoc | null>(null);
  const [phase, setPhase] = useState<"setup" | "play">("setup");
  const [draft, setDraft] = useState<Draft>(emptyDraft);
  const [preview, setPreview] = useState<Report | null>(null);
  const [selection, setSelection] = useState<Selection | null>(null);
  const [showLevels, setShowLevels] = useState(storedLevels);
  const [settlement, setSettlement] = useState<Report | null>(null);
  const [history, setHistory] = useState<Report[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const readOnly = !provider.canCompute;

  useEffect(() => {
    Promise.all([provider.gameSetup(), provider.gameScript()])
      .then(([doc, demo]) => { setSetup(doc); setScript(demo); })
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)));
    provider.modules().then(setCatalog).catch(() => setCatalog(null)); // the game still runs without the ledger
  }, [provider]);

  const quarter = setup?.state?.quarter ?? 1;
  // The static demo replays its recorded plans verbatim; the live engine gets the plan built from the draft.
  const scripted = readOnly && script ? script.steps[history.length] ?? null : null;
  const scriptDone = readOnly && script !== null && history.length >= script.steps.length;
  const plan: PlanDoc = useMemo(() => scripted?.plan ?? toPlan(draft, quarter), [scripted, draft, quarter]);
  const problem = scripted ? null : validate(draft);

  // Live feedback: every change asks the engine for a calculation (no advance), debounced.
  const planKey = JSON.stringify(plan);
  const latest = useRef(0);
  const runPreview = useCallback(async (): Promise<Report | null> => {
    if (phase !== "play" || problem || scriptDone) return null;
    const ticket = ++latest.current;
    try {
      const report = await provider.gamePreview(plan);
      if (ticket === latest.current) { setPreview(report); setError(null); }
      return report;
    } catch (e) {
      if (ticket === latest.current) setError(e instanceof Error ? e.message : String(e));
      return null;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [provider, planKey, phase, problem, scriptDone]);
  useEffect(() => {
    if (phase !== "play") return undefined;
    const t = setTimeout(() => { void runPreview(); }, PREVIEW_DELAY_MS);
    return () => clearTimeout(t);
  }, [runPreview, phase]);

  const start = async (config: GameStartConfig) => {
    setBusy(true);
    setError(null);
    try {
      const doc = await provider.gameStart(config);
      setSetup(doc);
      onPack?.(packOf(doc));
      const preset = doc.presets.find((p) => p.id === config.preset);
      setDraft(script && readOnly ? fromPlan(script.steps[0].plan, doc, true) : preset ? fromPlan(preset.plan, doc, true) : emptyDraft());
      setHistory([]);
      setPreview(null);
      setSelection(null);
      setPhase("play");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const calculate = async () => {
    setBusy(true);
    setSelection({ kind: "preview" });
    await runPreview();
    setBusy(false);
  };

  const endQuarter = async () => {
    if (problem) { setError(problem); return; }
    setBusy(true);
    setError(null);
    try {
      const report = await provider.gamePlay(plan);
      const doc = await provider.gameSetup();
      const played = [...history, report];
      setHistory(played);
      setSetup(doc);
      setSettlement(report);
      setPreview(null);
      setSelection(null);
      const next = readOnly && script ? script.steps[played.length] : undefined;
      setDraft(next ? fromPlan(next.plan, doc, true) : carryOver(fromPlan(plan, doc, false)));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const resume = async () => {
    if (!setup) return;
    setBusy(true);
    try {
      const game = await provider.game();
      const brands = Object.values(setup.state?.brands ?? {});
      setHistory(game.history);
      setDraft({ ...emptyDraft(), products: brands.map((b) => ({ name: b.name, brand_type: b.brand_type,
        components: b.components, price: 0, production: 0, advertising: 0, locked: true })) });
      setPhase("play");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  if (!setup) return error ? <p className="error">{error}</p> : <p className="muted">載入中…</p>;
  if (phase === "setup") {
    return (
      <>
        {error ? <p className="error" role="alert">{error}</p> : null}
        {provider.canCompute && setup.game ? (
          <Banner kind="info" title="進行中的一局">
            本機引擎裡還有一局（第 {setup.state?.quarter ?? 1} 季，{setup.game.opponents.length} 個對手）。
            <button type="button" className="btn" style={{ marginLeft: 10 }} disabled={busy} onClick={resume}>繼續這一局</button>
            ，或在下方重新開局。
          </Banner>
        ) : null}
        <GameSetup setup={setup} canCompute={provider.canCompute} script={script} busy={busy} onStart={start} />
      </>
    );
  }
  const shown = readOnly && scripted ? fromPlan(scripted.plan, setup, true) : draft;
  const levels = (on: boolean) => { setShowLevels(on); storeLevels(on); };
  return (
    <LevelsContext.Provider value={showLevels}>
      <div className="game">
        <SourceStrip setup={setup} mode={provider.mode} showLevels={showLevels} onShowLevels={levels}>
          <Timeline history={history} onOpen={setSettlement} />
        </SourceStrip>
        {readOnly ? (
          <p className="demo-line">
            Demo 重播：第 {Math.min(history.length + 1, script?.steps.length ?? 0)} / {script?.steps.length} 季的決策來自預錄的一局，只能看不能改。
            啟動本機 API 後就能自己經營。
          </p>
        ) : null}
        {error ? <p className="error" role="alert">{error}</p> : null}
        <div className={`stage${selection ? " with-sheet" : ""}`}>
          <div className="stage-main">
            <Board setup={setup} draft={shown} selection={selection} onSelect={setSelection} />
            <Garage setup={setup} draft={shown} preview={preview} readOnly={readOnly} selection={selection}
              onSelect={setSelection} onChange={setDraft} />
            <ModuleShelf catalog={catalog} draft={shown} setup={setup} selected={selection?.kind === "modules"}
              onOpen={() => setSelection({ kind: "modules" })} />
          </div>
          {selection ? (
            <Inspector setup={setup} draft={shown} preview={preview} readOnly={readOnly} onChange={setDraft}
              selection={selection} onClose={() => setSelection(null)} catalog={catalog} />
          ) : null}
        </div>
        <StatusBar setup={setup} problem={problem}>
          {scriptDone ? <span className="muted">預錄的一局已播完。</span> : null}
          <button type="button" className="btn" disabled={busy || Boolean(problem) || scriptDone} onClick={calculate}>
            試算這一季（不推進）
          </button>
          <button type="button" className="btn primary" disabled={busy || Boolean(problem) || scriptDone} onClick={endQuarter}>
            結束這一季
          </button>
        </StatusBar>
        {settlement ? <SettlementCard report={settlement} setup={setup} onClose={() => setSettlement(null)} /> : null}
      </div>
    </LevelsContext.Provider>
  );
}
