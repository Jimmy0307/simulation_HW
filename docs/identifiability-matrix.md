# Identifiability matrix

For each decision field, this shows how its effect on each output group can be observed **today**.
The cells come from static evidence. `W✅` marks a pair whose what-if path an operator experiment verified at runtime (EXP-01, 2026-11-03: `CD.deposit`, no save, Cancel restored, interest slope = displayed rate/4).

| Code | Meaning |
|---|---|
| **F** | Known client-side formula (exact arithmetic in REA-located module text) |
| **W** | Measurable through the what-if channel: `modify` → change → `calculate` → `cancel`, no `save` |
| **P** | Needs `save` (a real, reversible write teammates see); then pro forma projections reflect it (INFERRED, EXP-09) |
| **Q** | Needs quarter submission; observable next quarter, confounded by competitors |
| **X** | Not numerically observable (free text, qualitative grading, or no channel) |
| - | No expected relation |

Output groups: **own-calc** = the same screen's `calculate` outputs; **client** = client formulas; **pro forma** = ProForma Income/Balance/Cash-flow projections; **market** = Sales / MarketShare / IncomeStatement actuals / BalancedScorecard.

| Module | Field | Type | own-calc | client | pro forma | market | Own-calc outputs |
|---|---|---|---|---|---|---|---|
| BasesCompetitiveAdvantage | `basis` | unknown | - | - | P | Q | - |
| BuyInitialMarketResearch | `plan` | unknown | - | - | P | Q | - |
| BuyMarketResearch | `buy` | boolean | W | - | P | Q | total |
| CD | `deposit` | integer | W✅ (EXP-01) | - | P | Q | cd, interest |
| CD | `withdraw` | integer | W | - | P | Q | cd, interest |
| CompanyName | `companyName` | text | - | - | - | X | - |
| CompanyName | `logoDataName` | unknown | - | - | P | Q | - |
| CompanyName | `logoDataUri` | unknown | - | - | P | Q | - |
| CompetitorAnalysis | `aggressiveness` | enum | - | - | P | Q | - |
| CompetitorAnalysis | `changesInTactics` | text | - | - | - | X | - |
| CompetitorAnalysis | `levelOfThreat` | enum | - | - | P | Q | - |
| CompetitorAnalysis | `significantStrengths` | text | - | - | - | X | - |
| CompetitorAnalysis | `significantWeaknesses` | text | - | - | - | X | - |
| CompetitorAnalysis | `targetSegment1` | enum | - | - | P | Q | - |
| CompetitorAnalysis | `targetSegment2` | enum | - | - | P | Q | - |
| ComponentRework | `(none parsed)` | unknown | - | - | P | Q | - |
| ConfirmLongRFP | `action` | text | - | - | - | X | - |
| ConfirmLongRFP | `goalsAndIntent` | text | - | - | - | X | - |
| ConfirmLongRFP | `incentive` | text | - | - | - | X | - |
| ConfirmLongRFP | `partnerID` | enum | - | - | P | Q | - |
| ConfirmLongRFP | `specialTerms` | text | - | - | - | X | - |
| ConfirmRD | `buyerTeamID` | enum | - | - | P | Q | - |
| ConfirmRD | `cannotLicence` | boolean | - | - | P | Q | - |
| ConfirmRD | `cannotResell` | boolean | - | - | P | Q | - |
| ConfirmRD | `featureID` | enum | - | - | P | Q | - |
| ConfirmRD | `penalty` | integer | - | - | P | Q | - |
| ConfirmRD | `price` | integer | - | - | P | Q | - |
| ConfirmRD | `quarter` | enum | - | - | P | Q | - |
| ConfirmRD | `specialTerms` | text | - | - | - | X | - |
| ConfirmRFP | `contractEstimate` | integer | - | - | P | Q | cpuShipped |
| ConfirmRFP | `contractMax` | integer | - | - | P | Q | cpuShipped |
| ConfirmRFP | `contractQuantity` | integer | - | - | P | Q | cpuShipped |
| ConfirmRFP | `feeNotDelivered` | integer | - | - | P | Q | cpuShipped |
| ConfirmRFP | `feeNotDemanded` | integer | - | - | P | Q | cpuShipped |
| ConfirmRFP | `frequency` | enum | - | - | P | Q | cpuShipped |
| ConfirmRFP | `guaranteedMax` | integer | - | - | P | Q | cpuShipped |
| ConfirmRFP | `guaranteedMin` | integer | - | - | P | Q | cpuShipped |
| ConfirmRFP | `include` | boolean | - | - | P | Q | cpuShipped |
| ConfirmRFP | `mode` | enum | - | - | P | Q | cpuShipped |
| ConfirmRFP | `outsourcedPrice` | integer | - | - | P | Q | cpuShipped |
| ConfirmRFP | `preferredProductionPriority` | integer | - | - | P | Q | cpuShipped |
| ConfirmRFP | `shippingPaidBy` | enum | - | - | P | Q | cpuShipped |
| ConfirmRFP | `specialTerms` | text | - | - | - | X | cpuShipped |
| ConfirmRFP | `supplierID` | enum | - | - | P | Q | cpuShipped |
| CorporateObjectives | `(none parsed)` | unknown | - | - | P | Q | - |
| CorrectiveActions | `action` | text | - | - | - | X | - |
| CorrectiveActions | `problem` | text | - | - | - | X | - |
| Culture | `culture` | text | - | - | - | X | - |
| CurrencyFunds | `cashToCurrencies` | integer | - | - | P | Q | - |
| CurrencyFunds | `distrToCurrency` | integer | - | - | P | Q | - |
| CurrencyFunds | `withdraw` | integer | - | - | P | Q | - |
| DemandProjection | `demand` | integer | W | F | P | Q | brandDemand, brands, demandPerSp, demandPerWebSp, hasOperatingCapacity, hasZeroMaxEndingInventory, lqDemandPerSp, lqDemandPerWebSp |
| DemandProjection | `demandPerSp` | integer | W | F | P | Q | brandDemand, brands, demandPerSp, demandPerWebSp, hasOperatingCapacity, hasZeroMaxEndingInventory, lqDemandPerSp, lqDemandPerWebSp |
| DemandProjection | `demandPerWebSp` | integer | W | F | P | Q | brandDemand, brands, demandPerSp, demandPerWebSp, hasOperatingCapacity, hasZeroMaxEndingInventory, lqDemandPerSp, lqDemandPerWebSp |
| DemandProjectionNextQuarter | `demandPerSalesPerson` | integer | W | - | P | Q | projection |
| DemandProjectionNextQuarter | `demandPerWebSalesPerson` | integer | W | - | P | Q | projection |
| DemandProjectionNextQuarter | `salesPeople` | integer | W | - | P | Q | projection |
| DemandProjectionNextQuarter | `webSalesPeople` | integer | W | - | P | Q | projection |
| DemandProjectionNextQuarterRegional | `demandPerSalesPerson` | integer | W | - | P | Q | totalDemand |
| DemandProjectionNextQuarterRegional | `demandPerWebSalesPerson` | integer | W | - | P | Q | totalDemand |
| DemandProjectionNextQuarterRegional | `salesPeople` | integer | W | - | P | Q | totalDemand |
| DemandProjectionNextQuarterRegional | `webSalesPeople` | integer | W | - | P | Q | totalDemand |
| DemandProjectionRegional | `demand` | integer | W | F | P | Q | totalDemand |
| DemandProjectionRegional | `demandPerSp` | integer | W | F | P | Q | totalDemand |
| DemandProjectionRegional | `demandPerWebSp` | integer | W | F | P | Q | totalDemand |
| DesignWebPage | `ofKwId` | enum | W | - | P | Q | adsCost, keywords, regions, totalCost |
| DesignWebPage | `webActive` | enum | W | - | P | Q | adsCost, keywords, regions, totalCost |
| Dividends | `dividend` | integer | W | - | P | Q | dividends, sharesTotal, stockTotal |
| EmployeeInvolvement | `(none parsed)` | unknown | - | - | P | Q | - |
| EnvironmentalConcerns | `(none parsed)` | unknown | - | - | P | Q | - |
| ExecutiveCompensation | `(none parsed)` | unknown | - | - | P | Q | - |
| ExecutiveResponsibilities | `responsibilityID1` | enum | - | - | P | Q | - |
| ExecutiveResponsibilities | `responsibilityID2` | enum | - | - | P | Q | - |
| ExtFactorySimulation | `controlSystem` | enum | W | F | P | Q | RFPs, attr, brandID, brandsForProduction, brandsForSale, choverLabor, choverOC, choverOCPercent |
| ExtFactorySimulation | `demandMultiplier` | enum | W | F | P | Q | RFPs, attr, brandID, brandsForProduction, brandsForSale, choverLabor, choverOC, choverOCPercent |
| ExtFactorySimulation | `hoursInDay` | enum | W | F | P | Q | RFPs, attr, brandID, brandsForProduction, brandsForSale, choverLabor, choverOC, choverOCPercent |
| ExtFactorySimulation | `maxEndingInventory` | integer | W | F | P | Q | RFPs, attr, brandID, brandsForProduction, brandsForSale, choverLabor, choverOC, choverOCPercent |
| ExtFactorySimulation | `operatingCapacity` | integer | W | F | P | Q | RFPs, attr, brandID, brandsForProduction, brandsForSale, choverLabor, choverOC, choverOCPercent |
| ExtFactorySimulation | `plannedProduction` | integer | W | F | P | Q | RFPs, attr, brandID, brandsForProduction, brandsForSale, choverLabor, choverOC, choverOCPercent |
| ExtFactorySimulation | `projectedWorkersProductivity` | integer | W | F | P | Q | RFPs, attr, brandID, brandsForProduction, brandsForSale, choverLabor, choverOC, choverOCPercent |
| ExtFactorySimulationRegional | `demandMultiplier` | enum | W | F | P | Q | brandID, brandsForSale, demandMultiplier, demandProjection, hasWorkersCompensations, hasZeroMaxEndingInventory, hoursInDay, isEasyPush |
| ExtFactorySimulationRegional | `hoursInDay` | enum | W | F | P | Q | brandID, brandsForSale, demandMultiplier, demandProjection, hasWorkersCompensations, hasZeroMaxEndingInventory, hoursInDay, isEasyPush |
| ExtFactorySimulationRegional | `operatingCapacity` | integer | W | F | P | Q | brandID, brandsForSale, demandMultiplier, demandProjection, hasWorkersCompensations, hasZeroMaxEndingInventory, hoursInDay, isEasyPush |
| ExtFactorySimulationRegional | `projectedWorkersProductivity` | integer | W | F | P | Q | brandID, brandsForSale, demandMultiplier, demandProjection, hasWorkersCompensations, hasZeroMaxEndingInventory, hoursInDay, isEasyPush |
| FactoryEfficiency | `(none parsed)` | unknown | - | - | P | Q | - |
| FactoryLocation | `factoryRegion` | unknown | - | - | P | Q | - |
| FactoryLocationRegional | `open` | boolean | W | - | P | Q | total |
| FactorySimulation | `estimatedDemand` | integer | W | - | P | Q | brandsForProduction, brandsForSale, choverLabor, choverOC, choverOCPercent, choverOverhead, costToChangeOC, excessLabor |
| FactorySimulation | `estimatedPrice` | integer | W | - | P | Q | brandsForProduction, brandsForSale, choverLabor, choverOC, choverOCPercent, choverOverhead, costToChangeOC, excessLabor |
| FactorySimulationRegional | `estimatedDemand` | integer | W | - | P | Q | brandsForProduction, brandsForSale, choverLabor, choverOC, choverOCPercent, choverOverhead, costToChangeOC, excessLabor |
| FactorySimulationRegional | `estimatedPrice` | integer | W | - | P | Q | brandsForProduction, brandsForSale, choverLabor, choverOC, choverOCPercent, choverOverhead, costToChangeOC, excessLabor |
| FeatureRD | `(none parsed)` | unknown | W | - | P | Q | rdFeatures, total |
| Feedback | `disagreeExplanation` | text | - | - | - | X | - |
| FinancialResources | `(none parsed)` | unknown | - | - | P | Q | - |
| FixedCapacity | `increase` | unknown | W | F | P | Q | acquirement, expansion, total |
| FixedCapacity | `supplier` | enum | W | F | P | Q | acquirement, expansion, total |
| FollowUpStudy | `buy` | boolean | - | - | P | Q | - |
| Goals | `value` | integer | - | - | P | Q | - |
| GoalsDirectionThrusts | `mission` | text | - | - | - | X | - |
| GoalsDirectionThrusts | `priority` | enum | - | - | P | Q | - |
| GoalsDirectionThrusts | `strategicDirections` | unknown | - | - | P | Q | - |
| GoalsStrategicDirection | `mission` | text | - | - | - | X | - |
| GoalsStrategicDirection | `priority` | enum | - | - | P | Q | - |
| GoalsStrategicDirection | `strategicDirections` | unknown | - | - | P | Q | - |
| GoalsStrategicDirectionSupplier | `mission` | text | - | - | - | X | - |
| GoalsStrategicDirectionSupplier | `priority` | enum | - | - | P | Q | - |
| GoalsStrategicDirectionSupplier | `strategicDirections` | unknown | - | - | P | Q | - |
| GoodNeighbor | `(none parsed)` | unknown | - | - | P | Q | - |
| HRSurvey | `plan` | boolean | - | - | P | Q | - |
| HireSalesPeople | `sf` | integer | W | - | P | Q | regions, total |
| HireSalesPeople | `support` | integer | W | - | P | Q | regions, total |
| HireWebSalesPeople | `sf` | integer | W | - | P | Q | employCost, hireCost, lastQuarterSalesPeople, layOffCost, opened, regionID, regions, salesPeople |
| HireWebSalesPeople | `support` | integer | W | - | P | Q | employCost, hireCost, lastQuarterSalesPeople, layOffCost, opened, regionID, regions, salesPeople |
| ImproveChangeover | `rdChover` | integer | W | - | P | Q | changeoverCost, changeoverTime, costReductionPct, timeReductionPct |
| ImprovementActions | `operate` | boolean | W | - | P | Q | actions, groups, total |
| InspectQuality | `inspection` | boolean | W | - | P | Q | total |
| InventoryControl | `maxEndingInventory` | integer | - | - | P | Q | - |
| InventoryControl | `produce` | boolean | - | - | P | Q | - |
| InvestInActions | `budget` | integer | W | - | P | Q | budget, criticalGroups, total |
| LocalMedia | `inserts` | integer | W | - | P | Q | ads, adsCost, mediaCost, mediaCount, regionCost, regions, split |
| LongTermLoan | `borrow` | integer | W | - | P | Q | longTermLoan, ltRecord |
| Mission | `mission` | text | - | - | - | X | - |
| ModifyAd | `adID` | unknown | - | - | P | Q | - |
| ModifyAd | `decisions` | text | - | - | - | X | - |
| ModifyBrand | `brandID` | unknown | - | - | P | Q | - |
| ModifyBrand | `brandType` | unknown | - | - | P | Q | - |
| ModifyBrand | `decisions` | text | - | - | - | X | - |
| ModifyBrandSimple | `brandID` | unknown | - | - | P | Q | - |
| ModifyBrandSimple | `brandType` | unknown | - | - | P | Q | - |
| ModifyBrandSimple | `decisions` | text | - | - | - | X | - |
| OpenSalesOffice | `change` | boolean | W | - | P | Q | total, totalClose, totalFactorySetup, totalLease, totalSetup |
| OpenWebcenter | `change` | boolean | W | - | P | Q | total, totalClose, totalFactorySetup, totalLease, totalSetup |
| OperatingCapacity | `operatingCapacity` | integer | W | F | P | Q | chartSettings, costToChangeOperatingCapacity, data, directLaborCPU, fixedCapacity, graph, hasWorkersCompensation, height |
| OperatingCapacity | `projectedWorkersProductivity` | integer | W | F | P | Q | chartSettings, costToChangeOperatingCapacity, data, directLaborCPU, fixedCapacity, graph, hasWorkersCompensation, height |
| OperatingCapacityRegional | `fixedCapacityIncrease` | enum | - | F | P | Q | - |
| OperatingCapacityRegional | `operatingCapacity` | integer | - | F | P | Q | - |
| OperatingCapacityRegional | `projectedWorkersProductivity` | integer | - | F | P | Q | - |
| Overtime | `(none parsed)` | unknown | W | - | P | Q | data, fixedCapacity, hasWorkersCompensation, hoursInDay, overtimeLaborChange, showLegend, title, x |
| OvertimeRegional | `(none parsed)` | unknown | W | - | P | Q | hours, overtime, regions |
| PartnerAnalysis | `aggressiveness` | enum | - | - | P | Q | - |
| PartnerAnalysis | `changesInTactics` | text | - | - | - | X | - |
| PartnerAnalysis | `levelOfThreat` | enum | - | - | P | Q | - |
| PartnerAnalysis | `significantStrengths` | text | - | - | - | X | - |
| PartnerAnalysis | `significantWeaknesses` | text | - | - | - | X | - |
| PartnerAnalysis | `targetSegment1` | enum | - | - | P | Q | - |
| PartnerAnalysis | `targetSegment2` | enum | - | - | P | Q | - |
| PaymentToPartners | `payment` | integer | W | - | P | Q | total |
| PersonalGoals | `mostImportantGoal` | enum | - | - | P | Q | - |
| Pricing | `pop` | boolean | - | - | P | Q | - |
| Pricing | `price` | integer | - | - | P | Q | - |
| Pricing | `priority` | integer | - | - | P | Q | - |
| Pricing | `rebate` | integer | - | - | P | Q | - |
| Pricing | `sell` | boolean | - | - | P | Q | - |
| ProFormaCashFlow | `(none parsed)` | unknown | W | - | P | Q | items |
| ProFormaDivisionProfitability | `demandMultiplier` | enum | W | - | P | Q | brandsForSale, items |
| ProFormaDivisionProfitability | `estimatedDemand` | integer | W | - | P | Q | brandsForSale, items |
| ProFormaDivisionProfitability | `estimatedPrice` | integer | W | - | P | Q | brandsForSale, items |
| Problem | `problem` | text | - | - | - | X | - |
| Problem | `solution` | text | - | - | - | X | - |
| ProductionControlSystem | `systemID` | unknown | W | - | P | Q | productionSystems, quarterlyExpense, setupCost |
| ProductionRules | `rules` | unknown | - | - | P | Q | - |
| Promotions | `cashBonus` | integer | W | - | P | Q | brands, height, regionID, regions, totalBudget |
| Promotions | `freeGift` | integer | W | - | P | Q | brands, height, regionID, regions, totalBudget |
| RegionalMedia | `inserts` | integer | W | - | P | Q | ads, adsCost, mediaCost, mediaCount, regionCost, regions |
| RiskAnalysis | `explanation` | text | - | - | - | X | - |
| RiskAnalysis | `mitigation` | text | - | - | - | X | - |
| RiskAnalysis | `specification` | text | - | - | - | X | - |
| RiskAnalysisCompany | `explanation` | text | - | - | - | X | - |
| RiskAnalysisCompany | `mitigation` | text | - | - | - | X | - |
| RiskAnalysisCompany | `specification` | text | - | - | - | X | - |
| RiskAnalysisIndustry | `explanation` | text | - | - | - | X | - |
| RiskAnalysisIndustry | `mitigation` | text | - | - | - | X | - |
| RiskAnalysisIndustry | `specification` | text | - | - | - | X | - |
| RiskAnalysisStrategic | `explanation` | text | - | - | - | X | - |
| RiskAnalysisStrategic | `mitigation` | text | - | - | - | X | - |
| RiskAnalysisStrategic | `specification` | text | - | - | - | X | - |
| RiskManagementReview | `review` | text | - | - | - | X | - |
| RiskRegistryAll | `auditDate` | text | - | - | - | X | - |
| RiskRegistryAll | `auditParticipants` | text | - | - | - | X | - |
| RiskRegistryAll | `auditResults` | text | - | - | - | X | - |
| RiskRegistryAll | `processOwner` | enum | - | - | P | Q | - |
| RisksCompany | `description` | text | - | - | - | X | - |
| RisksCompany | `title` | text | - | - | - | X | - |
| RisksIndustry | `description` | text | - | - | - | X | - |
| RisksIndustry | `title` | text | - | - | - | X | - |
| RisksLikelihoodCompany | `impact` | enum | - | - | P | Q | - |
| RisksLikelihoodCompany | `likelihood` | enum | - | - | P | Q | - |
| RisksLikelihoodCompany | `mitigate` | boolean | - | - | P | Q | - |
| RisksLikelihoodIndustry | `impact` | enum | - | - | P | Q | - |
| RisksLikelihoodIndustry | `likelihood` | enum | - | - | P | Q | - |
| RisksLikelihoodIndustry | `mitigate` | boolean | - | - | P | Q | - |
| RisksLikelihoodStrategic | `impact` | enum | - | - | P | Q | - |
| RisksLikelihoodStrategic | `likelihood` | enum | - | - | P | Q | - |
| RisksLikelihoodStrategic | `mitigate` | boolean | - | - | P | Q | - |
| RisksMitigationCompany | `mitigation` | text | - | - | - | X | - |
| RisksMitigationIndustry | `mitigation` | text | - | - | - | X | - |
| RisksMitigationStrategic | `mitigation` | text | - | - | - | X | - |
| RisksStrategic | `description` | text | - | - | - | X | - |
| RisksStrategic | `title` | text | - | - | - | X | - |
| SWOTAnalysis | `opportunities` | text | - | - | - | X | - |
| SWOTAnalysis | `strengths` | text | - | - | - | X | - |
| SWOTAnalysis | `threats` | text | - | - | - | X | - |
| SWOTAnalysis | `weaknesses` | text | - | - | - | X | - |
| SalesForceCompensation | `(none parsed)` | unknown | - | - | P | Q | - |
| SearchEngineMarketing | `budget` | integer | W | - | P | Q | regions, totalBudget |
| SearchEngineMarketing | `maxBid` | float | W | - | P | Q | regions, totalBudget |
| SellUnwantedInventory | `sellInventory` | integer | W | - | P | Q | brands, totalPrice |
| ShortTermLoan | `borrow` | integer | W | - | P | Q | annualRate, borrow, interest, quarterlyRate, repay, shortTermLoan |
| ShortTermLoan | `repay` | integer | W | - | P | Q | annualRate, borrow, interest, quarterlyRate, repay, shortTermLoan |
| SimpleInternetMarketing | `budget` | integer | W | - | P | Q | ads, adsCost, is, prop, regionID, totalCost, val |
| SimpleInternetMarketing | `ofKwId` | enum | W | - | P | Q | ads, adsCost, is, prop, regionID, totalCost, val |
| SimpleInternetMarketing | `smActive` | boolean | W | - | P | Q | ads, adsCost, is, prop, regionID, totalCost, val |
| SimpleInternetMarketing | `webActive` | enum | W | - | P | Q | ads, adsCost, is, prop, regionID, totalCost, val |
| SocialMedia | `change` | boolean | W | - | P | Q | total |
| SocialMedia | `quarterlyBudget` | integer | W | - | P | Q | total |
| SourceStudy | `buy` | boolean | W | - | P | Q | total |
| SpecialPrograms | `contest` | integer | W | - | P | Q | contest, contestBudget, demoKit, demoKitBudget, newSalesForce, newWebSalesForce, totalBudget, totalSalesForce |
| SpecialPrograms | `demoKit` | integer | W | - | P | Q | contest, contestBudget, demoKit, demoKitBudget, newSalesForce, newWebSalesForce, totalBudget, totalSalesForce |
| SpecialPrograms | `training` | integer | W | - | P | Q | contest, contestBudget, demoKit, demoKitBudget, newSalesForce, newWebSalesForce, totalBudget, totalSalesForce |
| StrategicThrustsCorporate | `(none parsed)` | unknown | - | - | P | Q | - |
| StrategicThrustsFinance | `(none parsed)` | unknown | - | - | P | Q | - |
| StrategicThrustsHumanResource | `(none parsed)` | unknown | - | - | P | Q | - |
| StrategicThrustsManufacturing | `(none parsed)` | unknown | - | - | P | Q | - |
| StrategicThrustsMarketing | `(none parsed)` | unknown | - | - | P | Q | - |
| StrategicThrustsPurchasing | `(none parsed)` | unknown | - | - | P | Q | - |
| StrategicThrustsSales | `(none parsed)` | unknown | - | - | P | Q | - |
| StrategicThrustsSalesChannel | `(none parsed)` | unknown | - | - | P | Q | - |
| SupplyChainInformationSystem | `setupEdi` | boolean | W | - | P | Q | ediSetup, mis, misID, misQuarterlyCost, misSetup, partners |
| SupplyChainStrategy | `roleNo` | unknown | - | - | P | Q | - |
| TacticStrategyLinks | `(none parsed)` | unknown | - | - | P | Q | - |
| TacticStrategyLinksFinance | `(none parsed)` | unknown | - | - | P | Q | - |
| TacticStrategyLinksHumanResource | `(none parsed)` | unknown | - | - | P | Q | - |
| TacticStrategyLinksManufacturing | `(none parsed)` | unknown | - | - | P | Q | - |
| TacticStrategyLinksMarketing | `(none parsed)` | unknown | - | - | P | Q | - |
| TacticStrategyLinksSalesChannel | `(none parsed)` | unknown | - | - | P | Q | - |
| TacticalPlan | `(none parsed)` | unknown | - | - | P | Q | items |
| TargetReplenishPoint | `priority` | integer | - | - | P | Q | - |
| TargetReplenishPoint | `replenish` | integer | - | - | P | Q | - |
| TargetReplenishPoint | `target` | integer | - | - | P | Q | - |
| TargetSegments | `priority` | enum | - | - | P | Q | - |
| TeamNorms | `norms` | unknown | - | - | P | Q | - |
| TeamNorms | `processes` | unknown | - | - | P | Q | - |
| VarianceStudy | `buy` | boolean | W | - | P | Q | total |
| WarehouseLocation | `factoryRegion` | unknown | - | - | P | Q | - |
| WarehouseLocationRegional | `open` | boolean | W | - | P | Q | total |
| WebProductivity | `change` | boolean | W | - | P | Q | total |
| WebProductivity | `quarterlyBudget` | integer | W | - | P | Q | total |
| WebTraffic | `change` | boolean | W | - | P | Q | total |
| WebTraffic | `commission` | integer | W | - | P | Q | total |
| WebTraffic | `quarterlyBudget` | integer | W | - | P | Q | total |
| WorkersCompensation | `(none parsed)` | unknown | - | - | P | Q | - |
| WorkersCompensationRegional | `(none parsed)` | unknown | - | - | P | Q | - |
| WrapUp | `wrapped` | boolean | X | - | Q | Q | - |
| WrapUp | `targetSegments` | list | X | - | Q | Q | - |

Cell counts: -=450, F=24, P=197, Q=201, W=86, W✅ (EXP-01)=1, X=57

## Client formulas referenced (F)

| Module | Formula |
|---|---|
| FixedCapacity | units/quarter = units/day x 65; unit capacity cost = option cost / units |
| OperatingCapacity | quarterly = daily x maxDays(65); effective = OC x productivity / 100 |
| OperatingCapacityRegional | quarterly = daily x maxDays(65); effective = OC x productivity / 100 |
| ExtFactorySimulation | planned x 65 x productivity / 100; OC x 65 |
| ExtFactorySimulationRegional | OC x productivity / 100; demand / 65 |
| DemandProjection | brandDemand / 65; operatingCapacityNeeded / 65 |
| DemandProjectionRegional | brandDemand / 65; regional share = demand x 100 / lqTotalDemand |
