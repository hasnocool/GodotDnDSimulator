# tools/rules_importer/models.py
"""Typed data contracts for the SRD import pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

EntityStatus = Literal["executable", "data-only", "partial", "unsupported", "manual-review"]
BlockKind = Literal["heading", "paragraph", "list-item", "table-row"]


@dataclass(frozen=True, slots=True)
class SourcePolicy:
    source_id: str
    display_name: str
    document_version: str
    publisher: str
    landing_page_url: str
    download_url: str
    media_type: str
    license_id: str
    license_url: str
    official: bool
    allowed_for_ingestion: bool
    raw_redistribution: str
    expected_sha256: str | None = None


@dataclass(frozen=True, slots=True)
class SourceArtifact:
    source_id: str
    document_version: str
    license_id: str
    requested_url: str
    final_url: str
    retrieved_at: str
    sha256: str
    size_bytes: int
    media_type: str
    cache_path: str
    etag: str | None = None
    last_modified: str | None = None


@dataclass(frozen=True, slots=True)
class DocumentBlock:
    kind: BlockKind
    text: str
    page: int
    order: int
    level: int | None = None
    cells: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class NormalizedDocument:
    source: SourceArtifact
    blocks: tuple[DocumentBlock, ...]


@dataclass(frozen=True, slots=True)
class Provenance:
    source_id: str
    document_version: str
    license_id: str
    source_sha256: str
    page_start: int
    page_end: int
    section: str


@dataclass(frozen=True, slots=True)
class CanonicalEntity:
    entity_id: str
    kind: str
    name: str
    schema_version: int
    status: EntityStatus
    source_text: str
    provenance: Provenance
    mechanics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ImportReport:
    source_id: str
    source_sha256: str
    total_entities: int
    by_kind: dict[str, int]
    by_status: dict[str, int]
    unsupported_primitives: dict[str, int]
    canonical_sha256: str


@dataclass(frozen=True, slots=True)
class EntityDiff:
    added: tuple[str, ...]
    removed: tuple[str, ...]
    changed: tuple[str, ...]
    unchanged: tuple[str, ...]
    prose_only_changed: tuple[str, ...]
    mechanical_changed: tuple[str, ...]
