"""Thin projection of REA Evidence JSON into decision, metric and RPC catalogs.

REA (https://github.com/morluto/rea) performs the reverse engineering:

* ``inspect_web_network_capture`` decodes the HAR/DevTools capture.
* ``analyze_javascript_application`` inventories the webpack modules, records each
  module's exact source range and ``source_sha256``, and discovers literal
  ``.fetch("<name>")`` endpoint candidates.

This module does not parse JavaScript into an AST, build call graphs or decode HAR
files. It only reads REA Evidence JSON, slices the module bytes REA already
located, verifies them against REA's recorded digest, and applies a small set of
literal patterns that are specific to the Marketplace client (``window.X =
Base.extend({...})`` class registrations, ``this.com(...)`` controls,
``this.value(...)`` reads, ``this.data.calculate.*`` reads). REA has no view for
those application-specific conventions; ``docs/rea-pivot.md`` documents the gap.

Outputs from :func:`build_private_inventory` contain source locations and stay
under ``evidence/private``. :func:`public_catalogs` removes locations and values
and keeps only structure, types, bounds and provenance categories.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import asdict, dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from marketplace_sysid.security.redaction import safe_shape

JSON = dict[str, Any]

# Methods implemented by the shared ``Decision`` base class. Every registered
# class inherits them; the server decides which ones a given service accepts.
BASE_DECISION_METHODS: dict[str, dict[str, str]] = {
    "view": {"params": "[user, sendStatic, sendDynamic, sendErrors, sendCalculate]", "class": "READ"},
    "modify": {"params": "[user, 0]", "class": "STATE_TRACKING_LOCK"},
    "calculate": {"params": "[user, decisions, 0]", "class": "CALCULATION_TRIGGER"},
    "save": {"params": "[user, decisions, 0, lockToken]", "class": "WRITE"},
    "cancel": {"params": "[user, 0, lockToken]", "class": "STATE_TRACKING_LOCK"},
    "removeLock": {"params": "[user, 0]", "class": "STATE_TRACKING_LOCK"},
    "validateLock": {"params": "[user, 0, lockToken]", "class": "STATE_TRACKING_LOCK"},
    "prolongLock": {"params": "[user, 0, lockToken]", "class": "STATE_TRACKING_LOCK"},
}
FINALIZATION_BUTTONS = {"continueWrapup", "continueWrapup1", "unwrap"}
BASE_DEFAULTS: JSON = {"viewModeButtons": ["modify"], "modifyModeButtons": ["save", "cancel"], "sendCalculate": True}

_WRITE_NAME = re.compile(r"(?i)^(save|update|submit|set|store|commit|post|create|delete|remove|modify|cancel|prolong|join|run|fill|finish|wrap)")
_READ_NAME = re.compile(r"(?i)^(view|get|load|list|check|basic|welcome|resolve|schedule|team|students|your|left|resource|live|wrapup|gs$)")


@dataclass(frozen=True)
class ModuleSource:
    node_id: str
    module_key: str
    path: str
    line: int
    column: int
    offset: int
    text: str


@dataclass
class ClassProfile:
    name: str
    base: str
    module_key: str
    module_node_id: str
    location: str
    members: list[str] = field(default_factory=list)
    flags: JSON = field(default_factory=dict)
    fetch_methods: list[str] = field(default_factory=list)
    decision_fields: list[JSON] = field(default_factory=list)
    controls: list[JSON] = field(default_factory=list)
    calculate_bindings: list[JSON] = field(default_factory=list)
    calculate_reads: list[str] = field(default_factory=list)
    data_reads: dict[str, list[str]] = field(default_factory=dict)
    error_paths: list[str] = field(default_factory=list)
    arithmetic: list[JSON] = field(default_factory=list)


# ---------------------------------------------------------------------------
# REA Evidence access


def load_bundle(path: Path) -> JSON:
    data: JSON = json.loads(path.read_text(encoding="utf-8"))
    if "records" not in data:
        raise ValueError(f"{path} is not a REA Evidence bundle")
    return data


def find_record(bundle: JSON, operation: str) -> JSON:
    for record in bundle["records"]:
        if record.get("operation") == operation:
            return dict(record)
    raise KeyError(operation)


def _line_starts(text: str) -> list[int]:
    starts = [0]
    for index, char in enumerate(text):
        if char == "\n":
            starts.append(index + 1)
    return starts


def _line_col(starts: list[int], offset: int) -> tuple[int, int]:
    low, high = 0, len(starts) - 1
    while low < high:
        mid = (low + high + 1) // 2
        if starts[mid] <= offset:
            low = mid
        else:
            high = mid - 1
    return low + 1, offset - starts[low]


def iter_module_sources(app_record: JSON, source_root: Path) -> Iterator[ModuleSource]:
    """Yield each REA webpack module whose bytes match REA's recorded digest."""
    texts: dict[str, str] = {}
    starts: dict[str, list[int]] = {}
    seen: set[tuple[str, int]] = set()
    for node in app_record["normalized_result"]["graph"]["nodes"]:
        if node.get("kind") != "javascript-module":
            continue
        for observation in node.get("observations", []):
            props = observation.get("properties", {})
            location = observation.get("evidence", {}).get("location", {})
            digest = props.get("source_sha256")
            if not location.get("available") or not digest:
                continue
            value = location["value"]
            path = str(value["source"])
            if path not in texts:
                texts[path] = (source_root / path).read_text(encoding="utf-8")
                starts[path] = _line_starts(texts[path])
            line_starts = starts[path]
            begin = line_starts[value["start"]["line"] - 1] + value["start"]["column"]
            end = line_starts[value["end"]["line"] - 1] + value["end"]["column"]
            body = texts[path][begin:end]
            if hashlib.sha256(body.encode("utf-8")).hexdigest() != digest:
                continue
            if (path, begin) in seen:
                continue
            seen.add((path, begin))
            yield ModuleSource(
                node_id=str(node["node_id"]),
                module_key=str(props.get("module_key") or node["identity"]["key"]),
                path=path,
                line=int(value["start"]["line"]),
                column=int(value["start"]["column"]),
                offset=begin,
                text=body,
            )


