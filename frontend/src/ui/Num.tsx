import type { ChainStep, LevelLabel, Line } from "../types";
import { PRACTICE_TEXT, PracticeBadge } from "./Practice";

export const LEVEL_TEXT: Record<LevelLabel, { name: string; mark: string }> = {
  verified: { name: "已驗證", mark: "V" },
  derived: { name: "推導", mark: "D" },
  estimated: { name: "估計", mark: "E" },
  literature: { name: "文獻", mark: "L" },
  placeholder: { name: "佔位", mark: "P" },
  heuristic: { name: "練習規則", mark: "H" },
};

export const UNCALIBRATED_LABEL = "未校準 · 非預測";

/** The API marks every number; the level fallback only covers documents that predate the flag. */
export function isUncalibrated(line: Pick<Line, "level" | "uncalibrated">): boolean {
  // A practice (heuristic) number is never shown as trusted, whatever a document says.
  if (line.level === "heuristic") return true;
  return line.uncalibrated ?? (line.level === "literature" || line.level === "placeholder");
}

export function formatNumber(value: number, digits?: number): string {
  if (!Number.isFinite(value)) return String(value);
  const d = digits ?? (Math.abs(value) >= 100 || Number.isInteger(value) ? 0 : 2);
  return value.toLocaleString("zh-TW", { minimumFractionDigits: d, maximumFractionDigits: d });
}

export function LevelMark({ level }: { level: LevelLabel }) {
  return (
    <span className={`mark lv lv-${level}`} aria-label={`來源等級：${LEVEL_TEXT[level].name}`}>
      {LEVEL_TEXT[level].mark}
    </span>
  );
}

export function UncalibratedChip({ level }: { level: LevelLabel }) {
  return <span className={`uncal-chip lv lv-${level}`} role="note">{UNCALIBRATED_LABEL}</span>;
}

function Chain({ chain }: { chain: ChainStep[] }) {
  return (
    <ol>
      {chain.map((step) => (
        <li key={step.metric}>
          <code>{step.metric}</code> <LevelMark level={step.level} /> {step.formula}
          {step.evidence ? <span className="muted"> · {step.evidence}</span> : null}
        </li>
      ))}
    </ol>
  );
}

/** A number with its source level: colour, mark, the uncalibrated chip when needed, and a hover/focus source chain. */
export function Num({ line, digits, label }: { line: Line; digits?: number; label?: string }) {
  const uncal = isUncalibrated(line);
  return (
    <span className={`num lv lv-${line.level}${uncal ? " uncal" : ""}`} tabIndex={0} data-level={line.level}
      data-uncalibrated={uncal ? "true" : "false"}>
      <span className="v">{formatNumber(line.value, digits)}</span>
      <LevelMark level={line.level} />
      {line.level === "heuristic" ? <PracticeBadge /> : uncal ? <UncalibratedChip level={line.level} /> : null}
      <span className="tip" role="tooltip">
        <span className="tip-title">
          {label ? `${label} · ` : ""}{LEVEL_TEXT[line.level].name}（{line.level}）{uncal ? ` · ${UNCALIBRATED_LABEL}` : ""}
        </span>
        <span>規則：<code>{line.source}</code></span>
        {line.chain && line.chain.length > 0 ? (<><br /><span className="muted">來源鏈（由此往上游）：</span><Chain chain={line.chain} /></>) : null}
        {line.level === "heuristic" ? (
          <><br /><span><b>{PRACTICE_TEXT}</b>：上游含練習規則（一般商業常識，無文獻、無校準），只能看方向，不能當真。</span></>
        ) : uncal ? (
          <><br /><span>上游含 literature 或 placeholder：形式或數值未用本局資料校準，不可當作預測。</span></>
        ) : null}
      </span>
    </span>
  );
}
