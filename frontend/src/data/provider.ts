import type {
  CompareDoc, DiffDoc, EventType, FactoryRequest, FactoryResult, FactorySetup, GameDoc, GameScript, GameSetupDoc, GameStartConfig, LevelsDoc, ModulesDoc, PackInfo, PlanDoc,
  PlansDoc, Report, ScenarioRun, ScenarioSpecDoc, SweepResult,
} from "../types";
import { ApiProvider } from "./apiProvider";
import { StaticProvider } from "./staticProvider";

export type Source = "static" | "api";

/** Everything the screens need. Two implementations: precomputed synthetic JSON, or the live local API. */
export interface DataProvider {
  readonly mode: Source;
  /** false = read-only demo: only precomputed results can be shown. */
  readonly canCompute: boolean;
  pack(): Promise<PackInfo>;
  switchPack(source: "synthetic" | "private", path?: string): Promise<PackInfo>;
  levels(): Promise<LevelsDoc>;
  /** The modeling ledger: every business module with its maturity (public structure, no values). */
  modules(): Promise<ModulesDoc>;
  game(): Promise<GameDoc>;
  newGame(): Promise<GameDoc>;
  plans(): Promise<PlansDoc>;
  preview(plan: PlanDoc, presetId?: string): Promise<Report>;
  play(plan: PlanDoc): Promise<Report>;
  compare(plans: PlanDoc[], presetIds?: string[]): Promise<CompareDoc>;
  scenarioTemplates(): Promise<{ id: string; spec: ScenarioSpecDoc }[]>;
  events(): Promise<EventType[]>;
  runScenario(spec: ScenarioSpecDoc, templateId?: string): Promise<ScenarioRun>;
  sweepFiles(): Promise<{ id: string; sweep: Record<string, unknown> }[]>;
  runSweep(sweep: Record<string, unknown>, id?: string): Promise<SweepResult>;
  packs(): Promise<{ id: string; path?: string }[]>;
  diff(oldId: string, newId: string): Promise<DiffDoc>;
  // game mode: one quarter = one turn. Calculate/play go to the same engine calls as the decision editor.
  gameSetup(): Promise<GameSetupDoc>;
  gameStart(config: GameStartConfig): Promise<GameSetupDoc>;
  gamePreview(plan: PlanDoc): Promise<Report>;
  gamePlay(plan: PlanDoc): Promise<Report>;
  /** The pre-recorded demo game (static provider only); null when the engine is live. */
  gameScript(): Promise<GameScript | null>;
  // production scheduler: the team's orders -> operating capacity x overtime x demand outcome
  factorySetup(): Promise<FactorySetup>;
  factoryRun(request: FactoryRequest): Promise<FactoryResult>;
}

export { ReadOnlyError } from "./errors";

/** Order: ?source= in the URL, then VITE_DATA_SOURCE, then the mode default (static; `vite --mode live` = api). */
export function chooseSource(search: string, env: Record<string, unknown>, buildDefault: string): Source {
  const fromUrl = new URLSearchParams(search).get("source");
  const value = fromUrl ?? (typeof env.VITE_DATA_SOURCE === "string" ? env.VITE_DATA_SOURCE : undefined) ?? buildDefault;
  return value === "api" ? "api" : "static";
}

export function createProvider(source?: Source): DataProvider {
  const chosen = source ?? chooseSource(
    typeof window === "undefined" ? "" : window.location.search,
    import.meta.env as unknown as Record<string, unknown>,
    import.meta.env.MODE === "live" ? "api" : "static",
  );
  if (chosen === "api") {
    const base = (import.meta.env.VITE_API_URL as string | undefined) ?? "http://127.0.0.1:8765";
    return new ApiProvider(base);
  }
  return new StaticProvider(`${import.meta.env.BASE_URL}demo/`);
}
