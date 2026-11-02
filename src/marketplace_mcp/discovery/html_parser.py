"""Extract sanitized page, navigation, route and quarter structure from HTML."""

from __future__ import annotations

import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from marketplace_mcp.security.redaction import redact_text, safe_identifier

_QUARTER = re.compile(r"(?i)\b(?:quarter|q)\s*[-_: ]?\s*(\d{1,2})\b")
_PRIVATE_LABEL = re.compile(r"(?i)(?:@|\b(?:student|team\s*member|participant)\s+\d+\b|\b(?:game|team|student|user)[_-]?id\b)")
_SAFE_LABEL_WORDS = {
    "marketplace", "simulation", "customer", "needs", "market", "potential", "price", "willing",
    "pay", "segment", "segments", "marketing", "strategic", "strategy", "planning", "human",
    "resources", "sales", "channel", "manufacturing", "finance", "financial", "accounting",
    "summary", "of", "decision", "decisions", "final", "check", "submit", "quarter", "research",
    "brand", "product", "products", "capacity", "employee", "employees", "productivity", "report",
    "statement", "statements", "pro", "forma", "income", "balance", "cash", "profit", "revenue",
    "cost", "costs", "dashboard", "home", "settings", "status", "view", "select", "save", "next",
    "back", "help", "logout", "log", "in", "out", "overview", "operations", "people", "organization",
    "compensation", "benefits", "advertising", "promotion", "forecast", "demand", "salesforce", "factory",
    "production", "plan", "results", "performance", "scorecard", "index", "ratio", "unit", "units",
    "use", "pattern", "preferences", "willingness", "to", "about", "continue", "menu", "tab", "quarterly",
}


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title: list[str] = []
        self._title_depth = 0
        self._captures: list[tuple[str, int, list[str]]] = []
        self.elements: list[dict[str, Any]] = []
        self.scripts: list[str] = []
        self.stylesheets: list[str] = []
        self._stack: list[str] = []
        self.has_form = False
        self.has_input = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        self._stack.append(tag)
        if tag == "title":
            self._title_depth += 1
        if tag == "form":
            self.has_form = True
        if tag in {"input", "textarea", "select"}:
            self.has_input = True
        if tag == "script" and attributes.get("src"):
            self.scripts.append(str(attributes["src"]))
        if (
            tag == "link"
            and "stylesheet" in str(attributes.get("rel", "")).casefold()
            and attributes.get("href")
        ):
            self.stylesheets.append(str(attributes["href"]))
        if tag in {"a", "button", "li", "h1", "h2", "h3", "h4", "input"}:
            candidate_role = str(attributes.get("role", "")).casefold()
            role = candidate_role if candidate_role in {"tab", "menuitem", "button", "link", "navigation", "main", "treeitem", "presentation"} else ""
            element_index = len(self.elements)
            self.elements.append(
                {
                    "tag": tag,
                    "role": role[:24],
                    "href": attributes.get("href"),
                    "aria_label": attributes.get("aria-label"),
                    "title": attributes.get("title"),
                    "onclick": attributes.get("onclick"),
                    "data_resource": attributes.get("data-resource"),
                    "data_route": attributes.get("data-route"),
                    "depth": sum(1 for item in self._stack if item in {"ul", "ol"}),
                }
            )
            self._captures.append((tag, element_index, []))

    def handle_endtag(self, tag: str) -> None:
        if tag == "title" and self._title_depth:
            self._title_depth -= 1
        for index in range(len(self._captures) - 1, -1, -1):
            capture_tag, element_index, chunks = self._captures[index]
            if capture_tag == tag:
                self.elements[element_index]["text"] = " ".join(" ".join(chunks).split())[:160]
                del self._captures[index]
                break
        if self._stack:
            for index in range(len(self._stack) - 1, -1, -1):
                if self._stack[index] == tag:
                    del self._stack[index:]
                    break

    def handle_data(self, data: str) -> None:
        if self._title_depth:
            self.title.append(data)
        for _, _, chunks in self._captures:
            chunks.append(data)


