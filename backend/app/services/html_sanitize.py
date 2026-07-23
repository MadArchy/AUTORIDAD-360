"""Sanitización de HTML editorial antes de persistir o publicar."""
from __future__ import annotations

import re
from html.parser import HTMLParser


_ALLOWED_TAGS = {
    "article",
    "p",
    "br",
    "h1",
    "h2",
    "h3",
    "h4",
    "ul",
    "ol",
    "li",
    "strong",
    "em",
    "b",
    "i",
    "blockquote",
    "a",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
}
_ALLOWED_ATTRS = {
    "a": {"href", "title", "rel", "target"},
    "blockquote": {"cite"},
    "article": {"data-generation"},
}
_SAFE_HREF = re.compile(r"^(https?://|/|#|mailto:)", re.I)


class _Sanitizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._out: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "iframe", "object", "embed", "link", "meta"}:
            self._skip_depth += 1
            return
        if self._skip_depth or tag not in _ALLOWED_TAGS:
            return
        allowed = _ALLOWED_ATTRS.get(tag, set())
        clean_attrs: list[str] = []
        for key, value in attrs:
            key_l = key.lower()
            if key_l.startswith("on") or key_l not in allowed:
                continue
            val = value or ""
            if key_l == "href" and not _SAFE_HREF.match(val.strip()):
                continue
            if key_l == "target" and val not in {"_blank", "_self"}:
                continue
            if key_l == "rel":
                val = "noopener noreferrer"
            clean_attrs.append(f'{key_l}="{_escape_attr(val)}"')
        if tag == "a" and not any(a.startswith("rel=") for a in clean_attrs):
            if any(a.startswith("href=") for a in clean_attrs):
                clean_attrs.append('rel="noopener noreferrer"')
        attr_str = (" " + " ".join(clean_attrs)) if clean_attrs else ""
        if tag == "br":
            self._out.append("<br />")
        else:
            self._out.append(f"<{tag}{attr_str}>")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "iframe", "object", "embed", "link", "meta"}:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth or tag not in _ALLOWED_TAGS or tag == "br":
            return
        self._out.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        self._out.append(_escape_text(data))

    def get_html(self) -> str:
        return "".join(self._out)


def _escape_text(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _escape_attr(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def sanitize_editorial_html(raw: str | None) -> str:
    if not raw:
        return ""
    parser = _Sanitizer()
    parser.feed(str(raw))
    parser.close()
    return parser.get_html().strip()
