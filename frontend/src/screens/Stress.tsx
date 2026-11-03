import { useEffect, useState } from "react";
import type { DataProvider } from "../data/provider";
import type { SweepResult } from "../types";
import { BarChart } from "../ui/Chart";
import { Banner, Card, Status, plain, useAsync } from "../ui/common";
import { formatNumber, UNCALIBRATED_LABEL } from "../ui/Num";

export const DEMAND_BANNER =
  "需求尚未升為 estimated：壓力測試的結果（包括「最差情境」）反映的是 literature 需求假設（公開文獻的函數形式、未校準的係數），不是本局預測。";

export function Stress({ provider }: { provider: DataProvider }) {
  const files = useAsync(() => provider.sweepFiles(), [provider]);
  const [id, setId] = useState("");
  const [result, setResult] = useState<SweepResult | null>(null);
  const [top, setTop] = useState(5);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (files.data?.length && !id) setId(files.data[0].id);
  }, [files.data, id]);

  const run = async () => {
    const file = files.data?.find((f) => f.id === id);
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      setResult(await provider.runSweep(file.sweep, file.id));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const worstIds = new Set(
    (result?.rows ?? []).filter((r) => r.objective !== null).sort((a, b) => (a.objective ?? 0) - (b.objective ?? 0)).slice(0, top).map((r) => r.id));
  const variables = result ? Object.keys(result.rows[0]?.assignment ?? {}) : [];
  const showBanner = !result || result.demand_level !== "estimated";
  return (
    <>
      {showBanner ? <Banner kind="warn" title={UNCALIBRATED_LABEL}>{DEMAND_BANNER}</Banner> : null}
      <Status state={files} />
      {files.data ? (
        <Card title="壓力測試（sweep）" actions={
          <div className="row">
            <label className="field">sweep 定義
              <select value={id} onChange={(e) => { setId(e.target.value); setResult(null); }}>
                {files.data.map((f) => <option key={f.id} value={f.id}>{f.id}</option>)}
              </select>
            </label>
            <label className="field">最差 N<input type="number" min={1} value={top} onChange={(e) => setTop(Math.max(1, Number(e.target.value)))} /></label>
            <button className="btn primary" disabled={busy} onClick={run}>{provider.canCompute ? "執行" : "讀取預算結果"}</button>
          </div>}>
          <p className="note">每一列是一個情境組合，由本機引擎計算。紅底 = 目標值最差的 N 個情境。</p>
          {error ? <p className="error">{error}</p> : null}
        </Card>
      ) : null}
      {result ? (
        <>
          {result.caveat ? <Banner kind="warn" title="sweep 註記">{result.caveat}</Banner> : null}
          {result.is_private ? <Banner kind="danger" title="真實資料">此 sweep 使用私有參數包，結果只在本機顯示。</Banner> : null}
          <div className="grid cols-2">
            <Card title={`敏感度：各變數對 ${result.objective} 的主效果範圍`}>
              <BarChart title="main effect range" items={result.sensitivity.map((s) => ({ label: s.variable, value: s.main_effect_range ?? 0 }))} />
              <p className="note">需求等級：{result.demand_level}。數值越大，表示這個變數改變時目標值變動越多。</p>
            </Card>
            <Card title={`最差 ${top} 個情境（${result.objective}，越低越差）`}>
              <ol>
                {result.rows.filter((r) => worstIds.has(r.id)).sort((a, b) => (a.objective ?? 0) - (b.objective ?? 0)).map((r) => (
                  <li key={r.id}><b>{formatNumber(r.objective ?? NaN, 0)}</b> <span className="mono">{r.id}</span>{" "}
                    <span className="note">{Object.entries(r.assignment).map(([k, v]) => `${k}=${plain(v)}`).join(", ")}</span></li>
                ))}
              </ol>
            </Card>
          </div>
          <Card title={`全部 ${result.rows.length} 個情境`}>
            <div className="table-wrap">
              <table>
                <thead><tr><th>id</th><th>{result.objective}</th>{variables.map((v) => <th key={v}>{v}</th>)}<th>fingerprint</th></tr></thead>
                <tbody>
                  {result.rows.map((r) => (
                    <tr key={r.id} className={worstIds.has(r.id) ? "worst" : ""}>
                      <td className="mono">{r.id}</td><td>{plain(r.objective)}</td>
                      {variables.map((v) => <td key={v}>{plain(r.assignment[v])}</td>)}
                      <td className="mono">{r.fingerprint}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      ) : null}
    </>
  );
}
