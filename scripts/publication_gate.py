"""Fail closed on private evidence paths and sensitive public JSON fixtures.

Modes:
  python scripts/publication_gate.py                       working tree (staged + untracked, not ignored)
  python scripts/publication_gate.py --commits A..B        additionally scan every commit in a revision range
  python scripts/publication_gate.py --pre-push            git pre-push hook: scan every commit about to be pushed
                                                           (refs read from stdin); install with
                                                           scripts/install_git_hooks.py
Scanning commits matters because a leak that is scrubbed by a later commit still lives in history.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from marketplace_sysid.security.evidence_scan import PATTERNS, scan_evidence
from marketplace_sysid.security.value_leak import (
    RealValues,
    load_real_values,
    scan_file_text,
    scan_paths,
)

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_SUFFIXES = {
    ".har", ".devtools", ".session", ".zip", ".csv", ".js", ".mjs", ".css",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".pdf",
}
ALLOWED_ROOTS = {
    ".gitignore", "CONTRIBUTING.md", "LICENSE", "README.md", "SECURITY.md",
    "data", "docs", "examples", "fixtures", "legacy", "pyproject.toml", "scripts", "src", "tests",
}
ALLOWED_SUFFIXES = {".md", ".py", ".json", ".html", ".toml", ".yaml", ""}
REAL_VALUES = ROOT / "evidence" / "private" / "parameters" / "values.json"
PRIVATE_PACK = ROOT / "evidence" / "private" / "model" / "pack.json"
PUBLIC_SCAN_ROOTS = (
    ROOT / "data",
    ROOT / "legacy" / "data",
    ROOT / "fixtures" / "synthetic",
    ROOT / "evidence" / "private" / "staging_public",
)


def _git_paths() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
    )
    return [item.decode("utf-8", "replace") for item in result.stdout.split(b"\0") if item]


def _path_is_allowed(relative: str) -> bool:
    path = Path(relative)
    normalized = relative.replace("\\", "/")
    if path.parts[0] not in ALLOWED_ROOTS or path.suffix.casefold() not in ALLOWED_SUFFIXES:
        return False
    if normalized.startswith("data/"):
        return path.suffix.casefold() == ".json"
    if normalized.startswith("docs/"):
        return path.suffix.casefold() == ".md"
    if normalized.startswith("fixtures/"):
        return normalized.startswith("fixtures/synthetic/") and path.suffix.casefold() in {".json", ".html"}
    if normalized.startswith(("src/", "scripts/", "tests/")):
        return path.suffix.casefold() == ".py"
    if normalized.startswith("legacy/"):
        return path.suffix.casefold() in {".py", ".md", ".json"}
    if normalized.startswith("examples/"):
        return path.suffix.casefold() in {".json", ".yaml", ".md"}
    if path.suffix.casefold() == ".yaml":
        return False
    return len(path.parts) == 1 and relative in ALLOWED_ROOTS


def check_publication() -> dict[str, object]:
    paths = sorted(set(_git_paths()))
    forbidden = []
    for relative in paths:
        path = Path(relative)
        lowered = relative.casefold().replace("\\", "/")
        if not _path_is_allowed(relative):
            forbidden.append(relative)
        if "evidence/private/" in lowered or any(part.casefold().endswith("_files") for part in path.parts):
            forbidden.append(relative)
        if any(part.casefold() == "private" for part in path.parts):  # any directory named private, anywhere
            forbidden.append(relative)
        if path.suffix.casefold() in FORBIDDEN_SUFFIXES:
            forbidden.append(relative)
        if path.suffix.casefold() not in ALLOWED_SUFFIXES:
            forbidden.append(relative)
        if path.suffix.casefold() in {".html", ".htm"} and not lowered.startswith("fixtures/synthetic/"):
            forbidden.append(relative)
    ignore_probes = (
        "evidence/private/probe.json", "probe.har", "probe.devtools", "probe.session",
        "cookies.txt", "cookie.txt", "token.txt", "sample_files/probe.js",
    )
    ignore_results = {
        probe: subprocess.run(
            ["git", "check-ignore", "-q", probe], cwd=ROOT, check=False
        ).returncode == 0
        for probe in ignore_probes
    }
    ignored = all(ignore_results.values())
    scans = {str(root.relative_to(ROOT)): scan_evidence(root) for root in PUBLIC_SCAN_ROOTS if root.exists()}
    findings = {
        name: doc["finding_counts"]
        for name, doc in scans.items()
        if doc["files_with_findings"]
    }
    staged_payload_counts: dict[str, dict[str, int]] = {}
    staged_invalid_json: list[str] = []
    for relative in paths:
        if not relative.replace("\\", "/").startswith(("data/", "fixtures/", "legacy/data/")):
            continue
        staged_result = subprocess.run(
            ["git", "show", f":{relative}"], cwd=ROOT, check=False,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
        payload = (
            staged_result.stdout.decode("utf-8", "replace")
            if staged_result.returncode == 0
            else (ROOT / relative).read_text(encoding="utf-8", errors="replace")
        )
        if Path(relative).suffix.casefold() == ".json":
            try:
                json.loads(payload)
            except json.JSONDecodeError:
                staged_invalid_json.append(relative)
        counts = {name: len(pattern.findall(payload)) for name, pattern in PATTERNS.items()}
        if any(counts.values()):
            staged_payload_counts[relative] = counts
    real = load_real_values(REAL_VALUES, PRIVATE_PACK)
    candidates = [p for p in paths if not p.replace("\\", "/").startswith("evidence/")]
    leaks = [finding.__dict__ for finding in scan_paths(ROOT, candidates, real)]
    return {
        "private_evidence_ignored": ignored,
        "real_value_reference_loaded": not real.empty,
        "value_leak_findings": leaks,
        "ignore_probe_results": ignore_results,
        "forbidden_paths": sorted(set(forbidden)),
        "public_payload_scans": scans,
        "sensitive_findings": findings,
        "staged_payload_findings": staged_payload_counts,
        "staged_invalid_json": staged_invalid_json,
        "pass": (ignored and not forbidden and not findings and not staged_payload_counts and not staged_invalid_json
                 and not leaks),
    }


ZERO_SHA = "0" * 40


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, check=True, stdout=subprocess.PIPE).stdout.decode("utf-8", "replace")


def scan_commits(revs: list[str], real: RealValues, repo: Path = ROOT) -> list[dict[str, str]]:
    """Scan the files each commit adds or modifies, at that commit, with the same detectors as the working tree."""
    findings: list[dict[str, str]] = []
    for commit in revs:
        changed = _git(repo, "diff-tree", "-r", "--root", "--no-commit-id", "--name-only", "--diff-filter=AMR", commit)
        for relative in changed.splitlines():
            if not relative:
                continue
            short = commit[:7]
            if not _path_is_allowed(relative) or any(p.casefold() == "private" for p in Path(relative).parts):
                findings.append({"commit": short, "path": relative, "rule": "forbidden-path", "detail": ""})
                continue
            text = subprocess.run(["git", "show", f"{commit}:{relative}"], cwd=repo, check=False,
                                  stdout=subprocess.PIPE).stdout.decode("utf-8", "replace")
            for finding in scan_file_text(relative, text, real):
                findings.append({"commit": short, "path": relative, "rule": finding.rule, "detail": finding.detail})
    return findings


def _pre_push_revs(lines: list[str], repo: Path = ROOT) -> list[str]:
    revs: list[str] = []
    for line in lines:
        parts = line.split()
        if len(parts) != 4 or parts[1] == ZERO_SHA:  # deleting a remote ref pushes no content
            continue
        local_sha, remote_sha = parts[1], parts[3]
        if remote_sha == ZERO_SHA:
            revs += _git(repo, "rev-list", local_sha, "--not", "--remotes").split()
        else:
            revs += _git(repo, "rev-list", f"{remote_sha}..{local_sha}").split()
    return list(dict.fromkeys(revs))


def main() -> None:
    args = sys.argv[1:]
    result = check_publication()
    revs: list[str] = []
    if "--commits" in args:
        revs = _git(ROOT, "rev-list", args[args.index("--commits") + 1]).split()
    if "--pre-push" in args:
        revs = _pre_push_revs(sys.stdin.read().splitlines())
    if revs:
        commit_findings = scan_commits(revs, load_real_values(REAL_VALUES, PRIVATE_PACK))
        result["commits_scanned"] = len(revs)
        result["commit_findings"] = commit_findings
        result["pass"] = bool(result["pass"]) and not commit_findings
    print(json.dumps(result, ensure_ascii=False))
    if not result["pass"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
