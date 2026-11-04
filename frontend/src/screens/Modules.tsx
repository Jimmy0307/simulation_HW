import { useState } from "react";
import type { DataProvider } from "../data/provider";
import type { LedgerRow, Maturity, ModulesDoc } from "../types";
import { Card, Status, useAsync } from "../ui/common";
import { captureLabel, MATURITY_ORDER, MATURITY_TEXT, MaturityPill, PracticeBadge } from "../ui/Practice";

// "How far from the top": the modeling ledger (data/modeling_ledger.json) as a picture. Structure and maturity only;
// the counts are counts of ledger rows, not model results.

const REAL_TEXT = { measured: "實測", inferred: "推斷 · 未證實", unknown: "未知" } as const;
const KIND_TEXT: Record<LedgerRow["kind"], string> = {
  behaviour: "行為（因果反應）", accounting: "會計規則", information: "資訊", qualitative: "文字 / 規劃", scenario: "情境假設",
};

type Filter = Maturity | "all" | "gap";

function Bar({ counts, label, testId }: { counts: Record<Maturity, number>; label: string; testId?: string }) {
  return (
    <div className="ladder-row" data-testid={testId}>
      <span className="ladder-label">{label}</span>
      <div className="ladder-bar" role="img" aria-label={`${label}：${MATURITY_ORDER.map((m) => `${MATURITY_TEXT[m].name} ${counts[m] ?? 0} 個`).join("，")}`}>
        {MATURITY_ORDER.map((m) => (
          <span key={m} className={`ladder-seg m-${m}`} style={{ flexGrow: counts[m] || 0 }} title={`${MATURITY_TEXT[m].name}：${counts[m] ?? 0} 個`} />
        ))}
      </div>
    </div>
  );
}

function delta(now: number, before: number | undefined): string {
  if (before === undefined || now === before) return "±0";
  return now > before ? `+${now - before}` : `${now - before}`;
}

function Ladder({ doc }: { doc: ModulesDoc }) {
  const total = doc.modules.length;
  const previous = doc.history.at(-1);
  return (
    <figure className="ladder" aria-label="各成熟度的模組數">
      {previous ? <Bar counts={previous.counts} label={previous.label} testId="ladder-previous" /> : null}
      <Bar counts={doc.counts} label="現在" testId="ladder-now" />
      <figcaption className="ladder-legend">
        {MATURITY_ORDER.map((m) => (
          <span key={m} data-testid={`count-${m}`}><i className={`key m-${m}`} aria-hidden="true" />{MATURITY_TEXT[m].name} <b>{doc.counts[m]}</b>
            <small className="muted"> / {total}</small>
            {previous ? <small className={`ladder-delta${(doc.counts[m] ?? 0) !== (previous.counts[m] ?? 0) ? " moved" : ""}`} data-testid={`delta-${m}`}>
              {delta(doc.counts[m] ?? 0, previous.counts[m])}</small> : null}
          </span>
        ))}
      </figcaption>
      {previous ? (
        <p className="muted ladder-note">和「{previous.label}」（{previous.total} 列）相比{previous.total !== total ? `；總表現在是 ${total} 列（有模組拆成更細的列或新增列）` : ""}。</p>
      ) : null}
    </figure>
  );
}

function Detail({ row, doc, onClose }: { row: LedgerRow; doc: ModulesDoc; onClose: () => void }) {
  return (
    <aside className="ledger-detail" aria-label={`${row.name}：詳細`} data-testid="ledger-detail">
      <header className="sheet-head">
        <h2>{row.name}</h2>
        <button type="button" className="icon-btn" aria-label="關閉" onClick={onClose}>×</button>
      </header>
      <p className="ledger-tags"><MaturityPill maturity={row.maturity} />{row.maturity === "heuristic" && row.kind === "behaviour" ? <PracticeBadge /> : null}
        <code>{row.key}</code><span className="muted">{KIND_TEXT[row.kind]}</span></p>
      <dl className="ledger-fields">
        <dt>真實遊戲</dt><dd><b>{REAL_TEXT[row.real_status]}</b>。{row.real_note}</dd>
        <dt>對應畫面</dt><dd>{row.screens.length ? row.screens.map((s) => <code key={s}>{s}</code>) : "（沒有找到對應畫面）"}</dd>
        <dt>我們現在</dt><dd>{row.ours}{row.implementation ? <> · <code>{row.implementation}</code></> : null}</dd>
        {row.ranges && Object.keys(row.ranges).length ? (
          <><dt>文獻範圍</dt><dd data-testid="ledger-ranges">{Object.entries(row.ranges).map(([k, [lo, hi]]) => <code key={k}>{k} ∈ [{lo}, {hi}]</code>)}</dd></>
        ) : null}
        <dt>升級下一步</dt><dd>{row.next_step}</dd>
        <dt>何時可擷取</dt><dd>{captureLabel(row.capture)}<small className="muted"> · {row.capture}</small></dd>
        <dt>可以調嗎</dt><dd>{row.decidable ? "可以：在決策編輯或遊戲模式的「經營模組」" : row.maturity === "not-modeled" ? "不行：鎖定，引擎會拒絕這類決策" : "不在這裡：見決策編輯與遊戲畫面"}</dd>
      </dl>
      <h3 className="sheet-sub">來源</h3>
      <ul className="ledger-sources">{row.sources.map((s) => <li key={s}><b>{s}</b> {doc.sources[s]}</li>)}</ul>
    </aside>
  );
}

