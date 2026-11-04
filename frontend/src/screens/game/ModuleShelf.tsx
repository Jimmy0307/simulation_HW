import type { GameSetupDoc, ModulesDoc } from "../../types";
import { formatNumber } from "../../ui/Num";
import { PracticeBadge } from "../../ui/Practice";
import type { Draft } from "./draft";

/** The quiet literature mark used on cards (same meaning as the ≈ on numbers). */
function Lit() {
  return <span className="lit-mark" title="文獻：形式有公開文獻支持，係數未校準">≈ 文獻</span>;
}

/**
 * The company's other departments, under the bike cards: one card per module that can be decided (with the badge of
 * each part: ≈ literature, 練習 practice), and one for everything still locked. Any card opens the modules panel.
 */
export function ModuleShelf({ catalog, draft, setup, selected, onOpen }: {
  catalog: ModulesDoc | null; draft: Draft; setup: GameSetupDoc; selected: boolean; onOpen: () => void;
}) {
  if (!catalog) return null;
  const sales = draft.modules.sales_force as { headcount?: number } | undefined;
  const carried = setup.state?.module_state?.sales_force?.headcount ?? 0;
  const mix = (draft.modules["marketing.media_mix"] as { mix?: Record<string, unknown> } | undefined)?.mix ?? {};
  const inventory = draft.modules["supply.inventory"] as { sell_off?: Record<string, number> } | undefined;
  const contract = draft.modules["supply.purchasing"] as { contract_units?: number } | undefined;
  const cards = [
    { id: "sales", title: "業務團隊", badges: <><Lit /><PracticeBadge inert /></>,
      meta: sales ? `本季 ${formatNumber(sales.headcount ?? 0)} 人` : carried > 0 ? `在職約 ${formatNumber(carried, 1)} 人` : "未啟用" },
    { id: "media", title: "廣告分配", badges: <Lit />, meta: Object.keys(mix).length ? `${Object.keys(mix).length} 個產品分配中` : "未啟用" },
    { id: "inventory", title: "庫存", badges: <><Lit /><PracticeBadge inert /></>,
      meta: inventory ? (Object.keys(inventory.sell_off ?? {}).length ? "計持有成本 · 出清中" : "計持有成本") : "未啟用" },
    { id: "purchasing", title: "採購合約", badges: <PracticeBadge inert />,
      meta: contract ? `承諾 ${formatNumber(contract.contract_units ?? 0)} 件` : "未啟用" },
  ];
  const locked = catalog.counts["not-modeled"] ?? 0;
  return (
    <section className="module-shelf" aria-label="經營模組">
      {cards.map((c) => (
        <button key={c.id} type="button" className={`shelf-card${selected ? " selected" : ""}`} onClick={onOpen} data-testid={`shelf-${c.id}`}>
          <span className="shelf-title">{c.title} {c.badges}</span>
          <span className="shelf-meta">{c.meta}</span>
        </button>
      ))}
      <button type="button" className="shelf-card locked" onClick={onOpen} data-testid="shelf-locked">
        <span className="shelf-title"><span aria-hidden="true">🔒</span> 待建模組</span>
        <span className="shelf-meta">{locked} 個，還不能調</span>
      </button>
    </section>
  );
}
