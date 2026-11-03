// Game mode: opens, data source switches, uncalibrated numbers are in the estimate state, opponent count takes effect.
// The static runs use the real exported synthetic bundle (every number made by the Python engine).
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { App } from "../App";
import { ApiProvider } from "../data/apiProvider";
import { StaticProvider } from "../data/staticProvider";
import { Estimate } from "../screens/game/Estimate";
import { LITERATURE_NOTICE } from "../screens/game/Settlement";
import type { GameScript, GameSetupDoc, Line, Report } from "../types";
import { formatNumber } from "../ui/Num";

afterEach(cleanup);

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

describe("estimate state", () => {
  it("trusted levels show directly; uncalibrated levels start collapsed and reveal on click", () => {
    const { container } = render(<><Estimate line={line(1234, "verified")} label="v" /><Estimate line={line(77, "literature")} label="l" />
      <Estimate line={line(5, "placeholder")} label="p" /></>);
    const [trusted, lit, ph] = [...container.querySelectorAll("[data-estimate]")];
    expect(trusted.getAttribute("data-estimate")).toBe("false");
    expect(trusted.textContent).toContain("1,234");
    expect(lit.getAttribute("data-estimate")).toBe("true");
    expect(lit.textContent).toContain("預估");
    expect(lit.textContent).not.toContain("77");
    fireEvent.click(within(lit as HTMLElement).getByRole("button"));
    expect(lit.textContent).toContain("77");
    expect(lit.textContent).toContain("Q2 數據校準後變實際");
    fireEvent.click(within(ph as HTMLElement).getByRole("button"));
    expect(ph.textContent).toContain("成本規則尚未驗證");
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

  it("plays the recorded game: product, map, calculate, end quarter, settlement, timeline", async () => {
    const { container } = await openGame(staticProvider());
    await act(async () => fireEvent.click(screen.getByText("開始第一季")));
    expect((await screen.findByTestId("game-source")).textContent).toContain("SYNTHETIC");
    expect(screen.getAllByTestId("product-card")).toHaveLength(script.steps[0].plan.brands?.length ?? 0);
    // map: a click shows the city's segments and willingness to pay (data, trusted level)
    const firstCity = script.start.regions[0].cities[1];
    fireEvent.click(screen.getByTestId(`city-${firstCity.key}`));
    const panel = screen.getByTestId("city-panel");
    expect(panel.textContent).toContain(firstCity.name);
    expect(panel.textContent).toContain(formatNumber(firstCity.segments[0].wtp.value));
    expect(panel.textContent).toContain(formatNumber(firstCity.store!.setup_cost.value));
    // calculate (no advance) shows the engine's preview
    await act(async () => fireEvent.click(screen.getByText("試算這一季（不推進）")));
    expect(await screen.findByTestId("preview-panel")).toBeTruthy();
    // end the quarter: settlement card
    await act(async () => fireEvent.click(screen.getByText("結束這一季")));
    const card = await screen.findByTestId("settlement");
    const report = script.steps[0].report;
    expect(within(card).getByTestId("literature-notice").textContent).toBe(LITERATURE_NOTICE);
    expect(within(card).getAllByTestId("rival-row")).toHaveLength(3);
    expect(within(card).getByTestId("rival-table").textContent).toContain("對手 3 · 激進");
    // trusted cost lines are plain; every uncalibrated line is collapsed
    const rows = [...card.querySelectorAll("tr[data-uncalibrated]")];
    expect(rows.some((r) => r.getAttribute("data-uncalibrated") === "false" && r.querySelector('[data-estimate="false"]'))).toBe(true);
    const estimates = rows.filter((r) => r.getAttribute("data-uncalibrated") === "true");
    expect(estimates.length).toBeGreaterThan(5);
    expect(estimates.map((r) => r.textContent).join(" ")).toContain("單位成本"); // placeholder cost is an estimate too
    for (const row of estimates) {
      expect(row.querySelector('[data-estimate="true"] .estimate-btn')).not.toBeNull();
    }
    expect(within(card).getByText("成本面（可信的直接顯示）")).toBeTruthy();
    // the numbers are the engine's: reveal our market share and compare with the bundle
    fireEvent.click(within(card).getByText("全部展開"));
    expect(within(card).getByTestId("rival-table").textContent).toContain(formatNumber(report.lines.market_share.value));
    await act(async () => fireEvent.click(within(card).getByText("回到下一季")));
    expect(screen.getByTestId("timeline").textContent).toContain("Q1");
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
    else if (path === "/game/preview") out = { report: withRivals(script.steps[1].preview) };
    else if (path === "/game/play") { out = { report: withRivals(script.steps[1].report) }; quarter += 1; }
    else if (path === "/pack") out = { ...script.start, is_private: isPrivate };
    else out = {};
    return new Response(JSON.stringify(out));
  }) as unknown as typeof fetch;
  return { calls, provider: new ApiProvider("http://api", fetcher) };
}

describe("game mode on the live engine (fake API)", () => {
  it("data source and opponent count go to the engine and come back in the settlement", async () => {
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
    // make a product, open a store, set a price: each change is calculated by the engine (preview calls)
    await act(async () => fireEvent.click(screen.getByText("＋ 新增自行車")));
    expect(screen.getAllByTestId("product-card")).toHaveLength(1);
    fireEvent.change(screen.getByLabelText("價格"), { target: { value: "650" } });
    fireEvent.click(screen.getByTestId(`city-${script.start.regions[0].cities[0].key}`));
    await act(async () => fireEvent.click(screen.getByText("本季在這裡開店")));
    await waitFor(() => {
      const last = calls.filter((c) => c.path === "/game/preview").at(-1);
      expect(last?.body?.open_stores).toEqual([script.start.regions[0].cities[0].key]);
      expect((last?.body?.brands as { price: number }[])[0].price).toBe(650);
    }, { timeout: 3000 });
    await act(async () => fireEvent.click(screen.getByText("結束這一季")));
    const card = await screen.findByTestId("settlement");
    expect(within(card).getAllByTestId("rival-row")).toHaveLength(5);
    const play = calls.find((c) => c.path === "/game/play")!;
    expect((play.body?.brands as { name: string }[])[0].name).toBe("自行車-1");
  });
});
