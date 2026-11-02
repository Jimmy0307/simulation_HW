"""Small redaction primitives; public evidence exports omit observed values."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

_EMAIL = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
_BEARER = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]+=*")
_SENSITIVE_ASSIGNMENT = re.compile(
    r"(?i)(\b(?:cookie|set-cookie|authorization|x-xsrf-token|xsrf-token|csrf-token|"
    r"phpsessid|session(?:id)?|access_token|refresh_token|token)\b\s*[:=]\s*)"
    r"(?:\"[^\"]*\"|'[^']*'|[^\s,;]+)"
)
_LONG_ID = re.compile(r"\b(?=[A-Za-z0-9_-]{20,}\b)(?=[A-Za-z0-9_-]*\d)[A-Za-z0-9_-]+\b")


def redact_text(value: str) -> str:
    """Redact common private values before diagnostic text can be emitted."""
    value = _BEARER.sub("Bearer token_REDACTED", value)
    value = _SENSITIVE_ASSIGNMENT.sub(r"\1token_REDACTED", value)
    value = _EMAIL.sub("email_REDACTED", value)
    return _LONG_ID.sub("identifier_REDACTED", value)


def is_sensitive_key(key: object) -> bool:
    text = str(key)
    return bool(
        re.search(
            r"(?i)(cookie|authorization|xsrf|csrf|phpsessid|session|access.?token|refresh.?token)",
            text,
        )
        or re.fullmatch(r"(?i)(?:real)?(?:student|game|team|user|member)s?(?:id)?", text)
    )


def safe_shape(value: Any, *, depth: int = 0, max_depth: int = 5) -> Any:
    """Describe JSON structure without retaining any sample values."""
    if depth >= max_depth:
        return {"type": "truncated"}
    if isinstance(value, Mapping):
        properties: dict[str, Any] = {}
        for index, (key, child) in enumerate(value.items()):
            if index >= 64:
                properties["_additional_properties"] = {"type": "omitted"}
                break
            key_text = str(key)
            if is_sensitive_key(key_text):
                properties["_sensitive_field_redacted"] = {"type": type(child).__name__}
                continue
            if _EMAIL.search(key_text) or _LONG_ID.fullmatch(key_text):
                key_text = "_dynamic_key"
            properties[key_text] = safe_shape(child, depth=depth + 1, max_depth=max_depth)
        return {"type": "object", "properties": properties}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        item_shapes = [safe_shape(item, depth=depth + 1, max_depth=max_depth) for item in value[:3]]
        unique: list[Any] = []
        for item_shape in item_shapes:
            if item_shape not in unique:
                unique.append(item_shape)
        return {"type": "array", "items": unique or [{"type": "unknown"}]}
    if value is None:
        kind = "null"
    elif isinstance(value, bool):
        kind = "boolean"
    elif isinstance(value, (int, float)):
        kind = "number"
    elif isinstance(value, str):
        kind = "string"
    else:
        kind = "unknown"
    return {"type": kind}


def safe_identifier(value: str, *, prefix: str = "item") -> str:
    """Return a stable-looking placeholder without copying an identifier."""
    if _EMAIL.search(value) or _LONG_ID.fullmatch(value) or is_sensitive_key(value):
        return f"{prefix}_REDACTED"
    return re.sub(r"[^A-Za-z0-9_.:/-]+", "_", value)[:96]
