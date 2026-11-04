"""Sales force: headcount, pay, commission and training. Mixed maturity, each output tagged by the part behind it.

LITERATURE part (``sales_force.staffing``): selling effort responds to the size of the force with a constant
elasticity, the form used in the personal-selling literature (Lodish 1971 call-response curves; the meta-analysis of
Albers, Mantrala & Sridhar 2010 reports these elasticities):

    effort = (1 + force_per_market / force_reference) ^ selling_elasticity

  concave in headcount (diminishing returns), 1 with no salespeople. ``selling_elasticity`` must lie in the
  meta-analytic range (data/module_defaults.json ``ranges``); ``force_reference`` is a labelled scale default.
  Effort multiplies the attraction of our offers; for a small market share the sales elasticity is close to the
  attraction elasticity.

HEURISTIC parts (no published quantified relation found; practice rules, labelled):

* ``sales_force.training``: training builds a decaying skill stock in [0, 1] that raises effective force:
      force = headcount x (1 + skill_bonus x skill)
  Any skill (trained this quarter or carried) makes effort, and everything downstream of demand, heuristic.
* ``sales_force.compensation``: the quarterly quit rate falls as pay rises against a reference, bounded. Only
  the direction has published support (pay satisfaction and turnover, Griffeth, Hom & Gaertner 2000); no elasticity.
  The carried headcount after quits is heuristic, so a quarter that runs on carried headcount is heuristic.
* costs: salaries, hiring and severance, training, commission. The game's sales-force cost rules were not observed,
  so every cost line is heuristic (and so is cash once a sales force is paid).
* ``sales_force.web_sales``: web salespeople (phone and chat for the web centers) add their own constant-elasticity
  response, applied in proportion to the web share of our outlets:
      effort x (1 + web share x ((1 + web force / web reference) ^ web elasticity - 1))
  The personal-selling meta-analysis is about field sales forces, so its range is not carried over: the web
  elasticity is a labelled practice default and any web salesperson makes effort heuristic. Paid the same salary.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from marketplace_sim.business.base import (
    Maturity,
    ModuleInput,
    ModuleResult,
    ModuleSpec,
    in_range,
    number,
)
from marketplace_sim.pack import ParamPack
from marketplace_sim.provenance import Level, Tagged

H, L = Level.HEURISTIC, Level.LITERATURE
NOTE = "heuristic: no published quantified relation, no calibration"
LIT = "constant-elasticity selling response (Lodish 1971; elasticity range: Albers, Mantrala & Sridhar 2010)"


class SalesForceModule:
    spec = ModuleSpec(
        key="sales_force", title="業務人力與薪酬",
        rows={"sales_force.staffing": Maturity.LITERATURE, "sales_force.training": Maturity.HEURISTIC,
              "sales_force.compensation": Maturity.HEURISTIC, "sales_force.web_sales": Maturity.HEURISTIC},
        decisions=("headcount", "salary", "commission_pct", "training", "web_headcount"),
        outputs=("sales_force_headcount", "sales_force_hires", "sales_force_departures", "sales_force_quit_rate",
                 "sales_force_skill", "selling_effort", "sales_force_salaries", "sales_force_hiring",
                 "sales_force_training", "sales_force_commission", "web_sales_headcount", "web_sales_effort",
                 "web_sales_salaries"),
        couplings=("selling_effort", "expenses", "revenue_rates", "state"),
        evidence="src/marketplace_sim/business/sales_force.py; data/module_defaults.json (ranges)")

    def __init__(self, coefficients: Mapping[str, Any], pack: ParamPack | None = None,
                 ranges: Mapping[str, Any] | None = None) -> None:
        self.c = {k: float(v) for k, v in coefficients.items()}
        if ranges is None:
            from marketplace_sim.business.registry import defaults

            ranges = defaults().get("sales_force", {}).get("ranges", {})
        for name, (low, high) in (ranges or {}).items():
            in_range(name, self.c[name], float(low), float(high))

    # --- rules (pure functions, tested for direction and bounds) ---------------------------------------------------

    def quit_rate(self, salary: float, commission_pct: float) -> float:
        c = self.c
        w = c["commission_weight"]
        pay_index = (1 - w) * salary / c["reference_salary"] + w * commission_pct / c["reference_commission_pct"]
        rate = c["base_quit"] * math.exp(-c["pay_sensitivity"] * (pay_index - 1))
        return min(c["max_quit"], max(c["min_quit"], rate))

    def skill_after(self, skill: float, training: float) -> float:
        c = self.c
        kept = skill * (1 - c["skill_decay"])
        return kept + (1 - kept) * (1 - math.exp(-training / c["training_scale"]))

    def effort(self, headcount: float, skill: float, markets: int) -> float:
        c = self.c
        force = headcount * (1 + c["skill_bonus"] * skill)
        per_market = force / max(markets, 1)
        return float((1 + per_market / c["force_reference"]) ** c["selling_elasticity"])

    # --- one quarter ------------------------------------------------------------------------------------------------

    def run(self, inp: ModuleInput) -> ModuleResult:
        d, c = inp.decisions, self.c
        start = float(inp.state.get("headcount", c.get("initial_headcount", 0.0)))
        skill_prior = float(inp.state.get("skill", 0.0))
        decided = "headcount" in d
        # A quarter without a sales_force block keeps last quarter's pay and the carried headcount (people stay on).
        headcount = number(d, "headcount", start, high=c["max_headcount"])
        salary = number(d, "salary", float(inp.state.get("salary", c["reference_salary"])), high=100 * c["reference_salary"])
        commission = number(d, "commission_pct", float(inp.state.get("commission_pct", c["reference_commission_pct"])),
                            high=50.0)
        training = number(d, "training", 0.0, high=100 * c["reference_salary"])
        web = number(d, "web_headcount", float(inp.state.get("web_headcount", 0.0)), high=c["max_headcount"])
        hires, layoffs = max(headcount - start, 0.0), max(start - headcount, 0.0)
        skill_start = skill_prior * start / headcount if headcount > 0 and headcount > start else skill_prior
        skill = self.skill_after(skill_start, training) if headcount > 0 else 0.0
        effort = self.effort(headcount, skill, inp.markets_reached)
        web_factor = 1.0
        if web > 0:
            web_effort = (1 + web / c["web_force_reference"]) ** c["web_elasticity"]
            web_factor = 1 + inp.web_share * (web_effort - 1)
            effort *= web_factor
        quit_rate = self.quit_rate(salary, commission)
        # Literature only when the force this quarter is the decided headcount and no (heuristic) part is in play.
        clean = decided and skill == 0.0 and web == 0.0
        effort_level = L if clean else H
        part = "web salespeople" if web else "skill from training" if skill else "carried headcount after quits"
        why = LIT if clean else f"{LIT}; with heuristic parts ({part})"

        out = ModuleResult()
        out.selling_effort = Tagged(effort, effort_level, why)
        out.lines["selling_effort"] = out.selling_effort
        out.lines["sales_force_headcount"] = Tagged(headcount, L if decided else H,
                                                    "plan input (hiring assumed at quarter start)" if decided
                                                    else f"carried headcount after quits ({NOTE})")
        out.lines["sales_force_hires"] = Tagged(hires, L if decided else H, "max(headcount - carried headcount, 0)")
        out.lines["sales_force_skill"] = Tagged(skill, H, f"training stock with decay ({NOTE})")
        out.lines["sales_force_quit_rate"] = Tagged(quit_rate, H, f"base quit x exp(-sensitivity x (pay index - 1)) ({NOTE})")
        out.lines["sales_force_departures"] = Tagged(headcount * quit_rate, H, f"headcount x quit rate ({NOTE})")
        out.expenses["sales_force_salaries"] = Tagged(headcount * salary, H, f"headcount x salary ({NOTE}: game cost rule unobserved)")
        out.expenses["sales_force_hiring"] = Tagged(hires * c["hire_cost"] + layoffs * c["severance_cost"], H,
                                                    f"hires x hire cost + layoffs x severance ({NOTE})")
        out.expenses["sales_force_training"] = Tagged(headcount * training, H, f"headcount x training per person ({NOTE})")
        out.revenue_rates["sales_force_commission"] = Tagged(commission / 100, H, f"commission % of revenue ({NOTE})")
        if web > 0 or "web_headcount" in d:
            out.lines["web_sales_headcount"] = Tagged(web, H, f"web salespeople (plan input or carried; {NOTE})")
            out.lines["web_sales_effort"] = Tagged(web_factor, H, f"1 + web share x ((1 + web/ref)^e - 1) ({NOTE})")
            out.expenses["web_sales_salaries"] = Tagged(web * salary, H, f"web salespeople x salary ({NOTE})")
        # Nobody employed: the module stops carrying state, so it no longer runs (or marks numbers) next quarter.
        out.state = {} if headcount <= 0 and web <= 0 else {"headcount": headcount * (1 - quit_rate), "skill": skill,
                                                            "salary": salary, "commission_pct": commission,
                                                            **({"web_headcount": web} if web > 0 else {})}
        if headcount > 0 and inp.markets_reached == 0:
            out.notes.append("no open outlet at quarter start, so salespeople have no market to work")
        return out
