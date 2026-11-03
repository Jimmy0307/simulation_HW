# Web UI 使用指南（本機模擬器）

這個 Web UI 只是現有 Python 引擎的「臉」：所有數字都由 `src/marketplace_sim/` 的引擎與控制平面計算，前端只負責呈現和操作。
同一套前端有兩種資料來源：

| 模式 | 資料從哪來 | 能做什麼 | 用在哪 |
|---|---|---|---|
| **Demo（靜態）** | `frontend/public/demo/*.json`：用 **synthetic（虛構）** 參數包預先算好的結果 | 只能檢視。可以看預設方案、範本情境和預算好的壓力測試；修改後的內容需要本機引擎 | 公開展示（GitHub Pages，**目前不要發布**，見最後一節） |
| **實戰（本機 API）** | 本機的 FastAPI（`127.0.0.1:8765`）即時呼叫引擎，可以載入你的 private 參數包 | 全部功能：送出決策推進、即時比較、編輯並執行情境與 sweep、切換參數包 | 只在自己的電腦上用 |

畫面右上角一定會標出目前的參數包：綠色 **SYNTHETIC 虛構資料**，或閃爍的紅色 **PRIVATE 真實資料**。同時也會標出目前是哪個模式。

## 1. 啟動 Demo 模式

```powershell
# 一次做完：匯出 synthetic 結果 → 前端測試 → 建置 → 用 publication gate 檢查 dist/
python scripts\build_demo.py            # 加 --base /simulation_HW/ 可模擬 GitHub Pages 的路徑
cd frontend
npm run preview                          # 開 http://127.0.0.1:4173
```

開發時也可以直接執行 `cd frontend; npm run dev`（預設就是 Demo 模式，讀 `public/demo`）。

## 2. 啟動實戰模式

一鍵啟動（本機腳本，**不在 repo 裡**）：

```powershell
powershell -ExecutionPolicy Bypass -File tools\live\start_ui.ps1                 # 載入 private 參數包
powershell -ExecutionPolicy Bypass -File tools\live\start_ui.ps1 -Save <存檔路徑> # 接續某個私有存檔
powershell -ExecutionPolicy Bypass -File tools\live\start_ui.ps1 -Synthetic      # 用虛構參數練習
```

腳本會同時啟動本機 API 與 Vite 開發伺服器（live 模式），並開啟瀏覽器。按 Enter 會同時關閉兩者。

也可以手動在兩個終端機分別執行：

```powershell
.\.venv\Scripts\python.exe -m marketplace_sim.api --pack private      # 或 --pack synthetic、--save <存檔>
cd frontend; npm run dev:api                                           # 開 http://127.0.0.1:5173
```

* API **只會綁定 127.0.0.1**；指定其他位址會被拒絕。
* 任何 URL 都可以加 `?source=api` 或 `?source=static` 來強制指定資料來源。

## 3. 切換參數包

* 實戰模式：用右上角的「載入 synthetic」「載入 private」按鈕切換。切換後，所有畫面會重新讀取資料。
* private 參數包必須放在名為 `private` 的資料夾底下，否則 API 會拒絕載入。
* API 對每一個回應都標出 `is_private`；畫面依此顯示紅色警示橫幅。

## 4. 七個畫面

| 畫面 | 內容 |
|---|---|
| 總覽 | 目前參數包、公司狀態、逐季趨勢圖（虛線代表未校準的數列）、最近一季的完整報表 |
| 決策編輯 | 從預設方案開始，用表單修改，可以「試算（不推進）」或「送出並推進一季」。送出只在實戰模式可用 |
| 方案比較 | 從同一狀態並排比較多個方案：與第一個方案不同的格子有色條，有差異的整列加深底色 |
| 情境工作台 | 編輯參數覆寫、事件與對手設定後執行；逐季結果中，有事件的季別以 ⚑ 標記 |
| 壓力測試 | 執行或讀取 sweep，列出最差 N 個情境與各變數的敏感度。**頁首常駐橫幅**提醒結果反映文獻假設 |
| 參數 diff | 比較兩個參數包；已驗證模組的參數有變動時整列標紅，並列出紅旗。真實參數包之間的比較不顯示數值 |
| 來源等級說明 | 圖例、每個等級的意義、「未校準 · 非預測」標記的說明，以及每個指標的公式、上游與證據 |

