# Git 歷史外洩清除計畫（調查結果 + 待執行草稿）

> [!CAUTION]
> **這個 repo 目前是 PUBLIC**（2026-11-03 調查時，未登入的 GitHub API 回應 200）。
> **歷史清除完成前，不要讓任何人注意到這個 repo；UI 不要上 GitHub Pages。**
> 不要在任何地方張貼 repo 連結，也不要開 issue、PR 或 release。

> [!NOTE]
> **2026-11-04 更新：** 決定**暫不清除**，改為先留存、之後一次清除。外洩內容已完整匯出到 `evidence/private/leak-archive/`（不進 repo）。
> 置頂待辦、三條硬約束與自動提醒見 [`TODO-history-cleanup.md`](TODO-history-cleanup.md)。依使用者指示，repo 應維持 private（2026-11-04 這一輪未連網重新確認）。

> [!IMPORTANT]
> 本文件只是**調查報告與草稿**。所有改寫歷史的指令（filter-repo、force push）都**待使用者在場時執行**。
> 本輪沒有改寫歷史、沒有 force push，也沒有刪除任何 commit、分支、tag 或檔案。
> 文件中只記錄 commit、檔名、欄位名與類別，不含任何實際數值。

## 1. 調查範圍與方法（唯讀）

| 項目 | 內容 |
|---|---|
| 掃描的 refs | `rea/full-reconstruction`、`codex/marketplace-sim-mcp`，以及它們在 origin 上的對應分支（沒有 tag） |
| commit 數 | 16，所有 refs 合計 |
| 不重複 blob | 219，涵蓋歷史上出現過的 200 個路徑 |
| 偵測器 | 與 publication gate 相同：真實數列、欄位名 + 真實值、真實名稱、examples 嚴格檢查。另外加上：<br>• 新增的「由真實費率推導的值」規則（`derived-rate`）<br>• 獨特真實數字（相當於 `git log -S`）<br>• cookie/token/session 字樣、帳密指派、e-mail、ID 指派<br>• 隊友姓名（取自私有名單）<br>• 禁止的副檔名 |
| 工具（不進 repo） | `tools/history/scan_history.py`、`make_replacements.py`、`verify_clean.py` |
| 結果（私有） | `evidence/private/history-scan/scan.json`、`replacements.txt`、`leaking_blobs.json` |

## 2. 受影響的 commit（不含數值）

| commit | 檔案 | 欄位／內容 | 類別 |
|---|---|---|---|
| `2954b88` | `docs/experiments/EXP-01.md` | 文字中的「觀察到的斜率」（Δinterest/Δdeposit）。由它可推回 CD 年利率。 | 財務參數（利率）的推導值 |
| `2954b88` | `tests/test_rea_ingest.py` | 測試資料中的 `interest`（實測的試算結果） | 實測結果值 |
| `59e7567` | `docs/experiments/EXP-02.md` | 產能選項的單位數序列（對應 `FixedCapacity…capacityOptions[*].units`），以及每台機器的日產能、機器數範圍 | 參數表（產能選項） |
| `59e7567` | 沿用上述 EXP-01、測試檔 | 同上 | 同上 |
| `c529630` | 沿用 EXP-01、EXP-02、測試檔 | 同上 | 同上 |
| `9a9a0dd` | 沿用上述三檔，另含 `docs/calculate-screen-triage.md` | 欄位 `rate`、`slRateMin` 的實際值 | 財務參數（利率） |

* 受影響的 commit 共 **4 個**：`2954b88`、`59e7567`、`c529630`、`9a9a0dd`，全部在 `rea/full-reconstruction`，而且**已經 push 到 GitHub**。
* 外洩的 blob 共 **4 個**，對應上表四個檔案的舊版本。
* `bca60c7` 已清除這些內容；之後的 commit 都乾淨（強化後的 gate 用 `--commits` 逐一確認過）。
* `codex/marketplace-sim-mcp`（`c731c7c`）沒有真實數值。

## 3. 其他類別檢查結果

| 類別 | 結果 |
|---|---|
| HAR、DevTools、session 擷取檔 | 歷史中**從未**出現 |
| 截圖、圖片、PDF、遊戲 JS/CSS 資產、`*_files/` | 歷史中**從未**出現 |
| cookie、token 的實際值、帳密 | **沒有**。「cookie」「token」只以說明文字或程式碼中的字詞出現，沒有任何帳密指派 |
| e-mail | 只有測試用的假地址（`example.test`）與 commit 訊息中的 `Co-Authored-By` noreply 地址 |
| 隊友或對手姓名 | **沒有**，已用私有名單比對 |
| commit 作者資訊 | 每個 commit 的作者／提交者 e-mail 都是使用者的**公司網域**。這不是遊戲資料，但公開時會連帶曝光身分。可選擇用 `--mailmap` 改寫（見 §5 選項 B） |
| `data/client_symbols.json`（與 `legacy/` 的副本） | 數字命中是**誤判**：命中的是原始碼的欄位位置（column number），不是參數。但這個檔案本身是**從遊戲客戶端 JS 整理出的符號與位置索引**，在所有 commit 中都有。要不要從歷史中移除，需由使用者決定（見 §5 選項 C） |

