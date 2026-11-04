"""Sales force: headcount, pay, commission and training. HEURISTIC (practice rule).

Rules from general business sense only; no literature fit and no calibration on any game. Directions:

* more salespeople, or better trained ones, raise selling effort, with diminishing returns and a ceiling:
      effort = 1 + max_lift x (1 - exp(-force_per_market / force_scale))
      force  = headcount x (1 + skill_bonus x skill)
* training builds a skill stock in [0, 1] that decays:
      skill' = skill x (1 - skill_decay) + (1 - skill x (1 - skill_decay)) x (1 - exp(-training / training_scale))
* pay relative to a reference keeps people: the quarterly quit rate falls as relative pay rises, bounded:
      pay_index = (1 - commission_weight) x salary / reference_salary
                  + commission_weight x commission_pct / reference_commission_pct
      quit = clamp(base_quit x exp(-pay_sensitivity x (pay_index - 1)), min_quit, max_quit)
  the headcount carried to the next quarter is headcount x (1 - quit).
* costs: salaries (headcount x salary), hiring and severance per person, training (headcount x training),
  and commission (commission_pct % of revenue, charged by the engine after demand).

Selling effort multiplies the attraction of every offer of ours in every market it reaches (a company-wide force;
store and web sales staff are not separated yet). Coefficients: ``data/module_defaults.json`` (labelled defaults),
overridable per pack under ``modules.sales_force``. Next step to literature: docs/upgrade-protocol.md, ledger rows
``sales_force.*``.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from marketplace_sim.business.base import Maturity, ModuleInput, ModuleResult, ModuleSpec, number
from marketplace_sim.provenance import Level, Tagged

H = Level.HEURISTIC
NOTE = "heuristic: no literature, no calibration"


class SalesForceHeuristic:
    spec = ModuleSpec(
        key="sales_force", title="業務人力與薪酬", maturity=Maturity.HEURISTIC,
        decisions=("headcount", "salary", "commission_pct", "training"),
        outputs=("sales_force_headcount", "sales_force_hires", "sales_force_departures", "sales_force_quit_rate",
                 "sales_force_skill", "selling_effort", "sales_force_salaries", "sales_force_hiring",
                 "sales_force_training", "sales_force_commission"),
        couplings=("selling_effort", "expenses", "revenue_rates", "state"),
        evidence="src/marketplace_sim/business/sales_force.py (practice rule)")

    def __init__(self, coefficients: Mapping[str, Any]) -> None:
        self.c = {k: float(v) for k, v in coefficients.items()}

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
        return 1 + c["max_lift"] * (1 - math.exp(-per_market / c["force_scale"]))

    # --- one quarter ------------------------------------------------------------------------------------------------

    def run(self, inp: ModuleInput) -> ModuleResult:
        d, c = inp.decisions, self.c
        start = float(inp.state.get("headcount", c.get("initial_headcount", 0.0)))
        skill_prior = float(inp.state.get("skill", 0.0))
        # A quarter without a sales_force block keeps last quarter's pay and the carried headcount (people stay on).
        headcount = number(d, "headcount", start, high=c["max_headcount"])
        salary = number(d, "salary", float(inp.state.get("salary", c["reference_salary"])), high=100 * c["reference_salary"])
        commission = number(d, "commission_pct", float(inp.state.get("commission_pct", c["reference_commission_pct"])),
                            high=50.0)
        training = number(d, "training", 0.0, high=100 * c["reference_salary"])
        hires, departures_now = max(headcount - start, 0.0), max(start - headcount, 0.0)
        skill_start = skill_prior * start / headcount if headcount > 0 and headcount > start else skill_prior
        skill = self.skill_after(skill_start, training) if headcount > 0 else 0.0
        effort = self.effort(headcount, skill, inp.markets_reached)
        quit_rate = self.quit_rate(salary, commission)

        out = ModuleResult()
        out.selling_effort = Tagged(effort, H, f"1 + max_lift x (1 - exp(-force per market / scale)) ({NOTE})")
        out.lines["sales_force_headcount"] = Tagged(headcount, H, f"plan input; hiring assumed instant ({NOTE})")
        out.lines["sales_force_hires"] = Tagged(hires, H, f"max(headcount - carried headcount, 0) ({NOTE})")
        out.lines["sales_force_skill"] = Tagged(skill, H, f"training stock with decay ({NOTE})")
        out.lines["selling_effort"] = out.selling_effort
        out.lines["sales_force_quit_rate"] = Tagged(quit_rate, H, f"base quit x exp(-sensitivity x (pay index - 1)) ({NOTE})")
        out.lines["sales_force_departures"] = Tagged(headcount * quit_rate, H, f"headcount x quit rate ({NOTE})")
        out.expenses["sales_force_salaries"] = Tagged(headcount * salary, H, f"headcount x salary ({NOTE}: pay rule)")
        out.expenses["sales_force_hiring"] = Tagged(hires * c["hire_cost"] + departures_now * c["severance_cost"], H,
                                                    f"hires x hire cost + layoffs x severance ({NOTE})")
        out.expenses["sales_force_training"] = Tagged(headcount * training, H, f"headcount x training per person ({NOTE})")
        out.revenue_rates["sales_force_commission"] = Tagged(commission / 100, H, f"commission % of revenue ({NOTE})")
        # Nobody employed: the module stops carrying state, so it no longer runs (or marks numbers) next quarter.
        out.state = {} if headcount <= 0 else {"headcount": headcount * (1 - quit_rate), "skill": skill,
                                               "salary": salary, "commission_pct": commission}
        if headcount > 0 and inp.markets_reached == 0:
            out.notes.append("sales force: no open outlet at quarter start, so salespeople have no market to work")
        return out
