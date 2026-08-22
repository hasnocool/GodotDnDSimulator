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
- Local Python, schema/governance, and Godot headless CI via `scripts/local_ci.sh`.

The proof-of-foundation command is `simulation.roll_dice`. Given the same initial state, seed, and command, it produces byte-for-byte equivalent canonical event/state JSON and can be replayed from the event log.

## v0.2 SRD pipeline

The v0.2 phase adds a development-time, provenance-first importer under `tools/rules_importer/`. Runtime gameplay does **not** depend on the importer or PDF/network libraries.

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

The compiler currently emits provenance-rich **data-only** canonical entities. The remaining full-official-source fetch, 364-page audit, generated-data decision, and v0.2 exit criterion remain tracked in [`TODO.md`](TODO.md).

Raw SRD PDFs are ignored by Git. Generated/audited canonical output should only be committed or released after the complete official-source import has been reviewed.

See [`docs/V0.2_RULES_PIPELINE.md`](docs/V0.2_RULES_PIPELINE.md) and [`docs/RULES_INGESTION.md`](docs/RULES_INGESTION.md).

## v0.3 rules runtime

The merged v0.3 implementation adds a deterministic, headless rules runtime under `engine/src/godot_dnd_engine/rules/` without adding Godot authority or a second RNG system.

Implemented runtime families include ability/proficiency/D20/DC/save resolution, advantage/disadvantage, generic modifiers, resources/costs, requirements, target selectors, effects, conditions/durations, reactions/hooks, and ruleset capabilities.

The runtime uses the existing versioned `pcg32-v1` RNG through the established dice service. It has no filesystem, network, database, wall-clock, or Godot dependency.

See [`docs/V0.3_RULES_RUNTIME.md`](docs/V0.3_RULES_RUNTIME.md).

## v0.4 character runtime

The merged v0.4 phase adds a shared immutable actor model under `engine/src/godot_dnd_engine/actors/` for heroes, NPCs, and creatures.

Implemented character-state families include:

- six ability scores and explicit proficiency bonus;
- current/maximum/temporary HP plus armor class;
- typed skills, saves, and generic training proficiencies;
- walk/climb/swim/fly/burrow movement records;
- generic named senses with optional ranges;
- inventory entries and equipment-slot assignments;
- v0.3 resources and conditions embedded directly on actors;
- adapters that reuse the v0.3 effect pipeline;
- data-driven character options and constrained headless creation;
- canonical actor JSON serialization with `schema_version: 1` and explicit v0-to-v1 migration.

See [`docs/V0.4_CHARACTER_RUNTIME.md`](docs/V0.4_CHARACTER_RUNTIME.md).

## v0.5 tactical combat

The active phase adds deterministic tactical combat under `engine/src/godot_dnd_engine/combat/` while preserving the existing actor and rules runtimes.

Implemented combat families include:

- encounter preparation/start/end lifecycle;
- deterministic initiative, rounds, turns, and stable tie ordering;
- action, bonus-action, reaction, and movement-budget accounting;
- explicit reaction windows and data-driven combat-condition restrictions;
- abstract attack definitions using the existing v0.3 D20 resolver;
- armor-class attack resolution and critical attack-roll handling;
- generic damage/healing and temporary-hit-point handling;
- data-driven resistance, immunity, and vulnerability hooks;
- explicit character-style versus monster-style zero-HP policy;
- versioned `CombatEvent` records, a pure reducer, canonical JSON/JSONL logs, and deterministic replay;
- `schemas/v1/combat-event.schema.json`.

Movement in v0.5 is **budget accounting only**. Path legality, occupancy, distance/reach, terrain, LOS, cover, elevation, and AoE remain v0.6 Spatial Authority responsibilities.

The combat engine contains no named-item, named-spell, or named-creature special cases and no Godot scene authority.

See [`docs/V0.5_TACTICAL_COMBAT.md`](docs/V0.5_TACTICAL_COMBAT.md).

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

Focused v0.5 validation also runs the combat tests against the real `pcg32-v1` seeded RNG interface. The offline pre-PR suite reached 29 passing tests and 96% branch-aware coverage for `godot_dnd_engine.combat`.

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
- [`docs/V0.2_RULES_PIPELINE.md`](docs/V0.2_RULES_PIPELINE.md) — importer commands, contracts, outputs, tests, and remaining audit gates.
- [`docs/V0.3_RULES_RUNTIME.md`](docs/V0.3_RULES_RUNTIME.md) — executable rules primitives, modifier/effect semantics, determinism, and v0.4 handoff.
- [`docs/V0.4_CHARACTER_RUNTIME.md`](docs/V0.4_CHARACTER_RUNTIME.md) — shared actor state, creation API, rule adapters, serialization, and v0.5 handoff.
- [`docs/V0.5_TACTICAL_COMBAT.md`](docs/V0.5_TACTICAL_COMBAT.md) — encounter state, attacks, damage/healing, reactions, event replay, and v0.6 spatial handoff.
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

**v0.5 — Tactical combat**

The tactical-combat implementation is on the active feature branch with encounter lifecycle, deterministic initiative/turns, action economy, movement accounting, reactions, abstract attacks, damage/healing/defense hooks, combat conditions, supported zero-HP state transitions, and versioned event replay. The milestone remains open until the exact PR head passes the complete repository CI gates recorded in [`TODO.md`](TODO.md).

Outstanding earlier CI proof and full-source v0.2 audit items remain tracked as carryover rather than being silently considered complete.

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
