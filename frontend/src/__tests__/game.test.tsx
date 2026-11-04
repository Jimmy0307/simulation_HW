// Game mode: opens, data source switches, uncalibrated numbers carry a quiet ≈ (full marks only behind the switch),
// the map opens a side panel, product settings open behind "調整", opponent count takes effect.
// The static runs use the real exported synthetic bundle (every number made by the Python engine).
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { App } from "../App";
import { ApiProvider } from "../data/apiProvider";
import { StaticProvider } from "../data/staticProvider";
import { APPROX, Figure, LevelsContext } from "../screens/game/Figure";
import { summaryNote } from "../screens/game/Settlement";
import type { GameScript, GameSetupDoc, Line, ModulesDoc, Report } from "../types";
import { PRACTICE_TEXT } from "../ui/Practice";
import { formatNumber } from "../ui/Num";

afterEach(() => {
  cleanup();
  try { window.localStorage.clear(); } catch { /* no storage */ }
});

const DEMO = join(__dirname, "..", "..", "public", "demo");
const read = (name: string) => JSON.parse(readFileSync(join(DEMO, name), "utf-8"));
const script = read("gamemode.json") as GameScript;
const staticProvider = () => new StaticProvider("demo/", async (url) => read(url.replace("demo/", "")));

async function openGame(provider: StaticProvider | ApiProvider) {
  window.location.hash = "#/game";
  const view = render(<App provider={provider} />);
  await screen.findByText("開始第一季");
  return view;
}

const line = (value: number, level: Line["level"]): Line => ({ value, level, source: "rule", uncalibrated:
  level === "literature" || level === "placeholder" });

const percent = (value: number) => `${(value * 100).toLocaleString("zh-TW", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`;

describe("numbers in the game view", () => {
  const three = () => (
    <><Figure line={line(1234, "verified")} label="v" /><Figure line={line(77, "literature")} label="l" />
      <Figure line={line(5, "placeholder")} label="p" /></>
  );

  it("trusted numbers are plain; uncalibrated ones get a quiet ≈ with a hover note, never letter marks", () => {
    const { container } = render(three());
    const [trusted, lit, ph] = [...container.querySelectorAll("[data-estimate]")];
    expect(trusted.getAttribute("data-estimate")).toBe("false");
    expect(trusted.textContent).toBe("1,234");
    expect(lit.getAttribute("data-estimate")).toBe("true");
    expect(lit.querySelector(".fig-approx")?.textContent).toBe(APPROX);
    expect(lit.querySelector(".fig-v")?.textContent).toBe("77");
    expect(lit.querySelector('[role="tooltip"]')?.textContent).toContain("預估 · Q2 校準後變實際");
    expect(ph.querySelector('[role="tooltip"]')?.textContent).toContain("預估 · 成本規則驗證後變實際");
    expect(container.querySelectorAll(".mark, .uncal-chip, .estimate-btn")).toHaveLength(0);
    expect(container.textContent).not.toMatch(/[VDLP]/);
  });

  it("the 'show all source levels' switch brings back the full marks", () => {
    const { container } = render(<LevelsContext.Provider value={true}>{three()}</LevelsContext.Provider>);
    expect([...container.querySelectorAll(".mark")].map((m) => m.textContent)).toEqual(["V", "L", "P"]);
    expect(container.querySelectorAll(".uncal-chip")).toHaveLength(2);
    expect(container.querySelector(".fig-approx")).toBeNull();
  });
});

