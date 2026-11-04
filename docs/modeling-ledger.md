# 模組總表（modeling ledger）

> 由 `data/modeling_ledger.json` 產生（`python scripts/render_ledger.py`）。要改請改 JSON，測試會檢查兩者一致。只放結構與成熟度，不含任何遊戲數值。

這張表回答「離完整的企業經營模擬還差多少」，也是 agent 的工作清單：每次挑一列，照 [`docs/upgrade-protocol.md`](upgrade-protocol.md) 升一級。

## 摘要

* 共 49 個模組：verified（已驗證） 5、literature（文獻） 7、heuristic（練習規則） 11、not-modeled（未建） 26。
* 真實遊戲：實測 19、推斷 28、未知 2。推斷的部分一律「未證實 · 待擷取」。
* 真實遊戲有（實測或推斷）但我們完全沒做：24 個。
* heuristic（練習規則，可能被誤當成真實因果）：11 個，其中行為規則 4 個、佔位會計規則 6 個、情境假設 1 個。

## 成熟度與種類

| 成熟度 | 意思 |
|---|---|
| verified（已驗證） | Captured from the game and reproduced (or fitted on game data and passed hold-out validation). |
| literature（文獻） | Functional form backed by published literature; coefficients not calibrated on this game. |
| heuristic（練習規則） | Practice rule from general business sense; no literature, no calibration. Lowest rung. Placeholder accounting rules (structure from game parameters, combination unverified) are heuristic too. |
| not-modeled（未建） | The real game has it; this engine does not. |

| 種類 | 意思 |
|---|---|
| behaviour | A causal response (a lever moves demand, retention ...). Heuristic behaviour is the riskiest: it can be mistaken for real cause and effect. |
| accounting | A bookkeeping rule. Upgrades straight to verified by a controlled experiment; literature does not apply. |
| information | Buys or shows information; changes no number of the quarter. |
| qualitative | Text or planning decisions; no known numeric effect. |
| scenario | An assumption the player chooses (rival behaviour). Results are conditional on it. |

規則：Structure and maturity only. No game values, no market data, no fitted coefficients. real_status: measured = seen in the captured Q1 menu or reproduced by an experiment; inferred = a client screen is registered but was not seen in Q1, and/or a public teaching source describes it (unverified until captured); unknown = no evidence either way. Anything inferred stays 'unverified, awaiting capture' until a later quarter is captured. Downstream numbers always take the weakest maturity of their inputs.

## 總表

### 行銷

