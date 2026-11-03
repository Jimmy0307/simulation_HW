"""Detect real simulation values leaking into files that are about to be published.

Reference data is private and optional:

* ``evidence/private/parameters/values.json``: ``{service: {path: [distinct values in first-seen order]}}`` from
  ``marketplace_sysid.parameters``;
* ``evidence/private/model/pack.json``: a private parameter pack (its names and numbers).

Checks (all value-free in their output: findings report file, rule and field name, never the value):

1. **Sequence**: three consecutive numbers in a file equal three consecutive entries of a real table column
   (windows whose values are all below 10 in magnitude are ignored as trivial).
2. **Keyed scalar**: a line contains a real scalar field name (camelCase/snake_case-insensitive) together with that
   field's real value (values 0 and 1 are ignored).
3. **Examples**: in ``examples/``, any number of magnitude >= 1000 equal to any real value, or any keyed number equal to
   the real value of the same field name (values 0 and 1 ignored).
4. **Names**: a real proper name from the private pack (markets, segments, components, brand types; >= 8 characters)
   appears verbatim.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_NUMBER = re.compile(r"(?<![\w.])-?\d{1,3}(?:,\d{3})+(?:\.\d+)?(?![\w])|(?<![\w.])-?\d+(?:\.\d+)?(?![\w])")
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
TRIVIAL = {0.0, 1.0}
# Client-delivered constants already documented publicly from the browser JavaScript (docs/calculation-map.md).
EXEMPT_KEYS = {"daysperquarter"}
_ID_LIKE = re.compile(r"(?i)(id|order|index|sequence|position)$")


def norm_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]", "", key.lower())


def numbers_in(text: str) -> list[float]:
    return [float(m.group(0).replace(",", "")) for m in _NUMBER.finditer(text)]


@dataclass
class RealValues:
    sequences: list[tuple[str, list[float]]] = field(default_factory=list)
    scalars: dict[str, set[float]] = field(default_factory=lambda: defaultdict(set))  # true scalar fields
    keyed_all: dict[str, set[float]] = field(default_factory=lambda: defaultdict(set))  # scalars + table rows
    all_values: set[float] = field(default_factory=set)
    names: set[str] = field(default_factory=set)
    derived_rates: set[float] = field(default_factory=set)  # rate/4, /12, /100, /400 of real rate scalars

    @property
    def empty(self) -> bool:
        return not (self.sequences or self.scalars or self.all_values or self.names)


def _num(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def load_real_values(values_json: Path | None, private_pack: Path | None = None) -> RealValues:
    real = RealValues()
    if values_json and values_json.exists():
        data: dict[str, dict[str, list[Any]]] = json.loads(values_json.read_text(encoding="utf-8"))
        from marketplace_sysid.parameters import classify

        for service, paths in data.items():
            for path, values in paths.items():
                numbers = [v for v in (_num(x) for x in values) if v is not None]
                key = norm_key(re.split(r"[.\[\]*]+", path.rstrip("]*"))[-1])
                if key in EXEMPT_KEYS:
                    continue
                real.all_values.update(numbers)
                real.keyed_all[key].update(numbers)
                identifier = classify(path) == "identifier" or bool(_ID_LIKE.search(key))
                if "[*]" in path and len(numbers) >= 3 and not identifier:
                    real.sequences.append((f"{service}:{path}", numbers))
                if "[*]" not in path and not identifier:
                    real.scalars[key].update(numbers)
    if private_pack and private_pack.exists():
        _absorb_pack(real, json.loads(private_pack.read_text(encoding="utf-8")))
    real.derived_rates = derived_rates(real)
    return real


RATE_WORDS = re.compile(r"(?i)(rate|slope|interest|yield|apr|利率|斜率|利息)")


def derived_rates(real: RealValues) -> set[float]:
    """Values a document can leak a real rate through without naming it: rate/4 (quarterly), /12, /100, /400.

    Only values with at least two decimal places are kept (round numbers such as 0.1 or 1.5 are too common to be
    evidence). They are flagged only on lines that also talk about a rate, slope or interest.
    """
    out: set[float] = set()
    for key, values in real.scalars.items():
        if "rate" not in key:
            continue
        for rate in values:
            if rate <= 0:
                continue
            for divisor in (4, 12, 100, 400):
                value = round(rate / divisor, 10)
                if abs(round(value * 100, 9) - round(value * 100)) > 1e-9:
                    out.add(value)
    return out


def _absorb_pack(real: RealValues, pack: dict[str, Any]) -> None:
    def walk(node: Any, key: str = "", in_list: bool = False) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                if k in {"schema", "provenance", "source_map", "note", "name"} and not in_list:
                    continue
                walk(v, k, in_list)
        elif isinstance(node, list):
            for item in node:
                walk(item, key, True)
        else:
            number = _num(node)
            nk = norm_key(key)
            if number is not None and nk not in EXEMPT_KEYS:
                real.all_values.add(number)
                real.keyed_all[nk].add(number)
                if not in_list and not _ID_LIKE.search(nk):
                    real.scalars[nk].add(number)
            elif isinstance(node, str) and key == "name" and in_list and len(node.strip()) >= 8:
                real.names.add(node.strip())

    walk(pack)
    for market in pack.get("markets", []):
        for cell in market.get("segments", {}).values():
            for k, v in cell.items():
                n = _num(v)
                if n is not None:
                    real.keyed_all[norm_key(k)].add(n)
    for segment in pack.get("segments", []):
        for table in ("needs", "use_pattern"):
            for need in (segment.get(table) or {}):
                if len(need.strip()) >= 8:
                    real.names.add(need.strip())
    # Table columns as ordered sequences (e.g. all option costs in row order).
    for list_key in ("capacity_options", "stores", "web_centers", "components"):
        rows = pack.get(list_key) or []
        if rows and isinstance(rows[0], dict):
            for column in rows[0]:
                values = [n for n in (_num(r.get(column)) for r in rows) if n is not None]
                if len(values) >= 3 and not _ID_LIKE.search(norm_key(column)):
                    real.sequences.append((f"pack:{list_key}.{column}", values))


@dataclass(frozen=True)
class Finding:
    path: str
    rule: str
    detail: str


def _windows(values: list[float]) -> set[tuple[float, ...]]:
    windows: set[tuple[float, ...]] = set()
    for i in range(len(values) - 2):
        window = tuple(values[i:i + 3])
        if max(abs(v) for v in window) < 10:
            continue  # trivial small numbers
        if window[1] - window[0] == 1 and window[2] - window[1] == 1:
            continue  # consecutive integers look like numbering, not parameters
        windows.add(window)
    return windows


def scan_text(relpath: str, text: str, real: RealValues) -> list[Finding]:
    findings: list[Finding] = []
    if real.empty:
        return findings
    tokens = numbers_in(text)
    token_windows = {tuple(tokens[i:i + 3]) for i in range(len(tokens) - 2)}
    for name, sequence in real.sequences:
        if _windows(sequence) & token_windows:
            findings.append(Finding(relpath, "sequence", name))
    for line_no, line in enumerate(text.splitlines(), start=1):
        idents = {norm_key(m.group(0)) for m in _IDENT.finditer(line)}
        numbers = {n for n in numbers_in(line) if n not in TRIVIAL}
        if not numbers:
            continue
        for ident in idents & set(real.scalars):
            if numbers & real.scalars[ident]:
                findings.append(Finding(relpath, "keyed-scalar", f"line {line_no}: field '{ident}'"))
    if real.derived_rates:
        for line_no, line in enumerate(text.splitlines(), start=1):
            if RATE_WORDS.search(line) and {round(n, 10) for n in numbers_in(line)} & real.derived_rates:
                findings.append(Finding(relpath, "derived-rate", f"line {line_no}"))
    for name in real.names:
        if name in text:
            findings.append(Finding(relpath, "real-name", f"{len(name)}-char name"))
    return findings


def scan_example_values(relpath: str, data: Any, real: RealValues) -> list[Finding]:
    findings: list[Finding] = []

    def walk(node: Any, key: str = "") -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, str(k))
        elif isinstance(node, list):
            for item in node:
                walk(item, key)
        else:
            number = _num(node)
            if number is None or number in TRIVIAL:
                return
            if abs(number) >= 1000 and number in real.all_values:
                findings.append(Finding(relpath, "example-real-value", f"field '{key}'"))
            elif number in real.keyed_all.get(norm_key(key), set()):
                findings.append(Finding(relpath, "example-keyed-value", f"field '{key}'"))

    walk(data)
    return findings


def scan_paths(root: Path, relpaths: list[str], real: RealValues) -> list[Finding]:
    """Scan candidate publication files. YAML/JSON under examples/ also get the stricter example checks."""
    findings: list[Finding] = []
    for rel in relpaths:
        path = root / rel
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        findings += scan_file_text(rel, path.read_text(encoding="utf-8", errors="replace"), real)
    return findings


TEXT_SUFFIXES = {".py", ".md", ".json", ".yaml", ".yml", ".toml", ".html", ".ts", ".tsx", ".js", ".mjs", ".cjs",
                 ".css", ".txt", ".svg", ""}


def scan_file_text(rel: str, text: str, real: RealValues) -> list[Finding]:
    """All checks for one file's text (working tree or a historical blob). Example files get the strict checks."""
    findings = scan_text(rel, text, real)
    suffix = Path(rel).suffix.lower()
    if rel.replace("\\", "/").startswith("examples/") and suffix in {".json", ".yaml", ".yml"}:
        try:
            import yaml

            data = json.loads(text) if suffix == ".json" else yaml.safe_load(text)
        except Exception:  # noqa: BLE001 - unparsable example files are a finding of their own
            return [*findings, Finding(rel, "example-unparsable", "cannot parse")]
        findings += scan_example_values(rel, data, real)
    return findings
