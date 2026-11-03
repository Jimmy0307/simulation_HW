# Control-plane demo (synthetic, reproducible)

Every number here comes from the invented pack in `examples/synthetic/`. Nothing in this folder is game data.
All outputs go to `outputs/` (ignored by git) and are byte-for-byte reproducible: same spec + seed gives the same
result and the same fingerprint.

```bash
# 1. scenario with a cost shock: per-quarter report + offline HTML
mpsim scenario run examples/demo-control/scenario.yaml --out outputs/demo-control
#    open outputs/demo-control/demo-cost-shock.html in a browser (no network needed)

# 2. small stress sweep (3 x 3 x 2 = 18 runs) and the three worst cases
mpsim sweep run examples/demo-control/sweep.yaml --out outputs/demo-control
mpsim sweep worst outputs/demo-control/demo-stress.sweep.json --top 3

# 3. diff two synthetic parameter packs (values allowed because both packs are synthetic)
mpsim params diff examples/synthetic examples/demo-control/pack-v2 --values --out outputs/demo-control/params-diff.md

# 4. one-off what-if on a save
mpsim new --params examples/synthetic --out outputs/demo-control/demo-save.json
mpsim what-if outputs/demo-control/demo-save.json --decisions examples/demo/q1.yaml \
    --set "capacity_options[*].cost=x1.2" --event rate_change:cd:-1
```

| file | what it is |
|---|---|
| `scenario.yaml` | demo plans for Q1-Q3, balanced plan afterwards, +15% capacity cost shock in Q3 |
| `sweep.yaml` | grid over capacity cost x Q2 demand shock x rival behaviour, objective `min_cash` |
| `pack-v2/pack.json` | the synthetic pack with a few invented "next quarter" changes (CD rate, capacity costs, one lease, one market size, one new component) |

Expected highlights: the capacity-cost variable has the largest main effect on `min_cash`; the worst case is
capacity cost x1.25 with demand -30% against aggressive rivals; the diff flags three verified modules (CD interest,
capacity investment, store lease) for re-verification. Demand-side numbers are **placeholder** (illustrative only).
