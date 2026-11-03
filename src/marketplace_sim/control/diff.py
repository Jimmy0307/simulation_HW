"""Compare two parameter packs (e.g. last quarter's capture vs this quarter's) and rank changes by impact.

Reports with real values are private; ``render(..., include_values=False)`` gives a value-free summary.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from marketplace_sim.provenance import Level

_IDENTITY_KEYS = ("key", "id", "code", "units")
# path prefix -> (engine module, level of that module's rule)
MODULES: list[tuple[str, str, Level]] = [
    ("capacity_options", "capacity investment (EXP-02)", Level.VERIFIED),
    ("stores", "store opening cost (EXP-11) / lease", Level.VERIFIED),
    ("web_centers", "web-center opening cost (EXP-12) / lease", Level.VERIFIED),
    ("finance.cd_rate_annual_percent", "CD interest (EXP-01)", Level.VERIFIED),
    ("days_per_quarter", "quarterly capacity (EXP-02)", Level.VERIFIED),
    ("initial_state", "starting state", Level.DERIVED),
    ("finance", "tax / emergency loan", Level.PLACEHOLDER),
    ("components", "unit cost", Level.PLACEHOLDER),
    ("brand_types", "unit cost / segment fit", Level.PLACEHOLDER),
    ("production", "unit cost / design cost", Level.PLACEHOLDER),
    ("markets", "demand (literature form)", Level.LITERATURE),
    ("segments", "demand (literature form)", Level.LITERATURE),
    ("demand", "demand model / coefficients", Level.LITERATURE),
]


@dataclass(frozen=True)
class Change:
    path: str
    kind: str  # added | removed | changed
    old: Any
    new: Any
    module: str
    module_level: Level

    @property
    def relative(self) -> float | None:
        if self.kind != "changed" or not isinstance(self.old, (int, float)) or not isinstance(self.new, (int, float)):
            return None
        if isinstance(self.old, bool) or self.old == 0:
            return None
        return (self.new - self.old) / abs(self.old)

    @property
    def needs_reverification(self) -> bool:
        return self.module_level is Level.VERIFIED


def _identity(item: Any, index: int) -> str:
    if isinstance(item, dict):
        for key in _IDENTITY_KEYS:
            if key in item:
                return f"{key}={item[key]}"
    return str(index)


def flatten(node: Any, prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(node, dict):
        for key, value in node.items():
            if key in {"schema", "source_map", "note", "name", "provenance"} and not prefix:
                continue
            out.update(flatten(value, f"{prefix}.{key}" if prefix else str(key)))
    elif isinstance(node, list):
        for index, item in enumerate(node):
            out.update(flatten(item, f"{prefix}[{_identity(item, index)}]"))
    else:
        out[prefix] = node
    return out


def _module(path: str) -> tuple[str, Level]:
    for prefix, name, level in MODULES:
        if path.startswith(prefix):
            return name, level
    return "other", Level.PLACEHOLDER


def diff_packs(old: dict[str, Any], new: dict[str, Any]) -> list[Change]:
    a, b = flatten(old), flatten(new)
    changes = []
    for path in sorted(set(a) | set(b)):
        if path not in b:
            kind = "removed"
        elif path not in a:
            kind = "added"
        elif a[path] != b[path]:
            kind = "changed"
        else:
            continue
        module, level = _module(path)
        changes.append(Change(path, kind, a.get(path), b.get(path), module, level))
    return sorted(changes, key=lambda c: (-int(c.module_level), -(abs(c.relative) if c.relative is not None else 0), c.path))


def diff_dirs(old_dir: Path, new_dir: Path) -> list[Change]:
    def load(directory: Path) -> dict[str, Any]:
        data: dict[str, Any] = json.loads((Path(directory) / "pack.json").read_text(encoding="utf-8"))
        return data

    return diff_packs(load(old_dir), load(new_dir))


def render(changes: list[Change], *, include_values: bool) -> str:
    if not changes:
        return "No parameter changes.\n"
    reverify = sorted({c.module for c in changes if c.needs_reverification})
    lines = [f"# Parameter diff: {len(changes)} change(s)", ""]
    if reverify:
        lines += ["**⚠ Verified modules that may need re-verification:** " + ", ".join(reverify), ""]
    head = "| path | kind | module | module level | relative change |" + (" old | new |" if include_values else "")
    lines += [head, "|---|---|---|---|---|" + ("---|---|" if include_values else "")]
    for c in changes:
        rel = f"{c.relative:+.1%}" if c.relative is not None else "-"
        row = f"| `{c.path}` | {c.kind} | {c.module} | {c.module_level.label} | {rel} |"
        if include_values:
            row += f" {c.old} | {c.new} |"
        lines.append(row)
    return "\n".join(lines) + "\n"


def red_flags(changes: list[Change], *, threshold: float = 0.25) -> list[str]:
    """Value-free warnings: verified modules touched, structural changes, large relative moves."""
    flags = [f"RED FLAG: verified module changed, re-verify: {m}"
             for m in sorted({c.module for c in changes if c.needs_reverification})]
    if any(c.kind != "changed" for c in changes):
        flags.append(f"RED FLAG: {sum(c.kind != 'changed' for c in changes)} added/removed field(s) (schema or catalogue change)")
    big = [c for c in changes if c.relative is not None and abs(c.relative) >= threshold]
    if big:
        flags.append(f"RED FLAG: {len(big)} field(s) moved by >= {threshold:.0%}")
    return flags


def quarterly_snapshot(model_dir: Path, label: str) -> tuple[list[Change], str | None]:
    """Snapshot ``model_dir/pack.json`` as ``history/<label>`` and diff it against the previous snapshot.

    Called right after a private pack is rebuilt for a new quarter. The full diff (with values) is written to
    ``model_dir/diffs/<label>-vs-<previous>.md``; this only ever runs on private directories.
    """
    if "private" not in model_dir.resolve().as_posix().split("/"):
        raise ValueError("quarterly snapshots are for private model directories only")
    history = model_dir / "history"
    index_path = history / "index.json"
    index: list[str] = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else []
    previous = next((q for q in reversed(index) if q != label), None)
    target = history / label
    target.mkdir(parents=True, exist_ok=True)
    (target / "pack.json").write_text((model_dir / "pack.json").read_text(encoding="utf-8"), encoding="utf-8")
    if label not in index:
        index.append(label)
    index_path.write_text(json.dumps(index, indent=1), encoding="utf-8")
    if previous is None:
        return [], None
    changes = diff_dirs(history / previous, target)
    diffs = model_dir / "diffs"
    diffs.mkdir(parents=True, exist_ok=True)
    report = f"{label}-vs-{previous}.md"
    (diffs / report).write_text("\n".join(red_flags(changes)) + "\n\n" + render(changes, include_values=True), encoding="utf-8")
    return changes, previous
