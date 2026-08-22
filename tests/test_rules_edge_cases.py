# tests/test_rules_edge_cases.py
from __future__ import annotations

import argparse
import hashlib
from dataclasses import replace
from pathlib import Path

import httpx
import pytest

from tools.rules_importer import cli, smoke
from tools.rules_importer.compile import compile_entities, slugify
from tools.rules_importer.errors import (
    CompilationError,
    ExtractionError,
    SourceChangedError,
    SourcePolicyError,
)
from tools.rules_importer.extract import _classify_line, _looks_like_heading, extract_pdf
from tools.rules_importer.fetch import fetch_source
from tools.rules_importer.models import (
    CanonicalEntity,
    DocumentBlock,
    NormalizedDocument,
    Provenance,
    SourceArtifact,
    SourcePolicy,
)
from tools.rules_importer.pipeline import build_from_artifact
from tools.rules_importer.reports import attribution_text, build_import_report
from tools.rules_importer.serialization import dumps_canonical
from tools.rules_importer.sources import SourceRegistry, validate_policy
from tools.rules_importer.validate import validate_entities

ROOT = Path(__file__).resolve().parents[1]
HASH = "a" * 64


def policy(**changes: object) -> SourcePolicy:
    base = SourcePolicy(
        source_id="wotc-srd-5.2.1-en",
        display_name="Fixture",
        document_version="5.2.1",
        publisher="Wizards of the Coast LLC",
        landing_page_url="https://www.dndbeyond.com/srd",
        download_url="https://media.dndbeyond.com/fixture.pdf",
        media_type="application/pdf",
        license_id="CC-BY-4.0",
        license_url="https://creativecommons.org/licenses/by/4.0/legalcode",
        official=True,
        allowed_for_ingestion=True,
        raw_redistribution="transient-cache-only",
        expected_sha256=HASH,
    )
    return replace(base, **changes)


def artifact(path: Path) -> SourceArtifact:
    return SourceArtifact(
        source_id="wotc-srd-5.2.1-en",
        importer_version="0.2.0",
        document_version="5.2.1",
        license_id="CC-BY-4.0",
        requested_url="https://media.dndbeyond.com/fixture.pdf",
        final_url="https://media.dndbeyond.com/fixture.pdf",
        retrieved_at="fixture",
        sha256=HASH,
        size_bytes=1,
        media_type="application/pdf",
        cache_path=str(path),
    )


def sample_entity(**changes: object) -> CanonicalEntity:
    base = CanonicalEntity(
        entity_id="srd5.2.1:rule:test:test",
        kind="rule",
        name="Test",
        schema_version=1,
        status="data-only",
        source_text="text",
        provenance=Provenance(
            source_id="wotc-srd-5.2.1-en",
            document_version="5.2.1",
            license_id="CC-BY-4.0",
            source_sha256=HASH,
            page_start=1,
            page_end=1,
            section="Test",
        ),
        mechanics={},
    )
    return replace(base, **changes)


@pytest.mark.parametrize(
    "candidate",
    [
        policy(allowed_for_ingestion=False),
        policy(official=False),
        policy(download_url="http://media.dndbeyond.com/fixture.pdf"),
        policy(landing_page_url="https://example.com/srd"),
        policy(license_id="OGL-1.0a"),
        policy(media_type="text/html"),
        policy(expected_sha256="abc"),
        policy(expected_sha256="z" * 64),
    ],
)
def test_source_policy_rejections(candidate: SourcePolicy) -> None:
    with pytest.raises(SourcePolicyError):
        validate_policy(candidate)


def test_registry_rejects_duplicates_and_malformed_files(tmp_path: Path) -> None:
    with pytest.raises(SourcePolicyError):
        SourceRegistry((policy(), policy()))
    malformed = tmp_path / "sources.json"
    malformed.write_text('{"schema_version": 9, "sources": []}', encoding="utf-8")
    with pytest.raises(SourcePolicyError):
        SourceRegistry.from_path(malformed)
    malformed.write_text(
        '{"schema_version": 1, "sources": [{"source_id": "x"}]}',
        encoding="utf-8",
    )
    with pytest.raises(SourcePolicyError):
        SourceRegistry.from_path(malformed)