| 模組 | 真實遊戲 | 對應畫面 | 我們的成熟度 | 我們現在有什麼 | 升級下一步 | 預計哪季可擷取 |
|---|---|---|---|---|---|---|
| **廣告預算與累積效果**<br>`marketing.ad_budget` · behaviour | 推斷 · 未證實<br>Media and ad screens are registered; public teaching sources describe advertising decisions. | `LocalMedia`, `RegionalMedia`, `ModifyAd` | literature（文獻） | Goodwill stock with carryover; power or ADBUDG response with diminishing returns (demand chain). | To verified: fit ad_elasticity and carryover on Q2+ data; keep the literature ranges as priors. | Q2+ (unverified · awaiting Q2 capture) |
| **品牌設計（類型與元件）**<br>`marketing.brand_design` · behaviour | 實測<br>Design Brand is a decision screen in the captured Q1 menu. | `ModifyBrand`, `BrandJudgment (report)` | literature（文獻） | Brand type and components chosen per brand; fit enters the demand chain; component choice also drives the (heuristic) unit cost. | To verified: relate brand-judgment scores to sales once Q2 reports are captured; fit the quality term. | Q1 (captured) |
| **定價**<br>`marketing.pricing` · behaviour | 推斷 · 未證實<br>A Pricing screen is registered but was not in the Q1 menu; public teaching sources list pricing. | `Pricing`, `PriceJudgment (report)` | literature（文獻） | Price relative to willingness to pay enters the utility (price_sensitivity). | To verified: fit price_sensitivity on Q2+ price and sales variation. | Q2+ (unverified · awaiting Q2 capture) |
| **目標區隔選擇**<br>`marketing.segment_targeting` · behaviour | 實測<br>Target Segments is a decision screen in the captured Q1 menu. | `TargetSegments` | literature（文獻） | Each brand targets a segment; fit to other segments falls with need similarity (demand chain). | To verified: calibrate similarity_power and fit_weight on Q2+ brand-by-segment sales. | Q1 (captured) |
| **廣告媒體分配**<br>`marketing.media_mix` · behaviour | 推斷 · 未證實<br>Local, regional, social and search media screens are registered; public sources describe media selection. | `LocalMedia`, `RegionalMedia`, `SocialMedia`, `SearchEngineMarketing` | heuristic（練習規則） · `MediaMixHeuristic` | MediaMixHeuristic: split of each brand's budget across four media; efficiency (sum w sqrt(B_m))^2 / sum w^2 <= 1 scales the advertising that enters the demand chain. | To literature: replace the square-root rule with per-medium response curves (elasticity range from Sethuraman et al. 2011, shape from Vakratsas et al. 2004) plus a cross-media synergy term (Naik & Raman 2003); give coefficient ranges, not points; add sanity tests; update this row. | Q2+ (unverified · awaiting Q2 capture) |
| **廣告訊息與文案**<br>`marketing.ad_copy` · behaviour | 推斷 · 未證實<br>Ad design screen and ad judgment report are registered; public sources mention ad copy and appeals. | `ModifyAd`, `AdJudgment (report)`, `CompareAds (report)` | not-modeled（未建） | None (advertising has no message content). | To heuristic: message fit = similarity of the stressed benefits to the target segment's needs, multiplying ad effectiveness. | Q2+ (unverified · awaiting Q2 capture) |
| **網路行銷（網頁、流量、社群）**<br>`marketing.internet` · behaviour | 推斷 · 未證實<br>Web page, traffic and productivity screens are registered. | `DesignWebPage`, `WebTraffic`, `WebProductivity`, `SimpleInternetMarketing` | not-modeled（未建） | None beyond the web center's distribution weight. | To heuristic: web traffic budget raises web-channel coverage with diminishing returns; page quality multiplies conversion. | Q2+ (unverified · awaiting Q2 capture) |
| **市場調查購買**<br>`marketing.market_research` · information | 推斷 · 未證實<br>Market research purchase screens are registered; public sources list a research budget. | `BuyMarketResearch`, `FollowUpStudy`, `SourceStudy`, `VarianceStudy` | not-modeled（未建） | None (all research data the pack holds is visible). | To heuristic: a cost line plus gating which reports are shown; no effect on demand. | Q2+ (unverified · awaiting Q2 capture) |
| **促銷（回饋金、贈品、店頭陳列）**<br>`marketing.promotions` · behaviour | 推斷 · 未證實<br>Rebate and point-of-purchase fields on Pricing; a Promotions screen is registered. | `Pricing`, `Promotions` | not-modeled（未建） | None. | To heuristic: rebate lowers the effective price for the share of buyers who redeem it, and costs rebate x redeemed units; free gift as a fixed cost per unit with a small attraction lift. | Q2+ (unverified · awaiting Q2 capture) |

### 通路

| 模組 | 真實遊戲 | 對應畫面 | 我們的成熟度 | 我們現在有什麼 | 升級下一步 | 預計哪季可擷取 |
|---|---|---|---|---|---|---|
| **開店（設立成本）**<br>`channel.store_opening` · accounting | 實測<br>Open Stores is a decision screen in Q1; opening cost reproduced by EXP-11. | `OpenSalesOffice` | verified（已驗證） | Opening cost = setup cost of newly opened stores (cost_model). | Keep: re-run EXP-11 if the screen changes in a later quarter. | Q1 (captured) |
| **網路銷售中心（設立成本）**<br>`channel.web_center_opening` · accounting | 實測<br>Open Web Sales Center is a decision screen in Q1; opening cost reproduced by EXP-12. Not found in public descriptions. | `OpenWebcenter` | verified（已驗證） | Opening cost = setup cost of newly opened web centers. | Keep: re-run EXP-12 if the screen changes. | Q1 (captured) |
| **通路覆蓋對需求的效果**<br>`channel.distribution_coverage` · behaviour | 推斷 · 未證實<br>A channel demand report is registered; the effect of an open outlet on demand is not observable in Q1. | `ChannelDemand (report)` | literature（文獻） | Coverage = 1 - (1 - store)(1 - web weight x web), raised to the distribution elasticity. | To verified: fit distribution_elasticity and web_weight on Q2+ city-level sales. | Q2 settlement (unverified · awaiting Q2 capture) |
| **通路租金**<br>`channel.outlet_lease` · accounting | 實測<br>Lease cost is a field on the Q1 outlet screens; when it is charged was not observed (EXP-11/12 showed none in the opening quarter). | `OpenSalesOffice`, `OpenWebcenter` | heuristic（練習規則） | Placeholder: lease of outlets open at quarter start. | To verified (accounting skips literature): read the Q2 income statement after a Q1 opening; reproduce the lease row with zero residual. | Q2 settlement (unverified · awaiting Q2 capture) |