def endpoint_literals(app_record: JSON) -> list[JSON]:
    """REA ``discover-static-endpoint`` nodes whose key is an exact literal."""
    rows: list[JSON] = []
    for node in app_record["normalized_result"]["graph"]["nodes"]:
        if node.get("kind") != "endpoint":
            continue
        try:
            key = json.loads(node["identity"]["key"])
        except (KeyError, ValueError):
            continue
        if not isinstance(key, list) or len(key) != 2 or key[0] != "literal":
            continue
        for observation in node.get("observations", []):
            location = observation.get("evidence", {}).get("location", {})
            if location.get("available"):
                value = location["value"]
                rows.append({
                    "name": str(key[1]),
                    "node_id": node["node_id"],
                    "location": f'{value["source"]}:{value["start"]["line"]}:{value["start"]["column"]}',
                })
                break
    return sorted(rows, key=lambda row: str(row["name"]))


# ---------------------------------------------------------------------------
# Literal projections over REA-located module text


def _string_mask(text: str) -> list[bool]:
    mask = [False] * len(text)
    index = 0
    while index < len(text):
        char = text[index]
        if char in "\"'`":
            quote = char
            start = index
            index += 1
            while index < len(text) and text[index] != quote:
                if text[index] == "\\":
                    index += 1
                index += 1
            for position in range(start, min(index + 1, len(text))):
                mask[position] = True
        index += 1
    return mask


def balanced_end(text: str, start: int) -> int:
    """Return the index of the bracket closing the construct opened before ``start``."""
    depth = 0
    index = start
    while index < len(text):
        char = text[index]
        if char in "{([":
            depth += 1
        elif char in "})]":
            depth -= 1
            if depth < 0:
                return index
        elif char in "\"'`":
            quote = char
            index += 1
            while index < len(text) and text[index] != quote:
                if text[index] == "\\":
                    index += 1
                index += 1
        index += 1
    return len(text)


_MEMBER = re.compile(r"([A-Za-z_$][\w$]*)\s*:\s*(async\s+)?(function\b)?")


