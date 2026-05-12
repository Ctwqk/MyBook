"""Text normalization and body-character metrics for generation benchmarks."""
from __future__ import annotations

import re


_JSON_REMAINDER_RE = re.compile(r"^\s*[\{\[\]\",:]+|[\{\[\]\",:]+\s*$")
_TITLE_LINE_RE = re.compile(r"第[一二三四五六七八九十百千万\d]+章(?:[：:].*)?")
_META_LINE_RE = re.compile(
    r"^\s*(?:"
    r"章节标题|标题|摘要|大纲|钩子|正文|字数|元信息|JSON|提示词|"
    r"chapter|title|outline|summary|metadata|prompt"
    r")\s*[:：]",
    re.IGNORECASE,
)


def strip_non_body_text(text: str, title: str | None = None) -> str:
    """Remove obvious title, metadata, prompt, and JSON remnants before counting body chars."""
    if not text:
        return ""

    title_values = {value.strip() for value in [title] if value and value.strip()}
    lines: list[str] = []
    for raw_line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        normalized = line.strip("#*【】[]（）() -_")
        if normalized in title_values:
            continue
        if _TITLE_LINE_RE.fullmatch(normalized):
            continue
        if _META_LINE_RE.match(line):
            continue
        if line.startswith(("```", "<think", "</think", "<thinking", "</thinking")):
            continue
        lines.append(_JSON_REMAINDER_RE.sub("", line))

    return "\n".join(line for line in lines if line)


def count_chinese_body_chars(text: str, title: str | None = None) -> int:
    """Count Chinese CJK body characters after removing non-body scaffolding."""
    body = strip_non_body_text(text, title)
    return sum(1 for char in body if "\u4e00" <= char <= "\u9fff")


def tail_for_continuation(text: str, max_chars: int = 800) -> str:
    """Return a compact continuation anchor from the current generated body."""
    body = strip_non_body_text(text)
    if len(body) <= max_chars:
        return body
    return body[-max_chars:]
