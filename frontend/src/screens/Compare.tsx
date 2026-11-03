import { useState } from "react";
import type { DataProvider } from "../data/provider";
import type { CompareDoc } from "../types";
import { Card, Status, ValueCell, lineLabel, useAsync } from "../ui/common";

export function Compare({ provider }: { provider: DataProvider }) {
  const plans = useAsync(() => provider.plans(), [provider]);
  const [selected, setSelected] = useState<string[] | null>(null);
  const [doc, setDoc] = useState<CompareDoc | null>(null);
  const [error, setError] = useState<string | null>(null);
  const ids = selected ?? plans.data?.presets.map((p) => p.id) ?? [];

  const run = async () => {
    if (!plans.data) return;
    setError(null);
    try {
      const chosen = plans.data.presets.filter((p) => ids.includes(p.id));
      setDoc(await provider.compare(chosen.map((p) => p.plan), chosen.map((p) => p.id)));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const keys = doc ? [...new Set(doc.reports.flatMap((r) => Object.keys(r.lines)))] : [];
  return (
    <>
      <Status state={plans} />
      {plans.data ? (
        <Card title="選擇要並排的方案" actions={<button className="btn primary" onClick={run} disabled={ids.length < 2}>比較</button>}>
          <div className="checks">
            {plans.data.presets.map((p) => (
              <label key={p.id}><input type="checkbox" checked={ids.includes(p.id)}
                onChange={() => setSelected(ids.includes(p.id) ? ids.filter((i) => i !== p.id) : [...ids, p.id])} />{p.id}</label>
            ))}
          </div>
          <p className="note">從同一個公司狀態出發（Q{plans.data.quarter ?? "?"}）。與第一個方案不同的格子以左側色條標示；整列有差異者底色加深。</p>
          {error ? <p className="error">{error}</p> : null}
        </Card>
      ) : null}
      {doc ? (
        <Card title={`方案比較 · Q${doc.quarter}`}>
          <div className="table-wrap">
            <table>
              <thead><tr><th>項目</th>{doc.reports.map((r) => <th key={r.plan}>{r.plan}</th>)}</tr></thead>
              <tbody>
                {keys.map((key) => {
                  const base = doc.reports[0].lines[key]?.value;
                  const differs = doc.reports.some((r) => r.lines[key]?.value !== base);
                  return (
                    <tr key={key} className={differs ? "diff-row" : ""}>
                      <td>{lineLabel(key)} <span className="muted mono">{key}</span></td>
                      {doc.reports.map((r, i) => (
                        <td key={r.plan} className={i > 0 && r.lines[key]?.value !== base ? "changed" : ""}>
                          <ValueCell line={r.lines[key]} label={`${key} · ${r.plan}`} />
                        </td>
                      ))}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      ) : null}
    </>
  );
}
