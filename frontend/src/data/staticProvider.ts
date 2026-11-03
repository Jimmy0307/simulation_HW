import type {
  CompareDoc, DiffDoc, EventType, GameDoc, LevelsDoc, PackInfo, PlanDoc, PlansDoc, Report, ScenarioResult, ScenarioRun,
  ScenarioSpecDoc, SweepResult,
} from "../types";
import { ReadOnlyError } from "./errors";
import type { DataProvider } from "./provider";

type Fetcher = (url: string) => Promise<unknown>;

const defaultFetch: Fetcher = async (url) => {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`無法讀取 demo 資料 ${url}（${response.status}）`);
  return response.json();
};

const same = (a: unknown, b: unknown): boolean => JSON.stringify(a) === JSON.stringify(b);

/** Reads the synthetic bundle exported by `python -m marketplace_sim.api.export`. Never computes anything. */
export class StaticProvider implements DataProvider {
  readonly mode = "static" as const;
  readonly canCompute = false;
  private cache = new Map<string, Promise<unknown>>();

  constructor(private readonly base: string, private readonly fetcher: Fetcher = defaultFetch) {}

  private load<T>(name: string): Promise<T> {
    if (!this.cache.has(name)) this.cache.set(name, this.fetcher(`${this.base}${name}.json`));
    return this.cache.get(name) as Promise<T>;
  }

  pack(): Promise<PackInfo> {
    return this.load<PackInfo>("pack");
  }

  async switchPack(_source?: "synthetic" | "private", _path?: string): Promise<PackInfo> {
    throw new ReadOnlyError("切換參數包");
  }

  levels(): Promise<LevelsDoc> {
    return this.load<LevelsDoc>("levels");
  }

  game(): Promise<GameDoc> {
    return this.load<GameDoc>("game");
  }

  async newGame(): Promise<GameDoc> {
    throw new ReadOnlyError("開新局");
  }

  plans(): Promise<PlansDoc> {
    return this.load<PlansDoc>("plans");
  }

  async preview(plan: PlanDoc, presetId?: string): Promise<Report> {
    const doc = await this.plans();
    const preset = doc.presets.find((p) => p.id === presetId);
    if (!preset || !same(preset.plan, plan) || !doc.previews?.[preset.id]) throw new ReadOnlyError("試算修改過的方案");
    return doc.previews[preset.id];
  }

  async play(_plan: PlanDoc): Promise<Report> {
    throw new ReadOnlyError("送出決策並推進一季");
  }

  async compare(plans: PlanDoc[], presetIds?: string[]): Promise<CompareDoc> {
    const [doc, compared] = await Promise.all([this.plans(), this.load<CompareDoc>("compare")]);
    const ids = presetIds ?? [];
    const reports = ids.map((id, i) => {
      const index = doc.presets.findIndex((p) => p.id === id);
      if (index < 0 || !same(doc.presets[index].plan, plans[i])) throw new ReadOnlyError("比較修改過的方案");
      return compared.reports[index];
    });
    return { ...compared, reports };
  }

  async scenarioTemplates(): Promise<{ id: string; spec: ScenarioSpecDoc }[]> {
    return (await this.load<{ templates: { id: string; spec: ScenarioSpecDoc }[] }>("scenarios")).templates;
  }

  async events(): Promise<EventType[]> {
    return (await this.load<{ types: EventType[] }>("events")).types;
  }

  async runScenario(spec: ScenarioSpecDoc, templateId?: string): Promise<ScenarioRun> {
    const doc = await this.load<{ templates: { id: string; spec: ScenarioSpecDoc }[]; results: Record<string, ScenarioResult> }>(
      "scenarios");
    const template = doc.templates.find((t) => t.id === templateId);
    if (!template || !same(template.spec, spec)) throw new ReadOnlyError("執行修改過的情境");
    return { is_private: false, pack: "synthetic", result: doc.results[template.id] };
  }

  async sweepFiles(): Promise<{ id: string; sweep: Record<string, unknown> }[]> {
    return (await this.load<{ sweeps: { id: string; sweep: Record<string, unknown> }[] }>("sweeps")).sweeps;
  }

  async runSweep(sweep: Record<string, unknown>, id?: string): Promise<SweepResult> {
    const doc = await this.load<{ sweeps: { id: string; sweep: Record<string, unknown> }[];
      results: Record<string, SweepResult> }>("sweeps");
    const file = doc.sweeps.find((s) => s.id === id);
    if (!file || !same(file.sweep, sweep)) throw new ReadOnlyError("執行修改過的壓力測試");
    return doc.results[file.id];
  }

  async packs(): Promise<{ id: string; path?: string }[]> {
    return (await this.load<{ packs: { id: string }[] }>("diff")).packs;
  }

  async diff(oldId: string, newId: string): Promise<DiffDoc> {
    if (oldId !== "synthetic" || newId !== "synthetic-v2") throw new ReadOnlyError("比較其他參數包");
    return (await this.load<{ result: DiffDoc }>("diff")).result;
  }
}
