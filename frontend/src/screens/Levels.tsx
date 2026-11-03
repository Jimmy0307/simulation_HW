import type { DataProvider } from "../data/provider";
import { Card, Status, useAsync } from "../ui/common";
import { LEVEL_TEXT, LevelMark, Num, UNCALIBRATED_LABEL } from "../ui/Num";

export function Levels({ provider }: { provider: DataProvider }) {
  const levels = useAsync(() => provider.levels(), [provider]);
  return (
    <>
      <Status state={levels} />
      {levels.data ? (
        <>
          <Card title="來源等級">
            <p>每個數字都帶一個來源等級，排序為 {levels.data.order.join(" > ")}。組合出來的數字取上游<b>最弱</b>的等級，絕不會標得比它的來源更強。</p>
            <div className="table-wrap"><table>
              <thead><tr><th>等級</th><th>標記</th><th>意義</th><th>範例</th></tr></thead>
              <tbody>
                {levels.data.levels.map((lv) => (
                  <tr key={lv.label}>
                    <td>{LEVEL_TEXT[lv.label].name}（{lv.label}）</td>
                    <td><LevelMark level={lv.label} /></td>
                    <td style={{ whiteSpace: "normal", textAlign: "left" }}>{lv.meaning}</td>
                    <td><Num line={{ value: 12345.6, level: lv.label, source: "example", uncalibrated: lv.uncalibrated }} label="範例" /></td>
                  </tr>
                ))}
              </tbody>
            </table></div>
          </Card>
          <Card title={`「${UNCALIBRATED_LABEL}」標記`}>
            <p>只要上游含 <b>literature</b> 或 <b>placeholder</b>，數字旁就會出現斜紋的「{UNCALIBRATED_LABEL}」標記，數字本身也會加上點狀底線。滑鼠移到數字上（或用 Tab 鍵聚焦）會顯示：</p>
            <ul>
              <li>產生這個數字的規則；</li>
              <li>完整的來源鏈：從這個項目一路往上游，每一步都有等級、公式與證據位置。</li>
            </ul>
            <p><b>為什麼現在的銷量、市佔、營收不能當預測？</b></p>
            <ul>
              <li>需求面目前是 literature 等級：函數形式來自公開的行銷與經濟學文獻，係數是文獻中間值或標註的預設值，沒有用本局資料校準過。</li>
              <li>利潤與現金還受 placeholder 成本規則影響。</li>
              <li>它們適合用來比較方案之間的「方向」與「敏感度」，不適合當成本局的預測值。</li>
              <li>等需求面板累積足夠資料、通過留出季驗證後，需求才會升為 estimated。</li>
            </ul>
          </Card>
          <Card title="指標登錄（每個報表項目的公式、等級與上游）">
            <div className="table-wrap"><table>
              <thead><tr><th>指標</th><th>等級</th><th>公式</th><th>上游</th><th>證據</th></tr></thead>
              <tbody>
                {levels.data.metrics.map((m) => (
                  <tr key={m.metric}>
                    <td className="mono">{m.metric}</td><td><LevelMark level={m.level} /> {m.level}</td>
                    <td style={{ whiteSpace: "normal", textAlign: "left" }}>{m.formula}</td>
                    <td className="mono" style={{ whiteSpace: "normal", textAlign: "left" }}>{m.inputs.join(", ") || "—"}</td>
                    <td className="note" style={{ whiteSpace: "normal", textAlign: "left" }}>{m.evidence}</td>
                  </tr>
                ))}
              </tbody>
            </table></div>
          </Card>
        </>
      ) : null}
    </>
  );
}
