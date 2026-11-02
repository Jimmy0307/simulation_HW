"""Parse HAR and DevTools JSON without retaining headers, cookies, or values."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from marketplace_mcp.discovery.shapes import (
    endpoint_path,
    json_shape,
    method_classification,
    parse_json,
    rpc_method,
    service_from_url,
)
from marketplace_mcp.model.rpc import RPCObservation


def _body_text(body: Any) -> str | None:
    if isinstance(body, dict):
        text = body.get("text")
        if isinstance(text, str):
            return text
    if isinstance(body, str):
        return body
    return None


def _response_payload(entry: dict[str, Any]) -> Any | None:
    response = entry.get("response")
    if not isinstance(response, dict):
        return None
    content = response.get("content")
    text = _body_text(content)
    parsed = parse_json(text)
    if parsed is not None:
        return parsed
    # Chromium DevTools exports sometimes put a response body directly in a
    # custom field. Keep the same value-free shape rule.
    return response.get("_payload")


def _request_payload(request: dict[str, Any]) -> Any | None:
    post_data = request.get("postData")
    parsed = parse_json(_body_text(post_data))
    if parsed is not None:
        return parsed
    if isinstance(post_data, dict) and isinstance(post_data.get("params"), list):
        return post_data
    return None


def _initiator(entry: dict[str, Any]) -> dict[str, Any]:
    source = entry.get("_initiator") or entry.get("initiator")
    if not isinstance(source, dict):
        return {"kind": "unknown"}
    result: dict[str, Any] = {"kind": str(source.get("type", "unknown"))[:32]}
    stack = source.get("stack")
    frames = stack.get("callFrames") if isinstance(stack, dict) else None
    if isinstance(frames, list) and frames:
        call_stack = []
        for frame in frames[:8]:
            if not isinstance(frame, dict):
                continue
            frame_result: dict[str, Any] = {}
            url = frame.get("url")
            if isinstance(url, str):
                basename = Path(urlsplit(url).path).name[:96]
                match = re.fullmatch(r"(?i)(sstudent(?:-en-us)?|core|student|jquery(?:\.min)?)\.js(?:\..*)?", basename)
                frame_result["source_file"] = f"{match.group(1)}.js" if match else "script"
            for key in ("lineNumber", "columnNumber"):
                value = frame.get(key)
                if isinstance(value, int) and value >= 0:
                    frame_result[key] = value + 1
            if frame_result:
                call_stack.append(frame_result)
        if call_stack:
            result["call_stack"] = call_stack
            result.update(call_stack[0])
    return result


def _resource(entry: dict[str, Any], page_aliases: dict[str, str]) -> str:
    page_ref = entry.get("pageref")
    if page_ref is None:
        return "UNKNOWN"
    raw = str(page_ref)
    if raw not in page_aliases:
        page_aliases[raw] = f"page_{len(page_aliases) + 1}"
    return page_aliases[raw]


def _quarter(entry: dict[str, Any], page_quarters: dict[str, int | None] | None = None) -> int | None:
    fields = [entry.get("_resource"), entry.get("_quarter")]
    request = entry.get("request")
    if isinstance(request, dict):
        fields.append(request.get("url"))
    for field in fields:
        if isinstance(field, (str, int)):
            match = re.search(r"(?i)(?:quarter|\bq)\s*[-_: ]?\s*(\d{1,2})\b", str(field))
            if match:
                return int(match.group(1))
    page_ref = entry.get("pageref")
    if page_quarters and page_ref is not None:
        return page_quarters.get(str(page_ref))
    return None


def parse_har_object(document: dict[str, Any], *, evidence_ref: str = "capture_001") -> list[RPCObservation]:
    log = document.get("log", document)
    entries = log.get("entries", []) if isinstance(log, dict) else []
    if not isinstance(entries, list):
        return []
    observations: list[RPCObservation] = []
    page_aliases: dict[str, str] = {}
    page_quarters: dict[str, int | None] = {}
    pages = log.get("pages", []) if isinstance(log, dict) else []
    if isinstance(pages, list):
        for page in pages:
            if not isinstance(page, dict) or page.get("id") is None:
                continue
            raw_id = str(page["id"])
            page_aliases[raw_id] = f"page_{len(page_aliases) + 1}"
            title = page.get("title")
            match = re.search(r"(?i)(?:quarter|\bq)\s*[-_: ]?\s*(\d{1,2})\b", str(title)) if title is not None else None
            page_quarters[raw_id] = int(match.group(1)) if match else None
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        request = entry.get("request")
        if not isinstance(request, dict):
            continue
        url = request.get("url")
        if not isinstance(url, str):
            continue
        payload = _request_payload(request)
        method = rpc_method(payload)
        response_payload = _response_payload(entry)
        observations.append(
            RPCObservation(
                endpoint=endpoint_path(url),
                http_method=str(request.get("method", "UNKNOWN")).upper()[:16],
                service=service_from_url(url),
                rpc_method=method,
                parameter_shape=json_shape(payload),
                response_shape=json_shape(response_payload),
                initiator=_initiator(entry),
                resource=_resource(entry, page_aliases),
                quarter=_quarter(entry, page_quarters),
                classification=method_classification(method),
                evidence_ref=f"{evidence_ref}:entry_{index + 1}",
            )
        )
    return observations


def parse_har_file(path: str | Path, *, evidence_ref: str = "capture_001") -> list[RPCObservation]:
    document = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(document, dict):
        return []
    return parse_har_object(document, evidence_ref=evidence_ref)


def summarize_observations(observations: list[RPCObservation]) -> dict[str, Any]:
    counts = Counter((item.service or "UNKNOWN", item.rpc_method or "UNKNOWN") for item in observations)
    records = []
    for (service, method), count in sorted(counts.items()):
        examples = [item for item in observations if (item.service or "UNKNOWN", item.rpc_method or "UNKNOWN") == (service, method)]
        example = examples[0]
        parameter_shapes: list[dict[str, Any]] = []
        response_shapes: list[dict[str, Any]] = []
        for shape, bucket in ((item.parameter_shape, parameter_shapes) for item in examples):
            if shape is not None and shape not in bucket:
                bucket.append(shape)
        for shape in (item.response_shape for item in examples):
            if shape is not None and shape not in response_shapes:
                response_shapes.append(shape)
        records.append(
            {
                "service": service,
                "method": method,
                "endpoint": example.endpoint,
                "http_method": example.http_method,
                "parameter_shape": example.parameter_shape,
                "response_shape": example.response_shape,
                "parameter_shapes": parameter_shapes,
                "response_shapes": response_shapes,
                "classification": example.classification,
                "observed_count": count,
                "initiators": sorted({item.initiator.get("source_file", "unknown") for item in examples}),
                "resources": sorted({item.resource or "UNKNOWN" for item in examples}),
                "quarters": sorted({item.quarter for item in examples if item.quarter is not None}),
                "evidence_refs": [item.evidence_ref for item in examples],
                "provenance": "VERIFIED_NETWORK_TRACE",
            }
        )
    return {
        "format_version": 1,
        "observations": len(observations),
        "methods": records,
        "provenance": "VERIFIED_NETWORK_TRACE",
    }
