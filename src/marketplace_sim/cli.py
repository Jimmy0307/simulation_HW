"""mpsim: local business-planning simulator driven by parameter packs.

  mpsim new --params DIR --out SAVE.json [--quarter N]
  mpsim play SAVE.json --decisions PLAN.yaml [--seed N]
  mpsim compare SAVE.json PLAN.yaml [PLAN.yaml ...] [--seed N]
  mpsim explain METRIC
  mpsim scenario new|run|templates ...             (game master)
  mpsim what-if SAVE.json --set PATH=VALUE --event TYPE:TARGET:MAGNITUDE
  mpsim sweep run SWEEP.yaml --out DIR | mpsim sweep worst RESULTS.json --top N   (agent harness)
  mpsim params diff OLD_DIR NEW_DIR [--values --out PRIVATE_FILE]
  mpsim build-pack --out evidence/private/model [--har FILE.har ...] [--base OLD_PACK_DIR]   (private)
  mpsim reconcile --params DIR --har FILE.har --quarter N --plan PLAN.yaml [--save SAVE.json] --out PRIVATE.json
  mpsim cost-curve --params DIR [--brand-type T --components ID,ID,... --units N ...]   (private pack)
  mpsim intake --har FILE.har --out PRIVATE_ORDERS.yaml          (the team's entered decisions -> factory orders)
  mpsim factory --params DIR --orders ORDERS.yaml [--oc 12,14,16] [--ot 0,2] [--demand 0.5,1,1.5] [--reading factory|brand|both]
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path
from typing import Any

import yaml

from marketplace_sim.engine import CompanyState, Plan, Report, advance
from marketplace_sim.metrics import METRICS, lookup
from marketplace_sim.pack import ParamPack, load_pack
from marketplace_sim.provenance import Level

SAVE_SCHEMA = "marketplace-sim/save@1"


def _read_plan(path: Path) -> Plan:
    data: Any = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise SystemExit(f"{path}: plan must be a mapping")
    return Plan.from_dict(data, name=path.stem)


def _load_save(path: Path) -> tuple[dict[str, Any], ParamPack, CompanyState]:
    save = json.loads(path.read_text(encoding="utf-8"))
    if save.get("schema") != SAVE_SCHEMA:
        raise SystemExit(f"{path} is not a mpsim save")
    params = Path(save["params"])
    if not params.is_absolute():
        params = (path.parent / params).resolve()
    return save, load_pack(params), CompanyState.from_dict(save["state"])


def cmd_new(args: argparse.Namespace) -> None:
    pack = load_pack(Path(args.params))
    state = CompanyState.initial(pack, args.quarter)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        params_ref = str(Path(args.params).resolve().relative_to(out.parent.resolve()))
    except ValueError:
        params_ref = str(Path(args.params).resolve())
    out.write_text(json.dumps({"schema": SAVE_SCHEMA, "params": params_ref, "pack_name": pack.name,
                               "pack_provenance": pack.provenance, "state": state.to_dict(), "history": []},
                              indent=1), encoding="utf-8")
    print(f"new game: pack '{pack.name}' ({pack.provenance}), quarter {state.quarter}, cash {state.cash:,.2f} -> {out}")


def cmd_play(args: argparse.Namespace) -> None:
    path = Path(args.save)
    save, pack, state = _load_save(path)
    plan = _read_plan(Path(args.decisions))
    new_state, report = advance(state, plan, pack, seed=args.seed)
    save["state"] = new_state.to_dict()
    save["history"].append(report.to_dict())
    path.write_text(json.dumps(save, indent=1), encoding="utf-8")
    print(report.render())
    print(f"\nsaved: quarter {new_state.quarter} -> {path}")


def _compare_table(reports: list[Report]) -> str:
    keys: list[str] = []
    for report in reports:
        keys += [k for k in report.lines if k not in keys]
    width = max(len(k) for k in keys)
    header = "metric".ljust(width) + "".join(f"  {r.plan[:22]:>24}" for r in reports) + "  weakest"
    rows = [f"Quarter {reports[0].quarter} comparison   [V]=verified [D]=derived [E]=estimated [L]=literature [P]=placeholder",
            header, "-" * len(header)]
    for key in keys:
        cells, levels = [], []
        for report in reports:
            value = report.lines.get(key)
            cells.append(f"  {value.render() if value else '-':>24}")
            if value:
                levels.append(value.level)
        rows.append(key.ljust(width) + "".join(cells) + f"  {min(levels).label if levels else '-'}")
    return "\n".join(rows)


def cmd_compare(args: argparse.Namespace) -> None:
    _, pack, state = _load_save(Path(args.save))
    paths = [Path(p) for pattern in args.plans for p in (sorted(glob.glob(pattern)) or [pattern])]
    reports = [advance(state, _read_plan(p), pack, seed=args.seed)[1] for p in paths]
    print(_compare_table(reports))
    for report in reports:
        for note in report.notes:
            print(f"note [{report.plan}]: {note}")


def cmd_explain(args: argparse.Namespace) -> None:
    info = lookup(args.metric)
    if info is None:
        print(f"unknown metric '{args.metric}'. Known: {', '.join(sorted(METRICS))}")
        sys.exit(2)
    print(f"{info.name}\n  level:    {info.level.label} [{info.level.mark}]\n  formula:  {info.formula}\n"
          f"  evidence: {info.evidence}" + (f"\n  note:     {info.note}" if info.note else ""))
    print("\nLevels: verified = reproduced against measured server results; derived = follows from published "
          "parameters; estimated = fitted to data; literature = published functional form, coefficients not "
          "calibrated on this game (not a forecast); placeholder = illustrative, uncalibrated.")
    _ = Level


SCENARIO_TEMPLATE = """\
# Scenario definition (schema marketplace-sim/scenario@1). Run: mpsim scenario run {file} --out outputs/scenarios
name: {name}
description: "What this scenario tests"
base_params: {params}          # parameter pack directory (relative to this file); private packs stay private
horizon: 4                     # quarters to simulate
start_quarter: 1
seed: 0                        # same spec + seed => identical results
overrides:                     # parameter changes; path syntax: a.b, list[*], list[key=value], dict.*
  - {{path: "capacity_options[*].cost", scale: 1.0, from_quarter: 3}}
