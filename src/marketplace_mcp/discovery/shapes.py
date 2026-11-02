"""Helpers for value-free JSON and URL shape extraction."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import parse_qsl, urlsplit

from marketplace_mcp.security.redaction import safe_shape

_SERVICE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
_SAFE_ROUTE_SEGMENTS = {"mpl", "web7", "backend-json.php", "engine.php", "gengine.php"}
_SAFE_ASSET_EXTENSIONS = {"js", "mjs", "css", "png", "jpg", "jpeg", "gif", "svg", "woff", "woff2", "ttf"}


def parse_json(value: str | None) -> Any | None:
    if not value:
        return None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return None


def json_shape(value: Any) -> dict[str, Any] | None:
    return safe_shape(value) if value is not None else None


def endpoint_path(url: str) -> str:
    """Keep known route structure and replace all unrecognized path names."""
    parts = urlsplit(url)
    segments: list[str] = []
    for segment in parts.path.split("/"):
        lowered = segment.casefold()
        if not segment or lowered in _SAFE_ROUTE_SEGMENTS:
            segments.append(segment)
            continue
        suffix = segment.rsplit(".", 1)[-1].casefold() if "." in segment else ""
        segments.append(f":asset.{suffix}" if suffix in _SAFE_ASSET_EXTENSIONS else ":resource")
    path = "/".join(segments) or "/"
    service = service_from_url(url)
    return f"{path}?{service}" if service else path


def service_from_url(url: str) -> str | None:
    parts = urlsplit(url)
    query = parts.query
    if not query:
        return None
    if not parts.path.casefold().endswith("backend-json.php"):
        return None
    if "=" not in query:
        return query if "&" not in query and _SERVICE.fullmatch(query) else None
    pairs = parse_qsl(query, keep_blank_values=True)
    if pairs:
        for key, value in pairs:
            if key.casefold() == "service" and _SERVICE.fullmatch(value):
                return value
        return None
    return None


def rpc_method(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    candidate = payload.get("method") or payload.get("action")
    if isinstance(candidate, str) and candidate.casefold() not in {"gs", "call", "dispatch", "invoke"} and re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$.]{0,127}", candidate):
        return candidate
    # Some legacy dispatchers wrap a method name inside a generic `gs` call.
    params = payload.get("parameters")
    if isinstance(params, list):
        for item in params:
            if isinstance(item, str):
                match = re.search(r"\b([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)+)\s*\(", item)
                if match:
                    return match.group(1)
    if isinstance(candidate, str) and re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$.]{0,127}", candidate):
        return candidate
    return None


def method_classification(method: str | None) -> str:
    if not method:
        return "UNKNOWN"
    token = re.sub(r"[^a-z]", "", method.rsplit(".", 1)[-1].casefold())
    if any(word in token for word in ("finalize", "submit", "advancequarter", "endquarter")):
        return "FINALIZATION"
    if any(word in token for word in ("validate", "finalcheck", "checkdecision")):
        return "VALIDATION"
    if any(word in token for word in ("calculate", "recalculate", "forecast", "simulate", "score")):
        return "CALCULATION_TRIGGER"
    if any(word in token for word in ("track", "markseen", "markvisited", "state")):
        return "STATE_TRACKING"
    if any(word in token for word in ("view", "get", "list", "load", "show", "search", "find")):
        return "READ"
    if any(word in token for word in ("save", "update", "delete", "create", "insert", "write", "set")):
        return "WRITE"
    return "UNKNOWN"
