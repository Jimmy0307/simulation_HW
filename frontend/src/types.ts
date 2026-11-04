// Shapes of the documents served by the local API (and exported into the static demo bundle).
// The UI never computes these numbers; it only renders what the Python engine produced.

export type LevelLabel = "verified" | "derived" | "estimated" | "literature" | "placeholder" | "heuristic";

export interface ChainStep {
  metric: string;
  level: LevelLabel;
  formula: string;
  evidence?: string;
  note?: string;
}

export interface Line {
  value: number;
  level: LevelLabel;
  source: string;
  mark?: string;
  uncalibrated?: boolean;
  chain?: ChainStep[];
}

export type Lines = Record<string, Line>;

export interface Report {
  quarter: number;
  plan: string;
  notes: string[];
  lines: Lines;
}

export interface PackInfo {
  name: string;
  provenance: string;
  is_private: boolean;
  source: "synthetic" | "private";
  demand_model: string;
  quarter: number | null;
}

export interface CashState {
  value: number;
  level: LevelLabel;
  uncalibrated: boolean;
}

export interface CompanyState {
  quarter: number;
  cash: CashState;
  cd: number;
  fixed_capacity_units: number;
  stores_open: string[];
  web_centers_open: string[];
  brands: Record<string, { name: string; brand_type: string; components: string[]; segment_id: string | null }>;
  inventory: Record<string, number>;
  stock_total: number;
  shares_total: number;
  ad_stock?: Record<string, number>;
  /** Business-module state carried by the engine (e.g. the sales force still employed). */
  module_state?: Record<string, Record<string, number>>;
}

export interface GameDoc extends PackInfo {
  state: CompanyState | null;
  history: Report[];
}

export interface BrandPlan {
  name: string;
  brand_type: string;
  price: number;
  production: number;
  advertising?: number;
  components?: string[];
  segment?: string;
}

export interface PlanDoc {
  name: string;
  capacity_increase?: number;
  cd?: { deposit?: number; withdraw?: number };
  open_stores?: string[];
  open_web_centers?: string[];
  stock_issue?: { shares: number; price: number }[];
  brands?: BrandPlan[];
  /** Business-module decisions keyed like the ledger's `module` field (marketing.media_mix, sales_force). */
  modules?: ModuleDecisions;
}

export type ModuleDecisions = Record<string, Record<string, unknown>>;

export type Maturity = "verified" | "literature" | "heuristic" | "not-modeled";

export interface ModuleField {
  name: string;
  label: string;
  part: string;
  kind: "number" | "brand_number" | "choice" | "brand_choice" | "flag";
  low: number;
  high: number;
  step: number;
  default: number | string | boolean;
  unit: string;
  options: [string, string][];
}

export interface ModuleUi {
  toggle?: string;
  literature?: string;
  practice?: string;
  results?: [string, string, ("number" | "percent")?][];
}

/** One row of data/modeling_ledger.json, plus what the engine can decide now. Structure only, no values. */
export interface LedgerRow {
  key: string;
  module: string | null;
  area: string;
  name: string;
  kind: "behaviour" | "accounting" | "information" | "qualitative" | "scenario";
  real_status: "measured" | "inferred" | "unknown";
  real_note: string;
  screens: string[];
  maturity: Maturity;
  ours: string;
  next_step: string;
  capture: string;
  sources: string[];
  decidable: boolean;
  implementation: string | null;
  decisions: string[];
  coefficients: Record<string, unknown> | null;
  /** True on the row whose maturity group shows the module's levers (its main part). */
  primary?: boolean;
  /** Levers of the module (generic editor); each carries the ledger row (part) whose badge it shows. */
  fields?: ModuleField[];
  /** Texts and result lines for the generic editor; placeholders {brand}, {segment}, {rival} expand on line keys. */
  ui?: ModuleUi | null;
  /** A model option that can be switched off (sends {stop: true} while it carries state). */
  stoppable?: boolean;
  /** Published ranges of the literature coefficients (checked by the engine). */
  ranges: Record<string, [number, number]> | null;
}

export interface ModulesDoc {
  title: string;
  rules: string[];
  maturity_legend: Record<Maturity, string>;
  kind_legend: Record<string, string>;
  areas: { id: string; name: string }[];
  sources: Record<string, string>;
  modules: LedgerRow[];
  counts: Record<Maturity, number>;
  /** Counts of earlier rounds, so progress is visible. */
  history: { label: string; date: string; counts: Record<Maturity, number>; total: number }[];
  is_private: boolean;
}

export interface PlansDoc extends PackInfo {
  presets: { id: string; plan: PlanDoc }[];
  brand_types: string[];
  stores: string[];
  web_centers: string[];
  capacity_options: number[];
  previews?: Record<string, Report>;
}

