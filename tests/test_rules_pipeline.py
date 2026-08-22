# tests/test_rules_pipeline.py
from __future__ import annotations

import base64
import json
from dataclasses import replace
from pathlib import Path

import pytest

from tools.rules_importer.compile import compile_entities, slugify
from tools.rules_importer.diff import diff_entities
from tools.rules_importer.errors import SourceChangedError
from tools.rules_importer.extract import extract_pdf_async
from tools.rules_importer.models import SourceArtifact
from tools.rules_importer.normalize import normalize_blocks, normalize_dice_notation
from tools.rules_importer.pipeline import build_from_artifact
from tools.rules_importer.serialization import sha256_bytes
from tools.rules_importer.sources import SourceRegistry

ROOT = Path(__file__).resolve().parents[1]


def _fixture_artifact(tmp_path: Path) -> SourceArtifact:
    encoded = (ROOT / 'tests/fixtures/rules_importer/sample_pdf.b64').read_text().strip()
    data = base64.b64decode(encoded)
    path = tmp_path / 'fixture.pdf'
    path.write_bytes(data)
    return SourceArtifact(
        importer_version='0.2.0',
        source_id='wotc-srd-5.2.1-en',
        document_version='5.2.1',
        license_id='CC-BY-4.0',
        requested_url='https://media.dndbeyond.com/example.pdf',
        final_url='https://media.dndbeyond.com/example.pdf',
        retrieved_at='2026-08-21T00:00:00+00:00',
        sha256=sha256_bytes(data),
        size_bytes=len(data),
        media_type='application/pdf',
        cache_path=str(path),
    )


@pytest.mark.asyncio
async def test_pdf_extract_normalize_compile_is_deterministic(tmp_path: Path) -> None:
    artifact = _fixture_artifact(tmp_path)
    blocks = await extract_pdf_async(Path(artifact.cache_path), artifact)
    document = normalize_blocks(artifact, blocks)
    first = compile_entities(document)
    second = compile_entities(document)

    assert first == second
    assert any(entity.name == 'D20 Tests' for entity in first)
    assert any(entity.kind == 'spell' and entity.name == 'Fire Spark' for entity in first)
    assert '1d20+5' in '\n'.join(entity.source_text for entity in first)


def test_normalization_and_stable_slug() -> None:
    assert normalize_dice_notation('Roll 2 D 6 + 3 damage') == 'Roll 2d6+3 damage'
    assert slugify('D20 Tests!') == 'd20-tests'


@pytest.mark.asyncio
async def test_build_from_artifact_writes_valid_dataset(tmp_path: Path) -> None:
    artifact = _fixture_artifact(tmp_path)
    official = SourceRegistry.from_path(ROOT / 'config/rules/sources.json').require(
        'wotc-srd-5.2.1-en'
    )
    registry = SourceRegistry((replace(official, expected_sha256=artifact.sha256),))
    output = tmp_path / 'output'
    report = await build_from_artifact(
        registry=registry,
        source_id='wotc-srd-5.2.1-en',
        artifact=artifact,
        schema_dir=ROOT / 'schemas/rules/v1',
        output_dir=output,
    )
    entities = [json.loads(line) for line in (output / 'entities.jsonl').read_text().splitlines()]
    assert report.total_entities == len(entities)
    assert report.canonical_sha256
    assert (output / 'ATTRIBUTION.txt').exists()
    assert (output / 'import-report.json').exists()
    assert all(entity['provenance']['source_sha256'] == artifact.sha256 for entity in entities)


@pytest.mark.asyncio
async def test_diff_distinguishes_prose_and_mechanical_changes(tmp_path: Path) -> None:
    artifact = _fixture_artifact(tmp_path)
    blocks = await extract_pdf_async(Path(artifact.cache_path), artifact)
    original = compile_entities(normalize_blocks(artifact, blocks))
    first = original[0]
    prose = (replace(first, source_text=first.source_text + ' clarification.'), *original[1:])
    mechanical = (replace(first, mechanics={'unsupported': ['teleport']}), *original[1:])

    prose_diff = diff_entities(original, prose)
    mechanical_diff = diff_entities(original, mechanical)
    assert first.entity_id in prose_diff.prose_only_changed
    assert first.entity_id in mechanical_diff.mechanical_changed


@pytest.mark.asyncio
async def test_build_rejects_artifact_bytes_changed_after_manifest(tmp_path: Path) -> None:
    artifact = _fixture_artifact(tmp_path)
    official = SourceRegistry.from_path(ROOT / "config/rules/sources.json").require(
        "wotc-srd-5.2.1-en"
    )
    registry = SourceRegistry((replace(official, expected_sha256=artifact.sha256),))
    Path(artifact.cache_path).write_bytes(b"tampered")
    with pytest.raises(SourceChangedError, match="do not match the artifact manifest"):
        await build_from_artifact(
            registry=registry,
            source_id="wotc-srd-5.2.1-en",
            artifact=artifact,
            schema_dir=ROOT / "schemas/rules/v1",
            output_dir=tmp_path / "output",
        )
