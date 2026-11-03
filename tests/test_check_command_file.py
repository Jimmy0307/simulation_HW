"""The command-file dry-run checker: synthetic command files only; never connects."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("check_command_file", Path(__file__).parents[1] / "scripts" / "check_command_file.py")
assert SPEC and SPEC.loader
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)

BODY = "\n".join(checker.REQUIRED_HEADINGS + checker.REQUIRED_REPORT_FIELDS) + "\nquarter $ARGUMENTS\n"


def test_passes_when_everything_exists(tmp_path: Path) -> None:
    (tmp_path / "tool.txt").write_text("x", encoding="utf-8")
    cmd = tmp_path / "cmd.md"
    cmd.write_text(f"<!-- dry-run\npath {tmp_path / 'tool.txt'}\ndir {tmp_path}\nexec {sys.executable} --version\n-->\n{BODY}",
                   encoding="utf-8")
    result = checker.check(cmd)
    assert result["pass"] and result["checks"] == 3


def test_fails_on_missing_path_unsafe_exec_or_missing_section(tmp_path: Path) -> None:
    cmd = tmp_path / "cmd.md"
    cmd.write_text(f"<!-- dry-run\npath {tmp_path / 'nope'}\nexec {sys.executable} -c 1\n-->\n{BODY}", encoding="utf-8")
    result = checker.check(cmd)
    assert not result["pass"] and len(result["failed"]) == 2
    cmd.write_text(f"<!-- dry-run\ndir {tmp_path}\n-->\n" + BODY.replace("## Phase 4", ""), encoding="utf-8")
    assert not checker.check(cmd)["pass"]
