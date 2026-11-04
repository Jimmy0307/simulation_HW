import { useEffect, useState } from "react";
import type { DataProvider } from "../data/provider";
import type { BrandPlan, PlanDoc, Report } from "../types";
import { Banner, Card, LinesTable, Status, useAsync } from "../ui/common";
import { ModuleBoard } from "../ui/ModuleBoard";
import { Num } from "../ui/Num";

const clone = <T,>(v: T): T => JSON.parse(JSON.stringify(v)) as T;

function NumberField({ label, value, onChange, step }: { label: string; value: number | undefined; onChange: (v: number) => void; step?: number }) {
  return (
    <label className="field">{label}
      <input type="number" step={step ?? 1} value={value ?? 0} onChange={(e) => onChange(Number(e.target.value))} />
    </label>
  );
}

export function Decisions({ provider, onPlayed }: { provider: DataProvider; onPlayed?: () => void }) {
  const plans = useAsync(() => provider.plans(), [provider]);
  const catalog = useAsync(() => provider.modules(), [provider]);
  const game = useAsync(() => provider.game(), [provider]);
  const [presetId, setPresetId] = useState<string>("");
  const [plan, setPlan] = useState<PlanDoc>({ name: "my-plan" });
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (plans.data && !presetId && plans.data.presets.length) {
      setPresetId(plans.data.presets[0].id);
      setPlan(clone(plans.data.presets[0].plan));
    }
  }, [plans.data, presetId]);

  const choose = (id: string) => {
    const preset = plans.data?.presets.find((p) => p.id === id);
    setPresetId(id);
    if (preset) setPlan(clone(preset.plan));
    setReport(null);
    setError(null);
  };
  const update = (patch: Partial<PlanDoc>) => setPlan((p) => ({ ...p, ...patch }));
  const updateBrand = (i: number, patch: Partial<BrandPlan>) =>
    setPlan((p) => ({ ...p, brands: (p.brands ?? []).map((b, j) => (j === i ? { ...b, ...patch } : b)) }));
  const toggle = (key: "open_stores" | "open_web_centers", value: string) =>
    setPlan((p) => {
      const current = new Set(p[key] ?? []);
      if (current.has(value)) current.delete(value); else current.add(value);
      return { ...p, [key]: [...current] };
    });

  const run = async (kind: "preview" | "play") => {
    setBusy(true);
    setError(null);
    try {
      const result = kind === "preview" ? await provider.preview(plan, presetId) : await provider.play(plan);
      setReport(result);
      if (kind === "play") onPlayed?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const options = plans.data;
  return (
    <>
      <Status state={plans} />
      {!provider.canCompute ? (
        <Banner kind="info" title="Demo 唯讀">可以檢視預設方案的預先試算結果；修改後的方案需要實戰模式（本機引擎）才能計算。</Banner>
      ) : null}
      {options ? (
        <Card title="一季決策" actions={
          <label className="field">從預設方案開始
            <select value={presetId} onChange={(e) => choose(e.target.value)}>
              {options.presets.map((p) => <option key={p.id} value={p.id}>{p.id}</option>)}
            </select>
          </label>}>
          <h3>產能與財務</h3>
          <div className="row">
            <label className="field">產能增加（units/day）
              <select value={plan.capacity_increase ?? 0} onChange={(e) => update({ capacity_increase: Number(e.target.value) })}>
                {options.capacity_options.map((u) => <option key={u} value={u}>{u}</option>)}
              </select>
            </label>
            <NumberField label="CD 存入" value={plan.cd?.deposit} onChange={(v) => update({ cd: { ...plan.cd, deposit: v } })} />
            <NumberField label="CD 提領" value={plan.cd?.withdraw} onChange={(v) => update({ cd: { ...plan.cd, withdraw: v } })} />
            <NumberField label="增資股數" value={plan.stock_issue?.[0]?.shares}
              onChange={(v) => update({ stock_issue: v ? [{ shares: v, price: plan.stock_issue?.[0]?.price ?? 0 }] : [] })} />
            <NumberField label="每股價格" value={plan.stock_issue?.[0]?.price} step={0.01}
              onChange={(v) => update({ stock_issue: [{ shares: plan.stock_issue?.[0]?.shares ?? 0, price: v }] })} />
          </div>
          <h3>通路</h3>
          <div className="checks">
            {options.stores.map((s) => (
              <label key={s}><input type="checkbox" checked={(plan.open_stores ?? []).includes(s)} onChange={() => toggle("open_stores", s)} />開店 {s}</label>
            ))}
            {options.web_centers.map((w) => (
              <label key={w}><input type="checkbox" checked={(plan.open_web_centers ?? []).includes(w)} onChange={() => toggle("open_web_centers", w)} />網路中心 {w}</label>
            ))}
          </div>
          <h3>品牌</h3>
          <div className="table-wrap">
            <table>
              <thead><tr><th>品牌</th><th>類型</th><th>售價</th><th>生產量</th><th>廣告</th><th /></tr></thead>
              <tbody>
                {(plan.brands ?? []).map((b, i) => (
                  <tr key={i}>
                    <td><input value={b.name} onChange={(e) => updateBrand(i, { name: e.target.value })} /></td>
                    <td><select value={b.brand_type} onChange={(e) => updateBrand(i, { brand_type: e.target.value })}>
                      {options.brand_types.map((t) => <option key={t}>{t}</option>)}</select></td>
                    <td><input type="number" value={b.price} onChange={(e) => updateBrand(i, { price: Number(e.target.value) })} /></td>
                    <td><input type="number" value={b.production} onChange={(e) => updateBrand(i, { production: Number(e.target.value) })} /></td>
                    <td><input type="number" value={b.advertising ?? 0} onChange={(e) => updateBrand(i, { advertising: Number(e.target.value) })} /></td>
                    <td><button className="btn" onClick={() => update({ brands: (plan.brands ?? []).filter((_, j) => j !== i) })}>刪除</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="row" style={{ marginTop: 10 }}>
            <button className="btn" onClick={() => update({ brands: [...(plan.brands ?? []), { name: `Brand-${(plan.brands?.length ?? 0) + 1}`,
              brand_type: options.brand_types[0] ?? "", price: 0, production: 0, advertising: 0 }] })}>新增品牌</button>
            <span style={{ flex: 1 }} />
            <button className="btn" disabled={busy} onClick={() => run("preview")}>試算（不推進）</button>
            <button className="btn primary" disabled={busy || !provider.canCompute} onClick={() => run("play")}
              title={provider.canCompute ? "" : "Demo 模式唯讀"}>送出並推進一季</button>
          </div>
          {error ? <p className="error">{error}</p> : null}
        </Card>
      ) : null}
      {options && catalog.data ? (
        <Card title="經營模組（依可信度分組）">
          <p className="muted">練習規則（heuristic）可以在這裡調；已驗證與文獻等級的杆在上面的產能、通路、品牌欄；待建的模組鎖定，點一下看原因。完整總表見「模組成熟度」。</p>
          <ModuleBoard catalog={catalog.data} decisions={plan.modules ?? {}}
            onChange={provider.canCompute ? (modules) => update({ modules: Object.keys(modules).length ? modules : undefined }) : undefined}
            brands={(plan.brands ?? []).map((b) => ({ name: b.name, advertising: b.advertising ?? 0 }))}
            carried={game.data?.state?.module_state} lines={report?.lines}
            render={(line, label, format) => <Num line={line} label={label} digits={format === "percent" ? 3 : undefined} />} />
        </Card>
      ) : null}
      {report ? (
        <Card title={`報表：Q${report.quarter} · ${report.plan}`}>
          {report.notes.length ? <ul>{report.notes.map((n) => <li key={n} className="note">{n}</li>)}</ul> : null}
          <LinesTable lines={report.lines} />
        </Card>
      ) : null}
    </>
  );
}
