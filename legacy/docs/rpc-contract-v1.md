# Observed RPC contract

## Summary

The capture contains 102 network-entry observations. Of these, 70 have a recognized service query and method; the remaining 32 are non-service/unknown requests. The normalized registry has 31 service/method pairs and value-free request/response shapes. All recognized contracts used `POST` to `/mpl/web7/backend-json.php?<Service>` in this capture. The envelope shape is JSON with `method` and `parameters`; observed parameter and response schemas are preserved under `data/service_registry.json` and `data/rpc_observations.json`.

`observed_count` counts captured calls, not coverage or availability guarantees. `initiators`, page aliases, quarter, and evidence aliases are structural metadata only. Response values and headers are discarded.

## Observed services

The 29 methods classified `READ` are `view` on: `BasesCompetitiveAdvantage`, `CD`, `CompanyName`, `CorporateObjectives`, `Culture`, `CustomerNeeds`, `FinancialResources`, `FixedCapacity`, `InitialSalesForceCompensation`, `InitialWorkersCompensation`, `MarketSize`, `Mission`, `OpenSalesOffice`, `OpenWebcenter`, `PriceWillingToPay`, `ProFormaBalanceSheet`, `ProFormaCashFlow`, `ProFormaIncomeStatement`, `Problem`, `Stock`, `StrategicThrustsCorporate`, `StrategicThrustsFinance`, `StrategicThrustsMarketing`, `SummaryOfDecisions`, `SummaryOfStrategy`, `TacticStrategyLinksFinance`, `TacticStrategyLinksHumanResource`, `TacticStrategyLinksManufacturing`, and `UsePattern`.

Two observed contracts remain `UNKNOWN`: `GameInfo.studentsOnline` and `ServiceStatus.gs`. The former may expose activity about other users, and the latter is a generic dispatcher. Both are excluded from the runtime adapter. No write method or finalization contract was verified in this capture.

## Contract classes

The classifier recognizes `READ`, `WRITE`, `STATE_TRACKING`, `VALIDATION`, `CALCULATION_TRIGGER`, `FINALIZATION`, and `UNKNOWN`. A name-based classification is a conservative label over the observed method name, not a guarantee about server side effects. Only an explicitly observed `READ` is callable by the local adapter, and even that sends no request unless a caller separately creates the adapter with runtime credentials.

The MCP server currently serves local schemas and evidence. It does not make live RPC calls. The `MarketplaceRPCClient` is a separate optional adapter with an exact-host HTTPS check, a match against an observed service/method/request shape, redirect rejection, a response-size cap, and no write/finalization operation.