@pytest.mark.asyncio
async def test_fetch_304_and_input_rejections(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = b"cached bytes"
    expected = replace(policy(), expected_sha256=hashlib.sha256(data).hexdigest())
    calls = 0

    async def cached(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(
                200,
                headers={"content-type": "application/pdf", "etag": "v1"},
                content=data,
                request=request,
            )
        return httpx.Response(304, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(cached)) as client:
        first = await fetch_source(expected, tmp_path, client=client)
        assert await fetch_source(expected, tmp_path, client=client, force=True) == first

    async def wrong_media(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            content=b"x",
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(wrong_media)) as client:
        with pytest.raises(SourcePolicyError):
            await fetch_source(
                replace(policy(), expected_sha256=None),
                tmp_path,
                client=client,
                force=True,
            )

    monkeypatch.setattr("tools.rules_importer.fetch._MAX_SOURCE_BYTES", 2)

    async def large(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/pdf"},
            content=b"123",
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(large)) as client:
        with pytest.raises(SourcePolicyError):
            await fetch_source(
                replace(policy(), expected_sha256=None),
                tmp_path,
                client=client,
                force=True,
            )


def test_extract_classifier_outline_and_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert _looks_like_heading("Rules Glossary")
    assert not _looks_like_heading("This is a sentence.")
    assert not _looks_like_heading("x" * 101)
    assert _classify_line("- item", 1, 1).kind == "list-item"
    assert _classify_line("A  B  C", 1, 2).kind == "table-row"

    class Destination:
        def __init__(self, title: object, page: int) -> None:
            self.title = title
            self.page = page

    class Page:
        def extract_text(self) -> str:
            return "Visible Heading\nbody text."

    visible = Destination("Visible Heading", 0)
    injected = Destination("Injected Bookmark", 0)

    class Reader:
        def __init__(self) -> None:
            self.pages = [Page()]
            self.outline = [visible, [injected]]

        @staticmethod
        def get_destination_page_number(item: Destination) -> int:
            return item.page

    monkeypatch.setattr("tools.rules_importer.extract.PdfReader", lambda path: Reader())
    pdf = tmp_path / "fixture.pdf"
    pdf.write_bytes(b"fixture")
    blocks = extract_pdf(pdf, artifact(pdf))
    headings = {block.text for block in blocks if block.kind == "heading"}
    assert {"Visible Heading", "Injected Bookmark"} <= headings

    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"not a pdf")
    monkeypatch.undo()
    with pytest.raises(ExtractionError):
        extract_pdf(bad, artifact(bad))
    with pytest.raises(ExtractionError):
        extract_pdf(bad, replace(artifact(bad), media_type="text/plain"))


def test_compile_validation_and_report_rejections(tmp_path: Path) -> None:
    with pytest.raises(CompilationError):
        slugify("!!!")
    document = NormalizedDocument(
        source=artifact(tmp_path / "x"),
        blocks=(DocumentBlock(kind="paragraph", text="no heading", page=1, order=1),),
    )
    with pytest.raises(CompilationError):
        compile_entities(document)
    with pytest.raises(CompilationError):
        validate_entities((sample_entity(), sample_entity()), ROOT / "schemas/rules/v1")
    with pytest.raises(CompilationError):
        validate_entities(
            (replace(sample_entity(), kind="future-kind"),),
            ROOT / "schemas/rules/v1",
        )
    with pytest.raises(ValueError):
        build_import_report(())
    mixed = replace(
        sample_entity(),
        provenance=replace(sample_entity().provenance, source_sha256="b" * 64),
    )
    with pytest.raises(ValueError):
        build_import_report((sample_entity(), mixed))
    with pytest.raises(ValueError):
        attribution_text(policy(source_id="other"))
    assert "entity_id" in dumps_canonical(sample_entity())


@pytest.mark.asyncio
async def test_pipeline_rejects_artifact_identity_mismatches(tmp_path: Path) -> None:
    registry = SourceRegistry((policy(),))
    base = artifact(tmp_path / "missing.pdf")
    kwargs = {
        "registry": registry,
        "source_id": "wotc-srd-5.2.1-en",
        "schema_dir": ROOT / "schemas/rules/v1",
        "output_dir": tmp_path / "out",
    }
    for bad in (
        replace(base, source_id="other"),
        replace(base, document_version="5.2.0"),
        replace(base, license_id="other"),
        replace(base, sha256="b" * 64),
    ):
        with pytest.raises((SourcePolicyError, SourceChangedError)):
            await build_from_artifact(artifact=bad, **kwargs)


@pytest.mark.asyncio
async def test_cli_dispatch_and_parser(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    parser = cli._parser()
    assert parser.parse_args(["fetch"]).source_id == "wotc-srd-5.2.1-en"
    registry_path = tmp_path / "sources.json"
    registry_path.write_text(
        (ROOT / "config/rules/sources.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    fake_artifact = artifact(tmp_path / "x.pdf")

    async def fake_fetch(*args: object, **kwargs: object) -> SourceArtifact:
        return fake_artifact

    async def fake_build(**kwargs: object) -> object:
        return build_import_report((sample_entity(),))

    monkeypatch.setattr(cli, "fetch_source", fake_fetch)
    monkeypatch.setattr(cli, "build_source", fake_build)
    fetch_args = argparse.Namespace(
        command="fetch",
        registry=registry_path,
        source_id="wotc-srd-5.2.1-en",
        cache_dir=tmp_path,
    )
    assert await cli._run(fetch_args) == 0
    assert "source_id" in capsys.readouterr().out
    build_args = argparse.Namespace(
        command="build",
        registry=registry_path,
        source_id="wotc-srd-5.2.1-en",
        cache_dir=tmp_path,
        schema_dir=ROOT / "schemas/rules/v1",
        output_dir=tmp_path / "out",
    )
    assert await cli._run(build_args) == 0
    assert "total_entities" in capsys.readouterr().out


def test_rules_importer_smoke_entrypoint() -> None:
    assert smoke.main() == 0
