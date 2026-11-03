"""Dry-run check for a local agent command file: every declared path, directory and tool exists. Never connects.

The command file declares its requirements in an HTML comment block::

    <!-- dry-run
    path  C:\\some\\file
    dir   C:\\some\\directory
    exec  C:\\tool.exe --version
    -->

``exec`` lines are run only when their last argument is ``--version`` or ``--help`` (local, offline commands).
It also checks that every ``## Phase`` heading and the report section exist. Usage::

    python scripts/check_command_file.py .claude/commands/quarter.md
"""

from __future__ import annotations

import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

BLOCK = re.compile(r"<!--\s*dry-run\s*\n(.*?)-->", re.DOTALL)
SAFE_FLAGS = {"--version", "--help"}
REQUIRED_HEADINGS = ["## 永久規則", "## 硬停止條件", "## Phase 0", "## Phase 1", "## Phase 2", "## Phase 3",
                     "## Phase 4", "## Phase 5", "## Phase 6", "## 最後回報"]
REQUIRED_REPORT_FIELDS = ["QUARTER", "NEW_PAGES", "DEMAND_PANEL", "MODEL_STATUS", "PARAM_DIFF", "COMMITS"]


def check(command_file: Path) -> dict[str, object]:
    text = command_file.read_text(encoding="utf-8")
    match = BLOCK.search(text)
    results: list[dict[str, object]] = []
    if match is None:
        return {"file": str(command_file), "pass": False, "error": "no dry-run block"}
    for raw in match.group(1).splitlines():
        line = raw.strip()
        if not line:
            continue
        kind, _, rest = line.partition(" ")
        rest = rest.strip()
        if kind == "path":
            results.append({"kind": kind, "target": rest, "ok": Path(rest).is_file()})
        elif kind == "dir":
            results.append({"kind": kind, "target": rest, "ok": Path(rest).is_dir()})
        elif kind == "exec":
            argv = shlex.split(rest, posix=False)
            if argv[-1] not in SAFE_FLAGS:
                results.append({"kind": kind, "target": rest, "ok": False, "detail": "only --version/--help allowed"})
                continue
            try:
                proc = subprocess.run(argv, capture_output=True, text=True, timeout=60, check=False)
                first = (proc.stdout or proc.stderr).strip().splitlines()[:1]
                results.append({"kind": kind, "target": rest, "ok": proc.returncode == 0, "detail": first[0] if first else ""})
            except (OSError, subprocess.TimeoutExpired) as exc:
                results.append({"kind": kind, "target": rest, "ok": False, "detail": type(exc).__name__})
        else:
            results.append({"kind": kind, "target": rest, "ok": False, "detail": "unknown directive"})
    headings = {h: h in text for h in REQUIRED_HEADINGS}
    fields = {f: f in text for f in REQUIRED_REPORT_FIELDS}
    ok = all(r["ok"] for r in results) and all(headings.values()) and all(fields.values()) and "$ARGUMENTS" in text
    return {"file": str(command_file), "pass": ok, "checks": len(results),
            "failed": [r for r in results if not r["ok"]], "exec": [r for r in results if r["kind"] == "exec"],
            "headings": headings, "report_fields": fields, "accepts_arguments": "$ARGUMENTS" in text}


def main() -> None:
    target = Path(sys.argv[1] if len(sys.argv) > 1 else ".claude/commands/quarter.md")
    result = check(target)
    print(json.dumps(result, ensure_ascii=False, indent=1))
    raise SystemExit(0 if result["pass"] else 1)


if __name__ == "__main__":
    main()