def top_level_members(obj: str) -> dict[str, tuple[int, int]]:
    """Map object-literal member names to their value span (``obj`` starts at ``{``)."""
    members: dict[str, tuple[int, int]] = {}
    mask = _string_mask(obj)
    depth = 0
    index = 0
    expect_key = True
    while index < len(obj):
        char = obj[index]
        if mask[index]:
            index += 1
            continue
        if char in "{([":
            depth += 1
            if depth == 1:
                expect_key = True
            index += 1
            continue
        if char in "})]":
            depth -= 1
            index += 1
            continue
        if depth == 1 and char == ",":
            expect_key = True
            index += 1
            continue
        if depth == 1 and expect_key:
            match = _MEMBER.match(obj, index)
            if match:
                value_start = match.end(1)
                value_start = obj.index(":", value_start) + 1
                end = value_start
                inner = 0
                while end < len(obj):
                    if mask[end]:
                        end += 1
                        continue
                    current = obj[end]
                    if current in "{([":
                        inner += 1
                    elif current in "})]":
                        if inner == 0:
                            break
                        inner -= 1
                    elif current == "," and inner == 0:
                        break
                    end += 1
                members.setdefault(match.group(1), (value_start, end))
                index = end
                expect_key = False
                continue
            if not char.isspace():
                expect_key = False
        index += 1
    return members


def _literal(value: str) -> Any:
    text = value.strip()
    if text in {"!0", "true"}:
        return True
    if text in {"!1", "false"}:
        return False
    if text.startswith("[") and text.endswith("]"):
        items = re.findall(r'"([^"]*)"', text)
        if re.fullmatch(r'\[\s*(?:"[^"]*"\s*,?\s*)*\]', text):
            return items
    if re.fullmatch(r"-?\d+(?:\.\d+)?(?:e\d+)?", text):
        return float(text) if any(ch in text for ch in ".e") else int(text)
    if re.fullmatch(r'"[^"]*"', text):
        return text[1:-1]
    return None


_JS_BUILTINS = {"length", "push", "pop", "map", "filter", "forEach", "indexOf", "sort", "slice", "splice",
                "concat", "join", "toLookUp", "format", "formatInt", "formatFloat", "find", "some", "every",
                "reduce", "keys", "hasOwnProperty", "toString", "draw", "observe", "destroy"}
_LAYOUT_KEY = re.compile(r"^(has[A-Z]\w*|is[A-Z]\w*|show[A-Z]\w*|\w*[Tt]emplate|css|height|width|style|html|"
                         r"title|label|name|shortName|companyName|id|qtr|format|chartSettings|graph|x|y)$")
CONTROL_VALUE_TYPES = {"iedit": "integer", "fedit": "float", "checkbox": "boolean", "radio": "enum",
                       "combobox": "enum", "memo": "text", "edit": "text", "file": "file"}
_FLAG_MEMBERS = ("viewModeButtons", "modifyModeButtons", "sendCalculate", "sendStatic", "sendDynamic",
                 "sendErrors", "autoCalculated", "redrawOnModify", "tableName", "service")
_ALIAS = r"\b([A-Za-z_$][\w$]*)\s*=\s*this\.data\.{name}\b(?![\w$.])"


def _alias_reads(text: str, source: str) -> set[str]:
    reads: set[str] = set(re.findall(r"this\.data\." + source + r"\.([A-Za-z_$][\w$]*)", text))
    for alias in set(re.findall(_ALIAS.format(name=source), text)):
        reads.update(re.findall(r"(?<![\w$.])" + re.escape(alias) + r"\.([A-Za-z_$][\w$]*)", text))
    return reads


_ARITH = re.compile(
    r"(?<![\w$.\"'])((?:[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*|\[[^\]\[]{1,20}\])*|\d+(?:\.\d+)?)"
    r"(?:\s*[*/%]\s*(?:[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*|\[[^\]\[]{1,20}\])*|\d+(?:\.\d+)?))+)"
)
_CONTROL = re.compile(r'this\.com\("([A-Za-z]+)"\s*,\s*"([A-Za-z_$][\w$]*)')
_VALUE_READ = re.compile(
    r'\.([A-Za-z_$][\w$]*)\s*=\s*(?:[^=;,]{0,60}?)this\.(?:value|checked|intValue|floatValue|getValue)\("([A-Za-z_$][\w$]*)'
)
_BIND = re.compile(r'this\.bindCalculate\(\s*([^,()]{1,80}?)\s*,\s*"([a-z]+)"')


