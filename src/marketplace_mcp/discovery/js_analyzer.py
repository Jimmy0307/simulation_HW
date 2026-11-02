"""Conservative static symbol extraction for browser-delivered JavaScript."""

from __future__ import annotations

import re
from bisect import bisect_right
from pathlib import Path
from typing import Any

from marketplace_mcp.discovery.shapes import endpoint_path
from marketplace_mcp.security.redaction import safe_identifier

_FUNCTION = re.compile(r"\bfunction\s*\*?\s*([A-Za-z_$][\w$]*)?\s*\(([^)]*)\)\s*\{")
_CLASS = re.compile(r"\bclass\s+([A-Za-z_$][\w$]*)")
_ARROW = re.compile(
    r"\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:\(([^)]*)\)|([A-Za-z_$][\w$]*))\s*=>"
)
_ASSIGNED_FUNCTION = re.compile(
    r"(?:\b([A-Za-z_$][\w$]*)\s*[:=]\s*)(?:async\s*)?function\s*\(([^)]*)\)\s*\{"
)
_METHOD = re.compile(r"(?:^|[;,{}])\s*(?:async\s+)?([A-Za-z_$][\w$]*)\s*\(([^)]*)\)\s*\{")
_GLOBAL = re.compile(r"\b(?:window|globalThis)\.([A-Za-z_$][\w$]*)\s*=")
_ROUTE = re.compile(r"[\"']([^\"']{0,180}(?:backend-json\.php|engine\.php)[^\"']{0,180})[\"']", re.IGNORECASE)
_SERVICE = re.compile(r"backend-json\.php\?([A-Z][A-Za-z0-9_]{1,63})")
_RPC_LITERAL = re.compile(r"[\"']method[\"']\s*:\s*[\"']([A-Za-z_$][\w$.$]{0,127})[\"']")
_ARCHITECTURE = re.compile(r"(?i)(menu|resource|play|content|load|fetch|ajax|send|request|view|save|update|service|rpc|server|route|engine)")
_CALL = re.compile(r"(?:\bthis\s*\.\s*)?([A-Za-z_$][\w$]*)\s*\(")
_CALL_KEYWORDS = {"if", "for", "while", "switch", "catch", "function", "return", "new", "typeof", "delete", "void", "super"}
_CALC_TERMS = (
    "calc", "compute", "score", "demand", "price", "sales", "revenue", "cost", "profit",
    "share", "forecast", "capacity", "productivity", "balance", "cash", "income", "ratio", "index",
)


def _regex_literal_end(text: str, slash: int) -> int | None:
    # A bounded look-behind keeps analysis linear on multi-megabyte bundles.
    prefix = text[max(0, slash - 64) : slash].rstrip()
    if not prefix:
        can_start = True
    else:
        previous = prefix[-1]
        word_match = re.search(r"([A-Za-z_$][\w$]*)$", prefix)
        word = word_match.group(1) if word_match else ""
        can_start = previous in "=(:,[!&|?{};" or prefix.endswith("=>") or word in {
            "return", "case", "throw", "typeof", "instanceof", "yield", "await", "delete", "void", "new"
        }
    if not can_start:
        return None
    escaped = False
    in_class = False
    i = slash + 1
    while i < len(text):
        char = text[i]
        if char in "\r\n":
            return None
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == "[":
            in_class = True
        elif char == "]":
            in_class = False
        elif char == "/" and not in_class:
            i += 1
            while i < len(text) and text[i].isalpha():
                i += 1
            return i
        i += 1
    return None


def _brace_pairs(text: str) -> dict[int, int]:
    """Build brace pairs in one lexical pass for efficient minified-bundle analysis."""
    stack: list[int] = []
    pairs: dict[int, int] = {}
    quote: str | None = None
    escaped = False
    line_comment = False
    block_comment = False
    i = 0
    while i < len(text):
        char = text[i]
        next_char = text[i + 1] if i + 1 < len(text) else ""
        if line_comment:
            if char in "\r\n":
                line_comment = False
        elif block_comment:
            if char == "*" and next_char == "/":
                block_comment = False
                i += 1
        elif quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char == "/" and next_char == "/":
            line_comment = True
            i += 1
        elif char == "/" and next_char == "*":
            block_comment = True
            i += 1
        elif char == "/":
            regex_end = _regex_literal_end(text, i)
            if regex_end is not None:
                i = regex_end - 1
        elif char in "'\"`":
            quote = char
        elif char == "{":
            stack.append(i)
        elif char == "}" and stack:
            pairs[stack.pop()] = i
        i += 1
    return pairs


