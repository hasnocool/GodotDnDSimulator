# tools/rules_importer/extract.py
"""PDF extraction into a provenance-preserving intermediate block stream."""

from __future__ import annotations

import asyncio
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from .errors import ExtractionError
from .models import DocumentBlock, SourceArtifact

_BULLET_RE = re.compile(r"^(?:[-•●▪]|\d+[.)])\s+")
_TABLE_SPLIT_RE = re.compile(r"\s{2,}")


def _normalized_match_text(value: str) -> str:
    return " ".join(value.casefold().split())


def _looks_like_heading(line: str) -> bool:
    if not line or len(line) > 100:
        return False
    words = line.split()
    if len(words) > 12:
        return False
    if line.endswith((".", ";", ":", "?", "!")):
        return False
    letters = [char for char in line if char.isalpha()]
    if not letters:
        return False
    upper_ratio = sum(char.isupper() for char in letters) / len(letters)
    title_ratio = sum(word[:1].isupper() for word in words) / max(1, len(words))
    return upper_ratio > 0.72 or title_ratio > 0.80


def _classify_line(
    line: str,
    page: int,
    order: int,
    *,
    outline_titles: set[str] | None = None,
) -> DocumentBlock:
    normalized = _normalized_match_text(line)
    if outline_titles and normalized in outline_titles:
        return DocumentBlock(kind="heading", text=line, page=page, order=order, level=1)
    if _BULLET_RE.match(line):
        return DocumentBlock(kind="list-item", text=line, page=page, order=order)
    cells = tuple(cell.strip() for cell in _TABLE_SPLIT_RE.split(line) if cell.strip())
    if len(cells) >= 3:
        return DocumentBlock(kind="table-row", text=line, page=page, order=order, cells=cells)
    if outline_titles is None and _looks_like_heading(line):
        return DocumentBlock(kind="heading", text=line, page=page, order=order, level=1)
    return DocumentBlock(kind="paragraph", text=line, page=page, order=order)


def _collect_outline(reader: PdfReader) -> dict[int, list[tuple[str, int]]]:
    by_page: dict[int, list[tuple[str, int]]] = defaultdict(list)

    def walk(items: list[Any], level: int) -> None:
        for item in items:
            if isinstance(item, list):
                walk(item, level + 1)
                continue
            title = getattr(item, "title", None)
            if not isinstance(title, str) or not title.strip():
                continue
            try:
                page_index = reader.get_destination_page_number(item)
            except Exception:
                continue
            if page_index is None or page_index < 0:
                continue
            if page_index >= 0:
                by_page[page_index + 1].append((" ".join(title.split()), level))

    try:
        outline = reader.outline
    except Exception:
        return {}
    if isinstance(outline, list):
        walk(outline, 1)
    return dict(by_page)


def extract_pdf(path: Path, artifact: SourceArtifact) -> tuple[DocumentBlock, ...]:
    if artifact.media_type != "application/pdf":
        raise ExtractionError("PDF extractor received a non-PDF artifact")
    try:
        reader = PdfReader(path)
    except Exception as exc:  # pypdf exposes multiple backend parse exceptions
        raise ExtractionError(f"unable to open PDF: {path}") from exc

    outline = _collect_outline(reader)
    blocks: list[DocumentBlock] = []
    order = 0
    for page_index, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception as exc:
            raise ExtractionError(f"unable to extract page {page_index}") from exc

        page_outline = outline.get(page_index, [])
        expected = {_normalized_match_text(title): (title, level) for title, level in page_outline}
        seen: set[str] = set()
        for raw_line in text.splitlines():
            line = " ".join(raw_line.split())
            if not line:
                continue
            normalized = _normalized_match_text(line)
            order += 1
            block = _classify_line(
                line,
                page_index,
                order,
                outline_titles=set(expected) if outline else None,
            )
            if block.kind == "heading" and normalized in expected:
                title, level = expected[normalized]
                block = DocumentBlock(
                    kind="heading",
                    text=title,
                    page=page_index,
                    order=order,
                    level=level,
                )
                seen.add(normalized)
            blocks.append(block)

        for normalized, (title, level) in expected.items():
            if normalized in seen:
                continue
            order += 1
            blocks.append(
                DocumentBlock(
                    kind="heading",
                    text=title,
                    page=page_index,
                    order=order,
                    level=level,
                )
            )

    blocks.sort(key=lambda block: (block.page, block.order))
    if not blocks:
        raise ExtractionError("PDF extraction produced no text blocks")
    return tuple(blocks)


async def extract_pdf_async(path: Path, artifact: SourceArtifact) -> tuple[DocumentBlock, ...]:
    return await asyncio.to_thread(extract_pdf, path, artifact)
