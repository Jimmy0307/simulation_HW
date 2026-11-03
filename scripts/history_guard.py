"""Reminder: the public git history still holds leaked real values until docs/TODO-history-cleanup.md says CLEANED.

The TODO file carries one machine-readable marker line:  <!-- history-cleanup-status: NOT_CLEANED -->
(flip it to CLEANED only after tools/history/verify_clean.py reports clean on a fresh clone of the remote).

While the status is not CLEANED this guard rings (terminal bell + banner on stderr) whenever a publication action
runs. It never blocks local development; it is an added check, not a relaxed one.

  action   when it rings                                         who calls it
  dist     always (a build meant for publication)                scripts/build_demo.py
  pages    always (deploying the demo to GitHub Pages)           .github/workflows/pages.yml (with --strict)
  public   always (about to switch the repository to public)     you, by hand, before changing the visibility
  push     only if the repository is PUBLIC right now            publication_gate.py --pre-push (git hook)

`push` asks GitHub for the visibility with one anonymous read-only request (no token, no cookie): HTTP 200 on the
public API means PUBLIC. Set MPSIM_REPO_VISIBILITY=public|private to skip the request (offline, tests).
--strict turns the warning into exit code 3 (used in CI, where nobody hears a bell). Without it the exit code is 0.

usage: python scripts/history_guard.py --action {dist,pages,public,push} [--strict]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TODO_FILE = ROOT / "docs" / "TODO-history-cleanup.md"
MARKER = re.compile(r"<!--\s*history-cleanup-status:\s*([A-Z_]+)\s*-->")
CLEANED = "CLEANED"
ACTIONS = ("dist", "pages", "public", "push")
STRICT_EXIT = 3


def cleanup_status(todo: Path = TODO_FILE) -> str:
    """CLEANED, NOT_CLEANED, or UNKNOWN (file or marker missing: treated as not cleaned)."""
    if not todo.exists():
        return "UNKNOWN"
    match = MARKER.search(todo.read_text(encoding="utf-8"))
    return match.group(1) if match else "UNKNOWN"


def _github_slug(repo: Path = ROOT) -> str | None:
    url = subprocess.run(["git", "remote", "get-url", "origin"], cwd=repo, check=False,
                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True).stdout.strip()
    match = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?$", url)
    return f"{match.group(1)}/{match.group(2)}" if match else None


def repo_visibility(repo: Path = ROOT) -> str:
    """public, private (or not visible anonymously), or unknown. Honours MPSIM_REPO_VISIBILITY."""
    override = os.environ.get("MPSIM_REPO_VISIBILITY", "").strip().lower()
    if override in {"public", "private", "unknown"}:
        return override
    slug = _github_slug(repo)
    if not slug:
        return "unknown"
    request = urllib.request.Request(f"https://api.github.com/repos/{slug}",
                                     headers={"Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(request, timeout=8) as response:  # fixed https host, anonymous
            return "public" if response.status == 200 else "unknown"
    except urllib.error.HTTPError as error:
        return "private" if error.code == 404 else "unknown"
    except (urllib.error.URLError, OSError):
        return "unknown"


BANNER = """
\a\a\a
################################################################################
##  WARNING: git history NOT cleaned  (status: {status})
##  action: {action}{visibility}
##  The public history still contains real values and code excerpts derived
##  from the game client.  Hard rules until the cleanup is done:
##    a. do NOT switch the repository back to public
##    b. do NOT publish to GitHub Pages
##    c. cleanup plan: docs/history-cleanup-plan.md + tools/history/ ;
##       archived copy: evidence/private/leak-archive/
##  See docs/TODO-history-cleanup.md.
################################################################################
"""


def check(action: str, todo: Path = TODO_FILE, repo: Path = ROOT) -> dict[str, Any]:
    if action not in ACTIONS:
        raise ValueError(f"unknown action {action!r}; expected one of {ACTIONS}")
    status = cleanup_status(todo)
    visibility = repo_visibility(repo) if action == "push" and status != CLEANED else None
    rings = status != CLEANED and (action != "push" or visibility == "public")
    return {"action": action, "status": status, "visibility": visibility, "warn": rings}


def announce(result: dict[str, Any], stream: Any = None) -> None:
    if not result["warn"]:
        return
    visibility = f"   (repository visibility: {result['visibility']})" if result["visibility"] else ""
    print(BANNER.format(status=result["status"], action=result["action"], visibility=visibility),
          file=stream or sys.stderr, flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--action", choices=ACTIONS, required=True)
    parser.add_argument("--strict", action="store_true", help="exit 3 instead of 0 when the warning fires")
    args = parser.parse_args(argv)
    result = check(args.action)
    announce(result)
    print(json.dumps({"history_cleanup": result}))
    return STRICT_EXIT if args.strict and result["warn"] else 0


if __name__ == "__main__":
    sys.exit(main())