events:                        # cost_shock | demand_shock | rate_change | fx_shock | competitor_price_cut | supply_disruption
  - {{type: cost_shock, from_quarter: 3, target: capacity, magnitude: 0.15, duration: 2}}
competitors:                   # strategy: baseline | random | replay (replay panel files must be private)
  - {{name: rival-a, strategy: baseline}}
  - {{name: rival-b, strategy: random, params: {{price_factor: 0.95}}}}
our_policy:                    # hold | fixed (default + per-quarter plans) | external (dir with q<N>.yaml)
  type: fixed
  default: ../demo/plans/b-balanced.yaml
  plans: {{1: ../demo/q1.yaml}}
"""


def _guard_output(pack_provenance: str, out: Path) -> None:
    if pack_provenance != "synthetic" and "private" not in out.resolve().as_posix().split("/"):
        raise SystemExit("outputs built from a non-synthetic pack must be written under a 'private' directory")


def cmd_scenario(args: argparse.Namespace) -> None:
    from marketplace_sim.control.html import render_results
    from marketplace_sim.control.runner import run_scenario, write_result
    from marketplace_sim.control.spec import load_spec

    if args.action == "new":
        path = Path(args.file)
        if path.exists():
            raise SystemExit(f"{path} exists; refusing to overwrite")
        params = Path(args.params).resolve()
        try:
            params_ref = Path(str(params.relative_to(path.parent.resolve()))).as_posix()
        except ValueError:
            params_ref = params.as_posix()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(SCENARIO_TEMPLATE.format(file=path.as_posix(), name=path.stem, params=params_ref), encoding="utf-8")
        print(f"scenario skeleton written: {path}")
    elif args.action == "templates":
        for spec_path in sorted(Path(args.dir).glob("*.yaml")):
            spec = load_spec(spec_path)
            print(f"{spec_path.as_posix():45} {spec.name:22} {spec.description}")
    elif args.action == "run":
        spec = load_spec(Path(args.file))
        pack = load_pack(spec.resolve(spec.base_params))
        out = Path(args.out)
        _guard_output(pack.provenance, out)
        result = run_scenario(spec)
        path = write_result(result, out)
        data = result.to_dict()
        (out / f"{result.name}.html").write_text(render_results([data], f"Scenario {result.name}"), encoding="utf-8")
        for q in data["quarters"]:
            cash = q["lines"]["cash_end"]
            print(f"Q{q['quarter']}: cash_end {cash['value']:,.2f} [{cash['level'][0].upper()}]"
                  + (f"  events: {'; '.join(q['events'])}" if q["events"] else ""))
        print(f"summary: {json.dumps(data['summary'], ensure_ascii=False)}\nwritten: {path} and {result.name}.html")


def _parse_set(item: str) -> tuple[str, str, float | str]:
    path, _, raw = item.partition("=")
    if raw.startswith(("x", "*")):
        return path, "scale", float(raw[1:])
    if raw.startswith(("+", "-")) and raw[1:].replace(".", "", 1).isdigit():
        return path, "add", float(raw)
    try:
        return path, "set", float(raw)
    except ValueError:
        return path, "set", raw


def cmd_what_if(args: argparse.Namespace) -> None:
    from marketplace_sim.control.events import apply_events
    from marketplace_sim.control.spec import EventSpec, Override, apply_overrides
    from marketplace_sim.pack import pack_from_dict

    save, pack, state = _load_save(Path(args.save))
    raw = json.loads(pack.path.read_text(encoding="utf-8")) if pack.path else {}
    overrides = [Override(p, op, v) for p, op, v in (_parse_set(s) for s in args.set or [])]
    events = []
    for item in args.event or []:
        etype, target, magnitude = (item.split(":") + ["*", "0"])[:3]
        events.append(EventSpec(etype, state.quarter, float(magnitude), target))
    data, applied = apply_overrides(raw, overrides, state.quarter)
    data, adjust = apply_events(data, events, state.quarter)
    plan = _read_plan(Path(args.decisions)) if args.decisions else Plan(name="hold")
    base = advance(state, plan, pack, seed=args.seed)[1]
    base.plan = "baseline"
    changed = advance(state, plan, pack_from_dict(data, pack.path), seed=args.seed, adjust=adjust)[1]
    changed.plan = "what-if"
    print(_compare_table([base, changed]))
    for note in applied + [f"event: {label}" for label in adjust.labels]:
        print(f"applied: {note}")
    _ = save


def cmd_sweep(args: argparse.Namespace) -> None:
    from marketplace_sim.control.spec import load_spec
    from marketplace_sim.control.sweep import load_sweep, run_sweep, worst, write_sweep

    if args.action == "run":
        sweep = load_sweep(Path(args.file))
        spec = load_spec(sweep.base_scenario)
        _guard_output(load_pack(spec.resolve(spec.base_params)).provenance, Path(args.out))
        result = run_sweep(sweep)
        path = write_sweep(result, Path(args.out))
        print(f"{len(result['rows'])} scenarios -> {path}")
        if result["caveat"]:
            print(f"NOTE: {result['caveat']}")
        print("most sensitive: " + ", ".join(f"{s['variable']} (range {s['main_effect_range']:,.0f})"
                                             for s in result["sensitivity"] if s["main_effect_range"] is not None))
    else:
        data = json.loads(Path(args.file).read_text(encoding="utf-8"))
        rows = worst(data["rows"], args.top)
        print(f"worst {len(rows)} by {data['objective']} (lowest first):")
        if data.get("caveat"):
            print(f"NOTE: {data['caveat']}")
        for row in rows:
            print(f"  {row['id']}  {row['objective']:>16,.2f}  {json.dumps(row['assignment'], ensure_ascii=False)}  "
                  f"[{row['fingerprint']}]")


def cmd_params(args: argparse.Namespace) -> None:
    from marketplace_sim.control.diff import diff_dirs, render

    changes = diff_dirs(Path(args.old), Path(args.new))
    synthetic = load_pack(Path(args.old)).provenance == "synthetic" and load_pack(Path(args.new)).provenance == "synthetic"
    if args.out:
        out = Path(args.out)
        if args.values and not synthetic and "private" not in out.resolve().as_posix().split("/"):
            raise SystemExit("a diff with real values must be written under a 'private' directory")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render(changes, include_values=args.values), encoding="utf-8")
        print(f"written: {out}")
    print(render(changes, include_values=args.values and synthetic))


def cmd_build_pack(args: argparse.Namespace) -> None:
    from marketplace_sim.pack_builder import build_private_pack

    print(build_private_pack(Path(args.out), Path(args.evidence), [Path(h) for h in args.har or []],
                             Path(args.base) if args.base else None))
    if args.quarter_label:
        from marketplace_sim.control.diff import quarterly_snapshot, red_flags, render

        changes, previous = quarterly_snapshot(Path(args.out), args.quarter_label)
        if previous is None:
            print(f"snapshot {args.quarter_label} stored (first quarter, nothing to diff)")
            return
        print(f"diff vs {previous}: {len(changes)} change(s); full report in {args.out}/diffs/")
        for flag in red_flags(changes):
            print(flag)
        print(render(changes, include_values=False))


def cmd_reconcile(args: argparse.Namespace) -> None:
    """Replay one quarter's submitted plan and compare the engine with that quarter's settled statements.

    Values go to ``--out`` (must be under a private directory); the screen shows statuses only.
    """
    from marketplace_sim import reconcile as rc
    from marketplace_sim.pack_builder import _latest_views
    from marketplace_sysid.parameters import collect

    out = Path(args.out)
    if "private" not in out.resolve().as_posix().split("/"):
        raise SystemExit("--out must be inside a 'private' directory (the report holds game values)")
    pack = load_pack(Path(args.params))
    if args.save:
        _, _, state = _load_save(Path(args.save))
    elif args.quarter == 1:
        state = CompanyState(quarter=1, cash=0.0, cd=0.0, fixed_capacity_units=0.0)  # game start: nothing owned
    else:
        raise SystemExit("--save is needed for a quarter after the first (state at that quarter's start)")
    views = _latest_views(collect([], [], [Path(h) for h in args.har]))
    actuals = rc.actuals_from_views(views, args.quarter)
    if not actuals:
        raise SystemExit(f"no settled statements of quarter {args.quarter} in the capture")
    plan = _read_plan(Path(args.plan))
    plan.modules = {"accounting.accrual": {}, **plan.modules}
    _, report = advance(state, plan, pack, seed=args.seed)
    mappings = {"income": rc.INCOME_ROWS, "cash": rc.CASH_ROWS, "balance": rc.BALANCE_ROWS}
    result = {name: [vars(r) | {"lines": list(r.lines)} for r in rc.compare_values(report.lines, rows, mappings[name])]
              for name, rows in actuals.items()}
    levels = {k: v.level.label for k, v in report.lines.items()}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"quarter": args.quarter, "plan": plan.name, "statements": result, "line_levels": levels},
                              indent=1, ensure_ascii=False), encoding="utf-8")
    for name, rows in result.items():
        counts: dict[str, int] = {}
        for row in rows:
            counts[row["status"]] = counts.get(row["status"], 0) + 1
        print(f"{name}: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
        print("  differs: " + (", ".join(r["row"] for r in rows if r["status"] == "differs") or "-"))
    print(f"values written (private): {out}")


def cmd_cost_curve(args: argparse.Namespace) -> None:
    """Unit cost from the pack's cost table: leave-one-out check, or a what-if design at given volumes."""
    from marketplace_sim.cost_curve import curve_cost, validate

    pack = load_pack(Path(args.params))
    if not pack.cost_estimates:
        raise SystemExit("this pack has no cost_estimates (capture the CostOfProduction screen and rebuild)")
    check = validate(pack)
    print(f"cost table: {check['brands']:.0f} designs; leave-one-brand-out max |err| "
          f"{check['leave_one_brand_out_max_abs_pct']:.2f}%, leave-one-volume-out max |err| "
          f"{check['leave_one_volume_out_max_abs_pct']:.2f}%")
    if args.components:
        bt = pack.brand_type(args.brand_type)
        comps = [pack.component(c.strip()) for c in args.components.split(",")]
        for units in args.units or [100.0, 250.0, 500.0, 1000.0]:
            got = curve_cost(pack, bt, comps, units)
            print(f"{units:>8.0f} units: " + ("-" if got is None else f"{got.cost:,.2f} [E] {got.rule}"))