### 業務人力

| 模組 | 真實遊戲 | 對應畫面 | 我們的成熟度 | 我們現在有什麼 | 升級下一步 | 預計哪季可擷取 |
|---|---|---|---|---|---|---|
| **業務薪酬、佣金與留任**<br>`sales_force.compensation` · behaviour | 推斷 · 未證實<br>Industry Sales Force Compensation is a report in the Q1 menu (measured); the decision screen (SalesForceCompensation) is registered but not seen. | `InitialSalesForceCompensation (Q1 report)`, `SalesForceCompensation` | heuristic（練習規則） | SalesForceHeuristic: quit rate falls as pay (salary and commission) rises against a reference; salaries and commission are expenses. | To literature: commission share after Coughlan & Narasimhan 1992; turnover direction after Lucas et al. 1987 and Griffeth et al. 2000. No published pay-to-turnover elasticity was found, so retention may stay heuristic until Q2+ data; say so in the row. | Q2+ (unverified · awaiting Q2 capture) |
| **業務編制與招募**<br>`sales_force.staffing` · behaviour | 推斷 · 未證實<br>Hire Sales People is registered but not in the Q1 menu; public sources list the number of salespeople employed. | `HireSalesPeople`, `DemandProjection` | heuristic（練習規則） | SalesForceHeuristic: headcount and training give selling effort 1 + max_lift x (1 - exp(-force per market / scale)), multiplying the attraction of our offers; hiring and severance costs. | To literature: replace the effort curve with a power response whose elasticity range follows Albers et al. 2010 (about 0.31 mean), shape after Lodish 1971; give ranges; sanity tests; update this row. | Q2+ (unverified · awaiting Q2 capture) |
| **業務訓練**<br>`sales_force.training` · behaviour | 推斷 · 未證實<br>Special Programs (training, demo kit, contest) is registered; public sources list training. | `SpecialPrograms` | heuristic（練習規則） | SalesForceHeuristic: training builds a decaying skill stock that raises effective selling force. | To literature: bound the training lift with the general-training effect size of Arthur et al. 2003 (not sales-specific; mark that); add sanity tests. | Q2+ (unverified · awaiting Q2 capture) |
| **網路業務人員**<br>`sales_force.web_sales` · behaviour | 推斷 · 未證實<br>Hire Web Sales People is registered; demand projection screens have per-web-salesperson fields. | `HireWebSalesPeople`, `DemandProjectionNextQuarter` | not-modeled（未建） | None (the sales force is company-wide). | To heuristic: split selling effort into store and web forces; web effort applies to web coverage only. | Q2+ (unverified · awaiting Q2 capture) |

### 人資（其他）

