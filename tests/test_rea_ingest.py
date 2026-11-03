from __future__ import annotations

import hashlib
import json
from pathlib import Path

from marketplace_sysid.rea_ingest import (
    build_private_inventory,
    capture_rpc,
    classify_method,
    endpoint_literals,
    iter_module_sources,
    public_catalogs,
    top_level_members,
)

MODULE_A = (
    'function(){window.Widget=Decision.extend({sendCalculate:!1,'
    'read:function(){var d=this.data.decisions;d.price=this.value("price_1");d.open=this.value("open")},'
    'draw:function(){return this.com("iedit","price_1",1)+this.com("checkbox","open",!1)},'
    'observe:function(){this.bindCalculate("price_1","keyup",!0)},'
    'writeCalculate:function(){var c=this.data.calculate;j$("#t").html(c.total*65+"/x")}})}'
)
MODULE_B = 'function(){window.Report=Decision.extend({viewModeButtons:[],draw:function(){return this.data.dynamicData.sales}})}'
MODULE_C = 'function(){window.WidgetChild=Widget.extend()}'


def _module_node(key: str, path: str, text: str, start: int) -> dict[str, object]:
    return {
        "kind": "javascript-module",
        "node_id": f"jag_node_{key}",
        "identity": {"key": key},
        "observations": [{
            "properties": {"module_key": key, "source_sha256": hashlib.sha256(text.encode()).hexdigest()},
            "evidence": {"location": {"available": True, "value": {
                "source": path,
                "start": {"line": 1, "column": start},
                "end": {"line": 1, "column": start + len(text)},
            }}},
        }],
    }


def _write_fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    source_root = tmp_path / "app"
    source_root.mkdir()
    text = MODULE_A + ";" + MODULE_B + ";" + MODULE_C
    (source_root / "bundle.js").write_text(text, encoding="utf-8")
    b_start = len(MODULE_A) + 1
    c_start = b_start + len(MODULE_B) + 1
    nodes = [
        _module_node("1", "bundle.js", MODULE_A, 0),
        _module_node("2", "bundle.js", MODULE_B, b_start),
        _module_node("3", "bundle.js", MODULE_C, c_start),
        _module_node("bad", "bundle.js", "tampered", 0),
        {
            "kind": "endpoint",
            "node_id": "jag_node_ep",
            "identity": {"key": json.dumps(["literal", "saveThing"])},
            "observations": [{"evidence": {"location": {"available": True, "value": {
                "source": "bundle.js", "start": {"line": 1, "column": 5}, "end": {"line": 1, "column": 9}}}}}],
        },
    ]
    app_bundle = tmp_path / "app.bundle.json"
    app_bundle.write_text(json.dumps({"records": [{
        "evidence_id": "ev_app", "operation": "analyze_javascript_application",
        "normalized_result": {"graph": {"nodes": nodes}},
    }]}), encoding="utf-8")
    capture_bundle = tmp_path / "capture.bundle.json"
    capture_bundle.write_text(json.dumps({"records": [{
        "evidence_id": "ev_cap", "operation": "inspect_web_network_capture",
        "normalized_result": {"records": [
            {"ordinal": 0, "reported": {
                "request": {"method": "POST", "url": "https://example.test/mpl/backend-json.php?Widget",
                            "postData": {"text": json.dumps({"method": "view", "parameters": [{"studentID": 7}, True]})}},
                "response": {"content": {"text": json.dumps({"error": 0, "result": {
                    "decisions": {"price": 12.5}, "calculate": {"total": 99}}})}},
            }},
            {"ordinal": 1, "reported": {"request": {"method": "GET", "url": "https://example.test/a.png"}}},
        ]},
    }]}), encoding="utf-8")
    return capture_bundle, app_bundle, source_root


def test_module_slices_are_verified_against_rea_digest(tmp_path: Path) -> None:
    _, app_bundle, source_root = _write_fixture(tmp_path)
    record = json.loads(app_bundle.read_text())["records"][0]
    keys = sorted(module.module_key for module in iter_module_sources(record, source_root))
    assert keys == ["1", "2", "3"]
    assert endpoint_literals(record)[0]["name"] == "saveThing"


def test_inventory_and_public_catalogs_omit_values(tmp_path: Path) -> None:
    capture_bundle, app_bundle, source_root = _write_fixture(tmp_path)
    inventory = build_private_inventory(capture_bundle, app_bundle, source_root, None)
    widget = next(row for row in inventory["classes"] if row["name"] == "Widget")
    assert [field["field"] for field in widget["decision_fields"]] == ["open", "price"]
    assert widget["calculate_reads"] == ["total"]
    assert widget["calculate_bindings"][0]["id_prefix"] == "price_1"
    assert any("65" in item["expression"] for item in widget["arithmetic"])
    assert not any("/x" in item["expression"] for item in widget["arithmetic"])
    decisions, metrics, rpc = public_catalogs(inventory)
    names = {row["module"] for row in decisions["decisions"]}
    assert names == {"Widget", "WidgetChild"}
    child = next(row for row in decisions["decisions"] if row["module"] == "WidgetChild")
    assert {field["field"] for field in child["fields"]} == {"open", "price"}
    assert any(row["metric"] == "sales" and row["module"] == "Report" for row in metrics["metrics"])
    serialized = json.dumps([decisions, metrics, rpc])
    assert "12.5" not in serialized and "99" not in serialized
    assert '"studentID"' not in serialized
    assert rpc["observed_pairs"] == [{"service": "Widget", "method": "view", "observed_count": 1,
                                      "classification": "READ"}]


def test_capture_rpc_keeps_shapes_not_values(tmp_path: Path) -> None:
    capture_bundle, _, _ = _write_fixture(tmp_path)
    record = json.loads(capture_bundle.read_text())["records"][0]
    rows = capture_rpc(record)
    assert len(rows) == 1
    assert rows[0]["calculate_keys"] == ["total"]
    assert "12.5" not in json.dumps(rows)


def test_method_classification_is_conservative() -> None:
    assert classify_method("save") == "WRITE"
    assert classify_method("calculate") == "CALCULATION_TRIGGER"
    assert classify_method("saveOverlays") == "WRITE_CANDIDATE"
    assert classify_method("wrapupStatus") == "READ_CANDIDATE"
    assert classify_method("liveProForma") == "READ_CANDIDATE"
    assert classify_method("frobnicate") == "UNKNOWN"


def test_top_level_members_ignore_nested_and_string_keys() -> None:
    members = top_level_members('{a:1,b:function(){var x={c:2};return "d:3"},e:[1,2]}')
    assert sorted(members) == ["a", "b", "e"]
