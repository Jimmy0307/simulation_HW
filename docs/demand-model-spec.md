# Demand model specification (literature level)

This is the demand side of the local engine (`LiteratureDemand`, `src/marketplace_sim/demand.py`). The **forms** come
from published literature ([demand-literature.md](demand-literature.md)). The **coefficients** are literature midpoints
or explicitly labelled defaults, **not** values calibrated on this game. Every number it produces carries the source
level **literature**, which is weaker than estimated and never a forecast. Coefficient defaults live in
`data/demand_literature.json`; a parameter pack can override them under `demand.coefficients`.

## 1. Inputs

| Input | Where it comes from | Level of the input |
|---|---|---|
| Market potential per city × segment, 12 months | parameter pack `markets[].segments[].size_12m` (market-size research) | derived (published) |
| Willingness to pay (WTP) per city × segment | pack `markets[].segments[].wtp` (price research) | derived (published) |
| Need index per segment (100 = average) | pack `segments[].needs` (customer-needs research) | derived (published) |
| Brand position: segment the brand type is designed for | pack `brand_types[].segment_id` | derived |
| Our price and advertising per brand | decisions (plan) | input |
| Our availability per city: stores per city, web centres per region | decisions + state | input |
| Rival offers: price, advertising, availability, quality | competitor bots, or private replay of real rival data | scenario assumption |

## 2. The demand chain

For quarter *t*, city *m*, segment *s* and offer *j* (one brand of one firm):

1. **Segment potential per quarter**
   `M_ms = size_12m(m, s) / 4`. The even quarterly split is an assumption (seasonality unknown).
2. **Fit of the product to the segment** (ideal-point / characteristics model)
   `sim(a, s) = 1` if `a = s`, else `max(0, cos(n_a − 100, n_s − 100))`. Here `n` is the need-index vector, so this is the cosine similarity of the centred need profiles. Then
   `fit_js = q_j · sim(position_j, s)^ρ`, where `q_j ∈ [0, 1]` is product quality (1 for our designed brands; rival bots may use less).
3. **Relative price** (reservation-price normalisation)
   `x_jms = price_j / WTP_ms`.
4. **Advertising goodwill** (Nerlove–Arrow stock, Koyck carryover)
   `G_j,t = λ · G_j,t−1 + a_j,t` for our brands (carried in the save). Rivals are assumed to be in steady state: `G = a / (1 − λ)`.
5. **Advertising response**, relative to a segment scale `G_ref,s = κ · Σ_m M_ms · WTP_ms`:
   * `power` (default, concave): `g = (1 + G / G_ref,s)^γ`
   * `adbudg` (switchable, S-shaped when c > 1): `g = 1 + (g_max − 1) · (G/G_ref,s)^c / (1 + (G/G_ref,s)^c)`
6. **Distribution**
   `d_jm = 1 − (1 − store_jm) · (1 − w · web_jm)`. Here `store_jm` and `web_jm` are 0/1 indicators and `w` is the strength of a web centre relative to a store.
7. **Attraction** (MNL utility × MCI-style multiplicative marketing terms)
   `A_jms = exp(β_fit · (fit_js − 1) − β_p · (x_jms − 1)) · g_j · d_jm^δ`, and `A_jms = 0` when `d_jm = 0` or `price_j ≤ 0`.
8. **Share with an outside option** (market share theorem plus a no-purchase good)
   `s_jms = A_jms / (exp(u_0) + Σ_k A_kms)`.
9. **Units demanded**
   `q_jms = M_ms · s_jms`, and `q_j = Σ_m Σ_s q_jms`.
10. **Units sold, market share and revenue** (engine)
    * `sold_j = min(q_j, inventory_j)`; rivals are assumed unconstrained.
    * Market share of firm *f* = `Σ_{j∈f} sold_j / Σ_k units_k`. This sums to 1 over firms.
    * Revenue = `Σ sold_j · price_j`.

Implied local elasticities (the yardstick for the defaults):
* Price: `∂ln q/∂ln p = −β_p · x · (1 − s)`.
* Goodwill (power form): `γ · G/(G + G_ref) · (1 − s)`.
* Distribution: `δ · (1 − s)`.

## 3. Coefficients