export interface CompareDoc extends PackInfo {
  quarter: number;
  reports: Report[];
}

export interface EventType {
  type: string;
  targets: string[];
  effect: string;
}

export interface ScenarioSpecDoc {
  name: string;
  description?: string;
  base_params: string;
  horizon?: number;
  start_quarter?: number;
  seed?: number;
  overrides?: Record<string, unknown>[];
  events?: Record<string, unknown>[];
  competitors?: { name: string; strategy: string; params?: Record<string, unknown> }[];
  our_policy?: Record<string, unknown>;
}

export interface ScenarioQuarter {
  quarter: number;
  plan: string;
  events: string[];
  overrides: string[];
  lines: Lines;
  notes: string[];
}

export interface ScenarioResult {
  name: string;
  fingerprint: string;
  seed: number;
  summary: Record<string, unknown> & { weakest_level?: Record<string, LevelLabel> };
  quarters: ScenarioQuarter[];
}

export interface ScenarioRun {
  is_private: boolean;
  pack: string;
  result: ScenarioResult;
}

export interface SweepRow {
  id: string;
  fingerprint: string;
  assignment: Record<string, unknown>;
  objective: number | null;
  summary: Record<string, unknown>;
}

export interface Sensitivity {
  variable: string;
  kind: string;
  mean_objective_by_value: Record<string, number>;
  main_effect_range: number | null;
  local_slope?: number | null;
}

export interface SweepResult {
  name: string;
  objective: string;
  mode: string;
  demand_level: LevelLabel;
  caveat: string;
  is_private: boolean;
  rows: SweepRow[];
  worst: SweepRow[];
  sensitivity: Sensitivity[];
}

export interface DiffChange {
  path: string;
  kind: string;
  module: string;
  module_level: LevelLabel;
  relative: number | null;
  needs_reverification: boolean;
  old?: unknown;
  new?: unknown;
}

export interface DiffDoc {
  is_private: boolean;
  values_included: boolean;
  old: string;
  new: string;
  red_flags: string[];
  changes: DiffChange[];
}

export interface LevelsDoc {
  order: LevelLabel[];
  levels: { label: LevelLabel; mark: string; rank: number; uncalibrated: boolean; meaning: string }[];
  metrics: { metric: string; level: LevelLabel; formula: string; evidence: string; note: string; inputs: string[] }[];
}

// --- game mode (GET /api/game-mode/setup, POST /api/game-mode/start; demo: public/demo/gamemode.json) -------------

export interface GameStateView {
  state: CompanyState | null;
  capacity_units_per_quarter: Line;
}

export interface GameOpponent {
  name: string;
  difficulty: string;
  label: string;
  strategy?: string;
  params?: Record<string, unknown>;
}

export interface GameMeta {
  opponents: GameOpponent[];
  replay: boolean;
  objective: string;
  preset?: string | null;
}

export interface GameCity {
  key: string;
  name: string;
  store: { open: boolean; setup_cost: Line; lease_cost: Line } | null;
  segments: { id: string; name: string; size_12m: Line; wtp: Line }[];
}

export interface GameRegion {
  id: string;
  web_center: { key: string; name: string; open: boolean; setup_cost: Line; lease_cost: Line } | null;
  cities: GameCity[];
}

export interface GameSetupDoc extends PackInfo, GameStateView {
  theme: { product: string; unit: string; icon: string };
  max_opponents: number;
  difficulties: { id: string; label: string; strategy: string; params: Record<string, unknown>; description: string }[];
  replay: { available: boolean; reason: string; quarters?: number[] };
  objectives: { id: string; text: string; metric: string }[];
  game: GameMeta | null;
  brand_types: { code: string; name: string; segment_id: string | null; segment_name: string; components: string[];
    default_components: string[] }[];
  component_groups: { id: string; name: string; required: boolean; multi: boolean }[];
  components: { id: string; group: string; name: string; available_quarter: number | null }[];
  segments: { id: string; name: string; needs: string[] }[];
  regions: GameRegion[];
  capacity_options: { units: number; machines: number | null; cost: Line }[];
  presets: { id: string; plan: PlanDoc }[];
}

export interface GameStartConfig {
  source: "synthetic" | "private";
  opponents: { difficulty: string }[];
  replay?: boolean;
  objective: string;
  preset?: string | null;
}

export interface GameScriptStep {
  quarter: number;
  plan: PlanDoc;
  before: GameStateView;
  preview: Report;
  report: Report;
}

export interface GameScript {
  config: { source: "synthetic"; objective: string; opponents: { difficulty: string }[] };
  start: GameSetupDoc;
  steps: GameScriptStep[];
  final: GameStateView;
}
