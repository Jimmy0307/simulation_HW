"""Privacy audit for local evidence; output counts and aliases only."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

PATTERNS = {
    "sensitive_markers": re.compile(r"(?i)\b(cookie|set-cookie|authorization|xsrf|csrf|phpsessid|session(?:id)?|token)\b"),
    "credential_assignments": re.compile(
        r"(?i)[\"']?(cookie|set-cookie|authorization|x-xsrf-token|xsrf-token|csrf-token|phpsessid|session(?:id)?|token)[\"']?\s*[:=]\s*[\"'][^\"']{3,}[\"']"
    ),
    "email_addresses": re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"),
    "id_assignments": re.compile(r"(?i)[\"']?(student|game|team|user)(?:id)?[\"']?\s*[:=]\s*[\"'][^\"']{2,}[\"']"),
}
TEXT_EXTENSIONS = {".html", ".htm", ".js", ".mjs", ".css", ".json", ".har", ".devtools", ".xml", ".md", ".txt", ".py", ".csv", ".下載", ".download"}


def scan_evidence(root: Path) -> dict[str, Any]:
    files = [path for path in root.rglob("*") if path.is_file()]
    text_files = [path for path in files if path.suffix.casefold() in TEXT_EXTENSIONS]
    totals: Counter[str] = Counter()
    files_with_findings = 0
    for path in text_files:
        try:
            text = path.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            continue
        local = {name: len(pattern.findall(text)) for name, pattern in PATTERNS.items()}
        if any(local.values()):
            files_with_findings += 1
        totals.update(local)
    extensions = Counter(path.suffix.casefold() or "[no extension]" for path in files)
    return {
        "files": len(files),
        "text_files_scanned": len(text_files),
        "files_with_findings": files_with_findings,
        "finding_counts": dict(sorted(totals.items())),
        "extensions": dict(sorted(extensions.items())),
        "raw_values_printed": False,
        "interpretation": "Pattern counts are candidate markers and may include source-code field names; inspect only inside the private evidence directory.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path("evidence/private"))
    args = parser.parse_args()
    print(json.dumps(scan_evidence(args.root), ensure_ascii=False))


if __name__ == "__main__":
    main()