| 模組 | 真實遊戲 | 對應畫面 | 我們的成熟度 | 我們現在有什麼 | 升級下一步 | 預計哪季可擷取 |
|---|---|---|---|---|---|---|
| **主管薪酬、員工參與與人資調查**<br>`hr.executive_and_culture` · behaviour | 推斷 · 未證實<br>Executive compensation, employee involvement and HR survey screens are registered. | `ExecutiveCompensation`, `EmployeeInvolvement`, `HRSurvey` | not-modeled（未建） | None. | To heuristic only if a numeric effect is observed in a captured report; otherwise keep as qualitative. | Q3+ (unverified · awaiting capture) |
| **生產工人薪酬與生產力**<br>`hr.production_workers` · behaviour | 推斷 · 未證實<br>Industry Production Worker Compensation is a Q1 report; worker compensation and productivity screens are registered. | `InitialWorkersCompensation (Q1 report)`, `WorkersCompensation`, `OperatingCapacity` | not-modeled（未建） | None (labour is a fixed per-unit amount inside the unit cost). | To heuristic: worker pay against a reference sets productivity and turnover; productivity scales usable capacity. | Q2+ (unverified · awaiting Q2 capture) |

### 生產製造

| 模組 | 真實遊戲 | 對應畫面 | 我們的成熟度 | 我們現在有什麼 | 升級下一步 | 預計哪季可擷取 |
|---|---|---|---|---|---|---|
| **固定產能投資**<br>`production.fixed_capacity` · accounting | 實測<br>Fixed Capacity is a Q1 decision screen; capacity cost reproduced by EXP-02. | `FixedCapacity` | verified（已驗證） | Capacity option cost; capacity per quarter = units/day x days per quarter; usable next quarter. | Keep. | Q1 (captured) |
| **設計與開線費**<br>`production.design_cost` · accounting | 實測<br>Design and setup cost are Q1 brand-screen parameters; when they are charged is unverified. | `ModifyBrand` | heuristic（練習規則） | Placeholder: design cost per new brand. | To verified (accounting): match the Q2 income statement after designing one brand in Q1. | Q2 settlement (unverified · awaiting Q2 capture) |
| **單位生產成本**<br>`production.unit_cost` · accounting | 實測<br>Component prices, cost adjustment, minimum direct labour and overhead are Q1 brand-screen parameters; how they combine is unverified. | `ModifyBrand`, `CostOfProduction (report)` | heuristic（練習規則） | Placeholder: sum(component price) x cost adjustment + minimum labour + minimum overhead. | To verified (accounting): read the Q2 cost-of-production report for a known brand; reproduce it with zero residual. | Q2 settlement (unverified · awaiting Q2 capture) |
| **工廠與倉庫地點**<br>`production.factory_location` · accounting | 推斷 · 未證實<br>Factory and warehouse location screens are registered; public sources mention plant location. | `FactoryLocation`, `WarehouseLocation` | not-modeled（未建） | None (one factory, no location). | To heuristic: shipping cost per unit by distance band; a second factory adds fixed cost. | Q3+ (unverified · awaiting capture) |
| **營運產能、加班與排班**<br>`production.operating_capacity` · behaviour | 推斷 · 未證實<br>Operating capacity and overtime screens are registered. | `OperatingCapacity`, `Overtime`, `ExtFactorySimulation` | not-modeled（未建） | None (usable capacity = fixed capacity). | To heuristic: operating rate below fixed capacity; overtime adds capacity at a premium labour cost. | Q2+ (unverified · awaiting Q2 capture) |
| **品質、檢驗與重工**<br>`production.quality` · behaviour | 推斷 · 未證實<br>Inspection, rework and corrective-action screens and quality-cost reports are registered; public sources mention product quality. | `InspectQuality`, `ComponentRework`, `CorrectiveActions`, `ImprovementActions`, `QualityCosts (report)`, `WarrantyCosts (report)` | not-modeled（未建） | None (quality is fixed at 1 in the demand chain). | To heuristic: defect rate falls with inspection and improvement spend; defects cost warranty and lower the quality term. | Q3+ (unverified · awaiting capture) |
| **生產規則與排程**<br>`production.scheduling` · behaviour | 推斷 · 未證實<br>Production rules, control system and changeover screens are registered; scheduling is common to business games. | `ProductionRules`, `ProductionControlSystem`, `ImproveChangeover`, `FactoryEfficiency` | not-modeled（未建） | None (production = planned units, capped by capacity). | To heuristic: changeover loss per brand produced, reduced by changeover investment. | Q3+ (unverified · awaiting capture) |

### 供應鏈

