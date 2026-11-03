import { useEffect, useState } from "react";
import type { DataProvider } from "../data/provider";
import type { DiffDoc } from "../types";
import { Banner, Card, Status, plain, useAsync } from "../ui/common";
import { LevelMark } from "../ui/Num";

export function Diff({ provider }: { provider: DataProvider }) {
  const packs = useAsync(() => provider.packs(), [provider]);
  const [oldId, setOldId] = useState("");
  const [newId, setNewId] = useState("");
  const [doc, setDoc] = useState<DiffDoc | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (packs.data && packs.data.length >= 2 && !oldId) {
      setOldId(packs.data[packs.data.length - 2].id);
      setNewId(packs.data[packs.data.length - 1].id);
    }
  }, [packs.data, oldId]);

  const run = async () => {
    setError(null);
    try {
      setDoc(await provider.diff(oldId, newId));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };
  useEffect(() => {
    if (oldId && newId && !doc) void run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [oldId, newId]);

  return (
    <>
      <Status state={packs} />
      {packs.data ? (
        <Card title="參數包差異" actions={
          <div className="row">
            <label className="field">舊<select value={oldId} onChange={(e) => { setOldId(e.target.value); setDoc(null); }}>
              {packs.data.map((p) => <option key={p.id}>{p.id}</option>)}</select></label>
            <label className="field">新<select value={newId} onChange={(e) => { setNewId(e.target.value); setDoc(null); }}>
              {packs.data.map((p) => <option key={p.id}>{p.id}</option>)}</select></label>
            <button className="btn primary" onClick={run}>比較</button>
          </div>}>
          <p className="note">紅底 = 已驗證（verified）模組的參數變了，需要重新校準。真實參數包之間的比較不顯示數值，只顯示變動比例。</p>
          {error ? <p className="error">{error}</p> : null}
        </Card>
      ) : null}
      {doc ? (
        <>
          {doc.red_flags.length ? (
            <Banner kind="danger" title="紅旗"><ul style={{ margin: 0 }}>{doc.red_flags.map((f) => <li key={f}>{f}</li>)}</ul></Banner>
          ) : <Banner kind="info">沒有紅旗。</Banner>}
          <Card title={`${doc.old} → ${doc.new}：${doc.changes.length} 項變動`}>
            <div className="table-wrap">
              <table>
                <thead><tr><th>路徑</th><th>類型</th><th>模組</th><th>模組等級</th><th>變動</th>{doc.values_included ? <><th>舊</th><th>新</th></> : null}</tr></thead>
                <tbody>
                  {doc.changes.map((c) => (
                    <tr key={c.path} className={c.needs_reverification ? "reverify" : ""}>
                      <td className="mono">{c.path}</td><td>{c.kind}</td><td>{c.module}</td>
                      <td><LevelMark level={c.module_level} /> {c.module_level}{c.needs_reverification ? " · 需重新驗證" : ""}</td>
                      <td>{c.relative === null ? "—" : `${(c.relative * 100).toFixed(1)}%`}</td>
                      {doc.values_included ? <><td>{plain(c.old)}</td><td>{plain(c.new)}</td></> : null}
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
