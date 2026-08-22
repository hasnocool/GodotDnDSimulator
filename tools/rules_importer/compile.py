# tools/rules_importer/compile.py
"""Compile normalized SRD blocks into deterministic canonical entities."""

from __future__ import annotations

import re

from .errors import CompilationError
from .models import CanonicalEntity, NormalizedDocument, Provenance

_SLUG_RE = re.compile(r"[^a-z0-9]+")

_SECTION_KIND: tuple[tuple[str, str], ...] = (
    ("classes", "character-option"),
    ("character origins", "character-option"),
    ("background", "character-option"),
    ("species", "character-option"),
    ("feats", "character-option"),
    ("spells", "spell"),
    ("equipment", "item"),
    ("magic items", "item"),
    ("monsters", "creature"),
    ("animals", "creature"),
    ("rules glossary", "rule"),
    ("playing the game", "rule"),
    ("gameplay toolbox", "rule"),
)


def slugify(value: str) -> str:
    slug = _SLUG_RE.sub("-", value.casefold()).strip("-")
    if not slug:
        raise CompilationError("cannot create stable ID from empty heading")
    return slug


def _kind_for(section: str, name: str) -> str:
    combined = f"{section} {name}".casefold()
    for marker, kind in _SECTION_KIND:
        if marker in combined:
            return kind
    if "action" in name.casefold() or "reaction" in name.casefold():
        return "action"
    if any(word in name.casefold() for word in ("condition", "effect", "modifier", "resource")):
        return "condition-effect"
    if any(word in name.casefold() for word in ("movement", "vision", "sense", "terrain")):
        return "spatial-primitive"
    return "rule"


def compile_entities(document: NormalizedDocument) -> tuple[CanonicalEntity, ...]:
    blocks = document.blocks
    headings = [index for index, block in enumerate(blocks) if block.kind == "heading"]
    if not headings:
        raise CompilationError("normalized document contains no headings")
    entities: list[CanonicalEntity] = []
    current_section = "Document"
    used_ids: set[str] = set()

    for position, index in enumerate(headings):
        heading = blocks[index]
        next_index = headings[position + 1] if position + 1 < len(headings) else len(blocks)
        body_blocks = blocks[index + 1 : next_index]
        if heading.text.casefold() in {
            "playing the game",
            "character creation",
            "classes",
            "character origins",
            "feats",
            "equipment",
            "spells",
            "rules glossary",
            "gameplay toolbox",
            "magic items",
            "monsters",
            "animals",
        }:
            current_section = heading.text
        body = "\n".join(block.text for block in body_blocks).strip()
        kind = _kind_for(current_section, heading.text)
        entity_id = f"srd5.2.1:{kind}:{slugify(current_section)}:{slugify(heading.text)}"
        if entity_id in used_ids:
            raise CompilationError(
                f"stable ID collision requires a richer heading context: {entity_id}"
            )
        used_ids.add(entity_id)
        page_end = max([heading.page, *(block.page for block in body_blocks)])
        entities.append(
            CanonicalEntity(
                entity_id=entity_id,
                kind=kind,
                name=heading.text,
                schema_version=1,
                status="data-only",
                source_text=body,
                provenance=Provenance(
                    source_id=document.source.source_id,
                    document_version=document.source.document_version,
                    license_id=document.source.license_id,
                    source_sha256=document.source.sha256,
                    page_start=heading.page,
                    page_end=page_end,
                    section=current_section,
                ),
                mechanics={},
            )
        )
    return tuple(sorted(entities, key=lambda entity: entity.entity_id))