describe("game mode on the static synthetic demo", () => {
  it("is a new entry; the setup screen shows the demo configuration", async () => {
    const { container } = await openGame(staticProvider());
    expect(container.querySelector('a[href="#/game"]')?.textContent).toContain("遊戲模式");
    expect(screen.getByTestId("opponent-count").textContent).toBe("3 個對手");
    expect((screen.getByLabelText("對手 3 難度") as HTMLSelectElement).value).toBe("aggressive");
    expect((container.querySelector('input[value="private"]') as HTMLInputElement).disabled).toBe(true);
    expect(screen.getByTestId("replay-reason").textContent).toContain("private");
  });

  it("plays the recorded game: map, bike cards, side panels, calculate, report card, timeline", async () => {
    const { container } = await openGame(staticProvider());
    await act(async () => fireEvent.click(screen.getByText("開始第一季")));
    expect((await screen.findByTestId("game-source")).textContent).toContain("SYNTHETIC");
    const game = container.querySelector(".game") as HTMLElement;
    // default view: no side panel, bikes show name + price only, no letter marks anywhere
    expect(screen.queryByTestId("inspector")).toBeNull();
    const plan = script.steps[0].plan;
    const cards = screen.getAllByTestId("product-card");
    expect(cards).toHaveLength(plan.brands?.length ?? 0);
    expect(cards[0].textContent).toContain(plan.brands![0].name);
    expect(cards[0].querySelector("input, select, [type=range]")).toBeNull();
    expect(game.querySelectorAll(".mark, .uncal-chip")).toHaveLength(0);
    // map: a click on a city opens the panel with segments, willingness to pay and opening cost (trusted, plain)
    const city = script.start.regions[0].cities.find((c) => !(plan.open_stores ?? []).includes(c.key))!;
    fireEvent.click(screen.getByTestId(`city-${city.key}`));
    const panel = screen.getByTestId("city-panel");
    expect(screen.getByTestId("inspector").textContent).toContain(city.name);
    expect(panel.textContent).toContain(formatNumber(city.segments[0].wtp.value));
    expect(panel.textContent).toContain(formatNumber(city.store!.setup_cost.value));
    expect(panel.textContent).toContain("本季在這裡開店");
    const lease = within(panel).getByText("每季租金").parentElement!; // placeholder: the quiet ≈
    expect(lease.querySelector(".fig-approx")?.textContent).toBe(APPROX);
    // the factory opens the capacity panel; "調整" opens the bike's settings
    fireEvent.click(screen.getByTestId("factory"));
    expect(screen.getByTestId("factory-panel").textContent).toContain("擴充產能");
    fireEvent.click(within(cards[0]).getByText("調整"));
    const product = screen.getByTestId("product-panel");
    for (const group of script.start.component_groups) expect(product.textContent).toContain(group.name);
    for (const label of ["價格", "生產量", "廣告"]) expect(within(product).getByLabelText(label)).toBeTruthy();
    fireEvent.keyDown(screen.getByTestId("inspector"), { key: "Escape" });
    expect(screen.queryByTestId("inspector")).toBeNull();
    // calculate (no advance): the engine's preview in the side panel
    await act(async () => fireEvent.click(screen.getByText("試算這一季（不推進）")));
    await waitFor(() => expect(screen.getByTestId("preview-panel").querySelector('[data-testid="key-results"]')).not.toBeNull());
    // end the quarter: report card
    await act(async () => fireEvent.click(screen.getByText("結束這一季")));
    const card = await screen.findByTestId("settlement");
    const report = script.steps[0].report;
    const note = within(card).getByTestId("literature-notice").textContent ?? "";
    expect(note).toContain(APPROX);
    expect(note).toContain("Q2");
    expect(within(card).getAllByTestId("rival-row")).toHaveLength(3);
    expect(within(card).getByTestId("rival-table").textContent).toContain("對手 3 · 激進");
    expect(within(card).getByTestId("share-us").textContent).toContain(percent(report.lines.market_share.value));
    expect(card.querySelectorAll(".mark, .uncal-chip, .estimate-btn")).toHaveLength(0);
    // full details one click away: trusted rows plain, uncalibrated rows with ≈ (unit cost is placeholder)
    const rows = [...card.querySelectorAll("tr[data-uncalibrated]")];
    const trusted = rows.filter((r) => r.getAttribute("data-uncalibrated") === "false");
    const estimates = rows.filter((r) => r.getAttribute("data-uncalibrated") === "true");
    expect(trusted.length).toBeGreaterThan(3);
    for (const row of trusted) expect(row.querySelector(".fig-approx")).toBeNull();
    expect(estimates.length).toBeGreaterThan(5);
    for (const row of estimates) expect(row.querySelector(".fig-approx")).not.toBeNull();
    expect(estimates.map((r) => r.textContent).join(" ")).toContain("單位成本");
    await act(async () => fireEvent.click(within(card).getByText("回到下一季")));
    expect(screen.getByTestId("timeline").textContent).toContain("Q1");
    // the switch shows every source level; off again returns to the clean view
    const levels = screen.getByTestId("levels-switch");
    fireEvent.click(levels);
    expect(levels.getAttribute("aria-checked")).toBe("true");
    expect(game.querySelectorAll(".mark").length).toBeGreaterThan(0);
    fireEvent.click(levels);
    expect(game.querySelectorAll(".mark")).toHaveLength(0);
    // two more recorded quarters, then the replay ends
    for (const step of script.steps.slice(1)) {
      await act(async () => fireEvent.click(screen.getByText("結束這一季")));
      const next = await screen.findByTestId("settlement");
      expect(next.getAttribute("aria-label")).toBe(`第 ${step.quarter} 季結算`);
      await act(async () => fireEvent.click(within(next).getByText("回到下一季")));
    }
    expect(screen.getByTestId("timeline").querySelectorAll("li")).toHaveLength(script.steps.length);
    expect((screen.getByText("結束這一季") as HTMLButtonElement).disabled).toBe(true);
    expect(container.textContent).toContain("預錄的一局已播完");
    // after Q1 the stores opened in the recorded plan are lit on the map
    for (const key of plan.open_stores ?? []) expect(screen.getByTestId(`city-${key}`).getAttribute("class")).toContain("open");
  });
});

