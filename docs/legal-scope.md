# Scope and publication boundary

This repository is an **unofficial, independent** research and planning toolkit. It is not affiliated with, endorsed by
or connected to Marketplace Simulations, Innovative Learning Solutions, or any course provider. Product and company
names are used only to describe compatibility.

## What is public

* Generic code: the planning engine (`src/marketplace_sim`), REA-Evidence readers, the publication gate, tests.
* Structure only: schemas, field paths, types, units and evidence classes (`data/*.json`). These contain no values.
* Invented example data (`examples/`). Every name and number is made up and checked by the gate against private data.
* Method documentation: how evidence was gathered, how strong it is, and what is unknown.

## What is never public

Raw captures, page dumps, downloaded JavaScript/CSS/assets, screenshots, session material, team or account identifiers,
real parameter values, market-research data, competitor data, fitted models, private briefs and saves. All of these live
under git-ignored `evidence/private/` and are blocked by `scripts/publication_gate.py`.

## Users' responsibility

Anyone using this toolkit must obtain their data **themselves, from their own account, by legitimate means**, respect
the terms of their course and platform, and keep that data private. The toolkit does not bypass authentication, call
undocumented write endpoints, automate decisions in the live system, or submit quarters. Operator experiments use only
the client's own no-save calculation path, behind a guard that blocks `save` and submission, with teammate consent.

The repository makes no claim to recover the proprietary server algorithm. A client expression is described only as a
client expression. A server output is "verified" only within the measured range of the documented experiment. This
document describes the project's technical handling and is not a legal opinion.
