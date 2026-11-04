# Q2 擷取清單（對帳準備）

> 由 `data/modeling_ledger.json` 產生（`python scripts/render_ledger.py`）。只列畫面、報表列名與要做的比對，不含任何遊戲數值。

Q2 結算回來時，照這張表擷取；擷取到的東西只放 `evidence/private/`，不進 repo。

## 怎麼對帳

1. 擷取下表各列的畫面與報表（照第一季的方式存成 private 檔）。
2. 另存一份 `evidence/private/reconcile/q2.json`（private，不進 repo），格式：
   * `plans`：Q1、Q2 實際送出的決策，各自寫成引擎的 plan（與 `examples/synthetic/plans/*.yaml` 同欄位）；
   * `pack`：私有參數包的路徑（預設 `evidence/private/model/pack.json`）；
   * `statements`：Q2 報表各列的值，`income` / `balance` / `cash` 三組，鍵是報表列 id（例如 `sales`、`cogs`）。
3. 執行 `pytest tests/test_reconcile.py`。它用私有參數包重跑 Q1、Q2（打開應計會計選項），把引擎各列折算成報表列，逐列比對，結果只寫狀態（match / differs / not-modeled / missing），存到 `evidence/private/reconcile/q2-result.json`；不印任何數值。
4. 升級規則（`docs/upgrade-protocol.md`）：規則型的列要在「不是結構性 0」的一季重現（match），再用下一季當保留驗證，才能升到 verified；一季 match 只算候選。

## 要擷取的列

