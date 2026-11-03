# Demand-side literature review (public sources only)

Purpose: give the local engine a demand side whose **functional form** has published support. The **coefficients** are
not calibrated on this game's data. Everything here comes from academic papers, textbooks and author/publisher
statements. No game screens, parameters or data were used, and none from other players, teams or forums
(see `docs/decisions-log.md`, round "literature demand").

Fit to the game's known structure is graded **high / medium / low / uncertain**. The yardstick is what our own,
value-free parameter catalog shows (`data/parameter_catalog.json`): segments, need indices per segment, use-pattern
indices, willingness to pay (WTP) and market size per city and segment, brand types tied to a segment, components per
brand, stores per city, web centres per region, and a sales-force compensation screen.

## 1. Price response

| Candidate form | Typical parameters | Sources |
|---|---|---|
| Constant elasticity: `q = a · p^ε` | Mean selective-demand price elasticity −1.76 (367 estimates). Updated mean −2.62 (1,851 estimates, 81 studies). | Tellis (1988); Bijmolt, van Heerde & Pieters (2005) |
| Logit utility linear in price: `u = … − β·p` | Own elasticity `= −β·p·(1 − s)`. It rises with price and falls with share. | McFadden (1974); Guadagni & Little (1983) |
| Reservation price (WTP) threshold: buy only if value ≥ price. Heterogeneous WTP gives a smooth S-shaped curve. | Price is best expressed **relative to WTP** | Kohli & Mahajan (1991); Jedidi & Zhang (2002) |

**Fit: high (structure), coefficient unknown.** The game publishes a WTP per city × segment, which is exactly the
normaliser a reservation-price model uses (`p / WTP`). The slope must come from this game's data. Until then we use the
meta-analytic means.

## 2. Advertising response

| Candidate form | Typical parameters | Sources |
|---|---|---|
| Linear | Rejected by most evidence: no diminishing returns | Simon & Arndt (1980) review |
| Concave (power / log) | Mean short-term elasticity 0.22 (Assmus et al.). Updated mean 0.12 short-term and 0.24 long-term. | Assmus, Farley & Lehmann (1984); Sethuraman, Tellis & Briesch (2011) |
| S-shaped / saturating (ADBUDG `min + (max−min)·x^c/(d + x^c)`) | `c > 1` gives an S-shape, `c ≤ 1` a concave curve; saturation at `max` | Little (1970); Lilien, Kotler & Moorthy (1992) |
| Threshold / mixture of concave curves | Thresholds found in durables, not in a mature category | Vakratsas, Feinberg, Bass & Kalyanaram (2004) |
| Carryover (goodwill stock, geometric decay): `G_t = λ·G_{t−1} + a_t` | Koyck lag. With the meta-analytic means, long-term ≈ short-term / (1 − λ) gives λ ≈ 1 − 0.12/0.24 = 0.5 per period. | Nerlove & Arrow (1962); Clarke (1976) (duration depends on the data interval) |

**Fit: medium / uncertain.** Advertising decisions are not yet visible in our captures (first quarter). We expect
brand-level spending, but its media or market split is unknown. The concave form plus carryover is the
evidence-weighted default. The S-shape is kept as a switchable alternative.

## 3. Multi-attribute products

| Candidate form | Notes | Sources |
|---|---|---|
| Characteristics model: utility from product attributes | Foundation for attribute-based demand | Lancaster (1966) |
| Part-worth (additive) model: `u = Σ_k w_k · x_k` | The standard conjoint form | Green & Srinivasan (1978, 1990) |
| Ideal-point model: utility falls with the distance between product position and the segment's ideal point | Fits "brand type designed for segment X" | Green & Srinivasan (1978); Shocker & Srinivasan (1979) |
| Vector model: utility linear in each attribute | Special case of the part-worth model | Green & Srinivasan (1978) |

**Fit: high at the segment level, low at the component level.**
* **Segment level.** Each brand type is designed for one segment, and need indices per segment are published (100 = average). An ideal-point form can therefore use the **similarity of need profiles** between the brand's design segment and each buying segment.
* **Component level.** The game does not publish which component serves which need. Mapping component names to needs would be our own judgement, so component-level attribute scores stay **placeholder**.

## 4. Distribution / outlets

| Candidate form | Typical parameters | Sources |
|---|---|---|
| Share vs distribution: increasing and convex | Convex at the brand level. Increasing and convex at the SKU level in 86 % of 37 categories. | Reibstein & Farris (1995); Wilbur & Farris (2014) |
| Distribution elasticity of sales | Total (short-term + long-term) ≈ 0.74; larger than advertising (≈ 0.13) | Ataman, van Heerde & Mela (2010) |
| Spatial attraction (gravity) model: store pull ∝ attractiveness / distance^λ | Basis for "store present in the city" effects | Huff (1964) |

**Fit: medium.** Availability is decided per city (stores) and per region (web centres), so a multiplicative
distribution term `d^δ` fits. The relative strength of web centres versus stores has no public value and is a labelled
default.

