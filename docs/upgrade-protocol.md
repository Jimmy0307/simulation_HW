# 模組升級流程（upgrade protocol）

這份文件寫給 agent（也給人）照著做：從 [`docs/modeling-ledger.md`](modeling-ledger.md) 挑**一列**，把它升**一級**，
跑完清單上的測試，再提交。一次只升一列、一級。

成熟度由低到高：`not-modeled` → `heuristic` → `literature` → `verified`。
會計類（`kind: accounting`）的模組不經過 literature：會計規則沒有文獻可查，直接用受控實驗升到 verified。

## 0. 先懂框架（不要改框架）

* 介面：`src/marketplace_sim/business/base.py`。一個模組 = 一個類別，帶 `spec`（key、**每個 ledger 列各自的成熟度** `rows`、
  決策欄位、輸出、耦合點）和 `run(ModuleInput) -> ModuleResult`。一個實作可以同時有文獻部分和練習部分，
  每條輸出用「它背後那部分」的等級標示。
* 模組只能透過固定的**耦合點**影響一季（`base.py` 開頭有完整說明）：
  * 需求：`media_split[brand]`（各媒體的花費比例與彈性權重）、`selling_effort`；用到的需求耦合點中最弱的等級，
    套到需求下游的每個數字（銷量、市佔、營收、利潤、現金）。
  * 生產：`material_cost_factor`（乘在單位成本的材料部分）。
  * 供應：`inventory_release[brand]`（季初出清的件數，搭配 `salvage_fraction` 計收入）、`holding_rate`（季末庫存價值 × 費率）。
  * 現金：`expenses`、`income`、`revenue_rates`。
  * 其他：`state`、`lines`。
* 登記：`src/marketplace_sim/business/registry.py` 的 `IMPLEMENTATIONS`（key → 類別）。
  決策從 `plan.modules[key]` 進來；沒有實作的 key 會被拒絕，並回覆 ledger 裡的「升級下一步」。
* 係數：`data/module_defaults.json`（heuristic 的標示預設值）；pack 可以在 `modules.<key>` 覆寫。
* 總表：`data/modeling_ledger.json` 是唯一來源；`docs/modeling-ledger.md` 由 `scripts/render_ledger.py` 產生。
* 如果新模組需要的耦合點不在上面這些裡：**停下來**，先在 `docs/decisions-log.md` 寫明為什麼需要、會影響哪些下游，
  再在 `base.py` 加一個耦合點（加，不改舊的），並補一個「沒啟用時逐位元不變」的測試。

## 1. not-modeled → heuristic（建一個練習規則）

條件：ledger 該列的「升級下一步」寫的是 `To heuristic: ...`。

1. 在 `src/marketplace_sim/business/` 新增一個檔，類別名稱以 `Heuristic` 結尾，`spec.maturity = Maturity.HEURISTIC`。
   文件字串寫清楚每條規則的公式與「方向」，並寫明「no literature, no calibration」。
2. 所有輸出用 `Level.HEURISTIC`。來源字串寫公式和「heuristic」字樣。
3. 係數放進 `data/module_defaults.json`，每個模組附一句 `why`（為什麼取這個尺度）。不得放任何遊戲數值。
4. 在 `IMPLEMENTATIONS` 登記；在 `src/marketplace_sim/metrics.py` 登記新的報表列（level = HEURISTIC，`inputs` 寫上游）；
   費用列要加進 `_MODULE_OPEX`，讓 `cash_end` 的來源鏈包含它。
5. ledger 該列：`maturity` 改成 `heuristic`，`ours` 寫實作名稱與一句話規則，`next_step` 改成 `To literature: ...`
   （寫出要查哪類文獻）。跑 `python scripts/render_ledger.py`。
6. 前端：在 `frontend/src/ui/ModuleBoard.tsx` 為新模組加一個編輯器（決策編輯與遊戲模式側欄共用這個元件；
   模組總覽 `frontend/src/screens/Modules.tsx` 直接讀 ledger，不必改）。heuristic 的杆與結果一律帶「練習」徽章
   （`frontend/src/ui/Practice.tsx` 的 `PracticeBanner` / `PracticeBadge`），並在 `frontend/src/__tests__/` 加測試。
7. 測試（`tests/test_business_modules.py` 加一組，**是合理性測試，不是準確性測試**）：
   * 方向：加大投入 → 輸出往直覺方向動。
   * 單調與遞減：輸出對投入單調，邊際效果遞減（若規則如此）。
   * 極端值：0、上限、極大值都不爆走（有限、有界、不為負）。
   * 降級：啟用後，需求下游（units、share、revenue、net_income、cash_end）等級都是 `heuristic`。
   * 不啟用時：與沒有這個模組時逐位元相同（現有參考跑法）。
8. 在 `docs/decisions-log.md` 記一條：規則、方向、尺度怎麼選。

## 2. heuristic → literature（換成有文獻的形式）

條件：該列 `maturity = heuristic`、`kind = behaviour`，`next_step` 寫的是 `To literature: ...`。

