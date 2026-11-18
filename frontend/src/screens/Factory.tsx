import { useEffect, useState } from "react";
import type { DataProvider } from "../data/provider";
import type { FactoryOrder, FactoryResult } from "../types";
import { BarChart } from "../ui/Chart";
import { Banner, Card, Status, useAsync } from "../ui/common";
import { formatNumber, UNCALIBRATED_LABEL } from "../ui/Num";

export const FACTORY_BANNER =
  "需求高低是你設定的情境（預測的倍數），不是預測。材料與人工、管銷來自遊戲的生產成本表（estimated）；加班加給、調整產能費用與缺貨對下季需求的折損是練習規則（heuristic）。";

const list = (text: string, scale = 1): number[] =>
  text.split(",").map((x) => Number(x.trim()) / scale).filter((x) => Number.isFinite(x));
const show = (values: number[], scale = 1): string => values.map((v) => formatNumber(v * scale, 0)).join(", ");
const label = (oc: number, ot: number) => `${formatNumber(oc, 0)}/天 + ${formatNumber(ot, 0)}h 加班`;

/** Production scheduler: the orders Marketing and Sales entered -> operating capacity x overtime x demand outcome. */
export function Factory({ provider }: { provider: DataProvider }) {
  const setup = useAsync(() => provider.factorySetup(), [provider]);
  const [fileId, setFileId] = useState("");
  const [orders, setOrders] = useState<FactoryOrder[]>([]);
  const [oc, setOc] = useState("");
  const [ot, setOt] = useState("");
  const [demand, setDemand] = useState("");
  const [weights, setWeights] = useState("");
  const [reading, setReading] = useState<"factory" | "brand">("factory");
  const [result, setResult] = useState<FactoryResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const s = setup.data;
    if (!s || oc) return;
    setOc(show(s.defaults.operating_capacities));
    setOt(show(s.defaults.overtime_hours));
    setDemand(show(s.defaults.demand_factors, 100));
    setWeights(show(s.defaults.weights, 100));
    setReading(s.defaults.reading);
    if (s.orders_files.length) {
      setFileId(s.orders_files[0].id);
      setOrders(s.orders_files[0].orders);
    } else {
      setOrders(s.brands.map((b) => ({ ...b, price: 0, forecast: 0 })));
    }
  }, [setup.data, oc]);

  const pickFile = (id: string) => {
    setFileId(id);
    const file = setup.data?.orders_files.find((f) => f.id === id);
    if (file) setOrders(file.orders);
    setResult(null);
  };
  const edit = (i: number, key: "price" | "forecast", value: number) =>
    setOrders((rows) => rows.map((r, j) => (j === i ? { ...r, [key]: value } : r)));

  const runSweep = async () => {
    setBusy(true);
    setError(null);
    try {
      setResult(await provider.factoryRun({
        orders, operating_capacities: list(oc), overtime_hours: list(ot), demand_factors: list(demand, 100),
        weights: list(weights, 100), reading,
      }));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const best = result?.ranking[0];
  const bestRows = result && best ? result.rows.filter((r) =>
    r.operating_capacity === best.operating_capacity && r.max_overtime_hours === best.max_overtime_hours) : [];
  return (
    <>
      <Banner kind="warn" title={UNCALIBRATED_LABEL}>{FACTORY_BANNER}</Banner>
      <Status state={setup} />
      {setup.data && !setup.data.has_cost_table ? (
        <Banner kind="danger" title="這個參數包沒有生產成本表">
          用擷取到的 CostOfProduction 畫面重建私有參數包（mpsim build-pack），或改用 synthetic-factory 示範包。
        </Banner>
      ) : null}
      {setup.data ? (
        <Card title="工廠收到的訂單（行銷與業務的決策）" actions={
          setup.data.orders_files.length ? (
            <label className="field">訂單檔
              <select value={fileId} onChange={(e) => pickFile(e.target.value)}>
                {setup.data.orders_files.map((f) => <option key={f.id} value={f.id}>{f.id}</option>)}
              </select>
            </label>) : null}>
          <p className="note">訂單檔來自 <span className="mono">mpsim intake</span>（讀取隊友在遊戲裡填好的決策）。固定產能 {formatNumber(setup.data.fixed_capacity, 0)} 台/天，工人生產力 {formatNumber(setup.data.productivity, 0)}%。</p>
          <div className="table-wrap">
            <table>
              <thead><tr><th>品牌</th><th>類型</th><th>售價</th><th>預測（台）</th></tr></thead>
              <tbody>
                {orders.map((o, i) => (
                  <tr key={o.name}>
                    <td>{o.name}</td><td>{o.brand_type}</td>
                    <td><input type="number" aria-label={`${o.name} 售價`} value={o.price} onChange={(e) => edit(i, "price", Number(e.target.value))} /></td>
                    <td><input type="number" aria-label={`${o.name} 預測`} value={o.forecast} onChange={(e) => edit(i, "forecast", Number(e.target.value))} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="row">
            <label className="field">營運產能（台/天）<input value={oc} onChange={(e) => setOc(e.target.value)} /></label>
            <label className="field">加班上限（小時）<input value={ot} onChange={(e) => setOt(e.target.value)} /></label>
            <label className="field">需求情境（預測 %）<input value={demand} onChange={(e) => setDemand(e.target.value)} /></label>
            <label className="field">各情境機率（%）<input value={weights} onChange={(e) => setWeights(e.target.value)} /></label>
            <label className="field">成本表讀法
              <select value={reading} onChange={(e) => setReading(e.target.value as "factory" | "brand")}>
                <option value="factory">全廠總產量</option>
                <option value="brand">各品牌自己的產量</option>
              </select>
            </label>
            <button className="btn primary" disabled={busy || !setup.data.has_cost_table} onClick={runSweep}>
              {provider.canCompute ? "排程試算" : "讀取預算結果"}
            </button>
          </div>
          {error ? <p className="error">{error}</p> : null}
        </Card>
      ) : null}
      {result && best ? (
        <>
          {result.is_private ? <Banner kind="danger" title="真實資料">此結果使用私有參數包，只在本機顯示。</Banner> : null}
          <Card title={`建議排程：${label(best.operating_capacity, best.max_overtime_hours)}`}>
            <p data-testid="factory-recommendation">
              預測 {formatNumber(result.forecast, 0)} 台；說明檔公式需要 {formatNumber(result.required_operating_capacity, 1)} 台/天
              （+25% 緩衝 {formatNumber(result.required_with_buffer, 1)}）。依你給的情境機率，這個排程的期望值最高：
              {" "}<b>{formatNumber(best.expected_value, 0)}</b>（營收減生產成本，扣掉缺貨對下季需求的折損）；
              最差情境 {formatNumber(best.worst_contribution, 0)}，最多缺貨 {formatNumber(best.max_lost, 0)} 台。
            </p>
            <ul className="note">
              {Object.entries(result.levels).map(([k, v]) => <li key={k}>{k}：{v}</li>)}
            </ul>
          </Card>
          <div className="grid cols-2">
            <Card title="各排程的期望值">
              <BarChart title="expected value by schedule" items={result.ranking.slice(0, 10).map((r) =>
                ({ label: label(r.operating_capacity, r.max_overtime_hours), value: r.expected_value }))} />
            </Card>
            <Card title={`建議排程在各需求情境下`}>
              <div className="table-wrap">
                <table>
                  <thead><tr><th>需求</th><th>做出</th><th>缺貨</th><th>閒置</th><th>加班 h/天</th><th>每台成本</th><th>營收－生產成本</th><th>下季需求折損</th></tr></thead>
                  <tbody>
                    {bestRows.map((r) => (
                      <tr key={r.demand_factor} className={r.lost > 0 ? "worst" : ""}>
                        <td>{formatNumber(r.demand_factor * 100, 0)}%（{formatNumber(r.demand, 0)}）</td>
                        <td>{formatNumber(r.produced, 0)}</td><td>{formatNumber(r.lost, 0)}</td><td>{formatNumber(r.idle_units, 0)}</td>
                        <td>{formatNumber(r.overtime_hours_used, 1)}</td><td>{formatNumber(r.unit_cost, 0)}</td>
                        <td>{formatNumber(r.contribution, 0)}</td><td>{formatNumber(r.next_quarter_demand_cut * 100, 1)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>
        </>
      ) : null}
    </>
  );
}