def _private_out(path: Path) -> None:
    if "private" not in path.resolve().as_posix().split("/"):
        raise SystemExit("output must be inside a 'private' directory (it holds game data)")


def cmd_intake(args: argparse.Namespace) -> None:
    from marketplace_sim.intake import orders_from_views
    from marketplace_sim.pack_builder import _latest_views
    from marketplace_sysid.parameters import collect

    out = Path(args.out)
    _private_out(out)
    data = orders_from_views(_latest_views(collect([], [], [Path(h) for h in args.har])))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"{len(data['orders'])} brand(s) on sale; schedule entered: {data['schedule']}")
    for warning in data["warnings"]:
        print(f"warning: {warning}")
    print(f"orders written (private): {out}")


def _floats(text: str) -> list[float]:
    return [float(x) for x in text.split(",") if x.strip()]


def cmd_factory(args: argparse.Namespace) -> None:
    """Production scheduler's sweep: operating capacity x overtime x demand outcome, for the orders the team entered."""
    from marketplace_sim.factory import (
        DEFAULT_PRODUCTIVITY,
        BrandOrder,
        required_operating_capacity,
        sweep,
    )

    pack = load_pack(Path(args.params))
    spec = yaml.safe_load(Path(args.orders).read_text(encoding="utf-8")) or {}
    orders = [BrandOrder(str(o["name"]), str(o["brand_type"]), tuple(str(c) for c in o["components"]), float(o["price"]),
                         float(o["forecast"])) for o in spec.get("orders", [])]
    if not orders:
        raise SystemExit("no orders (no brand on sale)")
    entered = spec.get("schedule") or {}
    productivity = args.productivity or float(entered.get("productivity") or 0) or DEFAULT_PRODUCTIVITY
    forecast = sum(o.forecast for o in orders)
    need = required_operating_capacity(forecast, productivity)
    print(f"forecast {forecast:,.0f} units; productivity {productivity:g} %; help-text operating capacity "
          f"{need:.1f}/day (+25 % buffer: {required_operating_capacity(forecast, productivity, 0.25):.1f})")
    readings = ["factory", "brand"] if args.reading == "both" else [args.reading]
    rows = []
    for reading in readings:
        rows += sweep(pack, orders, _floats(args.oc), _floats(args.ot), _floats(args.demand), productivity=productivity,
                      reading=reading, previous_operating_capacity=args.previous_oc)
    header = f"{'reading':8} {'OC':>4} {'OT':>3} {'dem%':>5} {'demand':>7} {'made':>6} {'lost':>5} {'idle':>5} {'OTh':>4} " \
             f"{'cost/u':>7} {'prod.cost':>10} {'contrib.':>10} {'next-q cut':>10}"
    print(header)
    for r in rows:
        print(f"{r['reading']:8} {r['operating_capacity']:>4.0f} {r['max_overtime_hours']:>3.0f} {100 * float(r['demand_factor']):>5.0f} "
              f"{r['demand']:>7,.0f} {r['produced']:>6,.0f} {r['lost']:>5,.0f} {r['idle_units']:>5,.0f} "
              f"{r['overtime_hours_used']:>4.1f} {r['unit_cost']:>7,.0f} {r['production_cost']:>10,.0f} "
              f"{r['contribution']:>10,.0f} {100 * float(r['next_quarter_demand_cut']):>9.1f}%")
    if args.out:
        out = Path(args.out)
        _private_out(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(rows, indent=1), encoding="utf-8")
        print(f"rows written (private): {out}")