// --- live API mode with a recording fake server --------------------------------------------------------------------

function fakeServer() {
  const calls: { path: string; body?: Record<string, unknown> }[] = [];
  let opponents = 3;
  let isPrivate = false;
  let quarter = 1;
  const withRivals = (report: Report): Report => {
    const lines = Object.fromEntries(Object.entries(report.lines).filter(([k]) => !k.startsWith("rival_")));
    const share = report.lines["rival_share[rival-1]"];
    for (let i = 1; i <= opponents; i += 1) lines[`rival_share[rival-${i}]`] = share;
    return { ...report, quarter, lines };
  };
  const setup = (): GameSetupDoc => ({
    ...script.start, ...(quarter > 1 ? script.steps[0].before : {}), is_private: isPrivate,
    source: isPrivate ? "private" : "synthetic", name: isPrivate ? "private-from-evidence" : script.start.name,
    state: { ...(script.start.state as NonNullable<GameSetupDoc["state"]>), quarter },
    game: { opponents: Array.from({ length: opponents }, (_, i) => ({ name: `rival-${i + 1}`, difficulty: "normal", label: "普通" })),
      replay: false, objective: "讓期末現金最大化" },
  });
  const fetcher = (async (url: string, init?: RequestInit) => {
    const path = url.replace("http://api/api", "");
    const body = init?.body ? JSON.parse(String(init.body)) as Record<string, unknown> : undefined;
    calls.push({ path, body });
    let out: unknown;
    if (path === "/game-mode/start") {
      opponents = (body?.opponents as unknown[]).length;
      isPrivate = body?.source === "private";
      quarter = 1;
      out = setup();
    } else if (path === "/game-mode/setup") out = quarter === 1 && calls.length === 1 ? { ...setup(), game: null } : setup();
    else if (path === "/game/preview") {
      // the recorded preview, with its unit cost line renamed to the bike in the request
      const report = withRivals(script.steps[1].preview);
      const cost = Object.entries(report.lines).find(([k]) => k.startsWith("unit_cost["))?.[1];
      const names = ((body?.brands ?? []) as { name: string }[]).map((b) => b.name);
      let lines: Report["lines"] = { ...report.lines, ...Object.fromEntries(names.map((n) => [`unit_cost[${n}]`, cost as Line])) };
      if (body?.modules) {
        // a practice module was decided: the real engine then marks the demand chain heuristic (engine.advance);
        // the fake only mirrors that labelling so the screen can be checked
        const chain = /^(units_|market_|rival_|revenue|net_income|cash_end|operating_profit)/;
        lines = Object.fromEntries(Object.entries(lines).map(([k, l]) => [k, chain.test(k) ? { ...l, level: "heuristic" as const, uncalibrated: true } : l]));
        lines.selling_effort = { value: 1.2, level: "heuristic", source: "practice rule", uncalibrated: true };
      }
      out = { report: { ...report, lines } };
    }
    else if (path === "/game/play") { out = { report: withRivals(script.steps[1].report) }; quarter += 1; }
    else if (path === "/pack") out = { ...script.start, is_private: isPrivate };
    else if (path === "/modules") out = read("modules.json");
    else out = {};
    return new Response(JSON.stringify(out));
  }) as unknown as typeof fetch;
  return { calls, provider: new ApiProvider("http://api", fetcher) };
}