| 模組 | 真實遊戲 | 對應畫面 | 我們的成熟度 | 我們現在有什麼 | 升級下一步 | 預計哪季可擷取 |
|---|---|---|---|---|---|---|
| **庫存控制、補貨點與出清**<br>`supply.inventory` · accounting | 推斷 · 未證實<br>Inventory control, replenishment and sell-off screens are registered. | `InventoryControl`, `TargetReplenishPoint`, `SellUnwantedInventory` | not-modeled（未建） | Unsold units carry over; no holding cost, no replenishment rule. | To heuristic: holding cost per unit carried; sell-off at a discount. | Q2+ (unverified · awaiting Q2 capture) |
| **前置期與供應中斷**<br>`supply.lead_time_disruption` · behaviour | 未知<br>Risk and cost-trend screens are registered; no lead-time field has been seen. | `Risk* (risk screens)`, `CostTrends (report)` | not-modeled（未建） | None. The control plane can apply shocks as scenario events (capacity factor), which is a stress test, not a model. | Capture first; model only what a report shows. | unknown (unverified) |
| **採購、供應商與合約**<br>`supply.purchasing` · behaviour | 推斷 · 未證實<br>Supply-chain strategy, information system, contract and partner-payment screens are registered. | `SupplyChainStrategy`, `SupplyChainInformationSystem`, `ConfirmRFP`, `ConfirmLongRFP`, `PaymentToPartners` | not-modeled（未建） | None (components are bought at list price). | To heuristic: volume discount on component price; contract penalties as fixed costs. | Q3+ (unverified · awaiting capture) |

### 研發與產品線

| 模組 | 真實遊戲 | 對應畫面 | 我們的成熟度 | 我們現在有什麼 | 升級下一步 | 預計哪季可擷取 |
|---|---|---|---|---|---|---|
| **產品線（多品牌與相互侵蝕）**<br>`rnd.product_line` · behaviour | 實測<br>Several brands can be designed on the Q1 brand screen. | `ModifyBrand` | literature（文獻） | Several brands per firm; they compete for the same buyers inside the logit (cannibalisation). | To verified: check cannibalisation against Q2+ brand-level sales. | Q1 (captured) |
| **研發新功能**<br>`rnd.feature_development` · behaviour | 推斷 · 未證實<br>Feature R&D screens are registered; Q1 component data carry an appearance quarter and a project cost. | `FeatureRD`, `ConfirmRD` | not-modeled（未建） | Components can carry an availability quarter in the pack; project cost is not charged. | To heuristic: charge project cost and make the component available after a fixed delay. | Q2+ (unverified · awaiting Q2 capture) |

### 財務

| 模組 | 真實遊戲 | 對應畫面 | 我們的成熟度 | 我們現在有什麼 | 升級下一步 | 預計哪季可擷取 |
|---|---|---|---|---|---|---|
| **定存**<br>`finance.cd` · accounting | 實測<br>Certificate of Deposit is a Q1 decision screen; reproduced by EXP-01. | `CD` | verified（已驗證） | Balance and interest (cost_model). | Keep (the withdraw term was not varied: re-test when convenient). | Q1 (captured) |
| **增資（股票）**<br>`finance.stock` · accounting | 實測<br>Closely Held Stock is in the Q1 menu; the raise is a view identity. | `Stock` | verified（已驗證） | Raised = sum(shares x price) (derived identity). | Keep. | Q1 (captured) |
| **緊急貸款**<br>`finance.emergency_loan` · accounting | 實測<br>An emergency-loan rate field appears on the Q1 pro-forma cash flow; the rule was not observed. | `ProFormaCashFlow` | heuristic（練習規則） | Placeholder: covers negative cash; no interest charged. | To verified (accounting): observe a quarter that ends with negative cash (only if it happens naturally; never forced). | unknown (unverified) |
| **所得稅**<br>`finance.tax` · accounting | 實測<br>A tax-rate field appears on the Q1 pro-forma cash flow; the rule was not observed. | `ProFormaCashFlow`, `IncomeStatement (report)` | heuristic（練習規則） | Placeholder: max(pretax, 0) x tax rate. | To verified (accounting): reproduce the tax row of the first profitable quarter's income statement. | first profitable settlement (unverified) |
| **外匯與多幣別資金**<br>`finance.currency` · accounting | 推斷 · 未證實<br>Currency fund screen and exchange-rate report are registered (probably international editions only). | `CurrencyFunds`, `ExchangeRates (report)` | not-modeled（未建） | None (one currency). | Only if a captured course shows it. | unknown (unverified) |
| **股利**<br>`finance.dividends` · accounting | 推斷 · 未證實<br>A Dividends screen is registered; dividends are common to business games. | `Dividends` | not-modeled（未建） | None. | To heuristic: a cash outflow; to verified by experiment once the screen opens. | Q3+ (unverified · awaiting capture) |
| **短期與長期貸款**<br>`finance.loans` · accounting | 推斷 · 未證實<br>Short- and long-term loan screens are registered; public sources describe external funding. | `ShortTermLoan`, `LongTermLoan` | not-modeled（未建） | None (only the emergency loan). | To heuristic: borrow and repay with an interest rate from the pack; to verified by experiment once the screen opens. | Q2+ (unverified · awaiting Q2 capture) |
| **創投募資談判**<br>`finance.venture_capital` · behaviour | 推斷 · 未證實<br>Described in public teaching sources (business plan and equity negotiation); no matching decision screen has been identified. | （無） | not-modeled（未建） | Stock issue at a price the player enters. | Capture first; it may be a classroom activity outside the software. | unknown (unverified) |

