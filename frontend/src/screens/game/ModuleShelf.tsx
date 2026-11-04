import type { GameSetupDoc, ModulesDoc } from "../../types";
import { formatNumber } from "../../ui/Num";
import { PracticeBadge } from "../../ui/Practice";
import type { Draft } from "./draft";

/**
 * The company's other departments, under the bike cards: one card per practice module (with the practice badge),
 * and one for everything still locked. Clicking any of them opens the modules panel.
 */
export function ModuleShelf({ catalog, draft, setup, selected, onOpen }: {
  catalog: ModulesDoc | null; draft: Draft; setup: GameSetupDoc; selected: boolean; onOpen: () => void;
}) {
  if (!catalog) return null;
  const sales = draft.modules.sales_force as { headcount?: number } | undefined;
  const carried = setup.state?.module_state?.sales_force?.headcount ?? 0;
  const mix = (draft.modules["marketing.media_mix"] as { mix?: Record<string, unknown> } | undefined)?.mix ?? {};
  const salesText = sales ? `本季 ${formatNumber(sales.headcount ?? 0)} 人` : carried > 0 ? `在職約 ${formatNumber(carried, 1)} 人` : "未啟用";
  const mixText = Object.keys(mix).length ? `${Object.keys(mix).length} 個產品分配中` : "未啟用";
  const locked = catalog.counts["not-modeled"] ?? 0;
  return (
    <section className="module-shelf" aria-label="經營模組">
      <button type="button" className={`shelf-card${selected ? " selected" : ""}`} onClick={onOpen} data-testid="shelf-sales">
        <span className="shelf-title">業務團隊 <PracticeBadge inert /></span>
        <span className="shelf-meta">{salesText}</span>
      </button>
      <button type="button" className={`shelf-card${selected ? " selected" : ""}`} onClick={onOpen} data-testid="shelf-media">
        <span className="shelf-title">廣告分配 <PracticeBadge inert /></span>
        <span className="shelf-meta">{mixText}</span>
      </button>
      <button type="button" className="shelf-card locked" onClick={onOpen} data-testid="shelf-locked">
        <span className="shelf-title"><span aria-hidden="true">🔒</span> 待建模組</span>
        <span className="shelf-meta">{locked} 個，還不能調</span>
      </button>
    </section>
  );
}
