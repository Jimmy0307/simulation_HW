# Roadmap

1. **EXP-01 (operator, team consent):** verify that `calculate` is non-persistent and that Cancel releases the lock. Everything in the W column depends on it.
2. Capture additional quarters' menus and screens passively (REA `inspect_web_page` / `observe_web_session` on a CDP browser the operator logged into) to replace "registered but unseen" with observed screens.
3. Run EXP-02…08 and accumulate private `experiment_values.json`; fit local slopes, then held-out surrogates for the cost functions.
4. Add REA runtime verifiers (scenario replays with `compare_web_captures`) so `evaluate_reconstruction_coverage` can move from `unknown` to `partial`/`covered`.
5. Revisit REA's semantic coverage of `sstudent.js` when a REA release raises the parent result budget, and retire the literal patterns in `rea_ingest.py` that REA can then answer.
6. Keep synthetic-only fixtures and run the publication gate before staging or pushing.