### 會計報表

| 模組 | 真實遊戲 | 對應畫面 | 我們的成熟度 | 我們現在有什麼 | 升級下一步 | 預計哪季可擷取 |
|---|---|---|---|---|---|---|
| **現金流量與損益表**<br>`accounting.cash_flow` · accounting | 實測<br>Pro-forma cash flow and income statement are in the Q1 menu (no what-if path). | `ProFormaCashFlow`, `ProFormaIncomeStatement`, `IncomeStatement (report)`, `CashFlow (report)` | heuristic（練習規則） | Simplified chain: revenue, interest and expenses into pretax, tax, net income and cash; it takes the weakest level of its rows. | To verified (accounting): reproduce every row of the Q2 statements; then each placeholder row above can be promoted. | Q2 settlement (unverified · awaiting Q2 capture) |
| **資產負債表**<br>`accounting.balance_sheet` · accounting | 實測<br>Pro-forma balance sheet is in the Q1 menu. | `ProFormaBalanceSheet`, `BalanceSheet (report)` | not-modeled（未建） | None (state keeps cash, CD, capacity, stock, inventory, but no balance sheet). | To verified (accounting): build the sheet from state and reproduce the Q1/Q2 rows. | Q1 (captured) |

### 市場與競爭

| 模組 | 真實遊戲 | 對應畫面 | 我們的成熟度 | 我們現在有什麼 | 升級下一步 | 預計哪季可擷取 |
|---|---|---|---|---|---|---|
| **需求核心（區隔選擇與外部選項）**<br>`market.demand_core` · behaviour | 實測<br>Sales and market share are reported every quarter; the game's demand formula itself is not observable. | `Sales (report)`, `MarketShare* (report)` | literature（文獻） | LiteratureDemand: multinomial-logit / MCI attraction with an outside option (src/marketplace_sim/demand.py). | To verified: fit the coefficients on Q2+ demand panels (FittedDemand) and pass hold-out validation (MAPE <= 20 %, direction hit rate >= 70 %). | Q2 settlement (unverified · awaiting Q2 capture) |
| **對手行為**<br>`market.rival_behaviour` · scenario | 實測<br>Rivals are other teams; competitor reports are registered. | `Competitors* (reports)`, `CompetitorAnalysis` | heuristic（練習規則） | Bots with fixed rules (BaselineBot, RandomBot, price factors) chosen as opponents; a replay of real rival offers is reserved for the private Q2+ panel. Results are conditional on the chosen rivals. | To verified: replay captured rival offers (control-plane replay) from Q2 on; bots stay as what-if assumptions. | Q2 settlement (unverified · awaiting Q2 capture) |
| **市場潛量成長與季節性**<br>`market.potential_growth` · behaviour | 未知<br>Q1 market potential is a captured parameter; how it changes over quarters is unknown. An economic-index report is registered. | `MarketSize`, `EconomicIndexes (report)` | not-modeled（未建） | Constant: quarterly potential = 12-month size / 4 every quarter. | Capture the Q2 market-size screen and compare; model growth only from observed change. | Q2 (unverified · awaiting Q2 capture) |

