"""ScenarioSpec: a reproducible scenario definition (public schema; data comes from the referenced pack).

YAML/JSON fields:

``name``, ``description``
``base_params``  directory of a parameter pack (relative to the spec file or absolute)
``horizon``      number of quarters to run; ``start_quarter`` (default 1); ``seed`` (default 0)
``overrides``    list of ``{path, set|scale|add, from_quarter?, to_quarter?}`` applied to the pack before each quarter
``events``       list of ``{type, from_quarter, target?, magnitude, duration?, label?}`` (see ``control.events``);
                 ``quarter`` is accepted as an alias of ``from_quarter``
``competitors``  list of ``{name, strategy: baseline|random|replay, params?}``
``our_policy``   ``{type: fixed, default?, plans?: {quarter: file}}`` | ``{type: hold}`` | ``{type: external, dir}``

Override paths address the raw pack dict: ``finance.tax_rate_percent``, ``capacity_options[*].cost``,
``stores[key=N1-Northwick].setup_cost``, ``markets[*].segments.*.wtp``.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

SPEC_SCHEMA = "marketplace-sim/scenario@1"
FINGERPRINT_CHARS = 16


@dataclass(frozen=True)
class Override:
    path: str
    op: str  # set | scale | add
    value: float | str | bool
    from_quarter: int | None = None
    to_quarter: int | None = None

    def active(self, quarter: int) -> bool:
        return (self.from_quarter is None or quarter >= self.from_quarter) and (
            self.to_quarter is None or quarter <= self.to_quarter)


@dataclass(frozen=True)
class EventSpec:
    type: str
    quarter: int
    magnitude: float = 0.0
    target: str = "*"
    duration: int = 1
    label: str = ""

    def active(self, quarter: int) -> bool:
        return self.quarter <= quarter < self.quarter + max(self.duration, 1)


@dataclass(frozen=True)
class CompetitorSpec:
    name: str
    strategy: str = "baseline"
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class ScenarioSpec:
    name: str
    base_params: str
    horizon: int = 4
    start_quarter: int = 1
    seed: int = 0
    description: str = ""
    overrides: list[Override] = field(default_factory=list)
    events: list[EventSpec] = field(default_factory=list)
    competitors: list[CompetitorSpec] = field(default_factory=list)
    our_policy: dict[str, Any] = field(default_factory=lambda: {"type": "hold"})
    origin: str | None = None  # directory the spec was loaded from (for relative paths)

    def resolve(self, relative: str) -> Path:
        path = Path(relative)
        if path.is_absolute() or self.origin is None:
            return path
        return (Path(self.origin) / path).resolve()

    def canonical(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("origin", None)
        data["base_params"] = str(self.resolve(self.base_params))
        return data

    def fingerprint(self, pack_text: str = "") -> str:
        payload = json.dumps(self.canonical(), sort_keys=True, separators=(",", ":")) + pack_text
        return hashlib.sha256(payload.encode()).hexdigest()[:FINGERPRINT_CHARS]


def _override(raw: dict[str, Any]) -> Override:
    for op in ("set", "scale", "add"):
        if op in raw:
            return Override(str(raw["path"]), op, raw[op], raw.get("from_quarter"), raw.get("to_quarter"))
    raise ValueError(f"override needs one of set/scale/add: {raw}")


def spec_from_dict(data: dict[str, Any], origin: str | None = None) -> ScenarioSpec:
    if data.get("schema", SPEC_SCHEMA) != SPEC_SCHEMA:
        raise ValueError("not a scenario spec")
    if "base_params" not in data or "name" not in data:
        raise ValueError("scenario needs 'name' and 'base_params'")
    return ScenarioSpec(
        name=str(data["name"]), base_params=str(data["base_params"]), horizon=int(data.get("horizon", 4)),
        start_quarter=int(data.get("start_quarter", 1)), seed=int(data.get("seed", 0)),
        description=str(data.get("description", "")),
        overrides=[_override(o) for o in data.get("overrides") or []],
        events=[EventSpec(str(e["type"]), int(e.get("from_quarter", e.get("quarter", 1))), float(e.get("magnitude", 0)), str(e.get("target", "*")),
                          int(e.get("duration", 1)), str(e.get("label", ""))) for e in data.get("events") or []],
        competitors=[CompetitorSpec(str(c["name"]), str(c.get("strategy", "baseline")), dict(c.get("params") or {}))
                     for c in data.get("competitors") or []],
        our_policy=dict(data.get("our_policy") or {"type": "hold"}),
        origin=origin,
    )


def load_spec(path: Path) -> ScenarioSpec:
    text = path.read_text(encoding="utf-8")
    data = json.loads(text) if path.suffix.lower() == ".json" else yaml.safe_load(text)
    if not isinstance(data, dict):
        raise TypeError(f"{path}: scenario must be a mapping")
    return spec_from_dict(data, str(path.parent.resolve()))


# --- path addressing on the raw pack dict ----------------------------------------------------------------------------

def _tokens(path: str) -> list[str]:
    out: list[str] = []
    for part in path.split("."):
        while "[" in part:
            head, rest = part.split("[", 1)
            if head:
                out.append(head)
            selector, part = rest.split("]", 1)
            out.append(f"[{selector}]")
        if part:
            out.append(part)
    return out


def apply_path(data: Any, path: str, fn: Callable[[Any], Any]) -> int:
    """Apply ``fn`` to every value addressed by ``path``. Returns the number of values changed."""

    def walk(node: Any, tokens: list[str]) -> int:
        if not tokens:
            return 0
        token, rest = tokens[0], tokens[1:]
        if token.startswith("["):
            if not isinstance(node, list):
                return 0
            selector = token[1:-1]
            if selector == "*":
                items = list(range(len(node)))
            else:
                key, _, value = selector.partition("=")
                items = [i for i, item in enumerate(node) if isinstance(item, dict) and str(item.get(key)) == value]
            count = 0
            for i in items:
                if rest:
                    count += walk(node[i], rest)
                else:
                    node[i] = fn(node[i])
                    count += 1
            return count
        if not isinstance(node, dict):
            return 0
        keys = list(node) if token == "*" else ([token] if token in node else [])
        count = 0
        for key in keys:
            if rest:
                count += walk(node[key], rest)
            else:
                node[key] = fn(node[key])
                count += 1
        return count

    return walk(data, _tokens(path))


def _op_function(op: str, value: Any) -> Callable[[Any], Any]:
    def set_value(_old: Any) -> Any:
        return value

    def scale(old: Any) -> Any:
        return old * float(value)

    def add(old: Any) -> Any:
        return old + float(value)

    return {"set": set_value, "scale": scale, "add": add}[op]


def apply_overrides(raw_pack: dict[str, Any], overrides: list[Override], quarter: int) -> tuple[dict[str, Any], list[str]]:
    data = copy.deepcopy(raw_pack)
    applied: list[str] = []
    for override in overrides:
        if not override.active(quarter):
            continue
        fn = _op_function(override.op, override.value)
        changed = apply_path(data, override.path, fn)
        if changed == 0:
            raise ValueError(f"override path matched nothing: {override.path}")
        applied.append(f"override {override.op} {override.path} ({changed} value(s))")
    return data, applied
