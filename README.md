# GodotDnDSimulator

GodotDnDSimulator is an isometric, deterministic tabletop-RPG simulation platform and Godot client built around appropriately licensed System Reference Document (SRD) rules content plus original game content.

The project is designed as a reusable RPG engine/platform rather than a scene-script-only game: the headless simulation owns authoritative rules and campaign state, while Godot provides a polished 3D orthographic isometric presentation.

## Core architecture

```text
Approved licensed SRD source
          │
          ▼
Rules fetch / extract / normalize / compile
          │
          ▼
Canonical rules data + provenance
          │
          ▼
┌───────────────────────────────┐
│ Authoritative Headless Engine │
│                               │
│ command → resolution → events │
│                    → state    │
└──────────────┬────────────────┘
               │
       typed commands/events
               │
       ┌───────┼────────┐
       ▼       ▼        ▼
     Godot   Server   Tools/Tests
```

## v0.1 implementation foundation

The executable foundation uses **Python 3.12+** for the authoritative engine and **Godot 4.7.1+** for the presentation client. The decision and tradeoffs are recorded in [`docs/adr/0001-engine-runtime.md`](docs/adr/0001-engine-runtime.md).

Implemented foundation pieces include:

- versioned namespaced IDs for campaigns, sessions, actors, commands, events, rules, effects, and packs;
- typed immutable command/event/state contracts;
- `pcg32-v1` deterministic RNG with a published regression vector;
- deterministic dice expressions with raw-roll audit metadata;
- command validation and optimistic sequence checks;
- pure event reducers;
- versioned snapshot/event JSON serialization;
- event-log replay from a snapshot with RNG continuation;
- JSON Schemas for v1 command, event, and snapshot contracts;
- a minimal Godot 4.7.1 orthographic 3D project that owns presentation only;
- Python, schema/governance, and Godot headless CI jobs.

The proof-of-foundation command is `simulation.roll_dice`. Given the same initial state, seed, and command, it produces byte-for-byte equivalent canonical event/state JSON and can be replayed from the event log.

## v0.2 SRD pipeline

The next phase adds a development-time, provenance-first importer under `tools/rules_importer/`. Runtime gameplay does **not** depend on the importer or PDF/network libraries.

The production source policy currently allowlists only:

```text
source_id: wotc-srd-5.2.1-en
source:    D&D SRD 5.2.1 English PDF
license:   CC-BY-4.0
raw PDF:   transient local cache only
```

The allowlist pins the reviewed official URL and expected SHA-256. The fetcher rejects unapproved source IDs/hosts/licenses/media types, verifies downloaded and cached bytes, records retrieval metadata, and fails closed if the upstream checksum changes.

Pipeline:

```text
allowlisted source
      ↓
async fetch + cache validators
      ↓
SHA-256 verification + source manifest
      ↓
PDF extraction + bookmarks/pages
      ↓
normalization
      ↓
canonical entity compilation
      ↓
versioned JSON Schema validation
      ↓
entities.jsonl + reports + attribution
      ↓
version/source diff tooling
```

The compiler currently emits provenance-rich **data-only** canonical entities. Executable D&D mechanics belong to the later rules-runtime/effect-pipeline milestones rather than being hidden inside the importer.

Raw SRD PDFs are ignored by Git. Generated/audited canonical output should only be committed or released after the complete official-source import has been reviewed.

See [`docs/V0.2_RULES_PIPELINE.md`](docs/V0.2_RULES_PIPELINE.md) and [`docs/RULES_INGESTION.md`](docs/RULES_INGESTION.md).

## Local validation

With Python 3.12+:

```bash
python -m pip install -e '.[dev]'
ruff check .
mypy engine/src tools/rules_importer
pytest --cov=godot_dnd_engine --cov=tools.rules_importer --cov-report=term-missing
python scripts/check_governance.py
python scripts/determinism_smoke.py
python -m tools.rules_importer.smoke
```

With Godot 4.7.1 installed:

```bash
godot --headless --path apps/godot-client --editor --quit
```

### Rules importer

Fetch and checksum-verify the approved SRD into the ignored local cache:

```bash
python -m tools.rules_importer.cli fetch
```

