import { describe, expect, it } from "vitest";
import { ApiProvider } from "../data/apiProvider";
import { ReadOnlyError } from "../data/errors";
import { chooseSource } from "../data/provider";
import { StaticProvider } from "../data/staticProvider";

const plan = { name: "b", brands: [{ name: "X", brand_type: "A", price: 10, production: 1 }] };
const bundle: Record<string, unknown> = {
  "demo/pack.json": { name: "synthetic-demo", provenance: "synthetic", is_private: false, source: "synthetic", demand_model: "literature", quarter: 4 },
  "demo/plans.json": { presets: [{ id: "b-balanced", plan }], previews: { "b-balanced": { quarter: 4, plan: "b", notes: [], lines: {} } } },
  "demo/compare.json": { quarter: 4, reports: [{ quarter: 4, plan: "b", notes: [], lines: {} }] },
  "demo/diff.json": { packs: [{ id: "synthetic" }, { id: "synthetic-v2" }], result: { changes: [], red_flags: [] } },
};
const fakeFetch = async (url: string) => {
  if (!(url in bundle)) throw new Error(`missing ${url}`);
  return bundle[url];
};

describe("provider selection", () => {
  it("defaults to the static demo and lets ?source= override", () => {
    expect(chooseSource("", {}, "static")).toBe("static");
    expect(chooseSource("?source=api", {}, "static")).toBe("api");
    expect(chooseSource("", { VITE_DATA_SOURCE: "api" }, "static")).toBe("api");
    expect(chooseSource("?source=static", { VITE_DATA_SOURCE: "api" }, "api")).toBe("static");
    expect(chooseSource("?source=nonsense", {}, "static")).toBe("static");
  });
});

describe("StaticProvider", () => {
  const provider = new StaticProvider("demo/", fakeFetch);

  it("is read-only and serves only precomputed results", async () => {
    expect(provider.canCompute).toBe(false);
    expect((await provider.pack()).is_private).toBe(false);
    await expect(provider.play(plan)).rejects.toBeInstanceOf(ReadOnlyError);
    await expect(provider.newGame()).rejects.toBeInstanceOf(ReadOnlyError);
    await expect(provider.switchPack()).rejects.toBeInstanceOf(ReadOnlyError);
    expect((await provider.preview(plan, "b-balanced")).plan).toBe("b");
    await expect(provider.preview({ ...plan, name: "edited" }, "b-balanced")).rejects.toBeInstanceOf(ReadOnlyError);
    expect((await provider.compare([plan], ["b-balanced"])).reports).toHaveLength(1);
    await expect(provider.diff("synthetic", "other")).rejects.toBeInstanceOf(ReadOnlyError);
  });
});

describe("ApiProvider", () => {
  it("posts to the local API and passes numbers through unchanged", async () => {
    const calls: { url: string; init?: RequestInit }[] = [];
    const fetcher = (async (url: string, init?: RequestInit) => {
      calls.push({ url, init });
      return new Response(JSON.stringify({ report: { quarter: 1, plan: "b", notes: [], lines: { revenue: { value: 42, level: "literature", source: "x" } } } }));
    }) as unknown as typeof fetch;
    const provider = new ApiProvider("http://127.0.0.1:8765", fetcher);
    expect(provider.canCompute).toBe(true);
    const report = await provider.play(plan);
    expect(calls[0].url).toBe("http://127.0.0.1:8765/api/game/play");
    expect(calls[0].init?.method).toBe("POST");
    expect(report.lines.revenue.value).toBe(42);
  });

  it("surfaces API errors", async () => {
    const fetcher = (async () => new Response(JSON.stringify({ detail: "bad" }), { status: 400 })) as unknown as typeof fetch;
    await expect(new ApiProvider("http://x", fetcher).pack()).rejects.toThrow("bad");
  });
});
