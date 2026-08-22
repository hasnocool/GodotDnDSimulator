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

The first executable foundation uses **Python 3.12+** for the authoritative engine and **Godot 4.7.1+** for the presentation client. The decision and tradeoffs are recorded in [`docs/adr/0001-engine-runtime.md`](docs/adr/0001-engine-runtime.md).

Implemented foundation pieces include:

- versioned namespaced IDs for campaigns, sessions, actors, commands, events, rules, effects, and packs;
- typed immutable command/event/state contracts;
- `pcg32-v1` deterministic RNG with a published regression vector;
- deterministic dice expressions with raw-roll audit metadata;
- command validation and optimistic sequence checks;
- pure event reducers;
- versioned snapshot/event JSON serialization;
- event-log replay from a snapshot;
- JSON Schemas for v1 command, event, and snapshot contracts;
- a minimal Godot 4.7.1 orthographic 3D project that owns presentation only;
- Python, schema/governance, and Godot headless CI jobs.

The current proof-of-foundation command is `simulation.roll_dice`. Given the same initial state, seed, and command, it produces byte-for-byte equivalent canonical event/state JSON and can be replayed from the event log.

## Local validation

With Python 3.12+:

```bash
python -m pip install -e '.[dev]'
ruff check .
mypy engine/src
pytest --cov=godot_dnd_engine --cov-report=term-missing
python scripts/check_governance.py
python scripts/determinism_smoke.py
```

With Godot 4.7.1 installed:

```bash
godot --headless --path apps/godot-client --editor --quit
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

**v0.1 — Project foundation**

The executable foundation is now substantially in place. Remaining v0.1 work is tracked in [`TODO.md`](TODO.md), with CI required to prove the milestone exit criterion before advancing to the SRD pipeline.

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
