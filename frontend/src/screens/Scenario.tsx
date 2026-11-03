import { useEffect, useState } from "react";
import type { DataProvider } from "../data/provider";
import type { ScenarioRun, ScenarioSpecDoc } from "../types";
import { LineChart, weakest } from "../ui/Chart";
import { Banner, Card, Status, ValueCell, lineLabel, plain, useAsync } from "../ui/common";

type Row = Record<string, unknown>;
const clone = <T,>(v: T): T => JSON.parse(JSON.stringify(v)) as T;
const KEY_LINES = ["cash_end", "revenue", "net_income", "market_share", "capex_capacity", "production_cost"];

function RowEditor({ rows, fields, onChange, addLabel, template }: {
  rows: Row[]; fields: { key: string; label: string; type?: "number" | "text"; options?: string[] }[];
  onChange: (rows: Row[]) => void; addLabel: string; template: Row;
}) {
  const set = (i: number, key: string, value: unknown) => onChange(rows.map((r, j) => (j === i ? { ...r, [key]: value } : r)));
  return (
    <>
      {rows.map((row, i) => (
        <div className="row" key={i} style={{ marginBottom: 6 }}>
          {fields.map((f) => (
            <label className="field" key={f.key}>{f.label}
              {f.options ? (
                <select value={String(row[f.key] ?? "")} onChange={(e) => set(i, f.key, e.target.value)}>
                  {f.options.map((o) => <option key={o}>{o}</option>)}
                </select>
              ) : (
                <input type={f.type ?? "text"} value={row[f.key] === undefined ? "" : String(row[f.key])}
                  onChange={(e) => set(i, f.key, f.type === "number" ? (e.target.value === "" ? undefined : Number(e.target.value)) : e.target.value)} />
              )}
            </label>
          ))}
          <button className="btn" onClick={() => onChange(rows.filter((_, j) => j !== i))}>刪除</button>
        </div>
      ))}
      <button className="btn" onClick={() => onChange([...rows, clone(template)])}>{addLabel}</button>
    </>
  );
}

