# 主持端（Game Master）使用指南

本機模擬器的「主持端」讓你像出題老師一樣設定世界：改參數、在某一季丟事件、指定對手行為，然後一鍵跑完多季，
得到每季報表與一份可離線開啟的 HTML 報告。所有範例都是**虛構數字**（`examples/synthetic/`），與任何真實遊戲無關。

> 本工具只在本機運算，不連任何線上系統。用你自己的私有參數包跑出來的結果，一律留在 `evidence/private/`。

## 1. 三分鐘上手

```powershell
# 列出內建情境範本
.\.venv\Scripts\mpsim.exe scenario templates

# 跑一個情境：每季摘要印在終端機，結果 JSON 與 HTML 寫到 outputs/
.\.venv\Scripts\mpsim.exe scenario run examples/scenarios/cost-rise.yaml --out outputs/scenarios

# 用瀏覽器打開 outputs/scenarios/cost-rise.html（不需網路）
```

內建範本（`examples/scenarios/`，全為虛構資料）：

| 檔案 | 情境 |
|---|---|
| `baseline.yaml` | 基準：示範計畫、平穩對手、無事件 |
| `cost-rise.yaml` | 成本上漲：Q3 起產能成本 +15%（兩季）、Q2 起零件 +9%、通路租金永久 +7% |
| `demand-decline.yaml` | 需求衰退：Q2 起所有區隔 −25%，Q3 區隔 3 再 −15% |
| `price-war.yaml` | 價格戰：Q2 起對手降價 20%，一家對手隨機出招 |
| `combined-shock.yaml` | 綜合衝擊：成本、需求、價格戰、利率、匯率、供應中斷疊加 |

## 2. 寫一個自己的情境

```powershell
.\.venv\Scripts\mpsim.exe scenario new my-world.yaml --params examples/synthetic
```

會產生一份**附註解的骨架**，逐欄說明如下：

| 欄位 | 說明 |
|---|---|
| `name` / `description` | 名稱與說明（名稱會成為輸出檔名） |
| `base_params` | 參數包資料夾（相對於情境檔）。虛構：`../synthetic`；私有：指向 `evidence/private/model` |
| `horizon` / `start_quarter` | 跑幾季、從第幾季開始 |
| `seed` | 亂數種子。**同一份情境＋同一個 seed，結果逐位元相同** |
| `overrides` | 參數覆寫，可限定季別：`{path, set\|scale\|add, from_quarter?, to_quarter?}` |
| `events` | 事件清單（見第 3 節），依列出順序疊加 |
| `competitors` | 對手：`baseline`（平穩）、`random`（隨機）、`replay`（重播真實資料，只能放私有目錄） |
| `our_policy` | 我方決策：`hold`（不動）、`fixed`（`default` ＋ 每季 `plans`）、`external`（資料夾內 `q<N>.yaml`） |

**參數路徑語法**（對應 `pack.json` 結構）：

* `finance.cd_rate_annual_percent`：一般欄位
* `capacity_options[*].cost`：清單中每一列
* `stores[key=N1-Northwick].setup_cost`：清單中指定的那一列
* `markets[*].segments.*.wtp`：字典的所有鍵

路徑對不到任何欄位時會直接報錯，以免打錯字卻毫無作用。

## 3. 事件

事件在**每季推進之前**套用，會標示在當季報表上（終端機的 `events:`、HTML 的 ⚑ 標記與事件清單、JSON 的
`events` 欄位）。

| type | target | 效果（magnitude = m） |
|---|---|---|
| `cost_shock` | `capacity` / `stores` / `web_centers` / `outlets` / `components` / `production` / `*` | 成本欄位 ×(1+m) |
| `demand_shock` | 區隔 id 或 `*` | 12 個月市場規模 ×(1+m) |
| `rate_change` | `cd` / `tax` / `emergency` | 年利率 + m 個百分點 |
| `fx_shock` | 區域代碼或 `*` | 當地願付價格 ×(1+m) |
| `competitor_price_cut` | 對手名稱或 `*` | 對手售價 ×(1+m)（降價用負數） |
| `supply_disruption` | `capacity` | 可用產能 ×(1−m)，m 介於 0 與 1 |

時間欄位：`from_quarter`（起始季；`quarter` 也可接受）與 `duration`（持續幾季，預設 1）。
例：`{type: cost_shock, from_quarter: 3, target: capacity, magnitude: 0.15, duration: 2, label: "機台漲價"}`

> 事件代表「假設」。數字的來源等級仍描述計算它的規則：例如產能成本 +15% 之後，`capex_capacity` 仍是 `[V]`
> （規則已驗證，輸入是你的假設），而營收永遠是 `[P]`，直到需求模型被估計並驗證。

## 4. 單次 what-if

不寫情境檔，直接對存檔改一個參數或丟一個事件，並與原狀並排比較：

```powershell
.\.venv\Scripts\mpsim.exe new --params examples/synthetic --out outputs/my-save.json
.\.venv\Scripts\mpsim.exe what-if outputs/my-save.json --decisions examples/demo/q1.yaml `
    --set "capacity_options[*].cost=x1.2" --set "finance.tax_rate_percent=+5" --event rate_change:cd:-1
```

`--set` 的值：`x1.2` 代表乘以 1.2，`+5` 或 `-5` 代表加減，其他代表直接設定。
`--event` 的格式是 `類型:目標:幅度`。

## 5. 讀報告

* **終端機**：每季的期末現金與來源等級，以及當季事件；最後印出摘要（期末現金、最低現金、累計淨利、資本支出、
  緊急貸款、各關鍵輸出的最弱等級、有事件的季別）。
* **HTML**（`<name>.html`）：單一檔案、無外部資源、深淺色自動切換。內容包括：
  * 現金與淨利折線，事件季以 ⚑ 標出；
  * 產能折線、事件清單、摘要表；
  * 全部明細表：顏色代表來源等級，滑鼠停在數字上會顯示公式來源。
* **JSON**（`<name>.result.json`，schema `marketplace-sim/scenario-result@1`）：完整資料，附 `fingerprint`
  （情境＋參數包的雜湊）供重現比對。

來源等級：`[V]` 已驗證（與伺服器實測零殘差）、`[D]` 推導、`[E]` 估計、`[P]` 佔位（僅示意，**不是預測**）。

## 6. 用你自己的資料（私有）

1. 把情境檔放在 `evidence/private/scenarios/`，`base_params: ../model`。
2. 輸出必須寫到 `private` 目錄底下，例如 `--out evidence/private/outputs/scenarios`。若輸出路徑不在私有目錄，
   程式會拒絕執行。
3. `replay` 對手的資料檔（真實對手決策）也只能放在 `private` 目錄。

`outputs/` 與 `evidence/private/` 都不進版本庫。

## 7. 每季參數變化

每季重建私有參數包時加上 `--quarter-label`，會自動與上一季比對：

```powershell
.\.venv\Scripts\mpsim.exe build-pack --out evidence/private/model --quarter-label Q2
```

終端機只印**不含數值**的摘要與紅旗。紅旗包括：
* 已驗證模組的參數變了，需重新校準；
* 欄位新增或刪除；
* 變動幅度 ≥ 25%。

含數值的完整報告寫在 `evidence/private/model/diffs/Q2-vs-Q1.md`。
也可以手動比較兩個參數包：`mpsim params diff <舊> <新>`。
