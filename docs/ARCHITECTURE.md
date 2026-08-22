# Architecture

## Status

Initial architecture contract for v0.1+. Significant departures should be recorded as ADRs under `docs/adr/` and reflected in `ROADMAP.md`/`TODO.md`.

## Architectural goal

The project must support a polished Godot isometric game without making Godot scene state the canonical game state.

```text
Input / AI / Network
        │
        ▼
Typed Command
        │
        ▼
┌──────────────────────────────────┐
│ Authoritative Headless Engine    │
│                                  │
│ validate → resolve → emit events │
│                    → reduce state│
└──────────────┬───────────────────┘
               │
        events + snapshots
               │
        ┌──────┼─────────┐
        ▼      ▼         ▼
      Godot  Server   Test/Tools
```

## Layer responsibilities

### `engine/`

Owns authoritative domain behavior:

- commands and validation;
- state and reducers;
- deterministic RNG/dice;
- rule/effect resolution;
- actors/resources/conditions;
- combat lifecycle;
- spatial legality;
- quests/dialogue consequences;
- event emission;
- serialization contracts;
- replay support.

Must remain runnable/testable without a rendered Godot scene.

### `apps/godot-client/`

Owns presentation and player interaction:

- scene tree;
- 3D world rendering;
- orthographic camera;
- input;
- UI/HUD;
- animation;
- VFX;
- audio;
- debug visualization;
- translating player intent into engine commands;
- translating engine events/state into presentation changes.

Must not own authoritative combat/rules decisions.

### `tools/`

Owns development-time transforms and validation:

- licensed rules fetch/import;
- extraction/normalization;
- rule compilation;
- source/version diffing;
- schema validation;
- migrations;
- conformance reporting;
- generated-content verification.

Runtime gameplay should not require these tools.

### `content/`

Owns data packs:

- approved SRD-derived canonical data;
- original project content;
- campaigns;
- creatures/items/spells/abilities where represented as data;
- pack manifests.

Generated content must identify its generator/provenance and should not be hand-edited.

### `schemas/`

Owns versioned data contracts for:

- rules/content entities;
- commands/events where schema files are appropriate;
- save/snapshot formats;
- content packs/manifests;
- generated reports.

### `tests/`

Owns deterministic correctness evidence:

- unit tests;
- integration tests;
- conformance tests;
- replay fixtures;
- importer fixtures;
- migration fixtures.

## Authoritative state

The engine owns canonical simulation state. A Godot node may cache presentation state, but canonical values such as HP, initiative, resources, legal movement, conditions, quest consequences, inventory ownership, and rules outcomes must come from the engine.

### Forbidden example

```text
Godot Button
  └─ directly subtract target HP
```

### Required direction

```text
Godot Button
  ↓
AttackCommand
  ↓
Engine validates/resolves
  ↓
DamageApplied event
  ↓
Engine reducer changes HP
  ↓
Godot animates the event/new state
```

## Command model

A command represents requested intent and should include sufficient identity/version/context to support validation and idempotency where needed.

Candidate envelope fields:

- command ID;
- campaign/session ID;
- actor/requester ID;
- command type/version;
- payload;
- expected state/event position where concurrency requires it;
- client metadata that is not authoritative.

Commands may be rejected. Rejection should be structured and diagnosable.

## Event model

Events represent facts that the engine accepted/resolved.

Candidate envelope fields:

- event ID;
- campaign/session ID;
- monotonically ordered sequence/position;
- event type/version;
- deterministic timestamp/tick metadata where appropriate;
- correlation/causation IDs;
- payload;
- rules/source references when useful for audit.

Events drive:

- reducers;
- combat logs;
- animation/VFX/audio mapping;
- replay;
- networking;
- debugging/telemetry.

## State and reducers

Reducers should be deterministic and avoid hidden external I/O.

```text
previous state + ordered event = next state
```

Snapshotting is an optimization, not an alternate authority model.

## Randomness

Randomness must be deterministic and version-aware.

Rules code must never call global/ad-hoc random functions. A central RNG/dice abstraction must provide reproducible draws and sufficient recorded metadata for replay.