export function Scenario({ provider }: { provider: DataProvider }) {
  const templates = useAsync(() => provider.scenarioTemplates(), [provider]);
  const events = useAsync(() => provider.events(), [provider]);
  const [templateId, setTemplateId] = useState("");
  const [spec, setSpec] = useState<ScenarioSpecDoc | null>(null);
  const [run, setRun] = useState<ScenarioRun | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (templates.data?.length && !templateId) {
      setTemplateId(templates.data[0].id);
      setSpec(clone(templates.data[0].spec));
    }
  }, [templates.data, templateId]);

  const pick = (id: string) => {
    const t = templates.data?.find((x) => x.id === id);
    setTemplateId(id);
    if (t) setSpec(clone(t.spec));
    setRun(null);
    setError(null);
  };
  const execute = async () => {
    if (!spec) return;
    setError(null);
    try {
      setRun(await provider.runScenario(spec, templateId));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };
  const eventTypes = events.data?.map((e) => e.type) ?? [];
  const result = run?.result;
  return (
    <>
      <Status state={templates} />
      {!provider.canCompute ? <Banner kind="info" title="Demo 唯讀">可以檢視五個 synthetic 範本的預先結果；編輯後的情境需要實戰模式。</Banner> : null}
      {spec ? (
        <Card title="情境工作台" actions={
          <label className="field">範本
            <select value={templateId} onChange={(e) => pick(e.target.value)}>
              {templates.data?.map((t) => <option key={t.id} value={t.id}>{t.id}</option>)}
            </select>
          </label>}>
          <p className="muted">{spec.description}</p>
          <div className="row">
            <label className="field">季數<input type="number" value={spec.horizon ?? 4} onChange={(e) => setSpec({ ...spec, horizon: Number(e.target.value) })} /></label>
            <label className="field">起始季<input type="number" value={spec.start_quarter ?? 1} onChange={(e) => setSpec({ ...spec, start_quarter: Number(e.target.value) })} /></label>
            <label className="field">seed<input type="number" value={spec.seed ?? 0} onChange={(e) => setSpec({ ...spec, seed: Number(e.target.value) })} /></label>
          </div>
          <h3>參數覆寫</h3>
          <RowEditor rows={(spec.overrides ?? []) as Row[]} onChange={(rows) => setSpec({ ...spec, overrides: rows })} addLabel="新增覆寫"
            template={{ path: "capacity_options[*].cost", scale: 1.1, from_quarter: 2 }}
            fields={[{ key: "path", label: "路徑" }, { key: "scale", label: "scale ×", type: "number" }, { key: "add", label: "add +", type: "number" },
              { key: "set", label: "set =", type: "number" }, { key: "from_quarter", label: "起季", type: "number" }, { key: "to_quarter", label: "迄季", type: "number" }]} />
          <h3>事件（每季推進前套用，可疊加）</h3>
          <RowEditor rows={(spec.events ?? []) as Row[]} onChange={(rows) => setSpec({ ...spec, events: rows })} addLabel="新增事件"
            template={{ type: eventTypes[0] ?? "cost_shock", from_quarter: 2, target: "*", magnitude: 0.1, duration: 1 }}
            fields={[{ key: "type", label: "類型", options: eventTypes }, { key: "target", label: "目標" }, { key: "magnitude", label: "幅度", type: "number" },
              { key: "from_quarter", label: "起季", type: "number" }, { key: "duration", label: "持續季數", type: "number" }, { key: "label", label: "標籤" }]} />
          {events.data ? <p className="note">{events.data.map((e) => `${e.type}: ${e.effect}`).join("　·　")}</p> : null}
          <h3>對手</h3>
          <RowEditor rows={(spec.competitors ?? []) as Row[]} onChange={(rows) => setSpec({ ...spec, competitors: rows as ScenarioSpecDoc["competitors"] })}
            addLabel="新增對手" template={{ name: "rival-x", strategy: "baseline" }}
            fields={[{ key: "name", label: "名稱" }, { key: "strategy", label: "策略", options: ["baseline", "random", "replay"] }]} />
          <div className="row" style={{ marginTop: 12 }}>
            <button className="btn primary" onClick={execute}>執行情境</button>
            {error ? <span className="error">{error}</span> : null}
          </div>
        </Card>
      ) : null}
      {result ? (
        <>
          {run?.is_private ? <Banner kind="danger" title="真實資料">此情境使用私有參數包，結果只在本機顯示。</Banner> : null}
          <Card title={`結果：${result.name}`} actions={<span className="pill mono">fingerprint {result.fingerprint} · seed {result.seed}</span>}>
            <LineChart title="期末現金 / 淨利（⚑ = 事件）" quarters={result.quarters.map((q) => q.quarter)} events={result.quarters.map((q) => q.events)}
              series={["cash_end", "net_income"].map((key) => ({
                name: lineLabel(key), values: result.quarters.map((q) => q.lines[key]?.value ?? null),
                level: weakest(result.quarters.flatMap((q) => (q.lines[key] ? [q.lines[key].level] : []))),
              }))} />
            <div className="table-wrap">
              <table>
                <thead><tr><th>項目</th>{result.quarters.map((q) => <th key={q.quarter}>Q{q.quarter}{q.events.length ? " ⚑" : ""}</th>)}</tr></thead>
                <tbody>
                  <tr><td>事件</td>{result.quarters.map((q) => <td key={q.quarter} style={{ whiteSpace: "normal", maxWidth: 220 }} className="note">{q.events.join("；") || "—"}</td>)}</tr>
                  <tr><td>方案</td>{result.quarters.map((q) => <td key={q.quarter} className="mono">{q.plan}</td>)}</tr>
                  {KEY_LINES.map((key) => (
                    <tr key={key}><td>{lineLabel(key)}</td>{result.quarters.map((q) => <td key={q.quarter}><ValueCell line={q.lines[key]} label={key} /></td>)}</tr>
                  ))}
                </tbody>
              </table>
            </div>
            <h3>摘要</h3>
            <div className="table-wrap"><table><tbody>
              {Object.entries(result.summary).map(([k, v]) => <tr key={k}><td>{k}</td><td>{plain(v)}</td></tr>)}
            </tbody></table></div>
          </Card>
        </>
      ) : null}
    </>
  );
}