## 5. 來源等級怎麼看

順序：**verified（已驗證）> derived（推導）> estimated（估計）> literature（文獻）> placeholder（佔位）**。

* 數字的**顏色**和旁邊的**字母**代表等級：V、D、E、L、P。
* 上游只要含 literature 或 placeholder，數字旁就會出現斜紋的 **「未校準 · 非預測」** 標記，數字本身也加上點狀底線。
* 把滑鼠移到數字上（或用 Tab 鍵聚焦）會出現**來源鏈**：
  * 產生這個數字的規則；
  * 從這個項目往上游的每一步，各自的等級、公式與證據文件。
* 組合出來的數字一律取上游**最弱**的等級，不會標得比來源更強。

## 6. 為什麼現在的銷量、市佔、營收不能當預測

* 需求面目前是 **literature** 等級：函數形式來自公開的行銷與經濟學文獻（見 `docs/demand-literature.md`），係數是文獻中間值或標註的預設值，沒有用本局資料校準過（見 `docs/demand-model-spec.md`）。
* 利潤、稅與現金還受到 **placeholder** 的成本規則影響（生產成本、稅），所以這些數字也一樣帶有標記。
* 這些數字適合用來比較方案之間的方向與敏感度，不適合當作本局的預測值。
* 只有當需求面板累積足夠資料、擬合結果通過留出季驗證後，需求才會升為 **estimated**。
* 在那之前，壓力測試的「最差情境」反映的是文獻假設，不是本局預測。

## 7. 公開與私有的邊界

| 可以進 repo、可以上 Pages | 不進 repo、不進 build、不上 Pages |
|---|---|
| 前端原始碼（`frontend/src`）、設定檔、`frontend/public/demo` 中的 synthetic 匯出、建置腳本、GitHub Actions 設定 | private 參數包、真實結果、任何真實數值、`tools/` 下的啟動腳本、`frontend/dist`（由 CI 從已提交的內容重建） |

* 匯出 demo 只會使用 synthetic 參數包；只要有任何結果來自 private 參數包，或含本機絕對路徑，就拒絕匯出。
* publication gate 會檢查：
  * 前端原始碼與 demo 匯出檔（真實數值、私有標記、本機路徑）；
  * `--require-dist` 時的 `frontend/dist` 建置產物（真實數列、私有標記、本機路徑、不允許的檔案類型）。

## 8. 發布到 GitHub Pages（目前不要做）

> [!CAUTION]
> git 歷史中仍有真實數值（見 `docs/history-cleanup-plan.md` 與置頂待辦 `docs/TODO-history-cleanup.md`）。**歷史清除完成並驗證之前，不要發布 Pages，repo 也不要改回 public。**

完成清除之後的發布方式：
1. 在 GitHub 的 Settings → Pages，把 Source 設為 **GitHub Actions**。
2. 在本機執行 `python scripts\build_demo.py --base /simulation_HW/`，確認 gate 通過，再提交最新的 `frontend/public/demo`。
3. 在 GitHub 的 Actions 頁面手動執行 **demo-pages** workflow，並輸入確認文字 `PUBLISH-SYNTHETIC-DEMO`。

`docs/TODO-history-cleanup.md` 標示為 `CLEANED` 之前，這個 workflow 的第一步（`scripts/history_guard.py --action pages --strict`）會讓它直接失敗；本機的 `build_demo.py` 也會響鈴提醒，但不會擋住建置。

這個 workflow 只會建置已提交的原始碼與 synthetic 匯出，而且只能手動觸發（CI 上沒有私有資料可比對，所以真實值的檢查要在本機做）。
