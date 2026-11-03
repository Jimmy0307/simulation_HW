import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { StaticProvider } from "../data/staticProvider";
import { Overview } from "../screens/Overview";
import type { Line } from "../types";
import { isUncalibrated, Num, UNCALIBRATED_LABEL } from "../ui/Num";

afterEach(cleanup);

const chain = [
  { metric: "revenue", level: "literature" as const, formula: "sum(units_sold x price)", evidence: "docs/demand-model-spec.md" },
  { metric: "units_sold[brand]", level: "literature" as const, formula: "min(units_demanded, inventory)" },
];

describe("uncalibrated marker", () => {
  it("appears on literature and placeholder numbers, never on verified/derived/estimated", () => {
    const cases: [Line["level"], boolean][] = [["verified", false], ["derived", false], ["estimated", false], ["literature", true], ["placeholder", true]];
    for (const [level, expected] of cases) {
      const { container } = render(<Num line={{ value: 1000, level, source: "rule" }} />);
      const node = container.querySelector(".num")!;
      expect(node.getAttribute("data-uncalibrated")).toBe(String(expected));
      expect(node.textContent?.includes(UNCALIBRATED_LABEL)).toBe(expected);
      cleanup();
    }
  });

  it("follows the API flag when present", () => {
    expect(isUncalibrated({ level: "derived", uncalibrated: true })).toBe(true);
    expect(isUncalibrated({ level: "literature", uncalibrated: false })).toBe(false);
  });

  it("shows the full source chain in the hover tooltip", () => {
    render(<Num line={{ value: 5, level: "literature", source: "sum(units_sold x price)", uncalibrated: true, chain }} label="revenue" />);
    const tip = screen.getByRole("tooltip");
    expect(tip.textContent).toContain("units_sold[brand]");
    expect(tip.textContent).toContain("docs/demand-model-spec.md");
    expect(tip.textContent).toContain(UNCALIBRATED_LABEL);
  });
});

describe("screens through the static provider", () => {
  it("renders the overview with the synthetic badge data and marks revenue", async () => {
    const game = {
      name: "synthetic-demo", provenance: "synthetic", is_private: false, source: "synthetic", demand_model: "literature", quarter: 2,
      state: { quarter: 2, cash: { value: 10, level: "placeholder", uncalibrated: true }, cd: 0, fixed_capacity_units: 18, stores_open: ["S1"],
        web_centers_open: [], brands: {}, inventory: {}, stock_total: 0, shares_total: 0 },
      history: [{ quarter: 1, plan: "q1", notes: [], lines: {
        revenue: { value: 77, level: "literature", source: "r", uncalibrated: true, chain },
        capex_capacity: { value: 5, level: "verified", source: "c", uncalibrated: false },
      } }],
    };
    const provider = new StaticProvider("demo/", async (url) => (url.endsWith("game.json") ? game : {}));
    const { container } = render(<Overview provider={provider} />);
    await screen.findByText(/虛構資料/);
    const revenue = [...container.querySelectorAll(".num")].find((n) => n.textContent?.startsWith("77"))!;
    expect(revenue.getAttribute("data-uncalibrated")).toBe("true");
    const capex = [...container.querySelectorAll(".num")].find((n) => n.textContent?.startsWith("5"))!;
    expect(capex.getAttribute("data-uncalibrated")).toBe("false");
  });
});
