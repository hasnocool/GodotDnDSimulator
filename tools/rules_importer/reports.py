# tools/rules_importer/reports.py
"""Deterministic dataset, coverage, attribution, and unsupported-mechanic reports."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from .models import CanonicalEntity, ImportReport, SourcePolicy
from .serialization import dumps_canonical, sha256_text, write_canonical_json

_ATTRIBUTION = (
    'This work includes material from the System Reference Document 5.2.1 ("SRD 5.2.1") '
    "by Wizards of the Coast LLC, available at https://www.dndbeyond.com/srd. The SRD 5.2.1 "
    "is licensed under the Creative Commons Attribution 4.0 International License, available at "
    "https://creativecommons.org/licenses/by/4.0/legalcode."
)


def attribution_text(policy: SourcePolicy) -> str:
    if policy.source_id != "wotc-srd-5.2.1-en":
        raise ValueError(f"no reviewed attribution template for {policy.source_id}")
    return _ATTRIBUTION + "\n"


def build_import_report(entities: tuple[CanonicalEntity, ...]) -> ImportReport:
    if not entities:
        raise ValueError("cannot report on an empty canonical dataset")
    source = entities[0].provenance
    if any(entity.provenance.source_sha256 != source.source_sha256 for entity in entities):
        raise ValueError("canonical dataset mixes multiple source checksums")
    by_kind = Counter(entity.kind for entity in entities)
    by_status = Counter(entity.status for entity in entities)
    unsupported = Counter()
    for entity in entities:
        for primitive in entity.mechanics.get("unsupported", []):
            if isinstance(primitive, str) and primitive:
                unsupported[primitive] += 1
    canonical_text = "\n".join(dumps_canonical(entity) for entity in entities) + "\n"
    return ImportReport(
        source_id=source.source_id,
        source_sha256=source.source_sha256,
        total_entities=len(entities),
        by_kind=dict(sorted(by_kind.items())),
        by_status=dict(sorted(by_status.items())),
        unsupported_primitives=dict(sorted(unsupported.items())),
        canonical_sha256=sha256_text(canonical_text),
    )


def write_dataset(
    output_dir: Path,
    entities: tuple[CanonicalEntity, ...],
    report: ImportReport,
    policy: SourcePolicy,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    canonical_lines = "\n".join(dumps_canonical(entity) for entity in entities) + "\n"
    (output_dir / "entities.jsonl").write_text(canonical_lines, encoding="utf-8", newline="\n")
    write_canonical_json(output_dir / "import-report.json", report)
    write_canonical_json(
        output_dir / "unsupported-mechanics.json",
        {"unsupported_primitives": report.unsupported_primitives},
    )
    (output_dir / "ATTRIBUTION.txt").write_text(
        attribution_text(policy), encoding="utf-8", newline="\n"
    )