Fetch (or reuse the verified cache), extract, normalize, compile, validate, and export:

```bash
python -m tools.rules_importer.cli build
```

Default paths:

```text
source policy   config/rules/sources.json
raw cache       .cache/rules/
rule schemas    schemas/rules/v1/
generated data  content/generated/srd-5.2.1/
```

The full official-source build is still a v0.2 completion criterion; fixture success alone does not mark the milestone complete.

## Design commitments

- Godot 4.x true-3D orthographic/isometric presentation.
- Headless authoritative simulation separated from rendering.
- Deterministic seeded RNG/dice and replayable outcomes.
- Command -> validation -> resolution -> events -> reducer -> state architecture.
- Event-sourced campaign history with versioned snapshots/events.
- Data-driven rules/effects rather than named spell/item/monster conditionals.
- Headless spatial authority for movement, range, LOS, cover, terrain, elevation, and AoE.
- Licensed SRD ingestion with source allowlisting, checksums, provenance, validation, and attribution.
- Original setting, branding, characters, narrative, art, maps, and campaign content.
- Creator Studio/content packs/modding as first-class long-term capabilities.
- AI may query and submit legal typed commands but may never directly mutate authoritative game state.
- Multiplayer eventually synchronizes authoritative commands/events/snapshots rather than scene-tree state.

## Documentation

Start here:

- [`docs/PROJECT_PLAN.md`](docs/PROJECT_PLAN.md) — detailed game, platform, creator, AI, multiplayer, and monetization plan.
- [`ROADMAP.md`](ROADMAP.md) — milestone sequence from v0.1 foundation through v2.9 creator monetization.
- [`TODO.md`](TODO.md) — active implementation backlog and milestone exit criteria.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — authoritative engine/Godot/tooling boundaries.
- [`docs/RULES_INGESTION.md`](docs/RULES_INGESTION.md) — licensed rules-source policy, provenance, import, compilation, diffing, and attribution.
- [`docs/V0.2_RULES_PIPELINE.md`](docs/V0.2_RULES_PIPELINE.md) — implemented importer commands, contracts, outputs, tests, and completion gates.
- [`docs/GIT_WORKFLOW.md`](docs/GIT_WORKFLOW.md) — branch, commit, PR, review, merge, compatibility, and release workflow.
- [`docs/adr/`](docs/adr/) — durable architecture decisions.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — contributor validation and PR workflow.
- [`CHANGELOG.md`](CHANGELOG.md) — project change history.

## Agent governance

[`AGENTS.md`](AGENTS.md) is the canonical contract for coding agents and contributors performing automated work in this repository.

Tool adapters are also included:

- [`CLAUDE.md`](CLAUDE.md)
- [`GEMINI.md`](GEMINI.md)
- [`.github/copilot-instructions.md`](.github/copilot-instructions.md)

Agents must keep implementation, tests, `TODO.md`, `CHANGELOG.md`, roadmap scope, and documentation consistent within the same pull request.

## Rules/content boundary

The initial approved official rules target is D&D SRD 5.2.1 under CC BY 4.0, subject to the source/provenance controls documented in `docs/RULES_INGESTION.md`.

The project must not use D&D Beyond Basic Rules or non-SRD rulebook/setting/adventure content as a substitute for appropriately licensed source material. Imported official rules content and original/homebrew project content must remain traceable and separable.

## Current milestone

**v0.2 — Official SRD pipeline**

The importer infrastructure, schemas, deterministic fixture build, provenance controls, and diff/report tooling are implemented. The milestone remains open until the pinned official SRD 5.2.1 PDF is fetched and the complete 364-page dataset is successfully compiled, validated, audited, and reproduced as recorded in [`TODO.md`](TODO.md).

## First playable target

The first vertical slice will intentionally use a limited representative rules/content subset while exercising production architecture:

- one original village/hub;
- one dungeon;
- exploration and dialogue;
- a skill-check/conditional interaction;
- a trap/environmental obstacle;
- three tactical encounters;
- one boss;
- one branching quest/consequence;
- four premade heroes;
- a small representative set of character options, creatures, spells, items, and conditions.

The goal is to prove the reusable engine/platform before chasing complete rules coverage.
