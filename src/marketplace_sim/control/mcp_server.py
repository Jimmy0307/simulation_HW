"""Optional MCP thin layer over the LOCAL planning engine (stdio). Offline only.

This server exposes local scenario runs and sweeps to an agent. It has nothing to do with the REA MCP server used for
reverse engineering, and it never contacts any online system. Tools only read files under the current working
directory and write nothing except to ``outputs/`` when asked.

Run: ``python -m marketplace_sim.control.mcp_server`` (requires the ``mcp`` package, ``pip install "mcp>=2,<3"``).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from marketplace_sim.control.runner import run_scenario, write_result
from marketplace_sim.control.spec import load_spec
from marketplace_sim.control.sweep import load_sweep, run_sweep, worst, write_sweep
from marketplace_sim.metrics import lookup
from marketplace_sim.pack import load_pack

ROOT = Path.cwd().resolve()


def _inside(path: str) -> Path:
    resolved = (ROOT / path).resolve()
    if ROOT not in resolved.parents and resolved != ROOT:
        raise ValueError("path must stay inside the working directory")
    return resolved


def _out_dir(spec_path: Path, kind: str) -> Path:
    """Synthetic results go to outputs/; anything built from a non-synthetic pack stays in evidence/private/outputs."""
    spec = load_spec(spec_path)
    synthetic = load_pack(spec.resolve(spec.base_params)).provenance == "synthetic"
    return ROOT / ("outputs" if synthetic else "evidence/private/outputs") / kind


def tool_run_scenario(path: str, save_to_outputs: bool = False) -> dict[str, Any]:
    spec_path = _inside(path)
    result = run_scenario(load_spec(spec_path))
    if save_to_outputs:
        write_result(result, _out_dir(spec_path, "scenarios"))
    data = result.to_dict()
    return {"name": data["name"], "fingerprint": data["fingerprint"], "summary": data["summary"],
            "quarters": [{"quarter": q["quarter"], "events": q["events"],
                          "key_lines": {k: q["lines"][k] for k in ("cash_end", "net_income", "capex_capacity") if k in q["lines"]}}
                         for q in data["quarters"]]}


def tool_run_sweep(path: str, top: int = 5) -> dict[str, Any]:
    sweep = load_sweep(_inside(path))
    result = run_sweep(sweep)
    write_sweep(result, _out_dir(sweep.base_scenario, "sweeps"))
    return {"name": result["name"], "objective": result["objective"], "runs": len(result["rows"]),
            "demand_level": result["demand_level"], "caveat": result["caveat"],
            "worst": worst(result["rows"], top), "sensitivity": result["sensitivity"]}


def tool_list_scenarios(directory: str = "examples/scenarios") -> list[dict[str, str]]:
    out = []
    for path in sorted(_inside(directory).glob("*.yaml")):
        try:
            spec = load_spec(path)
            out.append({"path": path.relative_to(ROOT).as_posix(), "name": spec.name, "description": spec.description})
        except (ValueError, KeyError, TypeError):
            continue
    return out


def tool_explain_result(result_path: str, metric: str) -> dict[str, Any]:
    data = json.loads(_inside(result_path).read_text(encoding="utf-8"))
    info = lookup(metric)
    quarters = [q for q in data.get("quarters", []) if metric in q["lines"]]
    rows = [q["lines"][metric] for q in quarters]
    return {"metric": metric, "quarters": [q["quarter"] for q in quarters], "events": [q["events"] for q in quarters], "level": info.level.label if info else "unknown", "formula": info.formula if info else None,
            "evidence": info.evidence if info else None, "values": [r["value"] for r in rows],
            "levels": [r["level"] for r in rows]}


def main() -> None:
    try:
        from mcp.server import MCPServer  # type: ignore[import-not-found,unused-ignore]
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise SystemExit('The optional MCP layer needs the MCP SDK: pip install "mcp>=2,<3"') from exc
    server = MCPServer("marketplace-sim-local")
    server.tool(name="run_scenario", description="Run a local scenario YAML (offline engine).")(tool_run_scenario)
    server.tool(name="run_sweep", description="Run a local sweep YAML; writes outputs/sweeps (private packs: evidence/private/outputs).")(tool_run_sweep)
    server.tool(name="list_scenarios", description="List scenario YAML files in a local directory.")(tool_list_scenarios)
    server.tool(name="explain_result", description="Explain one metric of a saved scenario result.")(tool_explain_result)
    server.run()


if __name__ == "__main__":
    main()