def profile_class(name: str, base: str, obj: str, module: ModuleSource, location: str) -> ClassProfile:
    members = top_level_members(obj)
    profile = ClassProfile(name=name, base=base, module_key=module.module_key,
                           module_node_id=module.node_id, location=location, members=sorted(members))
    for flag in _FLAG_MEMBERS:
        if flag in members:
            start, end = members[flag]
            profile.flags[flag] = _literal(obj[start:end])
    if "autoCalculated" in obj and "autoCalculated" not in profile.flags:
        profile.flags["autoCalculated_dynamic"] = True
    profile.fetch_methods = sorted(
        set(re.findall(r'fetch\([^,()]{1,60},\s*"([A-Za-z_]+)"', obj))
        | set(re.findall(r'\.fetch\(\s*"([A-Za-z_]+)"\s*,', obj))
    )
    read_body = obj[slice(*members["read"])] if "read" in members else ""
    controls: dict[str, str] = {}
    for control_type, prefix in _CONTROL.findall(obj):
        controls.setdefault(prefix, control_type)
    for control_type, prefix in re.findall(r'cf\.get([A-Z][A-Za-z]+)\(\s*"([A-Za-z_$][\w$]*)', obj):
        controls.setdefault(prefix, control_type.lower())
    profile.controls = [{"id_prefix": key, "type": value} for key, value in sorted(controls.items())]
    fields: dict[str, JSON] = {}
    for field_name, prefix in _VALUE_READ.findall(read_body):
        fields.setdefault(field_name, {"field": field_name, "control_prefix": prefix,
                                       "control_type": controls.get(prefix, "unknown")})
    for field_name in re.findall(r"this\.data\.decisions\.([A-Za-z_$][\w$]*)\s*=(?!=)", read_body):
        fields.setdefault(field_name, {"field": field_name, "control_prefix": None, "control_type": "unknown"})
    profile.decision_fields = sorted(fields.values(), key=lambda item: str(item["field"]))
    bindings = []
    for target, event in sorted(set(_BIND.findall(obj))):
        literal = re.match(r'"([A-Za-z_$][\w$]*)"', target)
        bindings.append({"id_prefix": literal.group(1) if literal else None,
                         "dynamic_target": literal is None, "event": event})
    profile.calculate_bindings = bindings
    profile.calculate_reads = sorted(_alias_reads(obj, "calculate") - _JS_BUILTINS)
    profile.data_reads = {
        source: sorted(_alias_reads(obj, source) - _JS_BUILTINS)
        for source in ("staticData", "dynamicData", "decisions", "commonData")
    }
    profile.error_paths = sorted(set(re.findall(r"this\.data\.errors\.decisions\.([A-Za-z_$][\w$]*)", obj)))
    mask = _string_mask(obj)
    arithmetic: list[JSON] = []
    for member_name, (start, end) in members.items():
        segment = obj[start:end]
        for match in _ARITH.finditer(segment):
            absolute = start + match.start()
            if mask[absolute]:
                continue
            expression = match.group(1)
            if not re.search(r"[*/%]", expression) or re.fullmatch(r"[\d\s*/.%]+", expression):
                continue
            if expression.startswith(("this.tc", "Math.")):
                continue
            arithmetic.append({"member": member_name, "expression": expression[:120],
                               "offset_in_class": absolute})
    profile.arithmetic = arithmetic
    return profile


def class_profiles(modules: Iterable[ModuleSource], file_texts: dict[str, str]) -> list[ClassProfile]:
    profiles: list[ClassProfile] = []
    starts = {path: _line_starts(text) for path, text in file_texts.items()}
    seen: set[tuple[str, int]] = set()
    # Prefer the innermost (smallest) REA module that contains a registration.
    for module in sorted(modules, key=lambda item: len(item.text)):
        for match in re.finditer(r"window\.([A-Za-z0-9_]+)\s*=\s*([A-Za-z0-9_.]+)\.extend\(\s*([{)])",
                                 module.text):
            key = (module.path, module.offset + match.start())
            if key in seen:
                continue
            seen.add(key)
            if match.group(3) == ")":
                obj = "{}"
            else:
                open_brace = match.end() - 1
                close = balanced_end(module.text, open_brace + 1)
                obj = module.text[open_brace:close + 1]
            line, column = _line_col(starts[module.path], module.offset + match.start())
            profiles.append(profile_class(match.group(1), match.group(2).split(".")[-1], obj, module,
                                          f"{module.path}:{line}:{column}"))
    return profiles


