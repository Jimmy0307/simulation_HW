# Contributing

Contributions should preserve the boundary between observed facts, inferences, and unknowns. Add provenance and confidence when adding an assertion; prefer synthetic fixtures with the same shape as observed data and never paste Marketplace content into tests.

Run the local checks before proposing a change:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\ruff.exe check src tests scripts
.\.venv\Scripts\mypy.exe src
.\.venv\Scripts\python.exe scripts\publication_gate.py
```

Do not add automated write or final-submit behavior. Protocol changes should be backed by a sanitized schema and a local synthetic test.