## 5. Competition: attraction / MNL / MCI market-share models

| Candidate form | Notes | Sources |
|---|---|---|
| Market share theorem: `share_i = A_i / Σ_j A_j` | Holds when attractions are non-negative and symmetric | Bell, Keeney & Little (1975) |
| MCI: `A_i = Π_k x_ki^{β_k}` | Multiplicative competitive interaction; the log-linear estimation form is standard | Nakanishi & Cooper (1974); Cooper & Nakanishi (1988) |
| MNL: `A_i = exp(Σ_k β_k x_ki)` | Conditional logit; brand choice on scanner data | McFadden (1974); Guadagni & Little (1983) |
| Outside good (no-purchase option) | Lets total category demand respond to marketing; market size is an explicit assumption | Berry (1994) |
| Segment-level logit (latent classes) | Segments differ in preference and price sensitivity | Kamakura & Russell (1989) |

**Fit: high.** Several teams sell to the same segments in the same cities, and the game publishes segment market size
per city. An attraction model with an outside option over that potential is the natural fit.

## 6. Sales force

| Candidate form | Typical parameters | Sources |
|---|---|---|
| Concave response of sales to selling effort | Mean current-period personal-selling elasticity 0.34 (about 0.31 after bias correction) | Albers, Mantrala & Sridhar (2010) |

**Fit: uncertain.** A sales-force compensation screen exists, but the engine has no sales-force decision yet. Not
modelled; documented for later.

## 7. Business-simulation teaching literature

| Source | What it says publicly | Use |
|---|---|---|
| Cadotte (2016), *Journal of Marketing Education* | The author's view of simulation pedagogy and competitive learning | Context only. No demand equations are published. |
| Cadotte & MacGuire (2013), *Journal for Advancement of Marketing Education* | A pedagogy for simulations | Context only |
| Publisher site "Why Marketplace" and the textbook note (Cadotte & Bruce, *The Management of Strategy in the Marketplace*) | New-venture structure, functional areas, balanced scorecard | Context only. We did not obtain the textbook. |

**Fit: uncertain.** The public material describes pedagogy, not the demand mechanism. Nothing from it enters the
model.

## 8. Market potential

* Published 12-month potential per city × segment. The engine splits it evenly into quarters, which is an
  **assumption** with no source. Seasonality is unknown.
* Diffusion models (Bass 1969) would make potential grow over time. Not used: the potential is published per period
  and we have no evidence of growth rules.

## References

