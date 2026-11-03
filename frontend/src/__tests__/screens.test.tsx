// Smoke test: the real App + the real exported synthetic demo bundle (public/demo), every screen and its main interaction.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { App, ROUTES } from "../App";
import { StaticProvider } from "../data/staticProvider";
import { UNCALIBRATED_LABEL } from "../ui/Num";

afterEach(cleanup);

const DEMO = join(__dirname, "..", "..", "public", "demo");
const provider = () => new StaticProvider("demo/", async (url) => JSON.parse(readFileSync(join(DEMO, url.replace("demo/", "")), "utf-8")));

async function open(route: string) {
  window.location.hash = `#/${route}`;
  const view = render(<App provider={provider()} />);
  await screen.findByTestId("pack-badge");
  return view;
}

describe("all seven screens with the synthetic demo bundle", () => {
  it("keeps the seven analysis routes and adds game mode last", () => {
    expect(ROUTES).toHaveLength(8);
    expect(ROUTES.slice(0, 7).map((r) => r.id)).toEqual(["overview", "decisions", "compare", "scenario", "stress", "diff", "levels"]);
    expect(ROUTES[7]).toEqual({ id: "game", title: "遊戲模式" });
  });

  it("overview: synthetic badge, state, trend and uncalibrated marks", async () => {
    const { container } = await open("overview");
    expect(screen.getByTestId("pack-badge").textContent).toContain("SYNTHETIC");
    await screen.findByText(/逐季趨勢/);
    await waitFor(() => expect(container.querySelectorAll('[data-uncalibrated="true"]').length).toBeGreaterThan(0));
    expect(container.querySelectorAll('[data-level="verified"]').length).toBeGreaterThan(0);
  });

  it("decisions: preview a preset; play is disabled in the demo", async () => {
    await open("decisions");
    const preview = await screen.findByText("試算（不推進）");
    await act(async () => fireEvent.click(preview));
    await screen.findByText(/報表：Q/);
    expect((screen.getByText("送出並推進一季") as HTMLButtonElement).disabled).toBe(true);
  });

  it("compare: three plans side by side with marks", async () => {
    const { container } = await open("compare");
    const button = await screen.findByText("比較");
    await act(async () => fireEvent.click(button));
    await screen.findByText(/方案比較 · Q/);
    expect(container.querySelectorAll("thead th").length).toBeGreaterThanOrEqual(4);
    expect(container.querySelectorAll('[data-uncalibrated="true"]').length).toBeGreaterThan(0);
  });

  it("scenario: run a template and show event flags", async () => {
    const { container } = await open("scenario");
    const select = (await screen.findByText("範本")).querySelector("select")!;
    await act(async () => fireEvent.change(select, { target: { value: "combined-shock" } }));
    await act(async () => fireEvent.click(screen.getByText("執行情境")));
    await screen.findByText(/結果：combined-shock/);
    expect(container.textContent).toContain("⚑");
  });

  it("scenario: an edited spec is refused politely in the demo", async () => {
    await open("scenario");
    const seed = (await screen.findByText("seed")).querySelector("input")!;
    await act(async () => fireEvent.change(seed, { target: { value: "99" } }));
    await act(async () => fireEvent.click(screen.getByText("執行情境")));
    await screen.findByText(/Demo 模式為唯讀/);
  });

  it("stress: banner always visible; worst cases and sensitivity after loading", async () => {
    const { container } = await open("stress");
    expect(await screen.findAllByText(UNCALIBRATED_LABEL)).not.toHaveLength(0);
    await act(async () => fireEvent.click(await screen.findByText("讀取預算結果")));
    await screen.findByText(/敏感度/);
    expect(container.querySelectorAll("tr.worst").length).toBe(5);
    expect(container.textContent).toContain("不是本局預測");
  });

  it("diff: verified-module changes are highlighted red", async () => {
    const { container } = await open("diff");
    await screen.findByText(/項變動/);
    expect(container.querySelectorAll("tr.reverify").length).toBeGreaterThan(0);
    expect(container.textContent).toContain("紅旗");
  });

  it("levels: legend and registry", async () => {
    await open("levels");
    await screen.findByText(/指標登錄/);
    expect(screen.getAllByText(/literature/).length).toBeGreaterThan(0);
  });
});
