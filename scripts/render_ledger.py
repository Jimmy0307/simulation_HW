"""Render docs/modeling-ledger.md from data/modeling_ledger.json (the single source; edit the JSON, not the doc).

usage: python scripts/render_ledger.py [--check]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "data" / "modeling_ledger.json"
DOC = ROOT / "docs" / "modeling-ledger.md"
ORDER = ["verified", "literature", "heuristic", "not-modeled"]
MATURITY_ZH = {"verified": "verified（已驗證）", "literature": "literature（文獻）", "heuristic": "heuristic（練習規則）",
               "not-modeled": "not-modeled（未建）"}
REAL_ZH = {"measured": "實測", "inferred": "推斷 · 未證實", "unknown": "未知"}


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def implementations() -> dict[str, str]:
    sys.path.insert(0, str(ROOT / "src"))
    from marketplace_sim.business.registry import IMPLEMENTATIONS

    return {k: v.__name__ for k, v in IMPLEMENTATIONS.items()}


def render() -> str:
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    rows = data["modules"]
    impls = implementations()
    areas = {a["id"]: a["name"] for a in data["areas"]}
    counts = Counter(r["maturity"] for r in rows)
    real = Counter(r["real_status"] for r in rows)
    gap = [r for r in rows if r["real_status"] in {"measured", "inferred"} and r["maturity"] == "not-modeled"]
    weak = [r for r in rows if r["maturity"] == "heuristic"]
    out = [
        "# 模組總表（modeling ledger）",
        "",
        ("> 由 `data/modeling_ledger.json` 產生（`python scripts/render_ledger.py`）。要改請改 JSON，"
        "測試會檢查兩者一致。只放結構與成熟度，不含任何遊戲數值。"),
        "",
        ("這張表回答「離完整的企業經營模擬還差多少」，也是 agent 的工作清單：每次挑一列，"
        "照 [`docs/upgrade-protocol.md`](upgrade-protocol.md) 升一級。"),
        "",
        "## 摘要",
        "",
        f"* 共 {len(rows)} 個模組："
        + "、".join(f"{MATURITY_ZH[m]} {counts.get(m, 0)}" for m in ORDER) + "。",
        (f"* 真實遊戲：實測 {real.get('measured', 0)}、推斷 {real.get('inferred', 0)}、未知 {real.get('unknown', 0)}。"
        "推斷的部分一律「未證實 · 待擷取」。"),
        f"* 真實遊戲有（實測或推斷）但我們完全沒做：{len(gap)} 個。",
        (f"* heuristic（練習規則，可能被誤當成真實因果）：{len(weak)} 個，其中行為規則 "
        f"{sum(1 for r in weak if r['kind'] == 'behaviour')} 個、佔位會計規則 "
        f"{sum(1 for r in weak if r['kind'] == 'accounting')} 個、情境假設 {sum(1 for r in weak if r['kind'] == 'scenario')} 個。"),
        "",
        "## 成熟度與種類",
        "",
        "| 成熟度 | 意思 |",
        "|---|---|",
        *[f"| {MATURITY_ZH[k]} | {_cell(v)} |" for k, v in data["maturity_legend"].items()],
        "",
        "| 種類 | 意思 |",
        "|---|---|",
        *[f"| {k} | {_cell(v)} |" for k, v in data["kind_legend"].items()],
        "",
        "規則：" + " ".join(data["rules"]),
        "",
        "## 總表",
        "",
    ]
    for area_id, area_name in areas.items():
        area_rows = [r for r in rows if r["area"] == area_id]
        if not area_rows:
            continue
        area_rows.sort(key=lambda r: (ORDER.index(r["maturity"]), r["key"]))
        out += [f"### {area_name}", "",
                "| 模組 | 真實遊戲 | 對應畫面 | 我們的成熟度 | 我們現在有什麼 | 升級下一步 | 預計哪季可擷取 |",
                "|---|---|---|---|---|---|---|"]
        for r in area_rows:
            impl = f" · `{impls[r['key']]}`" if r["key"] in impls else ""
            screens = ", ".join(f"`{s}`" for s in r["screens"]) or "（無）"
            out.append(
                f"| **{_cell(r['name'])}**<br>`{r['key']}` · {r['kind']} | {REAL_ZH[r['real_status']]}<br>{_cell(r['real_note'])} "
                f"| {screens} | {MATURITY_ZH[r['maturity']]}{impl} | {_cell(r['ours'])} | {_cell(r['next_step'])} "
                f"| {_cell(r['capture'])} |")
        out.append("")
    out += ["## 來源", "",
            ("E- = 本專案已擷取的證據（只用畫面名稱與欄位名）；P- = 公開教學資料對該模擬的文字描述；"
            "R- = 企業模擬的綜述與公開產品說明；L- = 反應函數文獻。"), ""]
    out += [f"* **{k}** — {_cell(v)}" for k, v in data["sources"].items()]
    out.append("")
    return "\n".join(out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="exit 1 if docs/modeling-ledger.md is stale")
    text = render()
    if parser.parse_args().check:
        current = DOC.read_text(encoding="utf-8") if DOC.exists() else ""
        if current != text:
            print("docs/modeling-ledger.md is stale: run python scripts/render_ledger.py")
            raise SystemExit(1)
        return
    DOC.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {DOC.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