| Coefficient | Meaning | Default | Literature range | Basis |
|---|---|---|---|---|
| `price_sensitivity` β_p | Utility loss per unit of price/WTP | 2.6 | 1.5 – 4.0 | At p = WTP and share 0.15–0.33, gives elasticity −2.2 to −1.75: between the meta-analytic means −1.76 (Tellis 1988) and −2.62 (Bijmolt et al. 2005) |
| `ad_elasticity` γ | Elasticity of attraction to goodwill (long run, large spend) | 0.24 | 0.12 – 0.41 | Long-term mean 0.24 (Sethuraman et al. 2011). Implied long-term 0.41 from Assmus et al. (1984). |
| `carryover` λ | Quarterly retention of goodwill | 0.5 | 0.3 – 0.7 | Koyck identity with means: 1 − 0.12/0.24 = 0.5 (Sethuraman et al.); 1 − 0.22/0.41 ≈ 0.46 (Assmus et al.). Data-interval caveat (Clarke 1976). |
| `distribution_elasticity` δ | Exponent on distribution intensity | 1.0 | 0.74 – 1.5 | Total distribution elasticity 0.74 (Ataman et al. 2010); convex share–distribution curves, i.e. > 1 (Reibstein & Farris 1995; Wilbur & Farris 2014) |
| `ad_shape` | `power` or `adbudg` | `power` | – | Concave dominant (Simon & Arndt 1980). S-shape possible (Little 1970; Vakratsas et al. 2004). |
| `adbudg_c`, `adbudg_max` | ADBUDG exponent and ceiling | 2.0, 1.5 | – | **Labelled default** (form from Little 1970; no generalisable values) |
| `fit_weight` β_fit | Utility gap between perfect and zero fit | 3.0 | – | **Labelled default**: no published magnitude for this game's need indices |
| `similarity_power` ρ | Sharpness of cross-segment appeal | 1.0 | – | **Labelled default** |
| `web_weight` w | Web centre strength relative to a store | 0.5 | – | **Labelled default** |
| `outside_utility` u_0 | Attraction of not buying | 0.0 | – | **Labelled default**: one reference brand takes half the potential. Market size / outside good is an explicit assumption in this literature (Berry 1994). |
| `ad_reference_share` κ | Goodwill scale as a share of quarterly potential revenue | 0.01 | – | **Labelled default** |

Only the first four coefficients are tied to literature numbers. The labelled defaults are the first candidates for
calibration and for sensitivity sweeps (`demand.coefficients.*` overrides).

## 4. Fit to the game's known structure

| Relationship | Fit | Why |
|---|---|---|
| Attraction share with outside option over published potential | **high** | Several firms sell to the same city × segment cells, whose potential is published |
| Price relative to published WTP | **high (form)** / unknown slope | WTP per city × segment is published; the slope is not |
| Brand position ↔ segment via need-profile similarity | **medium** | Brand types are designed for a segment and need indices are published. Using need-profile similarity for cross-segment appeal is our modelling choice within the ideal-point family. |
| Advertising goodwill, concave response | **medium / uncertain** | Advertising screens are not yet captured; brand-level spending is assumed |
| Distribution (stores per city, web centres per region) | **medium** | Channel decisions exist at city and region level; the web-vs-store strength is unknown |
| Even quarterly split of 12-month potential | **low** | No evidence on seasonality |

## 5. Mapped vs still placeholder

| Mapped to literature (level literature) | Still placeholder (not modelled, documented) | Why not mapped |
|---|---|---|
| Market potential and WTP per city × segment | Component-level attribute scores (which component serves which need) | The game does not publish a component → need mapping; a name-based mapping would be our own guess |
| Need indices (segment-level fit) | Use-pattern indices | No decision maps to them; they describe segments, not products |
| Price, advertising, outlets | Sales force (compensation, headcount) | No sales-force decision in the engine yet. Literature: Albers et al. (2010), mean elasticity 0.34. |
| Brand-type design segment | Target-segment priority decision | No public evidence of any effect on demand |
| Competitor attraction and outside option | Brand-type `price_adj` | Meaning unverified |
| | Seasonality, market growth | No evidence |

## 6. Levels and the upgrade path

* `LiteratureDemand` outputs units at level **literature**. Downstream lines take the weakest input level:
  * units sold, market share and revenue are **literature**;
  * operating profit, tax, net income and cash end remain **placeholder** (production cost and tax are placeholders).
* `PlaceholderDemand` remains selectable: pack `demand.model: placeholder`, or `advance(demand=PlaceholderDemand())`.
* **Upgrade to estimated (FittedDemand)**. The interface is unchanged: `FittedDemand(model_path)`, `.units()`, level estimated.
  1. Accumulate the private demand panel: `evidence/private/model/demand_panel/Q<N>.json`, holding rival prices, advertising, outlets, units and share where pages show them.
  2. Fit the **same functional form**: estimate β_p, γ, λ, δ, β_fit, u_0 and w by maximum likelihood (or Berry inversion) on the panel, holding out the latest quarter.
  3. Write `evidence/private/model/fitted_demand.json` (`coefficients`, `validation: {holdout_quarter, mape, direction_hit_rate}`).
  4. `FittedDemand` loads it only if validation passes (MAPE ≤ 20 % and direction hit rate ≥ 70 %; the thresholds are this project's choice). The engine then reports demand lines as **estimated**. Otherwise it refuses and the engine stays at literature.
  5. Fitted coefficients stay private (they are this game's data). Only the form and the public defaults are published.