### 策略與規劃

| 模組 | 真實遊戲 | 對應畫面 | 我們的成熟度 | 我們現在有什麼 | 升級下一步 | 預計哪季可擷取 |
|---|---|---|---|---|---|---|
| **需求預測與產銷規劃工具**<br>`planning.demand_projection` · information | 推斷 · 未證實<br>Demand projection and factory simulation screens are registered; public sources describe a demand forecast by brand. | `DemandProjection`, `FactorySimulation`, `ProFormaDivisionProfitability` | not-modeled（未建） | The preview (calculate) shows the engine's own result instead. | No engine change needed; a UI aid only. | Q2+ (unverified · awaiting Q2 capture) |
| **平衡計分卡與排名**<br>`strategy.balanced_scorecard` · information | 推斷 · 未證實<br>Scorecard and standing reports are registered; public sources describe a cumulative balanced scorecard. | `BalancedScorecard`, `CumulativeBalancedScorecard`, `PlayersStanding` | not-modeled（未建） | Game mode follows one objective (cash, share or profit). | To heuristic: a weighted score of the report lines, weights labelled as practice; to verified only from captured scorecards. | Q1 settlement (unverified · awaiting capture) |
| **競爭、夥伴與風險分析**<br>`strategy.competitor_and_risk_analysis` · qualitative | 推斷 · 未證實<br>Competitor, partner, SWOT and risk screens are registered. | `CompetitorAnalysis`, `PartnerAnalysis`, `SWOTAnalysis`, `Risk* (risk screens)` | not-modeled（未建） | None. | Keep out of the numbers. | Q3+ (unverified · awaiting capture) |
| **策略規劃（使命、文化、策略主軸、戰術連結）**<br>`strategy.planning_statements` · qualitative | 實測<br>Mission, culture, objectives, strategic thrusts and tactic-strategy links are Q1 decision screens (text and choices). | `Mission`, `Culture`, `Problem`, `CorporateObjectives`, `StrategicThrusts*`, `TacticStrategyLinks*`, `BasesCompetitiveAdvantage` | not-modeled（未建） | None. | Keep out of the numbers unless a captured report shows a numeric effect; at most feed a scorecard. | Q1 (captured) |
| **團隊組織（職責、規範、個人目標）**<br>`strategy.team_organization` · qualitative | 實測<br>Executive responsibilities, team norms and personal goals are Q1 decision screens. | `ExecutiveResponsibilities`, `TeamNorms`, `PersonalGoals` | not-modeled（未建） | None. | Keep out of the numbers. | Q1 (captured) |

## 來源

E- = 本專案已擷取的證據（只用畫面名稱與欄位名）；P- = 公開教學資料對該模擬的文字描述；R- = 企業模擬的綜述與公開產品說明；L- = 反應函數文獻。

