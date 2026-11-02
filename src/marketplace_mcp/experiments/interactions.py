"""Generate pairwise experiment designs only from supported variables."""

from __future__ import annotations

from itertools import combinations

from marketplace_mcp.experiments.specification import DecisionVariable

_SUPPORTED_INTERACTIONS = {
    frozenset(("price", "advertising")),
    frozenset(("price", "brand")),
    frozenset(("advertising", "sales_coverage")),
    frozenset(("capacity", "demand")),
    frozenset(("compensation", "productivity")),
}


def supported_pairs(variables: list[DecisionVariable]) -> list[tuple[str, str]]:
    evidenced = {variable.name.casefold(): variable for variable in variables if variable.evidence and variable.provenance != "UNKNOWN"}
    pairs = []
    for left, right in combinations(sorted(evidenced), 2):
        normalized = frozenset((left.replace(" ", "_"), right.replace(" ", "_")))
        if normalized in _SUPPORTED_INTERACTIONS:
            pairs.append((left, right))
    return pairs
