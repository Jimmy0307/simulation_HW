"""mpsim: local business-planning simulator driven by parameter packs.

  mpsim new --params DIR --out SAVE.json [--quarter N]
  mpsim play SAVE.json --decisions PLAN.yaml [--seed N]
  mpsim compare SAVE.json PLAN.yaml [PLAN.yaml ...] [--seed N]
  mpsim explain METRIC
  mpsim build-pack --out evidence/private/model     (private; reads your own REA Evidence)
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
    rows = [f"Quarter {reports[0].quarter} comparison   [V]=verified [D]=derived [E]=estimated [P]=placeholder",
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
          "parameters; estimated = fitted to data; placeholder = illustrative, uncalibrated.")
    _ = Level


def cmd_build_pack(args: argparse.Namespace) -> None:
    from marketplace_sim.pack_builder import build_private_pack

    print(build_private_pack(Path(args.out), Path(args.evidence)))


def main(argv: list[str] | None = None) -> None:
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
    p = sub.add_parser("build-pack", help="build a private pack from your own REA Evidence")
    p.add_argument("--out", required=True)
    p.add_argument("--evidence", default="evidence/private")
    p.set_defaults(func=cmd_build_pack)
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
