import type { DataProvider } from "../data/provider";
import type { GameDoc } from "../types";
import { LineChart, weakest } from "../ui/Chart";
import { Banner, Card, LinesTable, Status, useAsync } from "../ui/common";
import { formatNumber, Num } from "../ui/Num";

const TREND = ["cash_end", "revenue", "net_income"] as const;
const TREND_NAMES: Record<string, string> = { cash_end: "期末現金", revenue: "營收", net_income: "淨利" };

export function Overview({ provider, onGame }: { provider: DataProvider; onGame?: (g: GameDoc) => void }) {
  const game = useAsync(() => provider.game().then((g) => { onGame?.(g); return g; }), [provider]);
  const doc = game.data;
  const last = doc?.history[doc.history.length - 1];
  return (
    <>
      <Status state={game} />
      {doc ? (
        <>
          <Banner kind={doc.is_private ? "danger" : "info"} title={doc.is_private ? "真實資料" : "虛構資料"}>
            {doc.is_private
              ? "目前載入的是私有參數包。畫面上的數字只存在於這台電腦，請勿截圖、分享或匯出到公開位置。"
              : "目前是 synthetic（虛構）參數包，所有數字都是編造的示範值，與任何真實遊戲無關。"}
          </Banner>
          <div className="grid cols-4">
            <Card><div className="stat"><div className="label">目前季度</div><div className="value">Q{doc.state?.quarter ?? "—"}</div></div></Card>
            <Card><div className="stat"><div className="label">現金（含來源等級）</div><div className="value">
              {doc.state ? <Num line={{ value: doc.state.cash.value, level: doc.state.cash.level, source: "carried state (cash_end of last quarter)",
                uncalibrated: doc.state.cash.uncalibrated }} label="cash" /> : "—"}</div></div></Card>
            <Card><div className="stat"><div className="label">固定產能（units/day）</div><div className="value">{formatNumber(doc.state?.fixed_capacity_units ?? 0)}</div></div></Card>
            <Card><div className="stat"><div className="label">通路</div><div className="value" style={{ fontSize: 16 }}>
              店面 {doc.state?.stores_open.length ?? 0} · 網路中心 {doc.state?.web_centers_open.length ?? 0}</div></div></Card>
          </div>
          <Card title="逐季趨勢">
            {doc.history.length ? (
              <LineChart title="期末現金 / 營收 / 淨利" quarters={doc.history.map((h) => h.quarter)}
                series={TREND.map((key) => ({
                  name: TREND_NAMES[key],
                  values: doc.history.map((h) => h.lines[key]?.value ?? null),
                  level: weakest(doc.history.flatMap((h) => (h.lines[key] ? [h.lines[key].level] : []))),
                }))} />
            ) : <p className="muted">尚未推進任何一季。到「決策編輯」送出第一季決策。</p>}
            <p className="note">虛線 = 上游含 literature 或 placeholder，未校準、不可當預測。</p>
          </Card>
          {last ? (
            <Card title={`最近一季報表：Q${last.quarter} · 方案 ${last.plan}`}>
              {last.notes.length ? <ul>{last.notes.map((n) => <li key={n} className="note">{n}</li>)}</ul> : null}
              <LinesTable lines={last.lines} />
            </Card>
          ) : null}
        </>
      ) : null}
    </>
  );
}
