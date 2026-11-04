import type { ReactNode } from "react";
import type { Maturity } from "../types";

/** The one sentence every heuristic lever and result carries. Louder than "≈" on purpose. */
export const PRACTICE_TEXT = "練習用 · 規則暫定 · 真實關係待 Q2";

/**
 * Heuristic = a practice rule from general business sense, with no literature and no calibration. The badge is
 * filled and striped so it cannot be read as an ordinary number; hover or focus repeats what it means.
 */
export function PracticeBadge({ size = "sm", inert = false }: { size?: "sm" | "lg"; inert?: boolean }) {
  if (inert) {
    // inside a button: no own focus stop, no tooltip (the button's panel explains)
    return <span className={`practice-badge ${size}`} data-testid="practice-badge" title={PRACTICE_TEXT}>練習</span>;
  }
  return (
    <span className={`practice-badge ${size}`} role="note" tabIndex={0} aria-label={`練習：${PRACTICE_TEXT}`}
      data-testid="practice-badge">
      練習
      <span className="practice-tip" role="tooltip">
        <b>{PRACTICE_TEXT}</b>
        <span>這是照一般商業常識訂的暫定規則，沒有文獻、沒有校準。只能看方向，不要把這裡的因果當真。</span>
      </span>
    </span>
  );
}

/** A banner for the heuristic part of a module (its levers and its results). */
export function PracticeBanner({ children }: { children?: ReactNode }) {
  return (
    <p className="practice-banner" role="note">
      <PracticeBadge size="lg" />
      <span><b>{PRACTICE_TEXT}</b>。{children ?? "調這裡的杆會改變結果，但改變的方式是暫定的練習規則；只要用了，受影響的數字都會一起標成「練習」。"}</span>
    </p>
  );
}

/** What the quiet "≈" means on a literature lever. */
export const APPROX_TEXT = "文獻：形式有公開文獻支持，係數未用本局資料校準；預估 · Q2 校準後變實際";

/** A quiet banner for the literature part of a module: the ≈ treatment, not the practice alarm. */
export function LiteratureBanner({ children }: { children: ReactNode }) {
  return (
    <p className="lit-banner" role="note">
      <span className="lit-mark" aria-hidden="true">≈ 文獻</span>
      <span>{children}<span className="muted">（預估 · Q2 校準後變實際）</span></span>
    </p>
  );
}

export const MATURITY_TEXT: Record<Maturity, { name: string; short: string }> = {
  verified: { name: "已驗證", short: "從遊戲擷取並實測重現" },
  literature: { name: "文獻", short: "形式有公開文獻支持，係數未校準" },
  heuristic: { name: "練習規則", short: "一般商業常識，無文獻、無校準" },
  "not-modeled": { name: "待建", short: "真實遊戲有，我們還沒做" },
};

export const MATURITY_ORDER: Maturity[] = ["verified", "literature", "heuristic", "not-modeled"];

export function MaturityPill({ maturity }: { maturity: Maturity }) {
  return (
    <span className={`maturity-pill m-${maturity}`} title={MATURITY_TEXT[maturity].short}>
      {maturity === "not-modeled" ? <span aria-hidden="true">🔒 </span> : null}
      {MATURITY_TEXT[maturity].name}
    </span>
  );
}

/** "Q2+ (unverified · awaiting Q2 capture)" -> a short Chinese label for the locked state. */
export function captureLabel(capture: string): string {
  const quarter = capture.match(/Q\d\+?/)?.[0];
  if (/^Q1 \(captured\)/.test(capture)) return "Q1 已擷取";
  if (quarter) return `預計 ${quarter} 開放（未證實）`;
  if (capture.startsWith("first profitable")) return "第一次獲利的季度（未證實）";
  return "開放季別未知";
}