| Reference | Link / DOI |
|---|---|
| Albers, S., Mantrala, M. K., & Sridhar, S. (2010). Personal selling elasticities: A meta-analysis. *JMR* 47(5), 840–853. | https://econbiz.de/Record/personal-selling-elasticities-a-meta-analysis-albers-s%C3%B6nke/10008665407 |
| Assmus, G., Farley, J. U., & Lehmann, D. R. (1984). How advertising affects sales: Meta-analysis of econometric results. *JMR* 21(1), 65–74. | doi:10.1177/002224378402100107 |
| Ataman, M. B., van Heerde, H. J., & Mela, C. F. (2010). The long-term effect of marketing strategy on brand sales. *JMR* 47(5), 866–882. | doi:10.1509/jmkr.47.5.866 |
| Bass, F. M. (1969). A new product growth for model consumer durables. *Management Science* 15(5), 215–227. | doi:10.1287/mnsc.15.5.215 |
| Bell, D. E., Keeney, R. L., & Little, J. D. C. (1975). A market share theorem. *JMR* 12(2), 136–141. | Working-paper version: https://dspace.mit.edu/handle/1721.1/48366 (journal DOI not verified) |
| Berry, S. T. (1994). Estimating discrete-choice models of product differentiation. *RAND Journal of Economics* 25(2), 242–262. | doi:10.2307/2555829 |
| Bijmolt, T. H. A., van Heerde, H. J., & Pieters, R. G. M. (2005). New empirical generalizations on the determinants of price elasticity. *JMR* 42(2), 141–156. | doi:10.1509/jmkr.42.2.141.62296 |
| Cadotte, E. R. (2016). Creating value in marketing and business simulations: An author's viewpoint. *Journal of Marketing Education* 38(2), 119–129. | doi:10.1177/0273475316649741 |
| Cadotte, E. R., & MacGuire, C. (2013). A pedagogy to enhance the value of simulations in the classroom. *Journal for Advancement of Marketing Education* 21(2), 38–52. | https://jame.scholasticahq.com/article/150534-a-pedagogy-to-enhance-the-value-of-simulations-in-the-classroom |
| Clarke, D. G. (1976). Econometric measurement of the duration of advertising effect on sales. *JMR* 13(4), 345–357. | https://journals.sagepub.com/toc/mrj/13/4 |
| Cooper, L. G., & Nakanishi, M. (1988). *Market-Share Analysis*. Boston: Kluwer. | Author page: https://www.anderson.ucla.edu/faculty/lee.cooper/MCI_Book/Book1.htm |
| Green, P. E., & Srinivasan, V. (1978). Conjoint analysis in consumer research: Issues and outlook. *Journal of Consumer Research* 5(2), 103–123. | doi:10.1086/208721 |
| Green, P. E., & Srinivasan, V. (1990). Conjoint analysis in marketing: New developments with implications for research and practice. *Journal of Marketing* 54(4), 3–19. | https://www.gsb.stanford.edu/faculty-research/working-papers/conjoint-analysis-marketing-research-review-new-developments |
| Guadagni, P. M., & Little, J. D. C. (1983). A logit model of brand choice calibrated on scanner data. *Marketing Science* 2(3), 203–238. | https://econpapers.repec.org/RePEc:inm:ormksc:v:2:y:1983:i:3:p:203-238 |
| Huff, D. L. (1964). Defining and estimating a trading area. *Journal of Marketing* 28(3), 34–38. | doi:10.2307/1249154 |
| Jedidi, K., & Zhang, Z. J. (2002). Augmenting conjoint analysis to estimate consumer reservation price. *Management Science* 48(10), 1350–1368. | doi:10.1287/mnsc.48.10.1350.272 |
| Kamakura, W. A., & Russell, G. J. (1989). A probabilistic choice model for market segmentation and elasticity structure. *JMR* 26(4), 379–390. | doi:10.1177/002224378902600401 |
| Kohli, R., & Mahajan, V. (1991). A reservation-price model for optimal pricing of multiattribute products in conjoint analysis. *JMR* 28(3), 347–354. | Erratum JMR 28(4), 506. Listed on the author CV: https://business.columbia.edu/sites/default/files-efs/person/cv/Kohli_Rajeev_CV_2025.pdf |
| Lancaster, K. J. (1966). A new approach to consumer theory. *Journal of Political Economy* 74(2), 132–157. | JSTOR stable 1828835 (https://www.jstor.org/stable/1828835) |
| Lilien, G. L., Kotler, P., & Moorthy, K. S. (1992). *Marketing Models*. Prentice-Hall. | Textbook (ADBUDG form, chapter on response models) |
| Little, J. D. C. (1970). Models and managers: The concept of a decision calculus. *Management Science* 16(8), B466–B485. | doi:10.1287/mnsc.16.8.B466 |
| McFadden, D. (1974). Conditional logit analysis of qualitative choice behavior. In P. Zarembka (Ed.), *Frontiers in Econometrics* (pp. 105–142). Academic Press. | Book chapter |
| Nakanishi, M., & Cooper, L. G. (1974). Parameter estimation for a multiplicative competitive interaction model: Least squares approach. *JMR* 11(3), 303–311. | doi:10.1177/002224377401100309 (JSTOR 10.2307/3151146) |
| Nerlove, M., & Arrow, K. J. (1962). Optimal advertising policy under dynamic conditions. *Economica* 29(114), 129–142. | doi:10.2307/2551549 |
| Reibstein, D. J., & Farris, P. W. (1995). Market share and distribution: A generalization, a speculation, and some implications. *Marketing Science* 14(3, suppl.), G190–G202. | doi:10.1287/mksc.14.3.G190 |
| Sethuraman, R., Tellis, G. J., & Briesch, R. A. (2011). How well does advertising work? Generalizations from meta-analysis of brand advertising elasticities. *JMR* 48(3), 457–471. | https://econbiz.de/Record/how-well-does-advertising-work-generalizations-from-meta-analysis-of-brand-advertising-elasticities-sethuraman-raj/10009161369 |
| Shocker, A. D., & Srinivasan, V. (1979). Multiattribute approaches for product concept evaluation and generation: A critical review. *JMR* 16(2), 159–180. | doi:10.1177/002224377901600202 |
| Simon, J. L., & Arndt, J. (1980). The shape of the advertising response function. *Journal of Advertising Research* 20(4), 11–28. | https://econbiz.de/Record/the-shape-of-the-advertising-response-function-simon-julian/10002824073 |
| Tellis, G. J. (1988). The price elasticity of selective demand: A meta-analysis of econometric models of sales. *JMR* 25(4), 331–341. | https://www.msi.org/working-papers/the-price-elasticity-of-selective-demand-a-metaanalysis-of-sales-response-models/ |
| Vakratsas, D., Feinberg, F. M., Bass, F. M., & Kalyanaram, G. (2004). The shape of advertising response functions revisited. *Marketing Science* 23(1), 109–119. | doi:10.1287/mksc.1030.0035 |
| Wilbur, K. C., & Farris, P. W. (2014). Distribution and market share. *Journal of Retailing* 90(2), 154–167. | doi:10.1016/j.jretai.2013.08.003 |

Every entry was checked during this round against publisher, RePEc, JSTOR or bibliographic records. Exceptions: the
journal DOI of Bell, Keeney & Little (1975), marked "not verified" (the MIT working-paper record is given), and the
McFadden (1974) chapter and the Lilien, Kotler & Moorthy (1992) textbook, which are book citations without DOIs.