## 4. 替換檔怎麼產生（不進 repo）

1. `tools/history/scan_history.py` 掃描全部歷史，結果寫入 `evidence/private/history-scan/scan.json`。
2. `tools/history/make_replacements.py` 讀取清除用 commit `bca60c7` 的 diff，把每個外洩檔案中**被刪除的那一行**和**對應的新寫法**成對取出，寫成 git-filter-repo 的 `--replace-text` 格式：
   `literal:<舊的整行>==><新的整行>`
   * 結果：`evidence/private/history-scan/replacements.txt`，目前共 8 條規則，涵蓋 4 個檔案。
   * 用整行比對，只會替換那幾行，不會誤改其他地方的數字。
   * 這個檔案含真實數值，**只放在 private**，執行完、驗證通過後可以刪除。
3. 同一個腳本也會寫出 `leaking_blobs.json`（外洩 blob 的 id），供驗證腳本確認它們已不存在。

## 5. git-filter-repo 指令草稿（**待使用者在場時執行**）

> [!WARNING]
> 以下是草稿，**本輪沒有執行**。請先在演練用的副本上跑一次。

```powershell
# 0) 安裝工具（放在 D:\tools，不放 repo）
python -m venv D:\tools\filter-repo-venv
D:\tools\filter-repo-venv\Scripts\python.exe -m pip install git-filter-repo

# 1) 重新產生私有替換檔（確保反映最新狀態）
cd D:\simulationHW\simulation_HW
.\.venv\Scripts\python.exe -I tools\history\scan_history.py
.\.venv\Scripts\python.exe -I tools\history\make_replacements.py

# 2) 在全新的 mirror clone 上改寫（不要動工作目錄；工作目錄裡有 evidence/private）
git clone --mirror https://github.com/Jimmy0307/simulation_HW.git D:\tools\history-rewrite\simulation_HW.git
cd D:\tools\history-rewrite\simulation_HW.git
D:\tools\filter-repo-venv\Scripts\git-filter-repo.exe `
    --replace-text D:\simulationHW\simulation_HW\evidence\private\history-scan\replacements.txt

# 3) 驗證（見 §8）：在改寫後的 mirror 做一個一般 clone，再對它跑驗證腳本
git clone D:\tools\history-rewrite\simulation_HW.git D:\tools\history-rewrite\check
cd D:\simulationHW\simulation_HW
.\.venv\Scripts\python.exe -I tools\history\verify_clean.py --repo D:\tools\history-rewrite\check

