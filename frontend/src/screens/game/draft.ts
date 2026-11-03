// The turn being edited, and its conversion to the engine's plan format. No numbers are computed here: the draft only
// holds the player's inputs; every result comes back from the engine (preview / play).
import type { GameSetupDoc, PlanDoc } from "../../types";

export interface ProductDraft {
  name: string;
  brand_type: string;
  components: string[];
  price: number;
  production: number;
  advertising: number;
  /** Already designed in an earlier quarter: the engine keeps its type and components, so they are locked here. */
  locked: boolean;
}

export interface Draft {
  products: ProductDraft[];
  open_stores: string[];
  open_web_centers: string[];
  capacity_increase: number;
  /** One-off finance decisions carried from the starting plan (first quarter only). */
  finance: Pick<PlanDoc, "cd" | "stock_issue">;
}

export const emptyDraft = (): Draft => ({ products: [], open_stores: [], open_web_centers: [], capacity_increase: 0, finance: {} });

export function designed(setup: GameSetupDoc): Record<string, { brand_type: string; components: string[] }> {
  return setup.state?.brands ?? {};
}

/** Draft from a plan (a preset, a demo script step, or the previous quarter). */
export function fromPlan(plan: PlanDoc, setup: GameSetupDoc, keepOneOff: boolean): Draft {
  const done = designed(setup);
  return {
    products: (plan.brands ?? []).map((b) => {
      const type = setup.brand_types.find((t) => t.code === b.brand_type);
      const existing = done[b.name];
      return {
        name: b.name, brand_type: existing?.brand_type ?? b.brand_type,
        components: existing?.components ?? b.components ?? type?.default_components ?? [],
        price: b.price, production: b.production, advertising: b.advertising ?? 0, locked: Boolean(existing),
      };
    }),
    open_stores: keepOneOff ? [...(plan.open_stores ?? [])] : [],
    open_web_centers: keepOneOff ? [...(plan.open_web_centers ?? [])] : [],
    capacity_increase: keepOneOff ? plan.capacity_increase ?? 0 : 0,
    finance: keepOneOff ? { ...(plan.cd ? { cd: plan.cd } : {}), ...(plan.stock_issue ? { stock_issue: plan.stock_issue } : {}) } : {},
  };
}

/** The engine plan for this turn (same format as the decision editor and the plan files). */
export function toPlan(draft: Draft, quarter: number): PlanDoc {
  return {
    name: `Q${quarter}`,
    ...(draft.capacity_increase ? { capacity_increase: draft.capacity_increase } : {}),
    ...(draft.open_stores.length ? { open_stores: draft.open_stores } : {}),
    ...(draft.open_web_centers.length ? { open_web_centers: draft.open_web_centers } : {}),
    ...draft.finance,
    brands: draft.products.map((p) => ({
      name: p.name, brand_type: p.brand_type, price: p.price, production: p.production, advertising: p.advertising,
      ...(p.locked ? {} : { components: p.components }),
    })),
  };
}

/** Next quarter keeps the products (now designed) and drops one-off decisions. */
export function carryOver(draft: Draft): Draft {
  return { ...emptyDraft(), products: draft.products.map((p) => ({ ...p, locked: true })) };
}

export function validate(draft: Draft): string | null {
  const names = draft.products.map((p) => p.name.trim());
  if (names.some((n) => !n)) return "每個產品都要有名稱。";
  if (new Set(names).size !== names.length) return "產品名稱不能重複。";
  return null;
}

/** Component choice per group: single-select groups replace, multi-select groups toggle. */
export function chooseComponent(setup: GameSetupDoc, current: string[], componentId: string): string[] {
  const component = setup.components.find((c) => c.id === componentId);
  const group = setup.component_groups.find((g) => g.id === component?.group);
  if (!component || !group) return current;
  if (group.multi) return current.includes(componentId) ? current.filter((c) => c !== componentId) : [...current, componentId];
  const others = current.filter((c) => setup.components.find((x) => x.id === c)?.group !== group.id);
  if (current.includes(componentId) && !group.required) return others; // optional single group: click again to clear
  return [...others, componentId];
}