| 模組 | 現在 | 要擷取的畫面 | 要讀的報表列 | 比對後要做什麼 |
|---|---|---|---|---|
| **通路覆蓋對需求的效果**<br>`channel.distribution_coverage` | literature（文獻） | `ChannelDemand (report)` | 見畫面 | To verified: fit distribution_elasticity and web_weight on Q2+ city-level sales. |
| **需求核心（區隔選擇與外部選項）**<br>`market.demand_core` | literature（文獻） | `Sales (report)`, `MarketShare* (report)` | 銷售報表：各產品、各客群的銷量 | To verified: fit the coefficients on Q2+ demand panels (FittedDemand) and pass hold-out validation (MAPE <= 20 %, direction hit rate >= 70 %). |
| **廣告預算與累積效果**<br>`marketing.ad_budget` | literature（文獻） | `LocalMedia`, `RegionalMedia`, `ModifyAd` | 銷售報表：不同廣告預算下的銷量 | To verified: fit ad_elasticity and carryover on Q2+ data; keep the literature ranges as priors. |
| **網路行銷（網頁、流量、社群）**<br>`marketing.internet` | literature（文獻） | `DesignWebPage`, `WebTraffic`, `WebProductivity`, `SimpleInternetMarketing` | IS `inet_exp` | To verified: the game's web marketing screens and their effect on web sales from Q2+ (fit the elasticity inside the range). |
| **廣告媒體分配**<br>`marketing.media_mix` | literature（文獻） | `LocalMedia`, `RegionalMedia`, `SocialMedia`, `SearchEngineMarketing` | 見畫面 | To verified: estimate the media weights w_m (and test a cross-media synergy term, Naik & Raman 2003) on Q2+ media-level spend and sales; pass hold-out validation. Still uncalibrated: the weights (neutral equal default; no published general ranking of these media). |
| **定價**<br>`marketing.pricing` | literature（文獻） | `Pricing`, `PriceJudgment (report)` | 銷售報表：不同售價下的銷量 | To verified: fit price_sensitivity on Q2+ price and sales variation. |
| **學習曲線**<br>`production.learning_curve` | literature（文獻） | `BrandManagement` | 品牌畫面的單位成本（不同累積產量） | To verified: compare unit costs across Q2+ quarters with known cumulative volume and fit the game's parameter. |
| **加班**<br>`production.overtime` | literature（文獻） | `OperatingCapacity`, `Overtime`, `ExtFactorySimulation` | 見畫面 | To verified: the game's overtime capacity and cost from Q2+ (fit the elasticities inside the range). |
| **研發新功能**<br>`rnd.feature_development` | literature（文獻） | `FeatureRD`, `ConfirmRD` | IS `rd` | Model the game's project cost and availability delay once FeatureRD is captured (Q2+); to verified then. |
| **業務編制與招募**<br>`sales_force.staffing` | literature（文獻） | `HireSalesPeople`, `DemandProjection` | IS `sf`；銷售報表 | To verified: fit the elasticity and the reference scale on Q2+ sales by quarter and headcount; the game's hiring cost rule needs the HireSalesPeople calculate (awaiting Q2 capture). |
| **需求預測與產銷規劃工具**<br>`planning.demand_projection` | literature（文獻） | `DemandProjection`, `FactorySimulation`, `ProFormaDivisionProfitability` | 見畫面 | To verified: the game's projection tool output against our estimate once captured (Q2+). |
| **庫存持有成本**<br>`supply.inventory_holding` | literature（文獻） | `InventoryControl`, `ProFormaCashFlow` | IS `other_exp`；報表參數 `inventoryTax` | To verified: read the game's holding or inventory-tax charge on a Q2+ statement with known ending inventory; reproduce it. |
| **補貨點與生產控制規則**<br>`supply.replenishment` | literature（文獻） | `InventoryControl`, `TargetReplenishPoint` | 見畫面 | To verified: the game's InventoryControl rule (max ending inventory, produce) from Q2+. |
| **損益表（應計基礎）**<br>`accounting.income_statement` | heuristic（練習規則） | `ProFormaIncomeStatement`, `IncomeStatement (report)` | IS 全部列（`reconcile.INCOME_ROWS`） | To verified (accounting): reproduce a Q2 income statement row by row with the accrual option. |
| **通路租金**<br>`channel.outlet_lease` | heuristic（練習規則） | `OpenSalesOffice`, `OpenWebcenter` | IS `so`; CF `so`（季初已開的店與網路中心） | Cannot be verified by arithmetic alone: needs the game's charge in the quarter after an opening. Read the Q2 statement after a Q1 opening; reproduce the lease row with zero residual. |
| **短期與長期貸款**<br>`finance.loans` | heuristic（練習規則） | `ShortTermLoan`, `LongTermLoan` | CF 借還款列；BS `short_loan`；IS `interest` | To verified: read the game's loan terms when the screens open (Q2+) and reproduce a loan's cash rows. |
| **所得稅**<br>`finance.tax` | heuristic（練習規則） | `ProFormaCashFlow`, `IncomeStatement (report)` | IS `e_income_before_taxes`, `loss`, `e_taxable_income`, `income_taxes`; CF `income_taxes` | Cannot be verified by arithmetic alone: needs the game's tax on a profitable quarter. First build the accrual income statement and carry-forward (structure measured), then reproduce the tax row of the first profitable settlement. |
| **生產工人薪酬與生產力**<br>`hr.production_workers` | heuristic（練習規則） | `InitialWorkersCompensation (Q1 report)`, `WorkersCompensation`, `OperatingCapacity` | 見畫面 | To literature: a verified wage elasticity of production (Krassoi Peach & Stanley 2009 meta-analysis: abstract only, value not verified). To verified: worker screens from Q2+. |
| **對手行為**<br>`market.rival_behaviour` | heuristic（練習規則） | `Competitors* (reports)`, `CompetitorAnalysis` | 見畫面 | To verified: replay captured rival offers (control-plane replay) from Q2 on; bots stay as what-if assumptions. |
| **廣告訊息與文案**<br>`marketing.ad_copy` | heuristic（練習規則） | `ModifyAd`, `AdJudgment (report)`, `CompareAds (report)` | 見畫面 | To literature: full text of Dall'Olio & Vakratsas 2023 (creative strategy and advertising elasticity; abstract has no numbers). To verified: the game's ad-copy screen from Q2+. |
| **市場調查購買**<br>`marketing.market_research` | heuristic（練習規則） | `BuyMarketResearch`, `FollowUpStudy`, `SourceStudy`, `VarianceStudy` | IS `mr` | To verified: the game's report list and prices once the market-research screen opens. |
| **促銷（回饋金、贈品、店頭陳列）**<br>`marketing.promotions` | heuristic（練習規則） | `Pricing`, `Promotions` | IS `rebates`；銷售報表 | To literature: a published perceived value of a rebate at purchase (none found; only choice shares from one experiment). Add gifts and display as further parts. To verified: Q2+ Promotions screen and the rebates row. |
| **設計與開線費**<br>`production.design_cost` | heuristic（練習規則） | `ModifyBrand` | IS `rd` 或 CF `production`（哪一列還沒確認） | Cannot be verified by arithmetic alone: when and where the game charges design cost (R&D row or production) is unobserved. Match the Q2 statements after designing one brand in Q1. |
| **閒置產能成本**<br>`production.excess_capacity` | heuristic（練習規則） | `ProFormaIncomeStatement` | IS `excess_capacity`（配合產能與產量） | To verified (accounting): read the row on a Q2 statement with known capacity and production, and reproduce it. |
| **營運產能：班別**<br>`production.operating_capacity` | heuristic（練習規則） | `OperatingCapacity`, `Overtime`, `ExtFactorySimulation` | 見畫面 | To literature: a verified relative output of later shifts (only accident risk found). To verified: the game's shift rules from Q2+. |
| **單位生產成本**<br>`production.unit_cost` | heuristic（練習規則） | `ModifyBrand`, `CostOfProduction (report)` | CF `production`；IS `cogs`（配合產量與售出量） | Cannot be verified by arithmetic alone: needs the game's cost of production for a known brand and volume (Q2 cost-of-production report or the FactorySimulation calculate). |
| **業務薪酬、佣金與留任**<br>`sales_force.compensation` | heuristic（練習規則） | `InitialSalesForceCompensation (Q1 report)`, `SalesForceCompensation` | IS `sf` | To literature: a published base quit rate for comparable sales jobs and a pay-index definition. To verified: Q2+ headcount after pay changes. |
| **業務訓練**<br>`sales_force.training` | heuristic（練習規則） | `SpecialPrograms` | 見畫面 | To literature: a published dose-response or decay of sales training (Arthur et al. 1998 skill-decay review is a candidate, not yet verified). To verified: observe the SpecialPrograms effect from Q2 on. |
| **網路業務人員**<br>`sales_force.web_sales` | heuristic（練習規則） | `HireWebSalesPeople`, `DemandProjectionNextQuarter` | IS `wsc_exp`（推測） | To literature: an elasticity for web or phone selling (none found). To verified: HireWebSalesPeople from Q2+. |
| **平衡計分卡與排名**<br>`strategy.balanced_scorecard` | heuristic（練習規則） | `BalancedScorecard`, `CumulativeBalancedScorecard`, `PlayersStanding` | 見畫面 | To verified: capture the game's scorecard after a settlement and reproduce its formula. |
| **庫存出清**<br>`supply.inventory_selloff` | heuristic（練習規則） | `SellUnwantedInventory` | 見畫面 | To verified: observe the game's sell-off price on SellUnwantedInventory once it opens; no general published salvage rate applies, so no literature step. |
| **市場潛量成長與季節性**<br>`market.potential_growth` | not-modeled（未建） | `MarketSize`, `EconomicIndexes (report)` | 見畫面 | Kept not-modeled on purpose: whether the game's market grows or has seasons is unknown; capture first (ledger rule for 'unknown'). |

共 32 列。
