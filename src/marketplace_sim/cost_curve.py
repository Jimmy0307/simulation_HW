"""Unit cost from the game's own cost-of-production estimate table (ESTIMATED level).

The game's CostOfProduction screen lists, for every designed brand, its estimated cost per unit at several production
volumes. That table is the only cost evidence before a settlement, so this module turns it into a cost function:

1. **Across brands (same volume).** At each listed volume the unit cost is linear in the brand's material cost
   (sum of component prices x costAdj): ``cost(n, m) = k(n) + s(n) x m``. Fitted per volume by least squares over
   the listed brands, so a brand that is not in the table (a new design) gets a cost too.
2. **Across volumes.** Between listed volumes the cost is interpolated with a natural cubic spline in
   log(units)-log(cost); outside the listed range the end segment is extended linearly in log-log (flagged).

A brand whose type and component set are in the table uses its own row (step 2 only). Pure Python, no fitted
constants are stored: everything is recomputed from the pack's ``cost_estimates``. Validation figures (leave-one-out)
are produced by ``validate`` on the private pack and are never written to the public repository.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from marketplace_sim.pack import BrandType, Component, CostEstimate, ParamPack


@dataclass(frozen=True)
class CurveCost:
    cost: float
    material_part: float  # s(n) x material (the part a material-cost factor scales)
    conversion_part: float  # the rest (labour, overhead, setup, learning)
    rule: str
    extrapolated: bool = False


def material_cost(brand_type: BrandType, components: Sequence[Component]) -> float:
    return sum(c.price for c in components) * brand_type.cost_adj


def _spline(xs: Sequence[float], ys: Sequence[float], x: float) -> tuple[float, bool]:
    """Natural cubic spline through (xs, ys) evaluated at x; linear extension of the end segments outside."""
    n = len(xs)
    if n == 1:
        return ys[0], x != xs[0]
    if x < xs[0] or x > xs[-1] or n == 2:
        i = 0 if x <= xs[0] else n - 2 if x >= xs[-1] else 0
        slope = (ys[i + 1] - ys[i]) / (xs[i + 1] - xs[i])
        return ys[i] + slope * (x - xs[i]), x < xs[0] or x > xs[-1]
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    # second derivatives m (natural: m0 = m_{n-1} = 0), tridiagonal solve
    a = [0.0] * n
    b = [1.0] * n
    c = [0.0] * n
    r = [0.0] * n
    for i in range(1, n - 1):
        a[i], b[i], c[i] = h[i - 1], 2 * (h[i - 1] + h[i]), h[i]
        r[i] = 6 * ((ys[i + 1] - ys[i]) / h[i] - (ys[i] - ys[i - 1]) / h[i - 1])
    for i in range(1, n):
        w = a[i] / b[i - 1]
        b[i] -= w * c[i - 1]
        r[i] -= w * r[i - 1]
    m = [0.0] * n
    m[-1] = r[-1] / b[-1]
    for i in range(n - 2, -1, -1):
        m[i] = (r[i] - c[i] * m[i + 1]) / b[i]
    i = max(j for j in range(n - 1) if xs[j] <= x)
    t1, t2 = xs[i + 1] - x, x - xs[i]
    value = (m[i] * t1 ** 3 + m[i + 1] * t2 ** 3) / (6 * h[i]) + (ys[i] / h[i] - m[i] * h[i] / 6) * t1 \
        + (ys[i + 1] / h[i] - m[i + 1] * h[i] / 6) * t2
    return value, False


def interpolate(points: Sequence[tuple[float, float]], units: float) -> tuple[float, bool]:
    """Cost per unit at ``units`` from (units, cost) points: natural cubic spline in log-log."""
    xs = [math.log(u) for u, _ in points]
    ys = [math.log(v) for _, v in points]
    value, outside = _spline(xs, ys, math.log(max(units, 1.0)))
    return math.exp(value), outside


def _fit_line(xs: Sequence[float], ys: Sequence[float]) -> tuple[float, float]:
    """Least-squares (intercept, slope); a single distinct x gives slope 1 through the mean (cost moves with material)."""
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return my - mx, 1.0
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / sxx
    return my - slope * mx, slope


def _known(pack: ParamPack, est: CostEstimate) -> float | None:
    ids = {c.id for c in pack.components}
    if not all(x in ids for x in est.components):
        return None
    try:
        bt = pack.brand_type(est.brand_type)
    except StopIteration:
        return None
    return material_cost(bt, [pack.component(x) for x in est.components])


def curve_cost(pack: ParamPack, brand_type: BrandType, components: Sequence[Component], units: float,
               *, exclude: CostEstimate | None = None) -> CurveCost | None:
    """Unit cost at ``units`` from the pack's estimate table, or None when the table cannot answer."""
    table = [e for e in pack.cost_estimates if e is not exclude]
    if not table or units <= 0:
        return None
    material = material_cost(brand_type, components)
    key = (brand_type.code, tuple(sorted(c.id for c in components)))
    own = next((e for e in table if (e.brand_type, tuple(sorted(e.components))) == key), None)
    rows = [(e, m) for e in table if (m := _known(pack, e)) is not None]
    volumes = sorted({u for e, _ in rows for u, _ in e.points})
    slopes: dict[float, float] = {}
    fitted: list[tuple[float, float]] = []
    for u in volumes:
        xs, ys = [], []
        for e, m in rows:
            hit = [v for uu, v in e.points if uu == u]
            if hit:
                xs.append(m)
                ys.append(hit[0])
        if xs:
            intercept, slope = _fit_line(xs, ys)
            slopes[u] = slope
            fitted.append((u, intercept + slope * material))
    if own is not None:
        cost, outside = interpolate(own.points, units)
        rule = "game's CostOfProduction estimate for this design, log-log spline over volume"
    elif len(fitted) >= 2 and len(rows) >= 2:
        cost, outside = interpolate(fitted, units)
        rule = ("game's CostOfProduction estimates of the other designs: cost linear in material cost at each volume, "
                "log-log spline over volume")
    else:
        return None
    slope = 1.0
    if slopes:
        slope, _ = interpolate([(u, max(s, 1e-9)) for u, s in sorted(slopes.items())], units)
    material_part = min(slope * material, cost)
    if outside:
        rule += " (outside the listed volumes: end segment extended)"
    return CurveCost(cost, material_part, cost - material_part, rule, outside)


