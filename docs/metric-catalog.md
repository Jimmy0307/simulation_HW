# Metric catalog

Generated from `data/metric_catalog.json` (structure only, no values).

* `calculate`: returned by `<Service>.calculate` / `view` as `calculate`. If `available_before_save`, it
  can be produced from draft decisions through the what-if path.
* `view.staticData` / `view.dynamicData`: report fields rendered by the client after `view`. These are
  server results for already-processed quarters (or projections from stored state).

## Where the headline outcomes live

| Outcome | Screen (service) | Data path | How it is produced |
|---|---|---|---|
| Unit sales | `Sales` | `staticData.officeSales / webSales / globalSales / outsourcingSales` | server, after quarter processing |
| Revenue, COGS, operating profit | `IncomeStatement` (FinanceReport) and `ProFormaIncomeStatement` (ProFormaFinance) | `staticData.sections[].items[].quarters[]` (row names come from the server) | server; ProForma adds `fill` projection columns |
| Market share | `MarketShare` | `staticData.segments / teams / demand`; client computes `% = demand x 100 / segment total` | server demand + client percentage |
| Channel share | `ChannelDemand` | `soDemand x 100 / total`, `webDemand x 100 / total` | client percentage of server demand |
| Balanced scorecard | `BalancedScorecard`, `CumulativeBalancedScorecard`, `DrillDownBSC` | `staticData.indicators` | server |
| Operating profit (prior quarter) | `FinancialPosition` | `staticData.operatingProfitPriorQtr` | server |
| Production cost per unit | `FactorySimulation` / `ExtFactorySimulation` (calculate) | `brandsForSale[].material / labor / overhead / prodCost / avgCost` | server, **what-if capable** |
| Projected demand next quarter | `FixedCapacity` | `dynamicData.projectDemandNextQuarter` (client shows `/65` per day) | server, read-only |
| Live pro forma gadget | `GameInfo.liveProForma([user])` | sections/items | server, from stored state (no draft parameter) |

## Key report modules

| Module | Fields read by the client |
|---|---|
| Sales | globalSales, officeSales, outsourcingSales, regions, unwanted, webSales |
| MarketShare | demand, segments, teams |
| MarketShareSupplier | teams, totalDemand |
| ChannelDemand | teams |
| BalancedScorecard | firstSegment, iAmSupOrRes, indicators, secondSegment, segmentsToChoose |
| CumulativeBalancedScorecard | indicators |
| FinanceReport | quarters, sections |
| FinancialPosition | available, netInvestment, newInvestment, operatingProfitPriorQtr, rd, soOpen, unusedFinances, unusedFinancesPriorQtr |
| BrandProfitability | brands |
| RegionalProfitability | regions |
| CostOfProduction | brands, demandProjection, units |
| ManufacturingResults | brandsForProduction, brandsForSale, inSupplyChain, overhead, producing, selling, split |
| PlayersStanding | ai, humanTeams, indicators, teams |
| ProFormaFinance | fill, quarters, sections |
| Grades | grade, gradingComponents, letterGrade, released |

## All modules

