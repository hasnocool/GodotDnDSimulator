# tools/rules_importer/normalize.py
"""Deterministic normalization for extracted source blocks."""

from __future__ import annotations

import re
import unicodedata

from .models import DocumentBlock, NormalizedDocument, SourceArtifact

_SPACE_RE = re.compile(r"\s+")
_DICE_RE = re.compile(r"\b(\d+)\s*[dD]\s*(\d+)(?:\s*([+-])\s*(\d+))?\b")


def normalize_text(text: str) -> str:
    value = unicodedata.normalize("NFKC", text)
    value = value.replace("\u00a0", " ")
    return _SPACE_RE.sub(" ", value).strip()


def normalize_dice_notation(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        base = f"{match.group(1)}d{match.group(2)}"
        if match.group(3) and match.group(4):
            return f"{base}{match.group(3)}{match.group(4)}"
        return base

    return _DICE_RE.sub(repl, text)


def normalize_blocks(
    source: SourceArtifact,
    blocks: tuple[DocumentBlock, ...],
) -> NormalizedDocument:
    normalized: list[DocumentBlock] = []
    for block in blocks:
        text = normalize_dice_notation(normalize_text(block.text))
        cells = tuple(normalize_text(cell) for cell in block.cells)
        normalized.append(
            DocumentBlock(
                kind=block.kind,
                text=text,
                page=block.page,
                order=block.order,
                level=block.level,
                cells=cells,
            )
        )
    return NormalizedDocument(source=source, blocks=tuple(normalized))
