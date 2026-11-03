"""Extract model parameters from REA Evidence of ``view``/``calculate`` responses.

Reads two REA Evidence kinds (no HAR or JavaScript parsing here):

* ``inspect_web_network_capture`` records (HAR), via their retained request/response bodies;
* ``capture_browser_scenario`` records, via their ``network-content`` events.

Every numeric or boolean leaf of a response ``result`` is generalized over array indices (``a[*].b``) and
classified as ``parameter_table``, ``parameter``, ``state_value``, ``result_value``, ``decision``,
``identifier`` or ``protocol``. The public catalog holds paths, types, units and classes only. Values are
written separately and must stay under ``evidence/private``.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from marketplace_sysid.rea_ingest import JSON, _decode_scenario_body, find_record, load_bundle

_ID_KEY = re.compile(r"(?i)(^id$|ID$|Id$|^optionID$)")
_TABLE_KEY = re.compile(r"(?i)(cost|price|rate|units|machines|size|salary|pension|insurance|vacation|lease|setup|"
                        r"investment|percent|weeks|value|quarters|importance|total)")
_SCALAR_PARAM_KEY = re.compile(r"(?i)(rate|tax|percent|^min|^max|Min$|Max$|warn|importance|fill|^quarters$)")
_UNITS = (
    (re.compile(r"(?i)(length|textsize)"), "characters"),
    (re.compile(r"(?i)(rate|tax|percent|productivity)"), "percent"),
    (re.compile(r"(?i)(cost|price|cash|salary|investment|equity|earnings|lease|setup|dividend|pension|"
                r"insurance|total|expansion|acquirement|interest|^cd$|deposit|withdraw|stock|budget)"), "currency"),
    (re.compile(r"(?i)(units|capacity|demand)"), "units"),
    (re.compile(r"(?i)(machines|shares|count|people|^sf$|support)"), "count"),
    (re.compile(r"(?i)weeks"), "weeks"),
    (re.compile(r"(?i)(quarter|fill)"), "quarters"),
    (re.compile(r"(?i)size"), "units_market"),
)


@dataclass(frozen=True)
class Response:
    service: str
    method: str | None
    result: Any
    source: str


def _service(url: str) -> str:
    return urlsplit(url).query.split("&")[0]


def responses_from_capture(record: JSON, source: str = "har") -> Iterator[Response]:
    for item in record["normalized_result"]["records"]:
        request = item.get("reported", {}).get("request", {})
        url = str(request.get("url", ""))
        if "backend-json.php" not in url:
            continue
        try:
            body = json.loads(request.get("postData", {}).get("text") or "{}")
            payload = json.loads(item["reported"]["response"]["content"].get("text") or "{}")
        except (ValueError, KeyError, AttributeError):
            continue
        if isinstance(payload, dict):
            yield Response(_service(url), body.get("method") if isinstance(body, dict) else None,
                           payload.get("result"), source)


def responses_from_scenario(record: JSON, source: str = "scenario") -> Iterator[Response]:
    events = record["normalized_result"]["events"]["items"]
    urls = {e["transaction_id"]: e["url"]["url"] for e in events if e.get("kind") == "request"}
    requests: dict[str, Any] = {}
    for event in events:
        if event.get("kind") == "network-content" and event.get("phase") == "request":
            requests[event["transaction_id"]] = _decode_scenario_body(event.get("body", {})) or {}
    for event in events:
        if event.get("kind") != "network-content" or event.get("phase") != "response":
            continue
        url = urls.get(event["transaction_id"], "")
        if "backend-json.php" not in url:
            continue
        payload = _decode_scenario_body(event.get("body", {}))
        if isinstance(payload, dict):
            request = requests.get(event["transaction_id"]) or {}
            yield Response(_service(url), request.get("method") if isinstance(request, dict) else None,
                           payload.get("result"), source)


def _leaves(value: Any, path: str = "") -> Iterator[tuple[str, str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _leaves(child, f"{path}.{key}" if path else str(key))
    elif isinstance(value, list):
        for child in value:
            yield from _leaves(child, f"{path}[*]")
    elif isinstance(value, bool):
        yield path, "boolean", value
    elif isinstance(value, (int, float)):
        yield path, "number", value


_PRESENTATION = re.compile(r"(?i)(chartTemplate|legend|\.css|maxWidth|height|width|barTemplate|pieTemplate)")
_EMBEDDED = re.compile(r"\.data\.(?=(staticData|dynamicData|decisions|calculate)\b)")


def classify(path: str) -> str:
    if _PRESENTATION.search(path):
        return "presentation"
    embedded = _EMBEDDED.search(path)
    if embedded:  # e.g. SummaryOfDecisions embeds other screens' {staticData, decisions, calculate}
        return classify(path[embedded.end():])
    section = path.split(".", 1)[0].split("[", 1)[0]
    key = re.split(r"[.\[\]*]+", path.rstrip("]*"))[-1] or path
    if section in {"checkResult", "lock", "modifyResult", "saveResult", "errors", "commonData", "shareContent"}:
        return "protocol"
    if re.search(r"sections\[\*\]\.items\[\*\]\.quarters", path):
        return "state_value"  # financial statement cells
    if section == "decisions":
        return "decision"
    if section in {"calculate", "calculateResult"}:
        return "identifier" if _ID_KEY.search(key) else "result_value"
    if _ID_KEY.search(key):
        return "identifier"
    if "[*]" in path and _TABLE_KEY.search(key):
        return "parameter_table"
    if _SCALAR_PARAM_KEY.search(key):
        return "parameter"
    return "state_value"


def unit_of(path: str) -> str:
    key = re.split(r"[.\[\]*]+", path.rstrip("]*"))[-1] or path
    for pattern, unit in _UNITS:
        if pattern.search(key):
            return unit
    return "unknown"


def build_catalog(responses: Iterable[Response]) -> tuple[JSON, JSON]:
    """Return (public catalog without values, private values keyed by service and path)."""
    public: dict[tuple[str, str], JSON] = {}
    private: dict[str, dict[str, list[Any]]] = defaultdict(lambda: defaultdict(list))
    for response in responses:
        if not isinstance(response.result, dict):
            continue
        for path, kind, value in _leaves(response.result):
            cls = classify(path)
            if cls in {"protocol", "presentation"}:
                continue
            entry = public.setdefault((response.service, path), {
                "service": response.service, "path": path, "type": kind, "unit": unit_of(path), "class": cls,
                "methods": [], "sources": [], "observations": 0,
            })
            if response.method and response.method not in entry["methods"]:
                entry["methods"].append(response.method)
            source_kind = "har" if response.source == "har" else "scenario"
            if source_kind not in entry["sources"]:
                entry["sources"].append(source_kind)
            entry["observations"] += 1
            bucket = private[response.service][path]
            if len(bucket) < 200 and value not in bucket:
                bucket.append(value)
    rows = sorted(public.values(), key=lambda r: (r["service"], r["class"], r["path"]))
    for row in rows:
        row["methods"].sort()
        row["sources"].sort()
    catalog = {"schema": "marketplace-sysid/parameter-catalog@1", "values_included": False,
               "classes": ["parameter_table", "parameter", "state_value", "result_value", "decision", "identifier"],
               "fields": rows}
    values = {service: dict(paths) for service, paths in private.items()}
    return catalog, values


def collect(capture_bundles: Iterable[Path], scenario_files: Iterable[Path]) -> list[Response]:
    found: list[Response] = []
    for bundle_path in capture_bundles:
        record = find_record(load_bundle(bundle_path), "inspect_web_network_capture")
        found.extend(responses_from_capture(record))
    for scenario_path in scenario_files:
        try:
            data = json.loads(scenario_path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        result = data.get("normalized_result") if isinstance(data, dict) else None
        if isinstance(result, dict) and "events" in result and "steps" in result:
            found.extend(responses_from_scenario(data, scenario_path.name))
    return found


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--capture-bundle", type=Path, action="append", default=[])
    parser.add_argument("--scenario-glob", action="append", default=[], help="glob for REA scenario Evidence JSON")
    parser.add_argument("--private-out", type=Path, required=True)
    parser.add_argument("--public-out", type=Path, required=True)
    args = parser.parse_args()
    if "private" not in args.private_out.resolve().as_posix().split("/"):
        raise SystemExit("--private-out must be inside a 'private' directory")
    scenario_files = sorted({p for pattern in args.scenario_glob for p in Path().glob(pattern)})
    catalog, values = build_catalog(collect(args.capture_bundle, scenario_files))
    args.private_out.mkdir(parents=True, exist_ok=True)
    (args.private_out / "values.json").write_text(json.dumps(values, indent=1), encoding="utf-8")
    args.public_out.write_text(json.dumps(catalog, indent=1) + "\n", encoding="utf-8")
    counts: dict[str, int] = defaultdict(int)
    for row in catalog["fields"]:
        counts[row["class"]] += 1
    print(json.dumps({"fields": len(catalog["fields"]), "services": len(values), "by_class": counts}))


if __name__ == "__main__":
    main()