# 4) 驗證通過後才推送（filter-repo 會移除 origin，需要重新加回）
cd D:\tools\history-rewrite\simulation_HW.git
git remote add origin https://github.com/Jimmy0307/simulation_HW.git
git push --force origin "refs/heads/*:refs/heads/*"
```

選項（需使用者決定）：

* **選項 B：改寫作者 e-mail。** 建立 `D:\tools\history-rewrite\mailmap.txt`，內容為一行
  `新名字 <新的noreply地址> <舊地址>`，然後在步驟 2 加上 `--mailmap D:\tools\history-rewrite\mailmap.txt`。
* **選項 C：從歷史移除 `client_symbols.json`。** 在步驟 2 之前，**另外**執行
  `git filter-repo --path data/client_symbols.json --path legacy/data/client_symbols.json --invert-paths`。
  這會連目前版本也一起移除，所以若程式仍在使用這個檔案，要先把它改成私有檔。

## 6. 執行前檢查清單

- [ ] **先把 repo 改成 private**（GitHub → Settings → General → Danger Zone → Change visibility）。這是立刻降低風險最有效的一步，不涉及歷史，可以先做。
- [ ] 確認沒有協作者的工作掛在舊 hash 上：
  * `git branch -a` 目前只有 2 個分支；
  * GitHub 上沒有 open PR；
  * Insights → Forks 沒有 fork；
  * 沒有其他機器上的 clone。
- [ ] 把未提交的工作提交或另外保存（UI 那一輪的 WIP）。
- [ ] 完整備份：
  * `git bundle create D:\tools\backup\simulation_HW-pre-cleanup.bundle --all`
  * 另外把 `evidence\private`、`tools`、`.claude` 複製到 `D:\tools\backup\`
  * 備份含外洩內容，**只放本機私有位置**，確認完成後再刪。
- [ ] 確認 remote 狀態：
  * `git fetch --all --prune`
  * `git status -sb` 顯示與 origin 沒有 ahead/behind
  * `git ls-remote origin` 的 SHA 記錄下來，以便比對
- [ ] 確認 GitHub Pages **沒有啟用**，Actions 沒有在跑。
- [ ] 先跑一次 `tools/history/verify_clean.py`，確認它目前回報「not clean」（有已知的壞基準可比對）。

## 7. 執行後的動作

1. **force push**：§5 步驟 4，兩個分支都要推。
2. **本機工作目錄對齊新歷史**：
   ```powershell
   git fetch origin
   git reset --hard origin/rea/full-reconstruction
   ```
   被 ignore 的 `evidence/private`、`tools`、`.claude` 不受影響。完成後重新安裝 hook：`python scripts/install_git_hooks.py`。
3. **通知所有協作者重新 clone**，並請他們**不要**把舊分支 merge 或 push 回來（否則外洩內容會被帶回）。
4. **GitHub 端的殘留**：
   * force push 之後，舊 commit 仍可能透過 SHA 網址、快取畫面或 fork 被看到，直到 GitHub 做垃圾回收。
   * 依 GitHub 的「Removing sensitive data from a repository」說明，聯絡 GitHub Support，請他們清除快取的 commit 畫面與相關 ref。
   * 若有 fork，要逐一處理。
5. **在 GitHub 的全新 clone 上**重跑 `verify_clean.py`，結果必須是 clean。
6. **即使清除了，也要視為「曾經外洩」**：
   * 這些內容自 push 起就曾公開。期間任何人都可能已經 clone、fork 或被搜尋引擎、存檔服務收錄，清除歷史無法收回已被複製的內容。
   * 外洩的是產能選項規模、一個利率與它的推導值、另一個利率欄位，以及一筆實測利息。沒有帳密，也沒有個資。
   * 以後的決策應假設這些值可能已被他人知道。
   * 不需要更換任何密碼或 token（沒有外洩）。
7. 清除完成並驗證之前，**不要**啟用 GitHub Pages。

## 8. 「乾淨性驗證」腳本設計（`tools/history/verify_clean.py`，不進 repo）

| 檢查 | 方法 | 通過條件 |
|---|---|---|
| 全歷史偵測 | 對指定 repo（`--repo`，可指向全新 clone）的所有 refs、所有 blob 跑 §1 的全部偵測器 | 除了已記錄的 `client_symbols.json` 欄位位置誤判，沒有任何數值類發現 |
| 外洩 blob 已消失 | 對 `leaking_blobs.json` 中每個 id 執行 `git cat-file -e` | 全部都不存在 |
| 逐行 pickaxe | 對每條替換規則的舊整行執行 `git log --all -S<舊行>` | 全部沒有結果 |
| 輸出 | 只印「clean／not clean」與問題清單（規則編號、檔名），不印數值 | exit code 0 |

目前（清除前）的結果：**not clean**，4 個外洩 blob 與 8 條規則都還在。這符合預期，也證明腳本確實抓得到。

## 9. 過渡期已完成的防護（不涉及歷史）

| 漏洞 | 補強 |
|---|---|
| 偵測器抓不到「由真實費率推導的值」（例如斜率 = 年利率 ÷ 400） | `value_leak` 新增 `derived-rate` 規則：把真實費率除以 4、12、100、400，若結果有兩位以上小數，且出現在提到 rate、slope、interest 或利率、斜率的行上，就擋下。已用植入的假資料測試。 |
| gate 只檢查最終的檔案樹；「先洩漏、後清除」的內容仍會留在歷史中（這次外洩正是如此） | gate 新增 `--commits A..B` 與 `--pre-push` 模式，逐一掃描每個要 push 的 commit；`scripts/install_git_hooks.py` 會安裝本機 pre-push hook（**尚未安裝**：本輪的權限檢查不允許自動安裝 hook，請使用者自行執行 `python scripts/install_git_hooks.py`）。逐 commit 掃描已用暫存 git repo 測試。 |
| CLI 與 API 會把任何名為 `private` 的資料夾當成私有輸出位置，但 `.gitignore` 只忽略 `evidence/private/` | `.gitignore` 加上 `**/private/`；gate 禁止任何路徑含有 `private` 目錄。 |
| 擬合的需求模型、需求面板、前端建置產物沒有被忽略 | `.gitignore` 加上 `**/fitted_demand.json`、`**/demand_panel/`、`frontend/node_modules/`、`frontend/dist/` 與 `.git-rewrite/` |

仍無法完全防範的情況（需要人工審查）：
* 以文字（而非數字）寫出的數值；
* 其他推導方式（不同的比例或差值）；
* 在 CI 上沒有私有數值可比對，所以只有本機的 pre-push hook 能做真實值檢查。
