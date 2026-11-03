<!-- history-cleanup-status: NOT_CLEANED -->
<!-- 上一行由 scripts/history_guard.py 讀取。只有在全新 clone 上 tools/history/verify_clean.py 回報 clean 之後，才可改成 CLEANED。 -->

# ⚠️ 待辦（未完成）：未清除：公開歷史仍含真實數值與遊戲客戶端程式碼

> [!CAUTION]
> **狀態：未清除（NOT_CLEANED）。** 已 push 到 GitHub 的 git 歷史（以下稱「公開歷史」）仍含有：
> * **真實數值**：4 個 commit（`2954b88`、`59e7567`、`c529630`、`9a9a0dd`）含 4 個檔案的舊版本，裡面有真實參數與實測結果；
> * **從遊戲客戶端程式碼整理出的內容**：每個 commit 都帶有從客戶端 JS 擷取的公式片段、符號與位置索引、呼叫圖（`legacy/data/` 與更早的 `data/` 下的 `client_*.json` 等檔案）；
> * **作者資訊**：每個 commit 的作者 e-mail 網域。
>
> 目前擋住風險的**只有「repo 設為 private」這一層**。工作目錄的最新版本是乾淨的，但歷史不是。

## ⛔ a. 歷史清除完成前，repo 不得改回 public

## ⛔ b. 歷史清除完成前，不得發布到 GitHub Pages

## ✅ c. 清除方案已就緒，留存已完成

| 項目 | 位置 |
|---|---|
| 清除計畫（步驟、filter-repo 指令草稿、驗證設計） | [`docs/history-cleanup-plan.md`](history-cleanup-plan.md) |
| 掃描、替換檔產生、驗證腳本（不進 repo） | `tools/history/`（`scan_history.py`、`make_replacements.py`、`verify_clean.py`、`export_leak_archive.py`） |
| 外洩內容的完整留存（不進 repo） | `evidence/private/leak-archive/`（各 commit 外洩檔案原樣、`legacy/` 快照、完整歷史 bundle、`INDEX.md`） |

---

## 為什麼現在不清

決定記在 `docs/decisions-log.md` 第 52 條起。簡單說：
* 課程遊戲還在進行，歷史與 `legacy/` 還有查詢與思考的價值；改寫歷史不可逆，而且會打斷所有 clone。
* 先把外洩內容完整匯出到 private，確保將來清除後仍查得到，再找適當時機**一次**清除。
* 在那之前，風險由「repo 維持 private」加上下面的自動提醒擋住。

## 建議的清除時機

**課程遊戲結束後，而且確定要公開（repo 改回 public 或上 Pages）之前。** 兩個條件都成立時就執行。若在此之前發現 repo 意外變成 public，請立刻改回 private，並提前清除。

## 自動提醒（防止忘記）

`scripts/history_guard.py` 會讀取本檔第一行的狀態。只要狀態不是 `CLEANED`，下列發布動作都會**響鈴並印出大型警告**（不會阻擋本機開發）：

| 動作 | 何時響 | 觸發來源 |
|---|---|---|
| 建置要發布的 `dist/` | 每次 | `scripts/build_demo.py`（開始與結束各一次）、`publication_gate.py --require-dist` |
| 發布 GitHub Pages | 每次，而且**讓 workflow 失敗** | `.github/workflows/pages.yml`（`--strict`；CI 沒人聽得到鈴聲） |
| 準備把 repo 改成 public | 每次 | 改設定前手動執行 `python scripts/history_guard.py --action public` |
| push | 只在 repo 目前是 public 時 | `publication_gate.py --pre-push`（需先執行 `python scripts/install_git_hooks.py` 安裝 hook）。它會向 GitHub 發一個不帶憑證的唯讀請求確認公開與否 |

## 清除完成後要做的事

1. 依 `docs/history-cleanup-plan.md` 執行清除，並在**全新 clone** 上確認 `tools/history/verify_clean.py` 回報 clean。
2. 把本檔第一行改成 `<!-- history-cleanup-status: CLEANED -->`，並把標題改為「已清除」，連同清除日期一起 commit。
3. `evidence/private/leak-archive/` 繼續留在本機（它是清除後唯一保有原始內容的地方），**不要**放回 repo。