def validate(pack: ParamPack) -> dict[str, float]:
    """Leave-one-out errors (percent) of both steps on the pack's own table. Private use: values are game data."""
    by_brand, by_volume = [], []
    for est in pack.cost_estimates:
        try:
            bt = pack.brand_type(est.brand_type)
            comps = [pack.component(x) for x in est.components]
        except StopIteration:
            continue
        for u, v in est.points:
            got = curve_cost(pack, bt, comps, u, exclude=est)
            if got is not None:
                by_brand.append(100 * (got.cost / v - 1))
        for j in range(1, len(est.points) - 1):
            rest = est.points[:j] + est.points[j + 1:]
            got_v, _ = interpolate(rest, est.points[j][0])
            by_volume.append(100 * (got_v / est.points[j][1] - 1))
    def stats(xs: list[float]) -> tuple[float, float]:
        return (max(abs(x) for x in xs), sum(abs(x) for x in xs) / len(xs)) if xs else (float("nan"), float("nan"))
    (b_max, b_mean), (v_max, v_mean) = stats(by_brand), stats(by_volume)
    return {"leave_one_brand_out_max_abs_pct": b_max, "leave_one_brand_out_mean_abs_pct": b_mean,
            "leave_one_volume_out_max_abs_pct": v_max, "leave_one_volume_out_mean_abs_pct": v_mean,
            "brands": float(len(pack.cost_estimates))}
