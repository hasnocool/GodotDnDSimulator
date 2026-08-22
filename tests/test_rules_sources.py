# tests/test_rules_sources.py
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.rules_importer.errors import SourcePolicyError
from tools.rules_importer.sources import SourceRegistry

ROOT = Path(__file__).resolve().parents[1]


def test_official_source_is_allowlisted() -> None:
    registry = SourceRegistry.from_path(ROOT / 'config/rules/sources.json')
    policy = registry.require('wotc-srd-5.2.1-en')
    assert policy.document_version == '5.2.1'
    assert policy.license_id == 'CC-BY-4.0'
    assert policy.expected_sha256 == (
        '8974902d109d6e63672d7c490bde9ccf052410503d9cfa768237154fbc5e3d87'
    )


def test_unknown_source_is_rejected() -> None:
    registry = SourceRegistry.from_path(ROOT / 'config/rules/sources.json')
    with pytest.raises(SourcePolicyError):
        registry.require('dnd-beyond-basic-rules')


def test_unapproved_host_is_rejected(tmp_path: Path) -> None:
    source = {
        'schema_version': 1,
        'sources': [{
            'source_id': 'bad',
            'display_name': 'Bad',
            'document_version': '1',
            'publisher': 'Example',
            'landing_page_url': 'https://www.dndbeyond.com/srd',
            'download_url': 'https://example.com/not-approved.pdf',
            'media_type': 'application/pdf',
            'license_id': 'CC-BY-4.0',
            'license_url': 'https://creativecommons.org/licenses/by/4.0/legalcode',
            'official': True,
            'allowed_for_ingestion': True,
            'raw_redistribution': 'transient-cache-only',
            'expected_sha256': None,
        }],
    }
    path = tmp_path / 'sources.json'
    path.write_text(json.dumps(source), encoding='utf-8')
    registry = SourceRegistry.from_path(path)
    with pytest.raises(SourcePolicyError):
        registry.require('bad')