describe("game mode on the live engine (fake API)", () => {
  it("data source and opponent count go to the engine and come back in the report card", async () => {
    const { calls, provider } = fakeServer();
    const { container } = await openGame(provider);
    fireEvent.change(screen.getByLabelText("對手數量"), { target: { value: "5" } });
    expect(screen.getByTestId("opponent-count").textContent).toBe("5 個對手");
    fireEvent.change(screen.getByLabelText("對手 5 難度"), { target: { value: "aggressive" } });
    fireEvent.click(container.querySelector('input[value="private"]') as HTMLInputElement);
    await act(async () => fireEvent.click(screen.getByText("開始第一季")));
    const start = calls.find((c) => c.path === "/game-mode/start")!;
    expect(start.body?.source).toBe("private");
    expect((start.body?.opponents as { difficulty: string }[]).map((o) => o.difficulty))
      .toEqual(["normal", "normal", "normal", "normal", "aggressive"]);
    expect((await screen.findByTestId("game-source")).textContent).toContain("PRIVATE");
    expect(screen.getByTestId("pack-badge").textContent).toContain("PRIVATE");
    // a new bike opens its settings; set a price, then open a store from the map: each change is calculated by the engine
    await act(async () => fireEvent.click(screen.getByText(/新增自行車/)));
    expect(screen.getAllByTestId("product-card")).toHaveLength(1);
    const product = screen.getByTestId("product-panel");
    fireEvent.change(within(product).getByLabelText("價格"), { target: { value: "650" } });
    expect(screen.getByTestId("product-card").querySelector(".bike-price-v")?.textContent).toBe("650");
    fireEvent.click(screen.getByTestId(`city-${script.start.regions[0].cities[0].key}`));
    await act(async () => fireEvent.click(screen.getByText("本季在這裡開店")));
    expect(screen.getByTestId(`city-${script.start.regions[0].cities[0].key}`).getAttribute("class")).toContain("planned");
    await waitFor(() => {
      const last = calls.filter((c) => c.path === "/game/preview").at(-1);
      expect(last?.body?.open_stores).toEqual([script.start.regions[0].cities[0].key]);
      expect((last?.body?.brands as { price: number }[])[0].price).toBe(650);
    }, { timeout: 3000 });
    // the engine's unit cost reaches the bike card's price gauge, with the quiet ≈ (placeholder)
    await waitFor(() => expect(screen.getByTestId("price-gauge").querySelector(".fig-approx")).not.toBeNull(), { timeout: 3000 });
    await act(async () => fireEvent.click(screen.getByText("結束這一季")));
    const card = await screen.findByTestId("settlement");
    expect(within(card).getAllByTestId("rival-row")).toHaveLength(5);
    const play = calls.find((c) => c.path === "/game/play")!;
    expect((play.body?.brands as { name: string }[])[0].name).toBe("自行車-1");
  });
});

// --- business modules: practice badge, locked modules, levers that reach the engine ------------------------------

describe("practice (heuristic) numbers", () => {
  it("get the loud practice badge, not the quiet ≈", () => {
    const { container } = render(<Figure line={line(42, "heuristic")} label="h" />);
    const fig = container.querySelector("[data-estimate]")!;
    expect(fig.getAttribute("data-level")).toBe("heuristic");
    expect(fig.querySelector(".fig-approx")).toBeNull();
    const badge = within(fig as HTMLElement).getByTestId("practice-badge");
    expect(badge.textContent).toContain("練習");
    expect(badge.textContent).toContain(PRACTICE_TEXT);
    expect(fig.querySelector(".fig-v")?.textContent).toBe("42");
  });

  it("with the levels switch on, the full mark is H plus the practice badge", () => {
    const { container } = render(<LevelsContext.Provider value={true}><Figure line={line(42, "heuristic")} label="h" /></LevelsContext.Provider>);
    expect(container.querySelector(".mark")?.textContent).toBe("H");
    expect(container.querySelector(".uncal-chip")).toBeNull();
    expect(screen.getByTestId("practice-badge")).toBeTruthy();
  });

  it("the report card's summary line says which numbers are practice", () => {
    const report = { quarter: 2, plan: "p", notes: [], lines: { revenue: line(10, "heuristic"), cash_end: line(5, "placeholder") } };
    const text = summaryNote(report) ?? "";
    expect(text).toContain("練習");
    expect(text).toContain(PRACTICE_TEXT);
    expect(text).toContain(APPROX);
  });
});

