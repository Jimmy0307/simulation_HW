import type {
  CompareDoc, DiffDoc, EventType, GameDoc, GameScript, GameSetupDoc, GameStartConfig, LevelsDoc, PackInfo, PlanDoc,
  PlansDoc, Report, ScenarioRun, ScenarioSpecDoc, SweepResult,
} from "../types";
import type { DataProvider } from "./provider";

type Fetch = typeof fetch;

/** Talks to the local FastAPI (python -m marketplace_sim.api). All numbers come from the Python engine. */
export class ApiProvider implements DataProvider {
  readonly mode = "api" as const;
  readonly canCompute = true;
  private packPaths = new Map<string, string>();

  constructor(private readonly base: string, private readonly fetcher: Fetch = (...a) => fetch(...a)) {}

  private async call<T>(path: string, body?: unknown): Promise<T> {
    const response = await this.fetcher(`${this.base}/api${path}`, body === undefined ? undefined : {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    });
    if (!response.ok) {
      let detail = `${response.status}`;
      try {
        detail = ((await response.json()) as { detail?: string }).detail ?? detail;
      } catch {
        /* keep status */
      }
      throw new Error(`API 錯誤：${detail}`);
    }
    return (await response.json()) as T;
  }

  pack(): Promise<PackInfo> {
    return this.call<PackInfo>("/pack");
  }

  switchPack(source: "synthetic" | "private", path?: string): Promise<PackInfo> {
    return this.call<PackInfo>("/pack", { source, path });
  }

  levels(): Promise<LevelsDoc> {
    return this.call<LevelsDoc>("/levels");
  }

  async game(): Promise<GameDoc> {
    const doc = await this.call<GameDoc>("/game");
    return doc.state ? doc : this.newGame();
  }

  newGame(): Promise<GameDoc> {
    return this.call<GameDoc>("/game/new", {});
  }

  plans(): Promise<PlansDoc> {
    return this.call<PlansDoc>("/plans");
  }

  async preview(plan: PlanDoc): Promise<Report> {
    return (await this.call<{ report: Report }>("/game/preview", plan)).report;
  }

  async play(plan: PlanDoc): Promise<Report> {
    return (await this.call<{ report: Report }>("/game/play", plan)).report;
  }

  compare(plans: PlanDoc[]): Promise<CompareDoc> {
    return this.call<CompareDoc>("/compare", { plans });
  }

  async scenarioTemplates(): Promise<{ id: string; spec: ScenarioSpecDoc }[]> {
    return (await this.call<{ templates: { id: string; spec: ScenarioSpecDoc }[] }>("/scenarios")).templates;
  }

  async events(): Promise<EventType[]> {
    return (await this.call<{ types: EventType[] }>("/events")).types;
  }

  runScenario(spec: ScenarioSpecDoc): Promise<ScenarioRun> {
    return this.call<ScenarioRun>("/scenario/run", spec);
  }

  async sweepFiles(): Promise<{ id: string; sweep: Record<string, unknown> }[]> {
    return (await this.call<{ sweeps: { id: string; sweep: Record<string, unknown> }[] }>("/sweeps")).sweeps;
  }

  runSweep(sweep: Record<string, unknown>): Promise<SweepResult> {
    return this.call<SweepResult>("/sweep/run", sweep);
  }

  async packs(): Promise<{ id: string; path?: string }[]> {
    const packs = (await this.call<{ packs: { id: string; path: string }[] }>("/packs")).packs;
    packs.forEach((p) => this.packPaths.set(p.id, p.path));
    return packs;
  }

  diff(oldId: string, newId: string): Promise<DiffDoc> {
    return this.call<DiffDoc>("/diff", { old: this.packPaths.get(oldId) ?? oldId, new: this.packPaths.get(newId) ?? newId });
  }

  gameSetup(): Promise<GameSetupDoc> {
    return this.call<GameSetupDoc>("/game-mode/setup");
  }

  gameStart(config: GameStartConfig): Promise<GameSetupDoc> {
    return this.call<GameSetupDoc>("/game-mode/start", config);
  }

  async gamePreview(plan: PlanDoc): Promise<Report> {
    return (await this.call<{ report: Report }>("/game/preview", plan)).report;
  }

  async gamePlay(plan: PlanDoc): Promise<Report> {
    return (await this.call<{ report: Report }>("/game/play", plan)).report;
  }

  async gameScript(): Promise<GameScript | null> {
    return null;
  }
}