def _safe_route(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    if value.startswith("javascript:"):
        route = re.search(r"(?:changeResource|load|play|setContent)\s*\(\s*['\"]([^'\"]+)", value)
        return f"javascript:{_safe_route(route.group(1))}" if route else "javascript:handler"
    parts = urlsplit(value)
    path = parts.path or value.split("?", 1)[0]
    segments = []
    for segment in path.split("/"):
        if not segment or segment.casefold() in {
            "mpl", "web7", "assets", "static", "resources", "js", "css",
            "engine.php", "gengine.php", "backend-json.php",
        }:
            segments.append(segment)
        else:
            segments.append(":resource")
    return safe_identifier("/".join(segments), prefix="route")


def _safe_label(value: str, *, max_chars: int = 120) -> str | None:
    text = redact_text(" ".join(value.split()))
    if not text or _PRIVATE_LABEL.search(text):
        return None
    words = [word.casefold() for word in re.findall(r"[A-Za-z]+", text)]
    if not words or len(words) > 8 or any(word not in _SAFE_LABEL_WORDS for word in words):
        return None
    return text[:max_chars]


def parse_html(text: str, *, source_file: str = "page_001.html", fallback_title: str | None = None) -> dict[str, Any]:
    parser = _PageParser()
    parser.feed(text)
    body = " ".join(parser.title)
    body_words = body.split()
    if len(body_words) % 2 == 0 and body_words[: len(body_words) // 2] == body_words[len(body_words) // 2 :]:
        body = " ".join(body_words[: len(body_words) // 2])
    quarter_match = _QUARTER.search(text)
    quarter = int(quarter_match.group(1)) if quarter_match else None
    sections: list[dict[str, Any]] = []
    for item in parser.elements:
        text_label = item.get("aria_label") or item.get("title") or item.get("text", "")
        text_label = _safe_label(str(text_label))
        if not text_label:
            continue
        route_source = item.get("href") or item.get("data_route") or item.get("onclick") or item.get("data_resource")
        sections.append(
            {
                "label": text_label[:120],
                "element": item["tag"],
                "role": item.get("role") or None,
                "route": _safe_route(str(route_source)) if route_source else None,
                "depth": item.get("depth", 0),
            }
        )
    # Preserve order but remove exact duplicate labels/routes from repeated responsive markup.
    unique: list[dict[str, Any]] = []
    seen: set[tuple[str, str | None]] = set()
    for item in sections:
        key = (item["label"], item["route"])
        if key not in seen:
            seen.add(key)
            unique.append(item)
    parent_stack: list[tuple[int, str]] = []
    for item in unique:
        depth = int(item.get("depth", 0))
        while parent_stack and parent_stack[-1][0] >= depth:
            parent_stack.pop()
        if item["element"] == "a":
            item["parent_element"] = parent_stack[-1][1] if parent_stack else None
            if depth > 0:
                parent_stack.append((depth, item["label"]))
        else:
            item["parent_element"] = None
    script_paths: list[str] = []
    for path in parser.scripts:
        parts = urlsplit(path)
        candidate = parts.path.rsplit("/", 1)[-1] or "script"
        candidate_low = candidate.casefold()
        if candidate_low.startswith("core.js"):
            candidate = "core.js"
        elif candidate_low.startswith("sstudent-en-us.js"):
            candidate = "sstudent-en-us.js"
        elif candidate_low.startswith("sstudent.js"):
            candidate = "sstudent.js"
        elif candidate_low.startswith("cdn-check.js"):
            candidate = "cdn-check.js"
        else:
            candidate = f"script_{len(script_paths) + 1}"
        script_paths.append(candidate[:120])
    stylesheet_paths: list[str] = [f"stylesheet_{index}" for index, _ in enumerate(parser.stylesheets, 1)]
    heading_count = sum(item["element"].startswith("h") for item in unique)
    has_decision_controls = parser.has_form or parser.has_input or any(
        item["element"] == "input" or (item["element"] == "button" and item["label"])
        for item in unique
    )
    page = {
        "resource": Path(source_file).stem,
        "title": _safe_label(body, max_chars=160) or (_safe_label(fallback_title, max_chars=160) if fallback_title else None),
        "parent": None,
        "quarter": quarter,
        "tabs": [item["label"] for item in unique if item["role"] == "tab"],
        "elements": unique,
        "decision_screen": bool(has_decision_controls),
        "heading_count": heading_count,
        "observed_services": [],
        "status": "VERIFIED_RENDERED_HTML",
        "provenance": "VERIFIED_RENDERED_HTML",
        "evidence_ref": source_file,
        "script_paths": sorted(set(script_paths)),
        "stylesheet_paths": sorted(set(stylesheet_paths)),
    }
    return page


def parse_html_file(path: str | Path, *, source_file: str = "page_001.html") -> dict[str, Any]:
    source = Path(path)
    return parse_html(
        source.read_text(encoding="utf-8", errors="replace"),
        source_file=source_file,
        fallback_title=source.stem,
    )


def summarize_pages(pages: list[dict[str, Any]]) -> dict[str, Any]:
    quarter_counts = Counter(str(page.get("quarter") or "UNKNOWN") for page in pages)
    all_scripts = sorted({script for page in pages for script in page.get("script_paths", [])})
    return {
        "format_version": 1,
        "provenance": "VERIFIED_RENDERED_HTML",
        "pages_observed": len(pages),
        "quarter_observations": dict(sorted(quarter_counts.items())),
        "scripts": all_scripts,
        "resources": pages,
    }