* **E-Q1** — Captured Q1 menu (docs/module-map.md section 1): screen names only.
* **E-REG** — Client screen registry (docs/module-map.md section 2; field names in docs/decision-catalog.md): the screen exists in the delivered client; whether a course shows it, and when, is unverified.
* **E-EXP** — Controlled experiments EXP-01, EXP-02, EXP-11, EXP-12 (docs/experiments/).
* **P-HALES** — Hales, C. Syllabus 'Managerial Game (Business Management)', University of Rzeszow, using Cadotte, The Business Management Simulation (2005) and Cadotte & Bruce, The Management of Strategy in the Marketplace (2008). https://www.ur.edu.pl/files/ur/import/Import/2012/7/MANAGERIAL-GAME-(BUSINESS-MANAGEMENT).pdf
* **P-IMPERIAL** — Imperial College London, Educational Development Unit, case study 'Business Simulation'. https://www.imperial.ac.uk/staff/educational-development/teaching-toolkit/anatomy-of-assessment/case-studies/business-simulation/
* **P-JAMS2003** — Book review of The Marketplace Game, Journal of the Academy of Marketing Science, Winter 2003 (reviewer attribution unclear; partially verified).
* **R-GOOSEN1999** — Goosen, K.R., Jensen, R. & Wells, R.A. (1999). Purpose and learning benefits of business simulations: a design and development perspective. Developments in Business Simulation and Experiential Learning 26 (reports Keys & Biggs 1990: price, R&D and production scheduling common to all ten games compared).
* **R-FARIA2009** — Faria, A.J., Hutchinson, D., Wellington, W.J. & Gold, S. (2009). Developments in business gaming: a review of the past 40 years. Simulation & Gaming 40(4), 464-487.
* **R-KEYS1990** — Keys, B. & Wolfe, J. (1990). The role of management games and simulations in education and research. Journal of Management 16(2), 307-336.
* **R-CAPSIM** — Capsim, Capstone team member guide, 'Company Departments' (public guide): R&D, marketing, production, finance; optional HR and TQM modules feeding a balanced scorecard.
* **R-MARKSTRAT** — StratX, Markstrat public description: brand portfolio, R&D projects, production, price, advertising, sales force size and channel allocation, market research.
* **L-SETHURAMAN2011** — Sethuraman, R., Tellis, G.J. & Briesch, R. (2011). How well does advertising work? Generalizations from meta-analysis of brand advertising elasticities. Journal of Marketing Research 48(3), 457-471 (mean short-term 0.12, long-term 0.24).
* **L-LITTLE1970** — Little, J.D.C. (1970). Models and managers: the concept of a decision calculus. Management Science 16(8), B466-B485 (ADBUDG).
* **L-CLARKE1976** — Clarke, D.G. (1976). Econometric measurement of the duration of advertising effect on sales. Journal of Marketing Research 13, 345-357.
* **L-KOHLER2017** — Kohler, C., Mantrala, M.K., Albers, S. & Kanuri, V.K. (2017). A meta-analysis of marketing communication carryover effects. Journal of Marketing Research 54(6), 990-1008.
* **L-NAIK2003** — Naik, P.A. & Raman, K. (2003). Understanding the impact of synergy in multimedia communications. Journal of Marketing Research 40(4), 375-388.
* **L-VAKRATSAS2004** — Vakratsas, D., Feinberg, F.M., Bass, F.M. & Kalyanaram, G. (2004). The shape of advertising response functions revisited. Marketing Science 23(1), 109-119.
* **L-ALBERS2010** — Albers, S., Mantrala, M.K. & Sridhar, S. (2010). Personal selling elasticities: a meta-analysis. Journal of Marketing Research 47(5), 840-853 (mean about 0.31 after method correction).
* **L-LODISH1971** — Lodish, L.M. (1971). CALLPLAN: an interactive salesman's call planning system. Management Science 18(4-II), P25-P40.
* **L-ZOLTNERS2004** — Zoltners, A.A., Sinha, P. & Lorimer, S.E. (2004). Sales Force Design for Strategic Advantage. Palgrave Macmillan.
* **L-ARTHUR2003** — Arthur, W. Jr., Bennett, W., Edens, P.S. & Bell, S.T. (2003). Effectiveness of training in organizations: a meta-analysis. Journal of Applied Psychology 88(2), 234-245 (general training, not sales-specific).
* **L-COUGHLAN1992** — Coughlan, A.T. & Narasimhan, C. (1992). An empirical analysis of sales-force compensation plans. Journal of Business 65(1), 93-121.
* **L-LUCAS1987** — Lucas, G.H., Parasuraman, A., Davis, R.A. & Enis, B.M. (1987). An empirical study of salesforce turnover. Journal of Marketing 51(3), 34-59.
* **L-GRIFFETH2000** — Griffeth, R.W., Hom, P.W. & Gaertner, S. (2000). A meta-analysis of antecedents and correlates of employee turnover. Journal of Management 26(3), 463-488 (pay satisfaction: direction only).
* **L-DEMAND** — docs/demand-literature.md (sources of the literature demand chain: multinomial logit / MCI attraction, outside option, distribution elasticity).