def resolve_flags(profiles: list[ClassProfile]) -> dict[str, JSON]:
    by_name = {profile.name: profile for profile in profiles}
    resolved: dict[str, JSON] = {}

    def effective(name: str, trail: tuple[str, ...] = ()) -> JSON:
        if name in resolved:
            return resolved[name]
        profile = by_name.get(name)
        if profile is None or name in trail:
            return dict(BASE_DEFAULTS)
        parent = dict(BASE_DEFAULTS) if profile.base == "Decision" else effective(profile.base, trail + (name,))
        merged = {**parent, **{k: v for k, v in profile.flags.items() if v is not None}}
        merged["chain"] = [name] + list(parent.get("chain", []))
        resolved[name] = merged
        return merged

    for profile in profiles:
        effective(profile.name)
    return resolved


# ---------------------------------------------------------------------------
# Capture projection


def capture_rpc(capture_record: JSON) -> list[JSON]:
    """Value-free RPC observations from REA ``inspect_web_network_capture`` records."""
    rows: list[JSON] = []
    for record in capture_record["normalized_result"]["records"]:
        reported = record.get("reported", {})
        request = reported.get("request", {})
        parts = urlsplit(str(request.get("url", "")))
        if not parts.path.endswith("backend-json.php"):
            continue
        service = parts.query.split("&")[0]
        method = None
        param_shape: Any = None
        try:
            body = json.loads(request.get("postData", {}).get("text") or "null")
            if isinstance(body, dict):
                method = body.get("method")
                param_shape = safe_shape(body.get("parameters"), max_depth=4)
        except ValueError:
            pass
        response_keys: list[str] = []
        calculate_keys: list[str] = []
        decision_shape: Any = None
        error_code = None
        try:
            payload = json.loads(reported.get("response", {}).get("content", {}).get("text") or "null")
        except ValueError:
            payload = None
        if isinstance(payload, dict):
            error_code = payload.get("error")
            result = payload.get("result")
            if isinstance(result, dict):
                response_keys = sorted(result)
                calc = result.get("calculate")
                if isinstance(calc, dict):
                    calculate_keys = sorted(calc)
                if isinstance(result.get("decisions"), (dict, list)):
                    decision_shape = safe_shape(result["decisions"], max_depth=5)
        rows.append({
            "ordinal": record.get("ordinal"),
            "service": service,
            "method": method,
            "http_method": request.get("method"),
            "parameter_shape": param_shape,
            "response_result_keys": response_keys,
            "calculate_keys": calculate_keys,
            "decision_shape": decision_shape,
            "error_code_is_zero": error_code in (0, "0") if error_code is not None else None,
        })
    return rows


