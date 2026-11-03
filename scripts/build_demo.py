"""Build the public static demo: export the synthetic bundle, build the frontend, then gate-check frontend/dist.

Steps (each must pass):
  1. python -m marketplace_sim.api.export        -> frontend/public/demo/*.json (synthetic pack only)
  2. npm ci && npm test && npm run build         -> frontend/dist (MPSIM_BASE sets the GitHub Pages base path)
  3. scripts/publication_gate.py --require-dist  -> no real values, private markers or local paths in dist/
A dist/ build is meant for publication, so scripts/history_guard.py rings (bell + banner, not blocking) at the start
and again at the end while docs/TODO-history-cleanup.md says the git history is not cleaned.

usage: python scripts/build_demo.py [--base /simulation_HW/] [--skip-install]
The Node binaries are taken from PATH (or NODE_HOME). npm's cache can be redirected with npm_config_cache.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"


def _npm() -> str:
    home = os.environ.get("NODE_HOME")
    candidates = [Path(home) / name for name in ("npm.cmd", "npm")] if home else []
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    found = shutil.which("npm") or shutil.which("npm.cmd")
    if not found:
        raise SystemExit("npm not found: put Node on PATH or set NODE_HOME")
    return found


def run(cmd: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    print("$", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=cwd, check=True, env=env)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", default="./", help="public base path, e.g. /simulation_HW/ for GitHub Pages")
    parser.add_argument("--skip-install", action="store_true")
    args = parser.parse_args()
    guard = [sys.executable, str(ROOT / "scripts" / "history_guard.py"), "--action", "dist"]
    subprocess.run(guard, cwd=ROOT, check=False, stdout=subprocess.DEVNULL)
    run([sys.executable, "-m", "marketplace_sim.api.export"], ROOT)
    npm = _npm()
    env = {**os.environ, "MPSIM_BASE": args.base, "VITE_DATA_SOURCE": "static"}
    if not args.skip_install:
        run([npm, "ci", "--no-audit", "--no-fund"], FRONTEND, env)
    run([npm, "test"], FRONTEND, env)
    run([npm, "run", "build"], FRONTEND, env)
    gate = subprocess.run([sys.executable, str(ROOT / "scripts" / "publication_gate.py"), "--require-dist"], cwd=ROOT,
                          stdout=subprocess.PIPE, check=False)
    result = json.loads(gate.stdout)
    print(json.dumps({"gate_pass": result["pass"], "dist": result["dist"], "demo_bundle": result["demo_bundle"],
                      "history_cleanup": result.get("history_cleanup")}, indent=1))
    if gate.returncode != 0:
        raise SystemExit("publication gate failed on the demo build; do not publish")


if __name__ == "__main__":
    main()