| Module | Source | Metrics | Before save? | Observed in capture |
|---|---|---|---|---|
| AdJudgment | view.staticData | ads, regionName, regions, segments, teams | no |  |
| AdReview | view.staticData | reviews, segments, teamID, teams | no |  |
| Assistant | view.staticData | active | no |  |
| BalancedScorecard | view.staticData | firstSegment, iAmSupOrRes, indicators, secondSegment, segmentsToChoose | no |  |
| BrandJudgment | view.staticData | brands, regionName, regions, segmentID, segments, teams | no |  |
| BrandProfitability | view.staticData | brands | no |  |
| BusinessRelationships | view.staticData | regions, segments, teams | no |  |
| BuyMarketResearch | calculate | total | yes |  |
| CCConfidentialNewsletter | view.staticData | messages | no |  |
| CCScorecard | view.staticData | culture, quarters, sections, startQuarter | no |  |
| CD | calculate | cd, interest | yes | yes |
| Certification | view.staticData | issuerUrl, openBadges | no |  |
| ChannelDemand | view.staticData | teams | no |  |
| CheckAdClaims | view.dynamicData | adID, ads | no |  |
| CompareAds | view.staticData | adGroups, ads | no |  |
| CompareBrands | view.staticData | brandType, brandTypes, brands, componentGroups | no |  |
| CompareDesigns | view.staticData | brandTypes, componentGroups, segments | no |  |
| CompetencyReport | view.staticData | DECENT_PERCENTILE, competencies, pools, student, studentCompetencies | no |  |
| CompetitorsAds | view.staticData | adGroups, teams | no |  |
| CompetitorsBrands | view.staticData | brandType, brandTypes, componentGroups, teams | no |  |
| CompetitorsInCity | view.staticData | regions, teams | no |  |
| CompetitorsLocalAdvertising | view.staticData | regions, teams | no |  |
| CompetitorsPrices | view.staticData | regions, teams | no |  |
| CompetitorsProfiles | view.staticData | companyItems, regions, teams | no |  |
| CompetitorsRegionalAdvertising | view.staticData | media, regions, teams | no |  |
| CompetitorsSalesForce | view.staticData | regions, segments, teams | no |  |
| CompetitorsSocialMediaDecisions | view.staticData | graphs, regions, teams | no |  |
| CompetitorsWebDecisions | view.staticData | regions, teams, webProductivities, webTraffics | no |  |
| ComponentChangeover | view.staticData | componentGroups | no |  |
| ConfirmRFP | calculate | cpuShipped | no |  |
| CostOfProduction | view.dynamicData | brands, demandProjection | no |  |
| CostOfProduction | view.staticData | units | no |  |
| CostOfProductionRegional | view.dynamicData | brands, demandProjection, regionID, regionName, regions | no |  |
| CostOfProductionRegional | view.staticData | units | no |  |
| CostTrends | view.staticData | graphs, params, regions | no |  |
| CumulativeBalancedScorecard | view.staticData | indicators | no |  |
| CustomerNeeds | view.staticData | items, sameData, segments, tableID, tableName, tables | no | yes |
| DemandImpactFactors | view.staticData | myTeam, sections, teams | no |  |
| DemandProjection | calculate | brandDemand, brands, demandPerSp, demandPerWebSp, hasOperatingCapacity, hasZeroMaxEndingInventory, lqDemandPerSp, lqDemandPerWebSp, lqSf, lqSoDemand, lqTotalDemand, lqTotalSf, lqWebDemand, lqWebSf, operatingCapacityNeeded, soDemand, totalDemand, webDemand | yes |  |
| DemandProjectionNextQuarter | calculate | projection | yes |  |
| DemandProjectionNextQuarterRegional | calculate | totalDemand | yes |  |
| DemandProjectionRegional | calculate | totalDemand | yes |  |
| DesignWebPage | calculate | adsCost, keywords, regions, totalCost | yes |  |
| DetailedBrandDemandReport | view.staticData | regions, segments, teams | no |  |
| Dividends | calculate | dividends, sharesTotal, stockTotal | yes |  |
| DrillDownBSC | view.staticData | ind, indicators, teams | no |  |
| EconomicIndexes | view.staticData | copyright, processDate, regions | no |  |
| ExchangeRates | view.staticData | currency, currencyName, er, headquarters, messages, processDate, regionName, regions, sourceInfo | no |  |
| ExtFactorySimulation | calculate | RFPs, attr, brandID, brandsForProduction, brandsForSale, choverLabor, choverOC, choverOCPercent, choverOverhead, contractID, costToChangeOC, demandProjection, directLaborCPUOtInc, estimatedDemand, estimatedPrice, excessLabor, excessOC, excessOCPercent, excessOverhead, hasFactoryProductivity, hasOvertime, hasWorkersCompensations, hasZeroMaxEndingInventory, html, inSupplyChain, isEasyPull, isEasyPush, isJustInTime, isPull, maxEndingInventory, operatingCapacityNeeded, operatingOverhead, overtimeAdjProductivity, overtimeHours, overtimeOC, plannedOC, plannedOCwithOt, plannedProduction, produce, produceIndex, producing, productionOC, productionOCPercent, productionOverhead, productionPriority, removeAttr, replenishmentPoint, resellerRFPs, supplierRFPs, targetPoint, teamID, totalOC, totalOverhead | yes |  |
| ExtFactorySimulationRegional | calculate | brandID, brandsForSale, demandMultiplier, demandProjection, hasWorkersCompensations, hasZeroMaxEndingInventory, hoursInDay, isEasyPush, isIn, isJustInTime, isProductivityEditable, operatingCapacityNeeded, price, teamID | yes |  |
| FactoryLocationRegional | calculate | total | yes |  |
| FactoryLocations | view.staticData | factoryCities, locations, mis, productionSystems | no |  |
| FactoryProductivity | view.staticData | quarters, teams | no |  |
| FactoryProductivityRegional | view.staticData | quarters, regionID, regionName, teams | no |  |
| FactorySimulation | calculate | brandsForProduction, brandsForSale, choverLabor, choverOC, choverOCPercent, choverOverhead, costToChangeOC, excessLabor, excessOC, excessOCPercent, excessOverhead, operatingOverhead, productionOC, productionOCPercent, productionOverhead, totalOC, totalOverhead | yes |  |
| FactorySimulationRegional | calculate | brandsForProduction, brandsForSale, choverLabor, choverOC, choverOCPercent, choverOverhead, costToChangeOC, excessLabor, excessOC, excessOCPercent, excessOverhead, operatingOverhead, productionOC, productionOCPercent, productionOverhead, totalOC, totalOverhead | yes |  |
| FeatureRD | calculate | rdFeatures, total | yes |  |
| FinalCheck | view.dynamicData | errors, notes, warnings | no |  |
| FinanceReport | view.staticData | quarters, sections | no |  |
| FinancialPosition | view.staticData | available, netInvestment, newInvestment, operatingProfitPriorQtr, rd, soOpen, unusedFinances, unusedFinancesPriorQtr | no |  |
| FinancialRatios | view.staticData | group, groups | no |  |
| FixedCapacity | calculate | acquirement, expansion, total | yes | yes |
| Fulfillment | view.staticData | teams | no |  |
| Grades | view.staticData | grade, gradingComponents, letterGrade, released | no |  |
| HRSurveyResult | view.staticData | hrSurveyBought, studies | no |  |
| HireSalesPeople | calculate | regions, total | yes |  |
| HireWebSalesPeople | calculate | employCost, hireCost, lastQuarterSalesPeople, layOffCost, opened, regionID, regions, salesPeople, sf, support, total | yes |  |
| IllWill | view.staticData | brands, illWillPenalty, percentOfLostSales | no |  |
| IllWillRegional | view.staticData | brands, illWillPenalty, percentOfLostSales, regionID, regionName, regions | no |  |
| ImproveChangeover | calculate | changeoverCost, changeoverTime, costReductionPct, timeReductionPct | yes |  |
| ImprovementActions | calculate | actions, groups, total | yes |  |
| ImprovementActionsCosts | view.staticData | fromRow, groups, jelement, toRow | no |  |
| ImprovementActionsInvestments | view.staticData | groups, teams | no |  |
| IndustryExecutiveCompensation | view.staticData | healthInsuranceOptions, regions, teams, vacationOptions | no |  |
| IndustrySalesForceCompensation | view.staticData | healthInsuranceOptions, regions, teams, vacationOptions | no |  |
| IndustrySearchEngineMarketingResults | view.staticData | keywords, regions, segments, teams | no |  |
| IndustryWorkersCompensation | view.staticData | healthInsuranceOptions, regions, teams, vacationOptions | no |  |
| InitialExecutiveCompensation | view.staticData | healthInsuranceOptions, importance, regions, vacationOptions | no |  |
| InitialFinancialPosition | view.staticData | available, minInvestment, netInvestment, newInvestment, operatingProfitPriorQtr, unusedFinancesPriorQtr | no |  |
| InitialSalesForceCompensation | view.staticData | healthInsuranceOptions, importance, regions, vacationOptions | no | yes |
| InitialWorkersCompensation | view.staticData | healthInsuranceOptions, importance, regions, vacationOptions | no | yes |
| InspectQuality | calculate | total | yes |  |
| InventoryControlRegional | view.dynamicData | brands | no |  |
| InventoryControlRegional | view.staticData | regions | no |  |
| InvestInActions | calculate | budget, criticalGroups, total | yes |  |
| InvestInActionsResults | view.staticData | criticalGroups, distrUnits, groupID, wasInvested | no |  |
| LocalMedia | calculate | ads, adsCost, mediaCost, mediaCount, regionCost, regions, split | yes |  |
| LongTermLoan | calculate | longTermLoan, ltRecord | yes |  |
| ManufacturingResults | view.staticData | brandsForProduction, brandsForSale, inSupplyChain, overhead, producing, selling, split | no |  |
| ManufacturingResultsRegional | view.staticData | brandsForSale, on, producing, regionID, regions, selling | no |  |
| MarketShare | view.staticData | demand, segments, teams | no |  |
| MarketShareSupplier | view.staticData | teams, totalDemand | no |  |
| MarketSize | view.staticData | regionID, regions | no | yes |
| Morale | view.staticData | startQuarter, teams | no |  |
| NewsSources | view.staticData | links | no |  |
| Newsletter | view.staticData | messages | no |  |
| NumberOfSearches | view.staticData | data, keywords, regions, series | no |  |
| OpenSalesOffice | calculate | total, totalClose, totalFactorySetup, totalLease, totalSetup | yes | yes |
| OpenWebcenter | calculate | total, totalClose, totalFactorySetup, totalLease, totalSetup | yes | yes |
| OperatingCapacity | calculate | chartSettings, costToChangeOperatingCapacity, data, directLaborCPU, fixedCapacity, graph, hasWorkersCompensation, height, isJustInTime, overheadCPU, previousQuarterFixedCapacity, previousQuarterOperatingCapacity | yes |  |
| OrganicSearchEngineResults | view.staticData | keywords, oldOrganic, rank, regions, teams | no |  |
| OutsourcedBrandResults | view.staticData | maxDays, outsourcedBrands, teams | no |  |
| Overtime | calculate | data, fixedCapacity, hasWorkersCompensation, hoursInDay, overtimeLaborChange, showLegend, title, x, y | yes |  |
| OvertimeRegional | calculate | hours, overtime, regions | yes |  |
| PaymentToPartners | calculate | total | yes |  |
| PlayersStanding | view.staticData | ai, humanTeams, indicators, teams | no |  |
| PriceWillingToPay | view.staticData | regionID, regions | no | yes |
| ProFormaCashFlow | calculate | items | yes | yes |
| ProFormaCashFlowLive | view.staticData | sections | no |  |
| ProFormaDivisionProfitability | calculate | brandsForSale, items | yes |  |
| ProFormaFinance | view.staticData | fill, quarters, sections | no |  |
| ProductionControlSystem | calculate | productionSystems, quarterlyExpense, setupCost | yes |  |
| Promotions | calculate | brands, height, regionID, regions, totalBudget | yes |  |
| QualityCosts | view.staticData | criticalGroups | no |  |
| RegionalMedia | calculate | ads, adsCost, mediaCost, mediaCount, regionCost, regions | yes |  |
| RegionalProfitability | view.staticData | regions | no |  |
| ReliabilityJudgment | view.staticData | teams | no |  |
| Reputation | view.staticData | startQuarter, teams | no |  |
| ResultCheck | view.dynamicData | warnings | no |  |
| ResultsOfContracts | view.staticData | contracts, teams | no |  |
| RiskAnalysisReview | view.staticData | riskTypes | no |  |
| Sales | view.staticData | globalSales, officeSales, outsourcingSales, regions, unwanted, webSales | no |  |
| SearchEngineMarketing | calculate | regions, totalBudget | yes |  |
| SearchEngineMarketingResults | view.staticData | keywords, regions, segments | no |  |
| SellUnwantedInventory | calculate | brands, totalPrice | yes |  |
| ShipmentOptions | calculate | all, data, frequency, graph, mode, partnerID, showLegend, title, units, x, y | no |  |
| ShipmentOptions | view.dynamicData | category, conditionalYLines, data, labelX, labelY, labels, legend, minX, minY, partners, units, yLines | no |  |
| ShipmentOptions | view.staticData | factoryCities, frequencies, frequency, maxDays, mode, modes, partnerID, teams, units | no |  |
| ShortTermLoan | calculate | annualRate, borrow, interest, quarterlyRate, repay, shortTermLoan | yes |  |
| SimpleInternetMarketing | calculate | ads, adsCost, is, prop, regionID, totalCost, val | yes |  |
| SimpleInternetMarketingResults | view.staticData | keywords, paidActive, regions, segments, smActive | no |  |
| SocialMedia | calculate | total | yes |  |
| SourceStudy | calculate | total | yes |  |
| SpecialPrograms | calculate | contest, contestBudget, demoKit, demoKitBudget, newSalesForce, newWebSalesForce, totalBudget, totalSalesForce, totalWebSalesForce, training, trainingBudget | yes |  |
| Stock | calculate | dividends, sharesIncrease, sharesTotal, stockIncrease, stockTotal, stocks | no | yes |
| Stock | view.dynamicData | investors | no | yes |
| Stock | view.staticData | stocks | no | yes |
| StrategicGraphs | view.staticData | categories, chartTemplates | no |  |
| SummaryOfDecisions | view.staticData | categories | no | yes |
| SummaryOfTacticsMarketing | view.staticData | categories | no |  |
| SupplyChainInformationSystem | calculate | ediSetup, mis, misID, misQuarterlyCost, misSetup, partners | yes |  |
| TacticalPlan | calculate | items | no |  |
| TrophyRoom | view.staticData | badges, badgesIG | no |  |
| VarianceStudy | calculate | total | yes |  |
| WarehouseLocationRegional | calculate | total | yes |  |
| WarrantyCosts | view.staticData | criticalGroups | no |  |
| WebProductivity | calculate | total | yes |  |
| WebTraffic | calculate | total | yes |  |
