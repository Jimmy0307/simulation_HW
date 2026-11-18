import { useEffect, useMemo, useState } from "react";
import type { DataProvider } from "./data/provider";
import type { PackInfo } from "./types";
import { Compare } from "./screens/Compare";
import { Decisions } from "./screens/Decisions";
import { Diff } from "./screens/Diff";
import { Factory } from "./screens/Factory";
import { GameMode } from "./screens/GameMode";
import { Levels } from "./screens/Levels";
import { Modules } from "./screens/Modules";
import { Overview } from "./screens/Overview";
import { Scenario } from "./screens/Scenario";
import { Stress } from "./screens/Stress";
import { PackBadge } from "./ui/common";
import { LEVEL_TEXT, LevelMark, UNCALIBRATED_LABEL } from "./ui/Num";

export const ROUTES = [
  { id: "overview", title: "總覽" },
  { id: "decisions", title: "決策編輯" },
  { id: "compare", title: "方案比較" },
  { id: "scenario", title: "情境工作台" },
  { id: "stress", title: "壓力測試" },
  { id: "diff", title: "參數 diff" },
  { id: "levels", title: "來源等級說明" },
  { id: "game", title: "遊戲模式" },
  { id: "modules", title: "模組成熟度" },
  { id: "factory", title: "工廠排程" },
] as const;
type RouteId = (typeof ROUTES)[number]["id"];

const routeFromHash = (): RouteId => {
  const id = window.location.hash.replace(/^#\/?/, "");
  return (ROUTES.find((r) => r.id === id)?.id ?? "overview") as RouteId;
};

function readTheme(): string | null {
  try {
    return window.localStorage.getItem("mpsim-theme");
  } catch {
    return null;
  }
}

export function App({ provider }: { provider: DataProvider }) {
  const [route, setRoute] = useState<RouteId>(routeFromHash);
  const [pack, setPack] = useState<PackInfo | null>(null);
  const [epoch, setEpoch] = useState(0); // bumps after pack switches / plays so screens reload
  const [theme, setTheme] = useState<string | null>(readTheme);
  const [packError, setPackError] = useState<string | null>(null);

  useEffect(() => {
    const onHash = () => setRoute(routeFromHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  useEffect(() => {
    provider.pack().then(setPack).catch((e: unknown) => setPackError(e instanceof Error ? e.message : String(e)));
  }, [provider, epoch]);
  useEffect(() => {
    if (theme) document.documentElement.dataset.theme = theme; else delete document.documentElement.dataset.theme;
    try {
      if (theme) window.localStorage.setItem("mpsim-theme", theme); else window.localStorage.removeItem("mpsim-theme");
    } catch {
      /* storage unavailable: theme still applies for this visit */
    }
  }, [theme]);

  const switchPack = async (source: "synthetic" | "private") => {
    setPackError(null);
    try {
      setPack(await provider.switchPack(source));
      setEpoch((e) => e + 1);
    } catch (e) {
      setPackError(e instanceof Error ? e.message : String(e));
    }
  };

  const screen = useMemo(() => {
    const key = `${route}-${epoch}`;
    switch (route) {
      case "decisions": return <Decisions key={key} provider={provider} onPlayed={() => setEpoch((e) => e + 1)} />;
      case "compare": return <Compare key={key} provider={provider} />;
      case "factory": return <Factory key={key} provider={provider} />;
      case "scenario": return <Scenario key={key} provider={provider} />;
      case "stress": return <Stress key={key} provider={provider} />;
      case "diff": return <Diff key={key} provider={provider} />;
      case "levels": return <Levels key={key} provider={provider} />;
      case "modules": return <Modules key={key} provider={provider} />;
      case "game": return <GameMode key={key} provider={provider} onPack={setPack} />;
      default: return <Overview key={key} provider={provider} />;
    }
  }, [route, epoch, provider]);

  const title = ROUTES.find((r) => r.id === route)?.title ?? "";
  return (
    <div className="shell">
      <aside className="side">
        <div className="brand">mpsim 模擬器<small>本機規劃引擎 · 每個數字都標來源等級</small></div>
        <nav className="nav" aria-label="主選單">
          {ROUTES.map((r, i) => (
            <a key={r.id} href={`#/${r.id}`} aria-current={route === r.id ? "page" : undefined}>
              <span className="num">{i + 1}</span>{r.title}
            </a>
          ))}
        </nav>
        <div style={{ marginTop: 22 }} className="legend" aria-label="來源等級圖例">
          {(["verified", "derived", "estimated", "literature", "placeholder", "heuristic"] as const).map((lv) => (
            <span key={lv}><LevelMark level={lv} />{LEVEL_TEXT[lv].name}</span>
          ))}
        </div>
        <p className="note" style={{ marginTop: 10 }}>斜紋標記「{UNCALIBRATED_LABEL}」= 上游含 literature 或 placeholder。</p>
        <div className="row" style={{ marginTop: 14 }}>
          <label className="field">主題
            <select value={theme ?? "auto"} onChange={(e) => setTheme(e.target.value === "auto" ? null : e.target.value)}>
              <option value="auto">跟隨系統</option><option value="light">淺色</option><option value="dark">深色</option>
            </select>
          </label>
        </div>
      </aside>
      <main className="main">
        <div className="topbar">
          <h1>{title}</h1>
          <div className="badges">
            <PackBadge pack={pack} mode={provider.mode} />
            {provider.canCompute ? (
              <>
                <button className="btn" onClick={() => switchPack("synthetic")}>載入 synthetic</button>
                <button className="btn" onClick={() => switchPack("private")}>載入 private</button>
              </>
            ) : null}
          </div>
        </div>
        {packError ? <p className="error">{packError}</p> : null}
        {screen}
      </main>
    </div>
  );
}
