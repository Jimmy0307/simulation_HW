"""Install a local git pre-push hook that runs the publication gate on every commit about to be pushed.

The hook lives in .git/hooks (local only, never committed). It blocks a push when any pushed commit, not just the
final tree, contains a forbidden path or a real value. Usage: python scripts/install_git_hooks.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = """#!/bin/sh
# Installed by scripts/install_git_hooks.py: scan every pushed commit with the publication gate.
exec "{python}" "{gate}" --pre-push
"""


def main() -> None:
    hooks = ROOT / ".git" / "hooks"
    if not hooks.is_dir():
        raise SystemExit("not a git checkout (no .git/hooks)")
    python = Path(sys.executable).as_posix()
    gate = (ROOT / "scripts" / "publication_gate.py").as_posix()
    target = hooks / "pre-push"
    target.write_text(HOOK.format(python=python, gate=gate), encoding="utf-8", newline="\n")
    target.chmod(0o755)
    print(f"installed {target}")


if __name__ == "__main__":
    main()
