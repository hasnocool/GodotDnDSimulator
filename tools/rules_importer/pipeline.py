# tools/rules_importer/pipeline.py
"""End-to-end deterministic build orchestration for an approved SRD source."""

from __future__ import annotations

import asyncio
from pathlib import Path
from urllib.parse import urlparse

from .compile import compile_entities
from .errors import SourceChangedError, SourcePolicyError
from .extract import extract_pdf_async
from .fetch import fetch_source
from .models import ImportReport, SourceArtifact
from .normalize import normalize_blocks
from .reports import build_import_report, write_dataset
from .serialization import sha256_bytes
from .sources import SourceRegistry
from .validate import validate_entities


def _verify_artifact_file(artifact: SourceArtifact) -> None:
    path = Path(artifact.cache_path)
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise SourceChangedError(f"unable to read cached source artifact: {path}") from exc
    if len(data) != artifact.size_bytes or sha256_bytes(data) != artifact.sha256:
        raise SourceChangedError("cached source bytes do not match the artifact manifest")


def _validate_artifact_policy(
    artifact: SourceArtifact,
    registry: SourceRegistry,
    source_id: str,
) -> None:
    policy = registry.require(source_id)
    if artifact.source_id != policy.source_id:
        raise SourcePolicyError("artifact source_id does not match requested policy")
    if artifact.document_version != policy.document_version:
        raise SourcePolicyError("artifact document version does not match source policy")
    if artifact.license_id != policy.license_id:
        raise SourcePolicyError("artifact license does not match source policy")
    if artifact.requested_url != policy.download_url:
        raise SourcePolicyError("artifact requested URL does not match source policy")
    if artifact.media_type != policy.media_type:
        raise SourcePolicyError("artifact media type does not match source policy")
    if artifact.size_bytes < 1:
        raise SourcePolicyError("artifact size must be at least one byte")

    final_url = urlparse(artifact.final_url)
    if final_url.scheme != "https" or final_url.hostname != "media.dndbeyond.com":
        raise SourcePolicyError("artifact final URL resolved to an unapproved host")
    if policy.expected_sha256 is not None and artifact.sha256 != policy.expected_sha256:
        raise SourceChangedError(
            f"artifact checksum does not match pinned source: {artifact.sha256}"
        )


async def build_from_artifact(
    *,
    registry: SourceRegistry,
    source_id: str,
    artifact: SourceArtifact,
    schema_dir: Path,
    output_dir: Path,
) -> ImportReport:
    policy = registry.require(source_id)
    _validate_artifact_policy(artifact, registry, source_id)
    await asyncio.to_thread(_verify_artifact_file, artifact)

    blocks = await extract_pdf_async(Path(artifact.cache_path), artifact)
    document = await asyncio.to_thread(normalize_blocks, artifact, blocks)
    entities = await asyncio.to_thread(compile_entities, document)
    await asyncio.to_thread(validate_entities, entities, schema_dir)
    report = await asyncio.to_thread(build_import_report, entities)
    await asyncio.to_thread(write_dataset, output_dir, entities, report, policy)
    return report


async def build_source(
    *,
    registry: SourceRegistry,
    source_id: str,
    cache_dir: Path,
    schema_dir: Path,
    output_dir: Path,
) -> ImportReport:
    policy = registry.require(source_id)
    artifact = await fetch_source(policy, cache_dir)
    return await build_from_artifact(
        registry=registry,
        source_id=source_id,
        artifact=artifact,
        schema_dir=schema_dir,
        output_dir=output_dir,
    )