describe("game mode: business modules (fake API)", () => {
  it("lists every module by maturity, locks the unbuilt ones, and sends practice levers to the engine", async () => {
    const { calls, provider } = fakeServer();
    await openGame(provider);
    await act(async () => fireEvent.click(screen.getByText("開始第一季")));
    await act(async () => fireEvent.click(await screen.findByText(/新增自行車/)));
    // the shelf under the bikes: two practice modules and the locked count
    const locked = await screen.findByTestId("shelf-locked");
    const ledger = read("modules.json") as ModulesDoc;
    expect(locked.textContent).toContain(`${ledger.counts["not-modeled"]} 個`);
    expect(within(screen.getByTestId("shelf-sales")).getByTestId("practice-badge")).toBeTruthy();
    await act(async () => fireEvent.click(screen.getByTestId("shelf-sales")));
    const panel = screen.getByTestId("modules-panel");
    // grouped by maturity, each group's size from the ledger
    for (const m of ["verified", "literature", "heuristic", "not-modeled"] as const) {
      expect(within(panel).getByTestId(`module-group-${m}`).textContent).toContain(`${ledger.counts[m]} 個`);
    }
    // a locked module explains itself when clicked
    const quality = within(panel).getByTestId("locked-production.quality");
    expect(quality.textContent).toContain("待建");
    fireEvent.click(quality);
    expect(within(panel).getByTestId("lock-reason").textContent).toContain("為什麼還不能調");
    // the practice levers carry the banner; turning the sales force on and moving a slider reaches the engine
    const sales = within(panel).getByTestId("sales-force-editor");
    expect(sales.textContent).toContain(PRACTICE_TEXT);
    fireEvent.click(within(sales).getByLabelText("啟用業務團隊"));
    fireEvent.change(within(sales).getByLabelText("業務人數"), { target: { value: "12" } });
    const media = within(panel).getByTestId("media-mix-editor");
    fireEvent.click(within(media).getByLabelText(/分配「自行車-1」的廣告/));
    fireEvent.change(within(media).getByLabelText("社群"), { target: { value: "60" } });
    await waitFor(() => {
      const last = calls.filter((c) => c.path === "/game/preview").at(-1);
      const modules = last?.body?.modules as Record<string, Record<string, unknown>>;
      expect(modules.sales_force.headcount).toBe(12);
      expect((modules["marketing.media_mix"].mix as Record<string, Record<string, number>>)["自行車-1"].social).toBe(60);
    }, { timeout: 3000 });
    // the engine's practice results come back with the badge, in the panel and on the report numbers
    await waitFor(() => expect(within(sales).getByText("銷售力倍數")).toBeTruthy(), { timeout: 3000 });
    expect(within(sales).getAllByTestId("practice-badge").length).toBeGreaterThan(1);
    await act(async () => fireEvent.click(screen.getByText("試算這一季（不推進）")));
    const preview = await screen.findByTestId("preview-panel");
    expect(within(preview).getAllByTestId("practice-badge").length).toBeGreaterThan(0);
    expect(within(preview).getByTestId("literature-notice").textContent).toContain(PRACTICE_TEXT);
  });

  it("the static demo shows the module list read-only", async () => {
    await openGame(staticProvider());
    await act(async () => fireEvent.click(screen.getByText("開始第一季")));
    await act(async () => fireEvent.click(await screen.findByTestId("shelf-media")));
    const sales = screen.getByTestId("sales-force-editor");
    expect((within(sales).getByLabelText("業務人數") as HTMLInputElement).disabled).toBe(true);
    expect((within(sales).getByRole("checkbox") as HTMLInputElement).disabled).toBe(true);
  });
});
