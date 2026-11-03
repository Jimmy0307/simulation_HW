# Black-box system identification

Treat the observable system as `Y = f(X, S, C)`, where `X` is a controlled decision vector, `S` is the same starting simulation state, `C` is the competitor/environment state, and `Y` is an observed output. This notation describes an experiment design, not the Marketplace server's implementation.

## Current status

There are no decision/result pairs from a controlled change in this evidence set. The framework supports OFAT proposals, local finite differences, evidenced pair candidates, and optional held-out surrogate fits. It does not apply changes or advance the simulation. Global flags remain `DRY_RUN=true`, `READ_ONLY=true`, `ALLOW_WRITE=false`, and `ALLOW_FINAL_SUBMIT=false`.

**Update (REA pass):** the static analysis found a no-save what-if channel (`<Service>.calculate` while the `modify` lock is held) on 48 screens. Step 1 below is now concrete: [experiment-runbook.md](experiment-runbook.md) EXP-01. Item classes per (decision, output) are in [identifiability-matrix.md](identifiability-matrix.md).

## Highest information gain sequence

1. From the legitimate UI, capture one screen with editable decisions and inspect its delivered validation, save, preview, and recalculate behavior. Record an edit only if the UI indicates it is reversible and does not finalize or advance the quarter. This identifies feasible experimental inputs and output metrics.
2. For each supported numeric decision with an observable preview result, capture baseline and one small permitted change on the same state, then restore baseline and capture the opposite perturbation. Keep competitor and quarter fixed. This supports a local slope and reveals immediate discontinuities.
3. For input pairs that the observed domain model supports, use a 2x2 design to separate interaction from main effects. Do not try generic pairs without an observed corresponding variable.
4. Repeat at two or more starting values only after a reversible preview path is established. This distinguishes local linear response from thresholds, saturation, or clipping.
5. Fit the simplest surrogate justified by the sample count. Preserve an out-of-sample holdout and report R², MAE, RMSE, and the empirical 90th percentile absolute holdout residual as an uncertainty band. That band is empirical, not a calibrated guarantee.

Candidate pair categories encoded in the framework are price × advertising, price × brand, advertising × sales coverage, capacity × demand, and compensation × productivity. They are candidate designs only when evidence supports both variables. No interaction has been measured in the current capture.

## Surrogate boundary

Supported estimators include linear/ridge regression, decision tree, random forest, gradient boosting, and Gaussian process. Every report is labeled `OBSERVED_SURROGATE` and includes `internal_formula_claim=false`. The model approximates observed behavior over sampled states; it is never described as the proprietary source formula.
