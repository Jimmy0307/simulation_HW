import { useState } from "react";
import type { LevelLabel, Line } from "../../types";
import { isUncalibrated, LEVEL_TEXT, Num } from "../../ui/Num";

export const ESTIMATE_LABEL = "預估";

/** When an uncalibrated number becomes "actual" (depends on why it is uncalibrated). */
export function becomesActual(level: LevelLabel): string {
  if (level === "literature") return "Q2 數據校準後變實際（需求擬合通過留出季驗證）";
  if (level === "placeholder") return "成本規則尚未驗證；完成驗證實驗後才變實際";
  return "";
}

/**
 * A number in the game. Trusted levels (verified / derived / estimated) show directly with their source level.
 * Uncalibrated levels (literature / placeholder) start collapsed as a faded "？ 預估" chip; one click reveals the
 * number (still small, with its uncalibrated mark and source chain) and when it becomes actual.
 */
export function Estimate({ line, label, open, note = true }: { line: Line; label: string; open?: boolean; note?: boolean }) {
  const [revealed, setRevealed] = useState(false);
  if (!isUncalibrated(line)) {
    return <span className="trusted" data-estimate="false"><Num line={line} label={label} /></span>;
  }
  const shown = open || revealed;
  return (
    <span className={`estimate lv lv-${line.level}${shown ? " open" : ""}`} data-estimate="true" data-level={line.level}>
      {shown ? (
        <>
          <Num line={line} label={label} />
          {note ? <small className="estimate-note">{becomesActual(line.level)}</small> : null}
        </>
      ) : (
        <button type="button" className="estimate-btn" onClick={() => setRevealed(true)}
          aria-label={`${label}：${LEVEL_TEXT[line.level].name}等級的預估值，點一下展開`}
          title={becomesActual(line.level)}>
          <span aria-hidden="true">？</span> {ESTIMATE_LABEL}
        </button>
      )}
    </span>
  );
}
