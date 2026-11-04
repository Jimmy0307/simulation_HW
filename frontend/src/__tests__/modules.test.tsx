// Module maturity: the overview screen draws the ledger; the decision editor lists modules by maturity, with practice
// levers (read-only in the demo) and locked unbuilt modules. Uses the real exported synthetic demo bundle.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { App } from "../App";
import { StaticProvider } from "../data/staticProvider";
import type { ModulesDoc } from "../types";
import { PRACTICE_TEXT } from "../ui/Practice";

afterEach(cleanup);

const DEMO = join(__dirname, "..", "..", "public", "demo");
const read = (name: string) => JSON.parse(readFileSync(join(DEMO, name), "utf-8"));
const provider = () => new StaticProvider("demo/", async (url) => read(url.replace("demo/", "")));
const ledger = read("modules.json") as ModulesDoc;

async function open(route: string) {
  window.location.hash = `#/${route}`;
  const view = render(<App provider={provider()} />);
  await screen.findByTestId("pack-badge");
  return view;
}

describe("the ledger in the demo bundle", () => {
  it("is structure only and covers every area the brief names", () => {
    expect(ledger.is_private).toBe(false);
    expect(new Set(ledger.modules.map((m) => m.area))).toEqual(new Set(ledger.areas.map((a) => a.id)));
    for (const area of ["marketing", "sales_force", "production", "supply", "rnd", "finance", "strategy"]) {
      expect(ledger.modules.some((m) => m.area === area)).toBe(true);
    }
    const total = Object.values(ledger.counts).reduce((a, b) => a + b, 0);
    expect(total).toBe(ledger.modules.length);
    // only the two practice modules can be decided; everything not modeled is locked
    expect(new Set(ledger.modules.filter((m) => m.decidable).map((m) => m.module))).toEqual(new Set(["marketing.media_mix", "sales_force"]));
    expect(ledger.modules.filter((m) => m.maturity === "not-modeled").every((m) => !m.decidable)).toBe(true);
  });
});

describe("module maturity overview", () => {
  it("shows the ladder, the gap, and a detail panel per module", async () => {
    await open("modules");
    for (const m of ["verified", "literature", "heuristic", "not-modeled"] as const) {
      expect((await screen.findByTestId(`count-${m}`)).textContent).toContain(String(ledger.counts[m]));
    }
    const gap = ledger.modules.filter((m) => m.maturity === "not-modeled" && m.real_status !== "unknown").length;
    expect(screen.getByTestId("ledger-gap").textContent).toContain(`${gap}`);
    expect(screen.getByTestId("ledger-areas").querySelectorAll(".ledger-tile")).toHaveLength(ledger.modules.length);
    // heuristic behaviour tiles carry the practice badge
    expect(within(screen.getByTestId("tile-marketing.media_mix")).getByTestId("practice-badge")).toBeTruthy();
    // a tile opens its row: real-game status, next step, sources
    fireEvent.click(screen.getByTestId("tile-sales_force.staffing"));
    const detail = screen.getByTestId("ledger-detail");
    const row = ledger.modules.find((m) => m.key === "sales_force.staffing")!;
    expect(detail.textContent).toContain("推斷 · 未證實");
    expect(detail.textContent).toContain(row.next_step);
    expect(detail.textContent).toContain("L-ALBERS2010");
    expect(detail.textContent).toContain("SalesForceHeuristic");
    // filter: only modules the game has and we lack stay bright
    fireEvent.click(screen.getByRole("button", { name: "遊戲有、我們沒做" }));
    const dim = screen.getByTestId("ledger-areas").querySelectorAll("li.dim").length;
    expect(dim).toBe(ledger.modules.length - gap);
  });
});

describe("decision editor: modules by maturity", () => {
  it("groups every module, shows the practice banner on levers, and explains locked modules", async () => {
    await open("decisions");
    const board = await screen.findByTestId("module-board");
    for (const m of ["verified", "literature", "heuristic", "not-modeled"] as const) {
      expect(within(board).getByTestId(`module-group-${m}`).textContent).toContain(`${ledger.counts[m]} 個`);
    }
    const sales = within(board).getByTestId("sales-force-editor");
    expect(sales.textContent).toContain(PRACTICE_TEXT);
    expect((within(sales).getByLabelText("業務人數") as HTMLInputElement).disabled).toBe(true); // demo is read-only
    expect(within(board).getByTestId("media-mix-editor").textContent).toContain(PRACTICE_TEXT);
    const loans = within(board).getByTestId("locked-finance.loans");
    expect(loans.getAttribute("aria-expanded")).toBe("false");
    await act(async () => fireEvent.click(loans));
    expect(loans.getAttribute("aria-expanded")).toBe("true");
    expect(within(board).getByTestId("lock-reason").textContent).toContain("會被拒絕");
  });
});
