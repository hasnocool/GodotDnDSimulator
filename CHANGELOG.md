# Changelog

All notable changes to this project will be documented in this file.

The format follows the spirit of [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses semantic versioning as documented in `docs/adr/0002-versioning.md`.

## [Unreleased]

### Added

- Repository bootstrap and project mission.
- Detailed product roadmap from v0.1 foundation through v2.9 creator monetization.
- Active milestone-oriented `TODO.md` execution backlog.
- Canonical `AGENTS.md` governance covering architecture, determinism, testing, TODO/changelog discipline, licensing, Git workflow, and scope control.
- Project architecture and implementation planning documentation.
- Licensed SRD ingestion/provenance plan and source-boundary rules.
- Git/branch/pull-request workflow documentation.
- Tool-specific agent instruction adapters for supported coding assistants.
- Python 3.12 authoritative headless engine package with typed command, event, and immutable state contracts.
- Versioned `pcg32-v1` deterministic RNG and auditable dice expressions/roll metadata.
- Pure event reducers, optimistic command sequencing, canonical JSON serialization, snapshot/event replay, and strict input validation.
- Complete simulation snapshots that persist both authoritative state and the exact RNG stream position for deterministic save/load continuation.
- Random events now carry typed RNG checkpoints so snapshot-plus-event replay restores the exact future random stream.
- Versioned JSON Schemas for v1 command, event, and snapshot contracts.
- Namespaced stable IDs for campaigns, sessions, actors, commands, events, rules, effects, and content packs.
- Minimal Godot 4.7.1 3D orthographic presentation project under `apps/godot-client/`.
- Python engine, governance/schema, deterministic smoke, and Godot headless CI checks.
- Contributor guide plus structured bug/feature issue templates.
- Architecture decisions for engine runtime, semantic/schema versioning, and stable identifiers.
- Deterministic/replay/validation test suite with a 90% minimum coverage gate.
- Machine-readable SRD 5.2.1 source allowlist with official URL, CC-BY-4.0 policy, and pinned SHA-256 verification.
- Async cache-aware SRD fetcher with ETag/Last-Modified validators, source manifests, size limits, redirect restrictions, and post-cache checksum validation.
- PDF extraction and normalization pipeline that preserves page/bookmark provenance and normalizes text, lists, tables, Unicode whitespace, and dice notation.
- Versioned canonical rule schemas for rules, actions, abilities, condition/effect resources, character options, spells, items, creatures, and spatial primitives.
- Deterministic normalized-document compiler, schema validation, canonical JSONL export, attribution bundle, unsupported-mechanics report, import report, and canonical output checksum.
- Canonical SRD entity diffing for added/removed/changed/unchanged entities and prose-only versus mechanical changes.
- `python -m tools.rules_importer.cli` fetch/build interface plus deterministic fixture smoke build.
- Mocked HTTP, policy, extraction, normalization, compiler, schema, reporting, diffing, tamper, and deterministic-generation regression coverage for the v0.2 importer.

### Changed

- `README.md` now documents the executable v0.1 foundation and local validation workflow.
- Release policy is now explicitly defined as semantic repository versioning plus independent serialized-contract/RNG algorithm versions.
- Development version advances to `0.2.0.dev0`; CI now lints, type-checks, tests, and coverage-checks both the engine and rules-import tooling.
- Rules-source PDF caches are explicitly ignored so raw upstream documents are fetched and verified rather than committed accidentally.

### Deprecated

- None yet.

### Removed

- None yet.

### Fixed

- Snapshot restore now resumes the deterministic RNG stream instead of only restoring visible game state.
- Replaying events after an older snapshot now advances RNG state through recorded event checkpoints before future commands execute.

### Security

- Added strict validation at command, event, snapshot, identifier, dice, and replay boundaries to reject malformed/untrusted input early.
- Rules ingestion now rejects unallowlisted source IDs, non-official/incorrectly licensed policies, non-HTTPS or unexpected hosts, unexpected media types, checksum drift, cache-manifest mismatches, and post-manifest source tampering.

<!--
Release process notes:
- Move applicable Unreleased entries into a versioned section when tagging a release.
- Add the release date in YYYY-MM-DD format.
- Never mark a feature as released before its tag/release exists.
- Do not rewrite historical sections except for factual corrections.
-->
