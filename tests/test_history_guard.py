"""The history-cleanup reminder: rings on publication actions while the TODO is not marked CLEANED."""

from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, file: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / file)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


guard = _load("history_guard_under_test", "history_guard.py")


def _todo(tmp_path: Path, status: str | None) -> Path:
    todo = tmp_path / "TODO.md"
    marker = f"<!-- history-cleanup-status: {status} -->\n" if status else ""
    todo.write_text(marker + "# TODO\n", encoding="utf-8")
    return todo


def test_status_marker_parsing(tmp_path: Path) -> None:
    assert guard.cleanup_status(_todo(tmp_path, "NOT_CLEANED")) == "NOT_CLEANED"
    assert guard.cleanup_status(_todo(tmp_path, "CLEANED")) == "CLEANED"
    assert guard.cleanup_status(_todo(tmp_path, None)) == "UNKNOWN"
    assert guard.cleanup_status(tmp_path / "missing.md") == "UNKNOWN"


def test_repository_todo_is_pinned_and_not_cleaned() -> None:
    text = guard.TODO_FILE.read_text(encoding="utf-8")
    assert text.startswith("<!-- history-cleanup-status: NOT_CLEANED -->")
    assert guard.cleanup_status() == "NOT_CLEANED"
    assert "未清除：公開歷史仍含真實數值與遊戲客戶端程式碼" in text
    for rule in ("a. 歷史清除完成前，repo 不得改回 public", "b. 歷史清除完成前，不得發布到 GitHub Pages",
                 "c. 清除方案已就緒", "evidence/private/leak-archive/", "docs/history-cleanup-plan.md",
                 "tools/history/"):
        assert rule in text


@pytest.mark.parametrize("action", ["dist", "pages", "public"])
def test_publication_actions_ring_while_not_cleaned(tmp_path: Path, action: str) -> None:
    result = guard.check(action, todo=_todo(tmp_path, "NOT_CLEANED"))
    assert result["warn"] is True and result["visibility"] is None  # no network for these actions
    stream = io.StringIO()
    guard.announce(result, stream)
    assert "\a" in stream.getvalue() and "NOT cleaned" in stream.getvalue()
    assert guard.check(action, todo=_todo(tmp_path, "CLEANED"))["warn"] is False
    assert guard.check(action, todo=tmp_path / "missing.md")["warn"] is True


def test_push_rings_only_when_the_repository_is_public(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _todo(tmp_path, "NOT_CLEANED")
    monkeypatch.setenv("MPSIM_REPO_VISIBILITY", "private")
    assert guard.check("push", todo=todo) == {"action": "push", "status": "NOT_CLEANED", "visibility": "private",
                                              "warn": False}
    monkeypatch.setenv("MPSIM_REPO_VISIBILITY", "unknown")
    assert guard.check("push", todo=todo)["warn"] is False
    monkeypatch.setenv("MPSIM_REPO_VISIBILITY", "public")
    assert guard.check("push", todo=todo)["warn"] is True
    assert guard.check("push", todo=_todo(tmp_path, "CLEANED"))["visibility"] is None  # cleaned: no request at all


def test_silent_when_not_warning() -> None:
    stream = io.StringIO()
    guard.announce({"action": "dist", "status": "CLEANED", "visibility": None, "warn": False}, stream)
    assert stream.getvalue() == ""


def test_cli_warns_without_blocking_unless_strict() -> None:
    run = [sys.executable, str(ROOT / "scripts" / "history_guard.py"), "--action", "pages"]
    plain = subprocess.run(run, capture_output=True, text=True, encoding="utf-8", check=False)
    assert plain.returncode == 0
    assert json.loads(plain.stdout)["history_cleanup"]["warn"] is True
    assert "\a" in plain.stderr and "do NOT publish to GitHub Pages" in plain.stderr
    strict = subprocess.run([*run, "--strict"], capture_output=True, text=True, encoding="utf-8", check=False)
    assert strict.returncode == guard.STRICT_EXIT


def test_unknown_action_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        guard.check("deploy-everything", todo=_todo(tmp_path, "NOT_CLEANED"))


def test_gate_reports_the_reminder_without_changing_its_result(monkeypatch: pytest.MonkeyPatch) -> None:
    gate = _load("gate_with_guard", "publication_gate.py")
    stream = io.StringIO()
    monkeypatch.setattr(sys, "stderr", stream)
    assert gate._history_reminder("dist")["warn"] is True
    assert "NOT cleaned" in stream.getvalue()
    source = (ROOT / "scripts" / "publication_gate.py").read_text(encoding="utf-8")
    assert 'result["history_cleanup"] = _history_reminder("dist")' in source
    assert 'result["history_cleanup"] = _history_reminder("push")' in source
    assert 'result["pass"]' not in source.split("def _history_reminder", 1)[1].split("def main", 1)[0]


def test_build_demo_and_pages_workflow_call_the_guard() -> None:
    build = (ROOT / "scripts" / "build_demo.py").read_text(encoding="utf-8")
    assert '"history_guard.py"' in build and '"--action", "dist"' in build
    workflow = (ROOT / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
    guard_step = workflow.index("history_guard.py --action pages --strict")
    assert guard_step < workflow.index("npm run build") < workflow.index("upload-pages-artifact")


def test_leak_archive_location_is_ignored_and_untracked() -> None:
    probe = "evidence/private/leak-archive/INDEX.md"
    assert subprocess.run(["git", "check-ignore", "-q", probe], cwd=ROOT, check=False).returncode == 0
    tracked = subprocess.run(["git", "ls-files", "evidence/private", "tools"], cwd=ROOT, check=True,
                             capture_output=True, text=True).stdout
    assert tracked.strip() == ""
