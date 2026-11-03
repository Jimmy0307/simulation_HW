"""Export the static demo bundle for the frontend's StaticProvider (GitHub Pages).

Everything is computed by the same service functions the live API uses, from the SYNTHETIC pack only. The export
refuses to run if any input is not synthetic, and strips absolute local paths. Output: frontend/public/demo/*.json.
usage: python -m marketplace_sim.api.export [--out DIR]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from marketplace_sim.api import service as svc

DEFAULT_OUT = svc.ROOT / "frontend" / "public" / "demo"
MANIFEST_SCHEMA = "marketplace-sim/demo-bundle@1"
DEMO_QUARTERS = ["q1.yaml", "q2.yaml", "q3.yaml"]
DEMO_SWEEPS = ["sweep.yaml", "sweep-plans.yaml", "sweep-demand.yaml"]


def _plan(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {"name": data.get("name", path.stem), **data}


def _assert_synthetic(obj: Any, where: str) -> None:
    text = json.dumps(obj)
    if '"is_private": true' in text:
        raise svc.ApiError(f"{where}: refusing to export results built from a private pack")
    root = str(svc.ROOT)
    if root in text or root.replace("\\", "\\\\") in text or root.replace("\\", "/") in text:
        raise svc.ApiError(f"{where}: refusing to export absolute local paths")


def build_bundle() -> dict[str, Any]:
    session = svc.Session()
    if session.is_private:
        raise svc.ApiError("demo export uses the synthetic pack only")
    bundle: dict[str, Any] = {"pack": svc.pack_info(session), "levels": svc.levels(), "events": svc.event_types()}
    svc.new_game(session)
    for name in DEMO_QUARTERS:
        svc.play(session, _plan(svc.SYNTHETIC_PLANS / name))
    bundle["game"] = svc.game(session)
    presets = svc.plan_presets(session)
    bundle["plans"] = {**presets, "previews": {p["id"]: svc.preview(session, p["plan"])["report"]
                                               for p in presets["presets"]}}
    bundle["compare"] = svc.compare(session, [p["plan"] for p in presets["presets"]])
    templates = svc.scenario_templates(session)
    bundle["scenarios"] = {**templates, "results": {t["id"]: svc.run_scenario(session, t["spec"])["result"]
                                                    for t in templates["templates"]}}
    sweeps = svc.sweep_files(session)
    sweeps["sweeps"] = [s for s in sweeps["sweeps"] if f"{s['id']}.yaml" in DEMO_SWEEPS]
    bundle["sweeps"] = {**sweeps, "results": {s["id"]: svc.run_sweep(session, s["sweep"]) for s in sweeps["sweeps"]}}
    bundle["diff"] = {"packs": [{"id": "synthetic"}, {"id": "synthetic-v2"}],
                      "result": svc.params_diff(str(svc.SYNTHETIC_PACK), str(svc.ROOT / "examples" / "demo-control" / "pack-v2"))}
    for key, value in bundle.items():
        _assert_synthetic(value, key)
    return bundle


def export_demo(out: str | None = None) -> dict[str, Any]:
    out_dir = Path(out) if out else DEFAULT_OUT
    if svc._is_private_path(out_dir):
        raise svc.ApiError("the demo export is public; do not write it under a private directory")
    bundle = build_bundle()
    out_dir.mkdir(parents=True, exist_ok=True)
    files = []
    for key, value in bundle.items():
        (out_dir / f"{key}.json").write_text(json.dumps(value, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                                             encoding="utf-8", newline="\n")
        files.append(f"{key}.json")
    manifest = {"schema": MANIFEST_SCHEMA, "provenance": "synthetic", "is_private": False,
                "source_pack": "examples/synthetic", "files": sorted(files)}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8", newline="\n")
    return {"written": str(out_dir), "files": sorted([*files, "manifest.json"]), "is_private": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out")
    print(json.dumps(export_demo(parser.parse_args().out), indent=1))


if __name__ == "__main__":
    main()
