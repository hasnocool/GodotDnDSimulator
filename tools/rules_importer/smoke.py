# tools/rules_importer/smoke.py
"""Prove deterministic rules-import generation from the checked-in PDF fixture."""

from __future__ import annotations

import asyncio
import base64
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from .models import SourceArtifact
from .pipeline import build_from_artifact
from .serialization import sha256_bytes
from .sources import SourceRegistry
from .version import IMPORTER_VERSION

ROOT = Path(__file__).resolve().parents[2]
SOURCE_ID = "wotc-srd-5.2.1-en"


def _tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


async def _run() -> None:
    encoded = (ROOT / "tests/fixtures/rules_importer/sample_pdf.b64").read_text(
        encoding="utf-8"
    )
    source_bytes = base64.b64decode(encoded)
    digest = sha256_bytes(source_bytes)
    official = SourceRegistry.from_path(ROOT / "config/rules/sources.json").require(SOURCE_ID)
    fixture_policy = replace(official, expected_sha256=digest)
    registry = SourceRegistry((fixture_policy,))

    with TemporaryDirectory(prefix="godot-dnd-rules-") as temp:
        work = Path(temp)
        source_path = work / "fixture.pdf"
        source_path.write_bytes(source_bytes)
        artifact = SourceArtifact(
            source_id=SOURCE_ID,
            importer_version=IMPORTER_VERSION,
            document_version=fixture_policy.document_version,
            license_id=fixture_policy.license_id,
            requested_url=fixture_policy.download_url,
            final_url=fixture_policy.download_url,
            retrieved_at="fixture",
            sha256=digest,
            size_bytes=len(source_bytes),
            media_type=fixture_policy.media_type,
            cache_path=str(source_path),
        )
        first = work / "first"
        second = work / "second"
        first_report = await build_from_artifact(
            registry=registry,
            source_id=SOURCE_ID,
            artifact=artifact,
            schema_dir=ROOT / "schemas/rules/v1",
            output_dir=first,
        )
        second_report = await build_from_artifact(
            registry=registry,
            source_id=SOURCE_ID,
            artifact=artifact,
            schema_dir=ROOT / "schemas/rules/v1",
            output_dir=second,
        )
        if first_report != second_report or _tree_bytes(first) != _tree_bytes(second):
            raise SystemExit("rules importer output is not deterministic")
        print(
            "Rules importer deterministic smoke passed: "
            f"{first_report.total_entities} entities, "
            f"canonical SHA-256 {first_report.canonical_sha256}"
        )


def main() -> int:
    asyncio.run(_run())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