def main(argv: list[str] | None = None) -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(prog="mpsim", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("new", help="create a new save from a parameter pack")
    p.add_argument("--params", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--quarter", type=int, default=1)
    p.set_defaults(func=cmd_new)
    p = sub.add_parser("play", help="advance one quarter with a decisions file")
    p.add_argument("save")
    p.add_argument("--decisions", required=True)
    p.add_argument("--seed", type=int, default=0)
    p.set_defaults(func=cmd_play)
    p = sub.add_parser("compare", help="compare plans from the same state (save is not modified)")
    p.add_argument("save")
    p.add_argument("plans", nargs="+")
    p.add_argument("--seed", type=int, default=0)
    p.set_defaults(func=cmd_compare)
    p = sub.add_parser("explain", help="explain a metric")
    p.add_argument("metric")
    p.set_defaults(func=cmd_explain)
    p = sub.add_parser("scenario", help="game master: create, list and run scenarios")
    p.add_argument("action", choices=["new", "run", "templates"])
    p.add_argument("file", nargs="?", default="")
    p.add_argument("--out", default="outputs/scenarios")
    p.add_argument("--params", default="examples/synthetic")
    p.add_argument("--dir", default="examples/scenarios")
    p.set_defaults(func=cmd_scenario)
    p = sub.add_parser("what-if", help="one-off parameter/event change on a save, compared with the baseline")
    p.add_argument("save")
    p.add_argument("--set", action="append", help="path=value | path=x1.15 (scale) | path=+5 (add)")
    p.add_argument("--event", action="append", help="type:target:magnitude, e.g. cost_shock:capacity:0.15")
    p.add_argument("--decisions")
    p.add_argument("--seed", type=int, default=0)
    p.set_defaults(func=cmd_what_if)
    p = sub.add_parser("sweep", help="agent harness: batch stress tests")
    p.add_argument("action", choices=["run", "worst"])
    p.add_argument("file")
    p.add_argument("--out", default="outputs/sweeps")
    p.add_argument("--top", type=int, default=10)
    p.set_defaults(func=cmd_sweep)
    p = sub.add_parser("params", help="parameter pack tools")
    p.add_argument("action", choices=["diff"])
    p.add_argument("old")
    p.add_argument("new")
    p.add_argument("--values", action="store_true", help="include old/new values (private output only)")
    p.add_argument("--out")
    p.set_defaults(func=cmd_params)
    p = sub.add_parser("build-pack", help="build a private pack from your own REA Evidence")
    p.add_argument("--out", required=True)
    p.add_argument("--evidence", default="evidence/private")
    p.add_argument("--quarter-label", help="e.g. Q2: snapshot the pack and diff it against the previous quarter")
    p.add_argument("--har", action="append", help="plain browser HAR export (private), repeatable")
    p.add_argument("--base", help="previous private pack dir: keeps what this capture does not show")
    p.set_defaults(func=cmd_build_pack)
    p = sub.add_parser("reconcile", help="replay a submitted quarter and compare with its settled statements (private)")
    p.add_argument("--params", required=True)
    p.add_argument("--har", action="append", required=True, help="capture holding the quarter's statements")
    p.add_argument("--quarter", type=int, required=True)
    p.add_argument("--plan", required=True, help="the plan actually submitted that quarter")
    p.add_argument("--save", help="save at that quarter's start (not needed for quarter 1)")
    p.add_argument("--out", required=True)
    p.add_argument("--seed", type=int, default=0)
    p.set_defaults(func=cmd_reconcile)
    p = sub.add_parser("cost-curve", help="unit cost from the pack's cost-of-production table (private pack)")
    p.add_argument("--params", required=True)
    p.add_argument("--brand-type")
    p.add_argument("--components", help="comma-separated component ids of a design")
    p.add_argument("--units", type=float, action="append")
    p.set_defaults(func=cmd_cost_curve)
    p = sub.add_parser("intake", help="the team's entered decisions (Summary of Decisions capture) -> factory orders")
    p.add_argument("--har", action="append", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_intake)
    p = sub.add_parser("factory", help="production scheduler: operating capacity x overtime x demand sweep (private)")
    p.add_argument("--params", required=True)
    p.add_argument("--orders", required=True)
    p.add_argument("--oc", default="10,12,14,16", help="operating capacities to try (units/day)")
    p.add_argument("--ot", default="0,2", help="maximum overtime hours to try")
    p.add_argument("--demand", default="0.5,0.75,1,1.25,1.5", help="demand outcomes as multiples of the forecast")
    p.add_argument("--reading", default="both", choices=["factory", "brand", "both"])
    p.add_argument("--productivity", type=float, help="override HR's projected productivity (percent)")
    p.add_argument("--previous-oc", type=float, default=0.0)
    p.add_argument("--out")
    p.set_defaults(func=cmd_factory)
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
