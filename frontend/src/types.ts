// Shapes of the documents served by the local API (and exported into the static demo bundle).
// The UI never computes these numbers; it only renders what the Python engine produced.

export type LevelLabel = "verified" | "derived" | "estimated" | "literature" | "placeholder";

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
