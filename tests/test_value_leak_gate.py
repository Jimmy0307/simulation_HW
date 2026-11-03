"""The value-leak checks must catch planted 'real' values. All data here is fake and created in tmp_path."""

from __future__ import annotations

import json
from pathlib import Path

from marketplace_sysid.security.value_leak import load_real_values, scan_paths


def _fake_private(tmp_path: Path) -> tuple[Path, Path]:
    values = tmp_path / "values.json"
    values.write_text(json.dumps({
        "Widget": {
            "staticData.options[*].cost": [0, 52341, 104682, 157023],
            "staticData.options[*].optionID": [1, 2, 3, 4],
            "staticData.taxRate": [37],
            "staticData.cash": [918273],
        }
    }), encoding="utf-8")
    pack = tmp_path / "pack.json"
    pack.write_text(json.dumps({
        "schema": "marketplace-sim/param-pack@1", "name": "ignored-root-name", "provenance": "private",
        "markets": [{"key": "M1", "name": "Planted Cityname", "segments": {"1": {"size_12m": 4711, "wtp": 873}}}],
        "segments": [{"id": "1", "name": "Segmentum", "needs": {"Planted need phrase": 101}}],
    }), encoding="utf-8")
    return values, pack


def _scan(tmp_path: Path, files: dict[str, str]) -> list[tuple[str, str]]:
    values, pack = _fake_private(tmp_path)
    root = tmp_path / "repo"
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    real = load_real_values(values, pack)
    return [(f.path, f.rule) for f in scan_paths(root, list(files), real)]


def test_sequence_of_three_real_table_values_is_blocked(tmp_path: Path) -> None:
    hits = _scan(tmp_path, {"docs/a.md": "options cost 52,341 then 104682 and 157023"})
    assert ("docs/a.md", "sequence") in hits


def test_identifier_and_numbering_sequences_are_not_blocked(tmp_path: Path) -> None:
    hits = _scan(tmp_path, {"docs/b.md": "steps 1 2 3 4 and rows 10 11 12"})
    assert hits == []


def test_keyed_scalar_needs_same_field_name_on_the_line(tmp_path: Path) -> None:
    hits = _scan(tmp_path, {"src/x.py": "TAX_RATE = 37\n", "src/y.py": "something = 37\n", "docs/z.md": "tax_rate is 12"})
    assert ("src/x.py", "keyed-scalar") in hits
    assert not any(path in {"src/y.py", "docs/z.md"} for path, _ in hits)


def test_examples_reject_real_values(tmp_path: Path) -> None:
    hits = _scan(tmp_path, {
        "examples/p/pack.json": json.dumps({"cash": 918273, "wtp": 873, "fine": 5}),
        "examples/p/ok.yaml": "cash: 918274\nwtp: 874\n",
    })
    rules = {(p, r) for p, r in hits}
    assert ("examples/p/pack.json", "example-real-value") in rules
    assert ("examples/p/pack.json", "example-keyed-value") in rules
    assert not any(p == "examples/p/ok.yaml" for p, _ in hits)


def test_real_names_are_blocked_but_root_pack_name_is_not(tmp_path: Path) -> None:
    hits = _scan(tmp_path, {"docs/n.md": "We open in Planted Cityname.", "docs/m.md": "ignored-root-name is fine",
                            "docs/k.md": "Planted need phrase"})
    assert ("docs/n.md", "real-name") in hits and ("docs/k.md", "real-name") in hits
    assert not any(path == "docs/m.md" for path, _ in hits)


def test_no_reference_data_means_no_findings(tmp_path: Path) -> None:
    real = load_real_values(tmp_path / "absent.json", tmp_path / "absent-pack.json")
    (tmp_path / "f.md").write_text("52341 104682 157023", encoding="utf-8")
    assert real.empty and scan_paths(tmp_path, ["f.md"], real) == []
