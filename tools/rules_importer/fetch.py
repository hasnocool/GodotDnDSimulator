# tools/rules_importer/fetch.py
"""Asynchronous, cache-aware retrieval for approved rules sources."""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlparse

import httpx

from .errors import SourceChangedError, SourcePolicyError
from .models import SourceArtifact, SourcePolicy
from .serialization import sha256_bytes
from .sources import validate_policy
from .version import IMPORTER_VERSION

_MAX_SOURCE_BYTES = 128 * 1024 * 1024


def _load_cached_manifest(path: Path) -> SourceArtifact | None:
    if not path.exists():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    try:
        return SourceArtifact(**raw)
    except (TypeError, ValueError):
        return None


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        handle.write(data)
        temp_name = handle.name
    os.replace(temp_name, path)


def _write_manifest(path: Path, artifact: SourceArtifact) -> None:
    payload = json.dumps(asdict(artifact), sort_keys=True, indent=2) + "\n"
    _atomic_write(path, payload.encode("utf-8"))


def _cached_artifact_is_valid(
    artifact: SourceArtifact,
    source_path: Path,
    policy: SourcePolicy,
) -> bool:
    if not source_path.exists():
        return False
    if (
        artifact.source_id != policy.source_id
        or artifact.document_version != policy.document_version
        or artifact.license_id != policy.license_id
        or artifact.requested_url != policy.download_url
        or artifact.media_type != policy.media_type
    ):
        return False
    if policy.expected_sha256 is not None and artifact.sha256 != policy.expected_sha256:
        return False
    data = source_path.read_bytes()
    return len(data) == artifact.size_bytes and sha256_bytes(data) == artifact.sha256


async def fetch_source(
    policy: SourcePolicy,
    cache_dir: Path,
    *,
    force: bool = False,
    timeout_seconds: float = 60.0,
    client: httpx.AsyncClient | None = None,
) -> SourceArtifact:
    """Fetch an allowlisted source without blocking the event loop on file operations."""

    validate_policy(policy)

    source_dir = cache_dir / policy.source_id
    source_path = source_dir / "source.pdf"
    manifest_path = source_dir / "source-manifest.json"
    cached = await asyncio.to_thread(_load_cached_manifest, manifest_path)

    if cached is not None and not force:
        valid = await asyncio.to_thread(_cached_artifact_is_valid, cached, source_path, policy)
        if valid:
            current = replace(cached, importer_version=IMPORTER_VERSION)
            if current != cached:
                await asyncio.to_thread(_write_manifest, manifest_path, current)
            return current

    headers: dict[str, str] = {}
    if cached is not None and cached.etag:
        headers["If-None-Match"] = cached.etag
    if cached is not None and cached.last_modified:
        headers["If-Modified-Since"] = cached.last_modified

    owns_client = client is None
    http = client or httpx.AsyncClient(follow_redirects=True, timeout=timeout_seconds)
    try:
        async with http.stream("GET", policy.download_url, headers=headers) as response:
            if response.status_code == 304:
                if cached is None:
                    raise SourcePolicyError("upstream returned 304 without a cached artifact")
                valid = await asyncio.to_thread(
                    _cached_artifact_is_valid, cached, source_path, policy
                )
                if not valid:
                    raise SourceChangedError(
                        "cached source failed checksum validation after HTTP 304"
                    )
                current = replace(cached, importer_version=IMPORTER_VERSION)
                if current != cached:
                    await asyncio.to_thread(_write_manifest, manifest_path, current)
                return current
            response.raise_for_status()
            final_url = urlparse(str(response.url))
            if final_url.scheme != "https" or final_url.hostname != "media.dndbeyond.com":
                raise SourcePolicyError("source redirect resolved to an unapproved host")
            content_type = response.headers.get("content-type", "").split(";", 1)[0].strip()
            if content_type and content_type != policy.media_type:
                raise SourcePolicyError(
                    f"unexpected media type for {policy.source_id}: {content_type!r}"
                )
            chunks: list[bytes] = []
            total = 0
            async for chunk in response.aiter_bytes():
                total += len(chunk)
                if total > _MAX_SOURCE_BYTES:
                    raise SourcePolicyError("source exceeds maximum allowed size")
                chunks.append(chunk)
            data = b"".join(chunks)
            if not data:
                raise SourcePolicyError("downloaded source is empty")
            digest = sha256_bytes(data)
            if policy.expected_sha256 is not None and digest != policy.expected_sha256:
                raise SourceChangedError(
                    f"source checksum changed: expected {policy.expected_sha256}, got {digest}"
                )
            artifact = SourceArtifact(
                source_id=policy.source_id,
                importer_version=IMPORTER_VERSION,
                document_version=policy.document_version,
                license_id=policy.license_id,
                requested_url=policy.download_url,
                final_url=str(response.url),
                retrieved_at=datetime.now(UTC).isoformat(),
                sha256=digest,
                size_bytes=len(data),
                media_type=policy.media_type,
                cache_path=str(source_path),
                etag=response.headers.get("etag"),
                last_modified=response.headers.get("last-modified"),
            )
            await asyncio.to_thread(_atomic_write, source_path, data)
            await asyncio.to_thread(_write_manifest, manifest_path, artifact)
            return artifact
    finally:
        if owns_client:
            await http.aclose()
