# Module map (v2)

v1 is in `legacy/docs/module-map-v1.md`.

Two sources, kept separate:

1. **Rendered Q1 task list.** This is the left-menu tree in the six saved Quarter 1 pages (private HTML, 62 items).
   The server supplies the menu per quarter (`LeftMenu.leftMenuItems([user@quarter])`,
   `Resource.resourceList`), so later quarters can differ.
2. **Client class registry.** These are all screens the delivered client can render (`window.X = ….extend`,
   310 registrations in REA-verified modules). Whether a registered screen appears in a given quarter or
   course configuration is decided by the server and is **unknown** for quarters not captured.

## 1. Rendered Q1 tree (✎ = marked "decision screen" by the UI)

```
Welcome to Marketplace · Virtual Business World · Overview of Activities · Getting Started
Company Name ✎ (CompanyName)
Marketing Research
  Customer Needs (CustomerNeeds) · Use Pattern (UsePattern) · Price Willing to Pay (PriceWillingToPay) · Market Potential (MarketSize)
Strategic Planning
  Mission ✎ · Culture ✎ · Problem ✎ · Corporate Objectives ✎ · Financial Resources ✎
  Basis for Competitive Advantage ✎ (BasesCompetitiveAdvantage) · Corporate Strategic Thrusts ✎ · Summary of Strategy
Marketing
  Marketing Strategy: Strategic Thrusts ✎ (StrategicThrustsMarketing) · Target Segments ✎
  Brand Management: Design Brand ✎ (ModifyBrand)
  Tactic-Strategy Links ✎ (TacticStrategyLinksMarketing)
Human Resources
  Human Resource Strategy: Strategic Thrusts ✎
  Executive Team: Responsibilities ✎ · Team Norms ✎ · Personal Goals ✎
  Industry Sales Force Compensation (InitialSalesForceCompensation) · Industry Production Worker Compensation (InitialWorkersCompensation)
  Tactic-Strategy Links ✎
Sales Channel
  Sales Channel Strategy: Strategic Thrusts ✎
  Stores: Open Stores ✎ (OpenSalesOffice) · Web Sales Center: Open Web Sales Center ✎ (OpenWebcenter)
  Tactic-Strategy Links ✎
Manufacturing
  Manufacturing Strategy: Strategic Thrusts ✎ · Fixed Capacity ✎ (FixedCapacity) · Tactic-Strategy Links ✎
Accounting
  Cash Flow (ProFormaCashFlow) · Income Statement (ProFormaIncomeStatement) · Balance Sheet (ProFormaBalanceSheet)
Finance
  Finance Strategy: Strategic Thrusts ✎ · Closely Held Stock (Stock) · Certificate of Deposit ✎ (CD) · Tactic-Strategy Links ✎
Summary of Decisions (SummaryOfDecisions)
Final Check (FinalCheck)
Submit  (WrapUp)   ⛔ FINALIZATION, never click during analysis
```

## 2. Registered screens beyond the Q1 tree

**Decision screens not seen in Q1 (95), by area:**

* Marketing: `Pricing`, `Promotions`, `LocalMedia`, `RegionalMedia`, `SocialMedia`, `SearchEngineMarketing`,
  `SimpleInternetMarketing`, `DesignWebPage`, `WebTraffic`, `WebProductivity`, `ModifyAd`, `ModifyBrandSimple`,
  `BuyMarketResearch`, `BuyInitialMarketResearch`, `FollowUpStudy`, `SourceStudy`, `VarianceStudy`, `CompetitorAnalysis`, `PartnerAnalysis`
* Sales force & HR: `HireSalesPeople`, `HireWebSalesPeople`, `SalesForceCompensation`, `SpecialPrograms`, `WorkersCompensation(Regional)`,
  `ExecutiveCompensation`, `EmployeeInvolvement`, `HRSurvey`, `Goals*`, `StrategicThrustsSales`, `StrategicThrustsPurchasing`
* Manufacturing & supply chain: `OperatingCapacity(Regional)`, `Overtime(Regional)`, `FactoryLocation(Regional)`, `FactoryEfficiency`,
  `FactorySimulation(Regional)`, `ExtFactorySimulation(Regional)`, `ProductionRules`, `ProductionControlSystem`, `InventoryControl`,
  `TargetReplenishPoint`, `SellUnwantedInventory`, `InspectQuality`, `ImproveChangeover`, `ImprovementActions`, `CorrectiveActions`,
  `ComponentRework`, `InvestInActions`, `FeatureRD`, `ConfirmRD`, `ConfirmRFP`, `ConfirmLongRFP`, `PaymentToPartners`,
  `SupplyChainStrategy`, `SupplyChainInformationSystem`, `WarehouseLocation(Regional)`, `EnvironmentalConcerns`, `GoodNeighbor`
* Finance: `ShortTermLoan`, `LongTermLoan`, `Dividends`, `CurrencyFunds`, `ProFormaDivisionProfitability`
* Planning: `DemandProjection(Regional)`, `DemandProjectionNextQuarter(Regional)`, `TacticalPlan`, `TacticStrategyLinks`, `SWOTAnalysis`,
  `Risk*` (14 risk screens), `RiskManagementReview`, `RiskRegistryAll`, `Feedback`

**Reports (128):** results (`Sales`, `MarketShare*`, `ChannelDemand`, `DetailedBrandDemandReport`, `DemandImpactFactors`,
`BrandProfitability`, `RegionalProfitability`, `DivisionProfitability`, `CostOfProduction(Regional)`, `ManufacturingResults(Regional)`,
`QualityCosts*`, `WarrantyCosts`, `Fulfillment`, `WarehousingResults`, `OutsourcedBrandResults`, `ResultsOfContracts`), finance
(`IncomeStatement`, `BalanceSheet`, `CashFlow`, `SimpleCashFlow`, `WealthCreation`, `FinancialPosition`, `FinancialRatios`,
`ProForma*`, `Stock`), scorecards (`BalancedScorecard`, `CumulativeBalancedScorecard`, `DrillDownBSC`, `PlayersStanding`,
`CumulativePlayersStanding`, `CCScorecard`, `Grades`, `TrophyRoom`, `Certification`, `CompetencyReport`), competitor
intelligence (`Competitors*` 10 screens, `AdJudgment`, `BrandJudgment`, `PriceJudgment`, `ReliabilityJudgment`, `CompareAds/Brands/Designs`),
market research (`CustomerNeeds`, `UsePattern`, `PriceWillingToPay`, `MarketSize`, `MediaPreference`, `EconomicIndexes`,
`ExchangeRates`, `CostTrends`, `NewsSources`, `Newsletter`, `Reputation`, `IllWill*`), summaries (`Summary*`, `ControlCharts*`, `FinalCheck`, `ResultCheck`).

Full field-level detail: `docs/decision-catalog.md`; outputs: `docs/metric-catalog.md`.
