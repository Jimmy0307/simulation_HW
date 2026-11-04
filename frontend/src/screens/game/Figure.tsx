import { createContext, useContext, useEffect, useRef, useState } from "react";
import type { LevelLabel, Line } from "../../types";
import { formatNumber, isUncalibrated, Num } from "../../ui/Num";

/** Quiet mark beside an uncalibrated number. "≈" already reads as "about" to anyone, before any explanation. */
export const APPROX = "≈";

/** The advanced switch: off = clean game view; on = every number carries its full source-level mark (as on screens 1–7). */
export const LevelsContext = createContext(false);

/** When an uncalibrated number becomes "actual" (depends on why it is uncalibrated). */
export function becomesActual(level: LevelLabel): string {
  if (level === "literature") return "Q2 數據校準後變實際（需求擬合通過留出季驗證）";
  if (level === "placeholder") return "成本規則尚未驗證；完成驗證實驗後才變實際";
  return "";
}

/** The short hover text next to the ≈ mark. */
export function estimateHint(level: LevelLabel): string {
  if (level === "literature") return "預估 · Q2 校準後變實際";
  if (level === "placeholder") return "預估 · 成本規則驗證後變實際";
  return "";
}

const WHY: Partial<Record<LevelLabel, string>> = {
  literature: "需求形式來自公開文獻，係數還沒用本局資料校準。",
  placeholder: "示意用的佔位規則，還沒有實驗驗證。",
};

export type FigureFormat = "number" | "percent";

function display(value: number, format: FigureFormat, digits?: number): string {
  // Display formatting only (a 0–1 share written as a percentage); the value itself is the engine's.
  if (format === "percent") return `${(value * 100).toLocaleString("zh-TW", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`;
  return formatNumber(value, digits);
}

/** A short highlight when the engine sends a new value, then back to rest (game feel, restrained). */
function useTick(value: number): boolean {
  const previous = useRef(value);
  const [tick, setTick] = useState(false);
  useEffect(() => {
    if (previous.current === value) return undefined;
    previous.current = value;
    setTick(true);
    const t = setTimeout(() => setTick(false), 700);
    return () => clearTimeout(t);
  }, [value]);
  return tick;
}

/**
 * A number in the game view. Trusted levels (verified / derived / estimated) are shown plainly, with no mark.
 * Uncalibrated levels (literature / placeholder) get a small grey ≈ in front; hover or focus explains it.
 * With the "show all source levels" switch on, the full mark from the analysis screens is shown instead.
 */
export function Figure({ line, label, digits, format = "number", unit }: {
  line: Line; label: string; digits?: number; format?: FigureFormat; unit?: string;
}) {
  const full = useContext(LevelsContext);
  const tick = useTick(line.value);
  const uncal = isUncalibrated(line);
  const cls = `fig${uncal ? " est" : ""}${tick ? " tick" : ""}`;
  if (full) {
    return (
      <span className={`${cls} full`} data-estimate={uncal ? "true" : "false"} data-level={line.level}>
        <Num line={line} label={label} digits={format === "percent" ? 3 : digits} />
      </span>
    );
  }
  const text = `${display(line.value, format, digits)}${unit ?? ""}`;
  if (!uncal) {
    return <span className={cls} data-estimate="false" data-level={line.level}>{text}</span>;
  }
  return (
    <span className={cls} data-estimate="true" data-level={line.level} tabIndex={0}
      aria-label={`${label}：約 ${text}，${estimateHint(line.level)}`}>
      <span className="fig-approx" aria-hidden="true">{APPROX}</span>
      <span className="fig-v">{text}</span>
      <span className="fig-tip" role="tooltip">
        <b>{estimateHint(line.level)}</b>
        <span>{WHY[line.level]}</span>
      </span>
    </span>
  );
}
