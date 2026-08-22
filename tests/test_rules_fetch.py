# tests/test_rules_fetch.py
from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from tools.rules_importer.errors import SourceChangedError, SourcePolicyError
from tools.rules_importer.fetch import fetch_source
from tools.rules_importer.models import SourcePolicy
from tools.rules_importer.serialization import sha256_bytes


def policy_for(data: bytes) -> SourcePolicy:
    return SourcePolicy(
        source_id='wotc-srd-5.2.1-en',
        display_name='Fixture',
        document_version='5.2.1',
        publisher='Wizards of the Coast LLC',
        landing_page_url='https://www.dndbeyond.com/srd',
        download_url=(
            'https://media.dndbeyond.com/compendium-images/srd/5.2/SRD_CC_v5.2.1.pdf'
        ),
        media_type='application/pdf',
        license_id='CC-BY-4.0',
        license_url='https://creativecommons.org/licenses/by/4.0/legalcode',
        official=True,
        allowed_for_ingestion=True,
        raw_redistribution='transient-cache-only',
        expected_sha256=sha256_bytes(data),
    )


@pytest.mark.asyncio
async def test_fetch_source_is_cached_and_hash_verified(tmp_path: Path) -> None:
    data = b'%PDF fixture bytes'
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            headers={'content-type': 'application/pdf', 'etag': 'fixture-etag'},
            content=data,
            request=request,
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        first = await fetch_source(policy_for(data), tmp_path, client=client)
        second = await fetch_source(policy_for(data), tmp_path, client=client)

    assert first.sha256 == sha256_bytes(data)
    assert second == first
    assert calls == 1
    assert Path(first.cache_path).read_bytes() == data


@pytest.mark.asyncio
async def test_fetch_source_rejects_changed_pin(tmp_path: Path) -> None:
    data = b'changed source'
    policy = policy_for(b'expected source')

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={'content-type': 'application/pdf'},
            content=data,
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(SourceChangedError):
            await fetch_source(policy, tmp_path, client=client)


@pytest.mark.asyncio
async def test_fetch_rejects_unapproved_final_redirect(tmp_path: Path) -> None:
    data = b"%PDF fixture bytes"

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "media.dndbeyond.com":
            return httpx.Response(302, headers={"location": "https://example.com/source.pdf"})
        return httpx.Response(
            200,
            headers={"content-type": "application/pdf"},
            content=data,
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        follow_redirects=True,
    ) as client:
        with pytest.raises(SourcePolicyError, match="unapproved host"):
            await fetch_source(policy_for(data), tmp_path, client=client)


@pytest.mark.asyncio
async def test_fetch_does_not_trust_mismatched_cached_manifest(tmp_path: Path) -> None:
    data = b"%PDF fixture bytes"
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            headers={"content-type": "application/pdf"},
            content=data,
            request=request,
        )

    policy = policy_for(data)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        first = await fetch_source(policy, tmp_path, client=client)
        manifest = Path(first.cache_path).with_name("source-manifest.json")
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        payload["license_id"] = "wrong-license"
        manifest.write_text(json.dumps(payload), encoding="utf-8")
        second = await fetch_source(policy, tmp_path, client=client)

    assert second.license_id == "CC-BY-4.0"
    assert calls == 2