Changing the RNG algorithm after public saves/replays exist may be a compatibility change and must be versioned/documented.

## Time

Treat game/simulation time as domain state rather than wall-clock time whenever possible.

Potential modes can include turn-based, timed turn-based, real-time-with-pause, or hybrid in future, but initial tactical implementation should prioritize deterministic turn-based semantics.

Wall-clock timestamps may be used for diagnostics/metadata; they should not silently determine rules outcomes.

## Rules runtime

Rules should compile into reusable structures:

```text
trigger
requirements
costs/resources
target selector
roll/check/save
modifier pipeline
outcomes
effects
durations/reactions/event hooks
```

Name-based special casing should be treated as architectural debt unless the mechanic is truly unique and cannot reasonably be expressed generically. Even then, define a typed reusable extension point.

## Spatial authority

The logical spatial model is independent from rendering.

It should support queries such as:

- is destination occupiable?;
- what is legal movement cost?;
- is target in range?;
- is target visible?;
- what cover applies?;
- which cells/entities intersect an area?;
- what movement modes are valid?;
- what triggers occur along a path?;
- what path is legal under rules constraints?

Godot's navigation/pathfinding may propose paths, but the engine validates tactical legality/cost.

## Godot presentation model

Target true 3D isometric presentation:

- `Camera3D` orthographic projection;
- 3D environment and actors;
- logical-to-world coordinate adapter;
- actor visual registry keyed by engine entity ID;
- event-to-animation/VFX/audio mapping;
- independent debug visualization.

Camera features:

- pan;
- zoom;
- discrete rotation initially;
- active-character focus;
- floor handling;
- roof/foreground occlusion.

## Dialogue and quests

Dialogue and quest systems should request/emit authoritative commands/events for meaningful consequences.

Dialogue UI can display text/choices, but a successful skill check, item transfer, faction change, or quest update must be resolved/accepted through engine-domain behavior.

## AI boundary

AI receives structured observations and legal actions from the engine.

```text
Engine state/query
   ↓
AI policy/planner
   ↓
Typed command
   ↓
Engine validation
```

Never grant AI direct mutable state access.

LLMs are especially untrusted: treat generated tool arguments like external input and validate everything.

## Networking boundary

Future multiplayer should synchronize commands/events/snapshots rather than scene-tree state.

The server owns authoritative simulation. Clients may predict presentation where useful but must reconcile to server-authoritative events/state.

## Content pack boundary

Content packs are data, not arbitrary executable code by default.

Validate:

- pack ID/version;
- dependencies;
- engine/rules compatibility;
- schemas;
- paths;
- asset references;
- licenses/provenance;
- limits/sizes.

A future scripting/mod execution layer, if added, requires an explicit security model and ADR.

## Async, threads, I/O

Do not perform blocking disk/network/database/subprocess or CPU-heavy operations on async/event-loop or frame-critical threads.

Use:

- asynchronous I/O APIs where available;
- worker threads/processes for blocking or CPU-heavy jobs;
- thread-safe queues/messages between workers and authoritative/main state;
- batch operations for import/database/network work;
- cancellation and bounded concurrency for long pipelines.

The authoritative simulation should avoid nondeterministic shared-state races.

## Compatibility/versioning

Version at least:

- command schemas;
- event schemas;
- save snapshots;
- canonical rule/content schemas;
- content pack manifests;
- rules/source version;
- protocol versions when multiplayer begins.

Migrations should be explicit and tested. Never silently reinterpret old saves/content with new semantics.

## Observability

Prefer structured diagnostics that include stable IDs:

- campaign/session ID;
- command/event ID;
- actor/entity ID;
- rule/effect ID;
- source/provenance ID where relevant;
- deterministic sequence position.

Avoid logging secrets or unnecessary user content.

## ADR policy

Create an Architecture Decision Record before locking in high-cost choices such as:

- engine language/runtime;
- Godot-engine binding/IPC approach;
- serialization format;
- database/event-log backend;
- spatial coordinate model;
- RNG algorithm/versioning;
- content pack dependency model;
- mod scripting security;
- multiplayer transport/protocol.

An ADR should record context, decision, alternatives, consequences, and migration implications.