def _params(value: str) -> list[str]:
    result = []
    for item in value.split(","):
        name = item.strip().split("=", 1)[0].strip()
        if re.fullmatch(r"[A-Za-z_$][\w$]*", name):
            result.append(name)
    return result


def _has_calculation_term(name: str) -> bool:
    split_name = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name)
    tokens = [item.casefold() for item in re.findall(r"[A-Za-z0-9]+", split_name)]
    return any(token.startswith(term) for token in tokens for term in _CALC_TERMS)


def _function_records(text: str, brace_pairs: dict[int, int]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    patterns = [(_FUNCTION, "function"), (_ASSIGNED_FUNCTION, "assigned_function"), (_METHOD, "method")]
    reserved = {"if", "for", "while", "switch", "catch", "with", "function", "return", "new"}
    for pattern, kind in patterns:
        for match in pattern.finditer(text):
            brace = match.end() - 1
            end = brace_pairs.get(brace)
            name = match.group(1) or "anonymous"
            if name in reserved:
                continue
            parameters = match.group(2) or ""
            complete = end is not None
            records.append(
                {
                    "name": name,
                    "kind": kind,
                    "parameters": _params(parameters),
                    "start": match.start(),
                    "end": end + 1 if end is not None else match.end(),
                    "body": text[brace + 1 : end] if end is not None else "",
                    "body_complete": complete,
                }
            )
    for match in _ARROW.finditer(text):
        name = match.group(1)
        params = match.group(2) if match.group(2) is not None else match.group(3) or ""
        body_start = match.end()
        while body_start < len(text) and text[body_start].isspace():
            body_start += 1
        if body_start < len(text) and text[body_start] == "{" and body_start in brace_pairs:
            body_end = brace_pairs[body_start]
            body = text[body_start + 1 : body_end]
            complete = True
            end = body_end + 1
        else:
            expression = re.match(r"([^;,\r\n]{1,180})", text[body_start:])
            body = f"return {expression.group(1).strip()};" if expression else ""
            complete = bool(expression)
            end = body_start + len(expression.group(1)) if expression else match.end()
        records.append(
            {
                "name": name,
                "kind": "arrow",
                "parameters": _params(params),
                "start": match.start(),
                "end": end,
                "body": body,
                "body_complete": complete,
            }
        )
    # Avoid returning a duplicate declaration found by multiple patterns.
    unique: dict[tuple[str, int], dict[str, Any]] = {}
    for record in records:
        unique[(record["name"], record["start"])] = record
    return sorted(unique.values(), key=lambda record: record["start"])


def _source_location(text: str, offset: int, line_starts: list[int]) -> str:
    line_index = bisect_right(line_starts, offset) - 1
    line = line_index + 1
    previous_newline = line_starts[line_index] - 1 if line_index else -1
    column = offset - previous_newline
    return f"line:{line},column:{column}"


def _formula_candidate(function: dict[str, Any]) -> dict[str, Any] | None:
    name = function["name"]
    body = function["body"]
    if not _has_calculation_term(name) or not body or not function.get("body_complete"):
        return None
    if re.search(r"(?i)\b(fetch|ajax|send|XMLHttpRequest|backend-json|document|window)\b", body):
        return None
    returns = list(re.finditer(r"\breturn\s+([^;{}\r\n]{1,180})", body))
    if len(returns) != 1:
        return None
    returned = returns[0]
    expression = returned.group(1).strip().rstrip(")")
    if not re.search(r"[+*/%-]", expression):
        return None
    if not re.fullmatch(r"[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)?(?:\s*[+*/%-]\s*(?:[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)?|\d+(?:\.\d+)?|\([^()]{1,64}\)))*", expression):
        return None
    identifiers = re.findall(r"this\.[A-Za-z_$][\w$]*|[A-Za-z_$][\w$]*", expression)
    identifiers = [token for token in identifiers if token != "this"]
    allowed = set(function["parameters"])
    residue = body[: returned.start()] + body[returned.end() :]
    residue = re.sub(r"/\*.*?\*/|//[^\r\n]*", "", residue, flags=re.DOTALL).strip(" ;\t\r\n")
    expression_has_call = bool(re.search(r"[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)?\s*\(", expression))
    formula_inputs = list(dict.fromkeys(identifiers))
    exactish = (
        not residue
        and not expression_has_call
        and all(token in allowed or token.startswith("this.") for token in identifiers)
    )
    if not exactish:
        return {
            "name": name,
            "expression": expression,
            "inputs": formula_inputs,
            "classification": "UNKNOWN",
            "confidence": 0.45,
            "notes": "Arithmetic return candidate requires manual dependency and purity review.",
        }
    return {
        "name": name,
        "expression": expression,
        "inputs": formula_inputs,
        "classification": "EXACT_CLIENT_FORMULA",
        "confidence": 1.0,
        "notes": "Function body contains one pure arithmetic return over declared parameters or an instance property; exact client code does not establish server usage.",
    }


def analyze_javascript(text: str, *, source_file: str = "client_asset_001.js") -> dict[str, Any]:
    functions = _function_records(text, _brace_pairs(text))
    line_starts = [0]
    line_starts.extend(index + 1 for index, char in enumerate(text) if char == "\n")
    symbols = []
    formulas = []
    calculation_review_candidates = []
    call_edges = []
    for function in functions:
        function_name = safe_identifier(function["name"], prefix="function")
        entry = {
            "name": function_name,
            "kind": function["kind"],
            "parameters": function["parameters"],
            "source_file": source_file,
            "source_location": _source_location(text, function["start"], line_starts),
            "classification": "VERIFIED_CLIENT_CODE",
            "provenance": "VERIFIED_CLIENT_CODE",
            "body_complete": function.get("body_complete", False),
        }
        symbols.append(entry)
        if _has_calculation_term(function_name):
            calculation_review_candidates.append(
                {
                    "name": function_name,
                    "inputs": [safe_identifier(item, prefix="parameter") for item in function["parameters"]],
                    "expression": None,
                    "source_file": source_file,
                    "source_location": entry["source_location"],
                    "classification": "UNKNOWN",
                    "provenance": "VERIFIED_CLIENT_CODE",
                    "confidence": 0.25,
                    "notes": "The function name matches a calculation-related term. This lexical candidate is not verified as a calculation or client transformation; inspect its body and dependencies before classification.",
                }
            )
        called = sorted(
            {
                safe_identifier(match.group(1), prefix="function")
                for match in _CALL.finditer(function["body"])
                if match.group(1) not in _CALL_KEYWORDS and _ARCHITECTURE.search(match.group(1))
            }
        )
        if _ARCHITECTURE.search(function_name):
            for callee in called:
                call_edges.append(
                    {
                        "caller": function_name,
                        "callee": callee,
                        "source_file": source_file,
                        "source_location": _source_location(text, function["start"], line_starts),
                        "provenance": "VERIFIED_CLIENT_CODE",
                    }
                )
        candidate = _formula_candidate(function)
        if candidate:
            candidate.update(
                {
                    "source_file": source_file,
                    "source_location": _source_location(text, function["start"], line_starts),
                    "confidence": candidate["confidence"],
                    "provenance": "VERIFIED_CLIENT_CODE",
                }
            )
            formulas.append(candidate)
    classes = sorted({safe_identifier(name, prefix="class") for name in _CLASS.findall(text)})
    globals_found = sorted({safe_identifier(name, prefix="global") for name in _GLOBAL.findall(text)})
    routes = sorted({endpoint_path(match.group(1)) for match in _ROUTE.finditer(text)})
    services = sorted({safe_identifier(name, prefix="service") for name in _SERVICE.findall(text)})
    rpc_methods = sorted({safe_identifier(name, prefix="method") for name in _RPC_LITERAL.findall(text)})
    for symbol in symbols:
        symbol["parameters"] = [safe_identifier(item, prefix="parameter") for item in symbol["parameters"]]
    for formula in formulas:
        formula["name"] = safe_identifier(formula["name"], prefix="function")
        formula["inputs"] = [safe_identifier(item, prefix="parameter") for item in formula["inputs"]]
    return {
        "source_file": source_file,
        "provenance": "VERIFIED_CLIENT_CODE",
        "functions": symbols,
        "classes": classes,
        "global_objects": globals_found,
        "route_builders": routes,
        "services": services,
        "rpc_methods": rpc_methods,
        "calculations": formulas,
        "calculation_review_candidates": calculation_review_candidates,
        "call_edges": call_edges,
    }


def analyze_javascript_file(path: str | Path, *, source_file: str = "client_asset_001.js") -> dict[str, Any]:
    return analyze_javascript(Path(path).read_text(encoding="utf-8", errors="replace"), source_file=source_file)


def summarize_javascript(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "format_version": 1,
        "provenance": "VERIFIED_CLIENT_CODE",
        "source_files": len(items),
        "function_count": sum(len(item["functions"]) for item in items),
        "functions": [function for item in items for function in item["functions"]],
        "classes": sorted({name for item in items for name in item["classes"]}),
        "global_objects": sorted({name for item in items for name in item["global_objects"]}),
        "route_builders": sorted({name for item in items for name in item["route_builders"]}),
        "services": sorted({name for item in items for name in item["services"]}),
        "rpc_methods": sorted({name for item in items for name in item["rpc_methods"]}),
        "call_edges": [edge for item in items for edge in item.get("call_edges", [])],
    }