def _flatten_numbers(value: Any, prefix: str = "") -> dict[str, float]:
    flat: dict[str, float] = {}
    if isinstance(value, dict):
        for key, child in value.items():
            flat.update(_flatten_numbers(child, f"{prefix}.{key}" if prefix else str(key)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            flat.update(_flatten_numbers(child, f"{prefix}[{index}]"))
    elif isinstance(value, (bool, int, float)):
        flat[prefix] = float(value)
    return flat


def experiment_value_rows(capture_record: JSON) -> list[JSON]:
    """PRIVATE: numeric decisions sent and calculate results returned, per RPC.

    Intended for HAR exports of operator-run what-if experiments. The rows contain
    simulation values and must only be written below ``evidence/private``.
    """
    rows: list[JSON] = []
    for record in capture_record["normalized_result"]["records"]:
        reported = record.get("reported", {})
        request = reported.get("request", {})
        parts = urlsplit(str(request.get("url", "")))
        if not parts.path.endswith("backend-json.php"):
            continue
        try:
            body = json.loads(request.get("postData", {}).get("text") or "null")
            payload = json.loads(reported.get("response", {}).get("content", {}).get("text") or "null")
        except ValueError:
            continue
        if not isinstance(body, dict) or not isinstance(payload, dict):
            continue
        method = body.get("method")
        if method not in {"view", "calculate", "save", "modify", "cancel"}:
            continue
        params = body.get("parameters") or []
        sent = params[1] if method in {"calculate", "save"} and len(params) > 1 else None
        raw_result = payload.get("result")
        result: JSON = raw_result if isinstance(raw_result, dict) else {}
        calc = result.get("calculateResult", result.get("calculate"))
        raw_check = result.get("checkResult")
        check: JSON = raw_check if isinstance(raw_check, dict) else {}
        errors = check.get("errors")
        rows.append({
            "ordinal": record.get("ordinal"),
            "started": reported.get("startedDateTime"),
            "service": parts.query.split("&")[0],
            "method": method,
            "decisions_sent": _flatten_numbers(sent) if sent is not None else None,
            "calculate_result": _flatten_numbers(calc) if calc is not None else None,
            "check_ok": check.get("ok"),
            "check_error_counts": ({k: errors.get(k) for k in ("fatalErrors", "warnings", "notes")}
                                   if isinstance(errors, dict) else None),
            "save_result": result.get("saveResult"),
        })
    return rows


# ---------------------------------------------------------------------------
# Rendered menu tree (private HTML pages)


class _TaskListParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.items: list[JSON] = []
        self._current: JSON | None = None
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key: value or "" for key, value in attrs}
        classes = attributes.get("class", "").split()
        if tag == "a" and "_tlItem" in classes:
            self._current = {"level": int(attributes.get("aria-level") or 0), "title": "", "slug": "",
                             "decision_screen": False, "collapsible": "clpsbl" in classes}
            self.items.append(self._current)
        elif self._current is not None and tag == "img":
            for item in classes:
                if item.startswith("tl-"):
                    self._current["slug"] = item[3:]
        elif self._current is not None and tag == "span" and "taskListItemTitle" in classes:
            self._in_title = True
        elif self._current is not None and tag == "div" and "taskListPencil" in classes:
            self._current["decision_screen"] = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "span":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title and self._current is not None:
            self._current["title"] += data.strip()


def menu_tree(html_paths: Iterable[Path]) -> list[JSON]:
    merged: dict[str, JSON] = {}
    order: list[str] = []
    for path in html_paths:
        parser = _TaskListParser()
        parser.feed(path.read_text(encoding="utf-8", errors="replace"))
        parents: dict[int, str] = {}
        for item in parser.items:
            key = item["slug"] or item["title"]
            parents[item["level"]] = key
            item["parent"] = parents.get(item["level"] - 1) if item["level"] > 1 else None
            if key not in merged:
                merged[key] = item
                order.append(key)
    return [merged[key] for key in order]


def language_labels(en_text: str) -> dict[str, dict[str, str]]:
    labels: dict[str, dict[str, str]] = {}
    for match in re.finditer(r'JSStrings\.add\("([A-Za-z0-9_]+)",\[', en_text):
        end = balanced_end(en_text, match.end())
        block = en_text[match.end():end]
        pairs = re.findall(r'\["([A-Za-z0-9_]+)","([^"\\<>{}]{1,48})"\]', block)
        labels[match.group(1).casefold()] = dict(pairs)
    return labels


# ---------------------------------------------------------------------------
# Inventory and catalogs


def classify_method(name: str) -> str:
    if name in BASE_DECISION_METHODS:
        return BASE_DECISION_METHODS[name]["class"]
    if name.endswith("Status") or name == "gs":
        return "READ_CANDIDATE"
    if _WRITE_NAME.match(name):
        return "WRITE_CANDIDATE"
    if _READ_NAME.match(name):
        return "READ_CANDIDATE"
    return "UNKNOWN"


def build_private_inventory(capture_bundle: Path, app_bundle: Path, source_root: Path,
                            html_dir: Path | None) -> JSON:
    capture = find_record(load_bundle(capture_bundle), "inspect_web_network_capture")
    application = find_record(load_bundle(app_bundle), "analyze_javascript_application")
    file_texts = {path.name: path.read_text(encoding="utf-8") for path in source_root.glob("*.js")}
    modules = list(iter_module_sources(application, source_root))
    profiles = class_profiles(modules, file_texts)
    flags = resolve_flags(profiles)
    en = file_texts.get("sstudent-en-us.js", "")
    labels = language_labels(en)
    observed = capture_rpc(capture)
    html_paths = sorted(html_dir.glob("*.html")) if html_dir else []
    return {
        "rea_evidence": {
            "capture_evidence_id": capture["evidence_id"],
            "application_evidence_id": application["evidence_id"],
            "verified_modules": len(modules),
            "graph_modules": sum(1 for node in application["normalized_result"]["graph"]["nodes"]
                                 if node.get("kind") == "javascript-module"),
        },
        "endpoint_literals": endpoint_literals(application),
        "classes": [asdict(profile) | {"effective": flags[profile.name],
                                        "labels": labels.get("decision_" + profile.name.casefold(), {})}
                    for profile in profiles],
        "observed_rpc": observed,
        "menu": menu_tree(html_paths),
    }


def _class_kind(row: JSON, by_name: dict[str, JSON] | None = None) -> str:
    effective = row["effective"]
    name = str(row["name"])
    if name.endswith(("Anim", "Anim2", "Editor")) or row["base"] in {"Class", "Editor"}:
        return "helper"
    if set(effective.get("viewModeButtons") or []) & FINALIZATION_BUTTONS:
        return "finalization"
    chain = [by_name[item] for item in effective.get("chain", [name]) if by_name and item in by_name] or [row]
    has_read = any(item["decision_fields"] or "read" in item["members"] for item in chain)
    if "modify" in (effective.get("viewModeButtons") or []) and has_read:
        return "decision"
    return "report"


def _inherited(row: JSON, by_name: dict[str, JSON], key: str) -> list[Any]:
    merged: list[Any] = []
    for item in row["effective"].get("chain", [row["name"]]):
        source = by_name.get(item)
        if source is None:
            continue
        for value in source[key]:
            if value not in merged:
                merged.append(value)
    return merged


def public_catalogs(inventory: JSON) -> tuple[JSON, JSON, JSON]:
    """Return de-identified (decision_catalog, metric_catalog, rpc_catalog)."""
    application_id = inventory["rea_evidence"]["application_evidence_id"]
    capture_id = inventory["rea_evidence"]["capture_evidence_id"]
    observed_by_service: dict[str, list[JSON]] = defaultdict(list)
    for row in inventory["observed_rpc"]:
        observed_by_service[str(row["service"])].append(row)
    menu_slugs = {str(item["slug"]): item for item in inventory["menu"] if item.get("slug")}
    decisions: list[JSON] = []
    metrics: list[JSON] = []
    by_name = {str(row["name"]): row for row in inventory["classes"]}
    for row in inventory["classes"]:
        kind = _class_kind(row, by_name)
        if kind == "helper":
            continue
        name = str(row["name"])
        effective = row["effective"]
        observed = observed_by_service.get(name, [])
        menu = menu_slugs.get(name.casefold())
        provenance = ["REA_STATIC_MODULE"] + (["REA_CAPTURE_RECORD"] if observed else [])
        bindings = _inherited(row, by_name, "calculate_bindings")
        bound_prefixes = {b["id_prefix"] for b in bindings}
        dynamic_binding = any(b.get("dynamic_target") for b in bindings)
        calculate_button = "calculate" in (effective.get("modifyModeButtons") or [])
        whatif = bool(bindings) or calculate_button or "calculate" in _inherited(row, by_name, "members")
        if kind == "finalization":
            decisions.append({
                "module": name,
                "service": name,
                "finalization": True,
                "never_automate": True,
                "rendered_in_q1_menu": menu is not None,
                "view_mode_buttons": effective.get("viewModeButtons"),
                "modify_mode_buttons": effective.get("modifyModeButtons"),
                "fields": [{"field": "wrapped", "value_type": "boolean", "control_type": "button"},
                           {"field": "targetSegments", "value_type": "list", "control_type": "checkbox"}],
                "submit_path": f"{name}.calculate then {name}.save(decisions={{wrapped: true, ...}})",
                "whatif_path": None,
                "provenance": provenance,
                "rea_evidence": [application_id] + ([capture_id] if observed else []),
                "rea_module_key": row["module_key"],
            })
            continue
        if kind == "decision":
            fields = []
            for item in _inherited(row, by_name, "decision_fields"):
                prefix = item.get("control_prefix")
                fields.append({
                    "field": item["field"],
                    "control_type": item["control_type"],
                    "value_type": CONTROL_VALUE_TYPES.get(str(item["control_type"]), "unknown"),
                    "label": row["labels"].get(str(item["field"])) or row["labels"].get(str(prefix)),
                    "client_bounds": "none-declared (numeric bounds are server-validated via checkResult)",
                    "server_validated": item["field"] in row["error_paths"] or bool(row["error_paths"]),
                    "triggers_live_calculate": (prefix in bound_prefixes) if prefix else None,
                    "possibly_triggers_live_calculate_via_dynamic_binding": dynamic_binding,
                    "recalculated_by_calculate_button": calculate_button,
                })
            decisions.append({
                "module": name,
                "service": name,
                "inherits": effective.get("chain", [])[1:],
                "rendered_in_q1_menu": menu is not None,
                "q1_menu_marked_decision_screen": bool(menu and menu.get("decision_screen")),
                "view_mode_buttons": effective.get("viewModeButtons"),
                "modify_mode_buttons": effective.get("modifyModeButtons"),
                "view_sends_calculate": effective.get("sendCalculate"),
                "live_calculate_bindings": len(bindings),
                "calculate_button": calculate_button,
                "fields": fields,
                "observed_decision_shape": next((o["decision_shape"] for o in observed if o["decision_shape"]), None),
                "submit_path": f"{name}.save(user, decisions, 0, lockToken)",
                "whatif_path": (f"{name}.calculate(user, decisions, 0) while {name}.modify lock is held"
                                if whatif else None),
                "provenance": provenance,
                "rea_evidence": [application_id] + ([capture_id] if observed else []),
                "rea_module_key": row["module_key"],
            })
        outputs = sorted(set(_inherited(row, by_name, "calculate_reads")) | {k for o in observed for k in o["calculate_keys"]})
        dynamic_reads = row["data_reads"].get("dynamicData", [])
        for metric_name in outputs:
            metrics.append({"metric": metric_name, "source": "calculate", "module": name,
                            "available_before_save": whatif and kind == "decision",
                            "provenance": provenance, "rea_module_key": row["module_key"]})
        if kind == "report":
            static_reads = row["data_reads"].get("staticData", [])
            for source_name, reads in (("dynamicData", dynamic_reads), ("staticData", static_reads)):
                for metric_name in reads:
                    if _LAYOUT_KEY.match(metric_name):
                        continue
                    metrics.append({"metric": metric_name, "source": f"view.{source_name}", "module": name,
                                    "available_before_save": False, "provenance": provenance,
                                    "observed_in_capture": bool(observed),
                                    "rea_module_key": row["module_key"]})
    endpoint_rows = [{"method": item["name"], "classification": classify_method(str(item["name"])),
                      "provenance": ["REA_STATIC_ENDPOINT"]} for item in inventory["endpoint_literals"]]
    observed_pairs = Counter((str(r["service"]), str(r["method"])) for r in inventory["observed_rpc"])
    rpc = {
        "base_decision_methods": {k: v for k, v in BASE_DECISION_METHODS.items()},
        "literal_methods": endpoint_rows,
        "observed_pairs": [{"service": s, "method": m, "observed_count": c,
                            "classification": classify_method(m)} for (s, m), c in sorted(observed_pairs.items())],
        "rea_evidence": [application_id, capture_id],
    }
    decision_catalog = {"schema": "marketplace-sysid/decision-catalog@1",
                        "values_included": False, "decisions": decisions}
    metric_catalog = {"schema": "marketplace-sysid/metric-catalog@1",
                      "values_included": False, "metrics": metrics}
    return decision_catalog, metric_catalog, rpc


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--capture-bundle", type=Path, required=True)
    parser.add_argument("--app-bundle", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--html-dir", type=Path)
    parser.add_argument("--private-out", type=Path, required=True,
                        help="Directory under evidence/private for located inventory")
    parser.add_argument("--public-out", type=Path, help="Directory for de-identified catalogs")
    parser.add_argument("--experiment-capture", type=Path,
                        help="PRIVATE: REA capture bundle of an operator experiment; values go to --private-out")
    args = parser.parse_args()
    if "private" not in args.private_out.resolve().as_posix().split("/"):
        raise SystemExit("--private-out must be inside a 'private' directory")
    args.private_out.mkdir(parents=True, exist_ok=True)
    if args.experiment_capture:
        rows = experiment_value_rows(find_record(load_bundle(args.experiment_capture),
                                                 "inspect_web_network_capture"))
        (args.private_out / "experiment_values.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    inventory = build_private_inventory(args.capture_bundle, args.app_bundle, args.source_root, args.html_dir)
    (args.private_out / "inventory.json").write_text(json.dumps(inventory, indent=1), encoding="utf-8")
    decision_catalog, metric_catalog, rpc = public_catalogs(inventory)
    target = args.public_out or args.private_out
    target.mkdir(parents=True, exist_ok=True)
    for name, payload in (("decision_catalog.json", decision_catalog), ("metric_catalog.json", metric_catalog),
                          ("rpc_catalog.json", rpc)):
        (target / name).write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"classes": len(inventory["classes"]), "decisions": len(decision_catalog["decisions"]),
                      "metrics": len(metric_catalog["metrics"]), "observed_rpc": len(inventory["observed_rpc"]),
                      "endpoint_literals": len(inventory["endpoint_literals"])}))


if __name__ == "__main__":
    main()