1. 查公開、可引用的文獻（期刊、專書、後設分析）。**不得**使用：論壇實戰數字、任何人擷取的逐季遊戲資料、
   別屆或別隊的 dump、Marketplace Simulations 的畫面、參數或資料。
2. 從文獻定**函數形式**；係數只給**文獻範圍**（例如後設分析平均與區間），預設取範圍中點並標示。
   找不到文獻支持的部分維持 heuristic，並在 ledger 寫明「哪一段仍是 heuristic」。
3. 新類別（例如 `MediaMixLiterature`），`spec.maturity = Maturity.LITERATURE`，輸出 `Level.LITERATURE`；
   **同一個 key、同樣的耦合點**，在 `IMPLEMENTATIONS` 換掉舊類別。舊類別可刪（git 歷史保留）。
4. 係數改放 `data/module_defaults.json` 該模組下，附來源與範圍；把文獻寫進 `docs/demand-literature.md`
   或新的 `docs/<module>-literature.md`。
5. ledger：`maturity = literature`，`sources` 加 L- 來源（同時加進 `sources` 字典），`next_step` 改成
   `To verified: ...`（寫要用哪一季、哪個報表校準）。重新產生文件。
6. 測試：第 1 節的合理性測試全部保留並通過；另加「係數在文獻範圍內」與「範圍兩端都不爆走」。
7. decisions-log 記一條：採用的文獻、範圍、中點，以及仍未涵蓋的部分。

## 3. literature → verified（用遊戲資料校準）

條件：已擷取 Q2 或之後的資料（只放 `evidence/private/`），而且至少兩季可分出留出季。

1. 資料只讀 `evidence/private/`；擬合結果、係數、殘差也只寫在 `evidence/private/`。**不得**把任何真實數值寫進 repo。
2. 用前幾季擬合、最後一季留出驗證。門檻（與需求相同，`docs/demand-model-spec.md` §6）：
   留出季 MAPE ≤ 20 %、方向命中率 ≥ 70 %。沒過就**停在 literature**，在 ledger 寫明差多少。
3. 通過後：以 private 檔案載入（像 `FittedDemand` 一樣，讀檔時重新檢查門檻），等級 `ESTIMATED`
   （模組成熟度對應 verified）。repo 內只改程式路徑與 ledger。
4. ledger：`maturity = verified`，`real_status` 若仍是 inferred 改為 measured，`capture` 寫實際擷取季別，
   `next_step` 寫「Keep: 每季重新驗證」。
5. 測試：沒有 private 檔時跳過；有時檢查門檻與「沒過就拒絕」。publication gate 必須通過（含 `dist/`）。
6. decisions-log 記一條（只寫結果是否通過與門檻，不寫數值）。

## 4. 會計類：heuristic（佔位）→ verified（受控實驗）

先分清楚是哪一種：

* **恆等式**（例如現金流量：期初 + 各列帶號加總 = 期末）：規則本身不依賴遊戲參數。用擷取到的報表**結構**（列、正負號）
  對照，再在每次執行驗證殘差為 0（`tests/test_accounting.py`）即可升 verified。每一列仍保留自己的等級。
* **規則**（稅、租金、設計費、緊急貸款、單位成本）：恆等式成立不能證明遊戲用同一條規則，**一定要遊戲端數值**。
  不要只靠內部一致性硬升；能做的是「結構性零」分支：輸入為空時答案在任何規則下都是 0（例如沒開店就沒有租金），
  那個分支可標 verified，其餘維持原級並在 ledger 寫明缺什麼。

規則類的步驟：

1. 照 `docs/experiment-runbook.md` 設計一次只改一個輸入的實驗；只用遊戲本身的試算或結算，不得送出不必要的決策。
2. 在 `marketplace_sysid.cost_model` 實作規則，用實測值重現且殘差為 0；引擎模組改呼叫它，等級 `VERIFIED`。
3. 實驗紀錄寫 `docs/experiments/EXP-xx.md`（不含真實數值，依 publication gate 規則）；ledger 改 `verified`。

## 5. 每次升級都要跑

```
.venv/Scripts/python -m pytest -q
.venv/Scripts/python -m ruff check src tests scripts
.venv/Scripts/python -m mypy src
.venv/Scripts/python scripts/render_ledger.py --check
cd frontend && npx tsc --noEmit && npx vitest run
.venv/Scripts/python scripts/build_demo.py --base /simulation_HW/      # 含 publication gate（檢查 dist/）
```

全部通過才提交；commit 訊息寫「<模組 key>: <舊等級> → <新等級>」。

## 6. 硬規則（每一步都適用）

* heuristic 與 not-modeled 的輸出絕不偽裝成可信：等級照實標，下游取最弱。
* 畫面上 heuristic 一律帶「練習」徽章，並寫「練習用 · 規則暫定 · 真實關係待 Q2」。
* not-modeled 的決策在畫面上是鎖定狀態，點了說明原因與預計開放季別；引擎拒絕它的決策。
* 推斷的真實遊戲範圍一律標「未證實 · 待擷取」，直到真的擷取到。
* 不連遊戲擷取尚未開放的畫面；不改 git 歷史；private 不進 repo。
