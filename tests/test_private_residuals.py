"""Private regression: engine VERIFIED modules vs measured server results. Skipped unless private evidence exists.

Reads only files under evidence/private (never committed). Asserts zero residual; prints no values.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from marketplace_sim import modules as m
from marketplace_sim.pack import load_pack

P = Path(__file__).parents[1] / "evidence" / "private"
NEEDED = [P / "model" / "pack.json", P / "exp-01" / "experiment_values.json", P / "exp-02" / "experiment_values.json",
          P / "auto" / "exp03_rows.json", P / "auto" / "exp04_rows.json"]
pytestmark = pytest.mark.skipif(not all(p.exists() for p in NEEDED), reason="private evidence not present")


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def test_cd_matches_exp01() -> None:
    pack = load_pack(P / "model")
    rows = [r for r in _load(P / "exp-01" / "experiment_values.json") if r["method"] == "calculate" and r["check_ok"]]
    assert rows
    for row in rows:
        cd, interest = m.cd_quarter(pack, 0.0, row["decisions_sent"]["deposit"], row["decisions_sent"]["withdraw"])
        assert cd.value == row["calculate_result"]["cd"]
        assert interest.value == pytest.approx(row["calculate_result"]["interest"], abs=0)


def test_capacity_matches_exp02() -> None:
    pack = load_pack(P / "model")
    rows = [r for r in _load(P / "exp-02" / "experiment_values.json") if r["method"] == "calculate"]
    assert len(rows) >= 9
    for row in rows:
        assert m.capacity_purchase(pack, row["decisions_sent"]["increase"]).value == row["calculate_result"]["total"]


@pytest.mark.parametrize(("rows_file", "attr"), [("exp03_rows.json", "stores"), ("exp04_rows.json", "web_centers")])
def test_opening_matches_exp11_exp12(rows_file: str, attr: str) -> None:
    pack = load_pack(P / "model")
    outlets = getattr(pack, attr)
    for row in _load(P / "auto" / rows_file):
        keys = [f"R{k[0]}-C{k[1]}" if isinstance(k, list) else f"R{k}" for k in row["on"]]
        assert m.opening_cost(outlets, keys, set(), attr).value == row["calc"]["total"]