/** The maturity overview: one tile per business module, coloured by maturity, grouped by area. */
export function Modules({ provider }: { provider: DataProvider }) {
  const state = useAsync(() => provider.modules(), [provider]);
  const [filter, setFilter] = useState<Filter>("all");
  const [open, setOpen] = useState<string | null>(null);
  const doc = state.data;
  if (!doc) return <Status state={state} />;
  const gap = doc.modules.filter((r) => r.maturity === "not-modeled" && r.real_status !== "unknown");
  const keep = (r: LedgerRow) => filter === "all" || (filter === "gap" ? gap.includes(r) : r.maturity === filter);
  const selected = doc.modules.find((r) => r.key === open) ?? null;
  return (
    <>
      <Card title="離完整的企業經營模擬還差多少">
        <p className="muted">每個方塊是一個經營模組（共 {doc.modules.length} 個），顏色是它現在多可信。只有結構與等級，沒有任何遊戲數值。
          推斷的真實遊戲範圍一律「未證實 · 待擷取」。</p>
        <Ladder doc={doc} />
        <p className="ledger-gap" data-testid="ledger-gap">真實遊戲有（實測或推斷）、我們完全還沒做：<b>{gap.length}</b> 個。
          可以調的模組：{doc.modules.filter((r) => r.decidable).map((r) => r.name).join("、") || "（無）"}；
          練習規則（heuristic）共 <b>{doc.counts.heuristic}</b> 列。</p>
      </Card>
      <div className="ledger-filters" role="group" aria-label="篩選">
        {(["all", ...MATURITY_ORDER, "gap"] as Filter[]).map((f) => (
          <button key={f} type="button" className={`chip${filter === f ? " on" : ""}`} aria-pressed={filter === f} onClick={() => setFilter(f)}>
            {f === "all" ? "全部" : f === "gap" ? "遊戲有、我們沒做" : MATURITY_TEXT[f].name}
          </button>
        ))}
      </div>
      <div className={`ledger-layout${selected ? " with-detail" : ""}`}>
        <div className="ledger-areas" data-testid="ledger-areas">
          {doc.areas.map((area) => {
            const rows = doc.modules.filter((r) => r.area === area.id)
              .sort((a, b) => MATURITY_ORDER.indexOf(a.maturity) - MATURITY_ORDER.indexOf(b.maturity));
            if (!rows.length) return null;
            return (
              <section key={area.id} className="ledger-area" aria-label={area.name}>
                <h3>{area.name}</h3>
                <ul>
                  {rows.map((r) => (
                    <li key={r.key} className={keep(r) ? "" : "dim"}>
                      <button type="button" className={`ledger-tile m-${r.maturity}${open === r.key ? " selected" : ""}`}
                        data-testid={`tile-${r.key}`} aria-pressed={open === r.key} onClick={() => setOpen(open === r.key ? null : r.key)}>
                        <span className="tile-name">{r.maturity === "not-modeled" ? <span aria-hidden="true">🔒 </span> : null}{r.name}</span>
                        <span className="tile-meta">{MATURITY_TEXT[r.maturity].name} · {REAL_TEXT[r.real_status]}
                          {r.maturity === "heuristic" && r.kind === "behaviour" ? <PracticeBadge inert /> : null}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              </section>
            );
          })}
        </div>
        {selected ? <Detail row={selected} doc={doc} onClose={() => setOpen(null)} /> : null}
      </div>
      <Card title="成熟度的意思">
        <dl className="ledger-legend">
          {MATURITY_ORDER.map((m) => <div key={m}><dt><MaturityPill maturity={m} /></dt><dd>{MATURITY_TEXT[m].short}。{doc.maturity_legend[m]}</dd></div>)}
        </dl>
        <p className="muted">升級的做法寫在 docs/upgrade-protocol.md；總表的文字版是 docs/modeling-ledger.md。</p>
      </Card>
    </>
  );
}
