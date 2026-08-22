# GodotDnDSimulator Project Plan

## 1. Vision

GodotDnDSimulator is a commercial-quality, party-based, isometric fantasy RPG and reusable RPG platform. The project should feel like a modern tactical tabletop campaign presented through a 3D isometric Godot client, while keeping the actual rules simulation independent from rendering.

The project is not intended to be a thin scene-script prototype. It should become a reusable platform capable of supporting:

- a complete original single-player campaign;
- co-op multiplayer;
- campaign creation tools;
- community content packs;
- deterministic combat replays;
- headless testing and simulation;
- alternate clients;
- AI-assisted narration and NPC control;
- optional hosted campaign services.

The official rules foundation should come only from appropriately licensed System Reference Document material, initially SRD 5.2.1 under CC BY 4.0, with source provenance and attribution preserved. The game's branding, setting, characters, narrative, maps, art, music, and non-SRD content should be original project IP.

## 2. Core design principles

1. **The simulation engine is authoritative.** Godot renders and submits intent; it does not decide rules outcomes.
2. **Determinism is mandatory.** Rules outcomes, random rolls, and replays must be reproducible.
3. **Rules are data-driven.** Extend reusable mechanics instead of hardcoding named spells/items/monsters.
4. **The rules source is reproducible.** Imported content carries version, license, source, and checksums.
5. **Presentation and simulation are separate.** The same campaign state should be usable by Godot, tests, servers, tools, or other clients.
6. **Campaign history is durable.** Event sourcing enables replay, audit, branching, and debugging.
7. **Spatial legality is headless.** Rendering/navigation must not be the only source of truth for movement, LOS, cover, range, or AoE.
8. **Creator tooling is part of the product.** Campaign creation should not be an afterthought.
9. **AI cannot bypass the rules engine.** AI may query and request legal actions but cannot directly mutate authoritative state.
10. **Scope is milestone-driven.** A strong v0.7 vertical slice matters more than prematurely implementing every SRD entity.

## 3. Target player experience

### Main gameplay loop

```text
Create or load party
        ↓
Campaign/world map
        ↓
Explore location
        ↓
Talk / investigate / interact / loot
        ↓
Encounter or consequence
        ↓
Turn-based tactical combat when needed
        ↓
Rewards / injuries / reputation / quest state
        ↓
Rest / travel / level / manage inventory
        ↓
World and NPC state evolve
        ↓
Next objective
```

### Party model

Target 1-6 controllable party members, with companions and NPCs using the same shared actor foundations where practical.

### Core screens

- world/exploration view;
- combat HUD;
- character sheet;
- inventory/equipment;
- spellbook/abilities;
- journal/quest log;
- area/world map;
- party management;
- dialogue;
- trade;
- rest/camp;
- level-up;
- character creator;
- settings/accessibility.

## 4. Presentation strategy: true 3D isometric

Use Godot 4.x with a 3D world and orthographic camera rather than fake 2D isometric tiles.

### Why

A real 3D world makes these mechanics substantially easier and more faithful:

- elevation;
- stairs and multiple floors;
- roofs;
- pits and cliffs;
- flying;
- jumping;
- cover;
- line of sight;
- spell volumes;
- dynamic lighting;
- occlusion;
- terrain height;
- camera rotation.

### Camera system

```text
CameraRig
├── Camera3D
├── PanController
├── ZoomController
├── RotationController
├── OcclusionController
└── FloorController
```

Required behavior:

- orthographic projection;
- smooth pan and zoom;
- optional follow/focus;
- 90-degree rotation increments initially;
- roof and foreground-wall fading/hiding;
- floor selection in multi-level interiors;
- focus active combatant without stealing manual camera control;
- debug overlays for grid, paths, LOS, cover, target areas, and engine entity IDs.

## 5. System architecture

```text
Approved SRD source
       │
       ▼
Rules fetch/extract/normalize pipeline
       │
       ▼
Canonical rules/content data + provenance
       │
       ▼
Rule compiler / validator
       │
       ▼
┌────────────────────────────┐
│ Authoritative Headless     │
│ Simulation / Rules Engine  │
│                            │
│ commands → resolution      │
│          → events → state  │
└────────────┬───────────────┘
             │
    typed commands/events
             │
   ┌─────────┼──────────┐
   ▼         ▼          ▼
Godot      Server     Tooling
Client                 /Tests
```

### Intended repository shape

```text
GodotDnDSimulator/
├── apps/
│   ├── godot-client/
│   ├── campaign-editor/
│   └── rules-browser/
├── engine/
│   ├── commands/
│   ├── events/
│   ├── state/
│   ├── rules/
│   ├── effects/
│   ├── actors/
│   ├── combat/
│   ├── spatial/
│   ├── dialogue/
│   ├── quests/
│   └── ai/
├── content/
│   ├── srd/
│   ├── original/
│   ├── campaigns/
│   └── packs/
├── schemas/
├── tools/
│   ├── rules-importer/
│   ├── rule-compiler/
│   ├── validators/
│   └── migrations/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── conformance/
│   └── replay/
├── docs/
│   └── adr/
└── LICENSES/
```

Exact names may evolve through ADRs, but separation of responsibilities should remain.

## 6. Rules ingestion and conversion

The game runtime must never depend on parsing an SRD document directly.

### Development-time pipeline

```text
Approved official source
        ↓
Fetch
        ↓
Checksum + source manifest
        ↓
Extract
        ↓
Normalize headings/tables/text
        ↓
Identify entities/relationships
        ↓
Compile to canonical schemas
        ↓
Validate
        ↓
Generate provenance + attribution
        ↓
Generate canonical rules pack
        ↓
Rules runtime consumes only canonical data
```

### Required importer properties

- allowlisted sources only;
- idempotent where practical;
- deterministic output ordering;
- stable IDs;
- source/version/license metadata on every entity;
- checksums for source and generated output;
- validation errors must fail the pipeline;
- unsupported mechanics should be reported, not silently ignored;
- generated content should not be hand-edited;
- upstream source changes should produce an explicit diff/review step.

See `docs/RULES_INGESTION.md` for the legal/source boundary and detailed pipeline.

## 7. Canonical rules model

The canonical data model should support at least:

- Rule;
- Action;
- BonusAction or equivalent action-category metadata;
- Reaction;
- Ability;
- Skill;
- Save;
- Condition;
- Effect;
- Modifier;
- Resource;
- DamageType;
- Actor/Creature;
- Species;
- Background;
- Class;
- Subclass where licensed content requires it;
- LevelFeature;
- Feat;
- Spell;
- Item;
- Weapon;
- Armor;
- Equipment;
- Encounter;
- Rest;
- Terrain;
- MovementMode;
- VisionMode;
- Sense.

All entities should use a common envelope for stable ID, schema version, source information, and provenance.

## 8. Rule compiler instead of prose execution

The importer may preserve rules text for reference where licensing allows it, but gameplay must rely on executable structures.

Conceptual executable rule:

```text
Trigger
  ↓
Requirements
  ↓
Costs/resources
  ↓
Target selection
  ↓
Roll/check/save
  ↓
Modifiers
  ↓
Resolution outcome
  ↓
Effects
  ↓
Events
```

This enables both imported official mechanics and original/custom mechanics to use the same runtime.

## 9. Generic effect system

Prefer composable effects such as:

- DamageEffect;
- HealingEffect;
- ConditionEffect;
- MovementEffect;
- TeleportEffect;
- ModifierEffect;
- ResourceEffect;
- SpawnEffect;
- SummonEffect;
- TransformEffect;
- DetectionEffect;
- AreaEffect;
- RollModifierEffect;
- Advantage/Disadvantage effects;
- ongoing/periodic effects;
- trigger registration/removal.

Avoid patterns like `if spell_name == ...` or `if monster_name == ...` in the rules runtime.

When a mechanic cannot be expressed, add a reusable primitive with tests and capability metadata.

## 10. Deterministic command/event runtime

The preferred simulation flow is:

```text
Command
   ↓
Validation
   ↓
Rule resolution
   ↓
Deterministic random service
   ↓
Effects
   ↓
Domain events
   ↓
Reducer(s)
   ↓
New state
```

Example combat sequence:

```text
AttackCommand
   ↓
AttackDeclared
   ↓
ReactionWindowOpened
   ↓
AttackRollResolved
   ↓
AttackHit / AttackMissed
   ↓
DamageResolved
   ↓
DamageApplied
   ↓
ActorStateChanged
```

Events should carry enough structured context to drive logs, VFX, animation, replays, networking, and debugging without forcing presentation code to re-derive the rules result.

## 11. Deterministic dice and randomness

All randomness must flow through one abstraction.

Record at minimum:

- RNG/campaign/encounter context needed for replay;
- dice expression;
- raw dice;
- modifiers;
- advantage/disadvantage state;
- final result;
- reason/rule identifier;
- actor/target IDs where applicable.

Benefits:

- reproducible bugs;
- deterministic tests;
- save/reload consistency;
- synchronized multiplayer;
- battle replay;
- AI simulation/testing.

## 12. Event-sourced campaigns

Prefer an ordered history of meaningful state changes rather than opaque mutable saves.

```text
Initial State + Ordered Events = Current State
```

Use snapshots for performance, but preserve ordered events after/between snapshots.

Potential capabilities:

- replay entire battles;
- reconstruct bug states;
- rewind/debug in development;
- branch campaign timelines in tooling;
- verify multiplayer state;
- implement command idempotency;
- audit AI or server decisions.

Save/event schema versioning must be planned before public save compatibility is promised.

## 13. Spatial authority

The logical spatial system should be testable without Godot scenes.

Subsystem responsibilities:

```text
Spatial Authority
├── logical coordinates/grid/space
├── occupancy
├── distance
├── reach
├── movement costs
├── terrain
├── collision boundaries
├── elevation
├── line of sight
├── visibility/senses
├── cover
├── areas of effect
└── movement modes
```

Godot navigation answers “can a physical path be found?” The rules engine answers “may this actor legally take this path now, and what does it cost?”

The Godot client should be able to preview:

- normally reachable locations;
- locations reachable with alternate action economy such as a dash-like action where supported;
- difficult terrain;
- invalid destinations;
- hazardous/threatened movement;
- enemy threat/reach;
- attack/spell range;
- LOS and cover;
- AoE shapes.

## 14. Character system

Playable heroes, companions, NPCs, and monsters should share a common actor foundation when possible.

Core actor capabilities:

- identity;
- attributes;
- skills/proficiencies;
- defenses;
- HP/resources;
- movement modes;
- senses;
- inventory/equipment;
- abilities/actions/reactions;
- effects/conditions;
- faction/relationship metadata;
- optional AI controller;
- optional schedule/goals/memory.

### Character creator flow

```text
Identity
  ↓
Species
  ↓
Background
  ↓
Class
  ↓
Ability Scores
  ↓
Skills / Proficiencies
  ↓
Equipment
  ↓
Spells / Features
  ↓
Appearance
  ↓
Biography
  ↓
Validation / Review
```

The UI must request legal/current choices from the engine or canonical rules data. It should not contain its own duplicated hardcoded list of allowed class/species/etc. choices.

## 15. Tactical combat

Combat needs:

- initiative;
- rounds/turns;
- action economy;
- movement;
- attacks;
- damage/healing;
- conditions;
- reactions and reaction windows;
- resources;
- concentration/ongoing effects when applicable;
- encounter lifecycle;
- deterministic log/events.

The engine should expose legal actions for an actor. UI and AI should choose from them rather than reconstructing legality separately.

## 16. Dialogue system

Use graph/data-driven dialogue.

```text
DialogueNode
├── speaker
├── localized text/reference
├── visibility requirements
├── checks
├── choices
├── consequences/commands
└── next nodes
```

Choices may depend on character traits, skills, inventory, quest state, relationships, prior knowledge, faction state, and previous choices.

Checks are resolved by the engine; dialogue UI never fabricates outcomes.

## 17. Quest system

Represent quests as durable state machines/graphs.

A quest can contain:

- prerequisites;
- stages;
- objectives;
- optional objectives;
- branches;
- failure/abandonment conditions;
- rewards;
- world consequences;
- journal entries.

Quest consequences should produce authoritative commands/events rather than directly editing arbitrary world state.

## 18. NPC and world simulation

Long-term NPC model:

```text
Actor
├── rules state
├── inventory
├── abilities
├── perception
├── memories
├── relationships
├── faction
├── schedule
├── goals
└── AI controller
```

This permits NPCs to fight, trade, equip items, change faction, become companions, and participate in persistent world simulation without creating a separate incompatible rule system.

## 19. Tactical AI

Suggested layers:

```text
Strategic goal selection
        ↓
Tactical planner
        ↓
engine.get_legal_actions(actor)
        ↓
utility/scoring model
        ↓
selected command
        ↓
engine validates and executes
```

The AI should never create an action outside engine legality.

Future scoring can consider expected damage/healing, risk, positioning, cover, resources, objectives, ally safety, and retreat behavior.

## 20. Optional AI Dungeon Master / narrator

An LLM integration is useful only when strongly bounded.

```text
Rules Engine / Campaign State
          │
          ▼
      AI Director
      ├── Narrator
      ├── GM assistant
      └── NPC dialogue
```

Allowed typed capabilities may include:

- query rule;
- query actor;
- query location;
- query campaign history;
- get legal actions;
- preview legal command;
- request dialogue/encounter content;
- submit a typed command for validation.

Do not allow:

- direct HP edits;
- arbitrary inventory mutation;
- arbitrary quest completion;
- bypassing costs/requirements;
- arbitrary code execution from model output.

Local-model support should be favored where practical, with optional cloud inference kept behind a provider interface.

## 21. Campaign Creator Studio

Creator tooling should evolve toward:

- Campaign Editor;
- Map Editor;
- Character Editor;
- NPC Editor;
- Creature Editor;
- Encounter Editor;
- Item Editor;
- Spell/Ability Editor;
- Dialogue Graph Editor;
- Quest Graph Editor;
- Faction Editor;
- Loot Table Editor;
- Rules/Content Pack Manager;
- validation/preview/export.

The editor should write the same canonical content formats consumed by the game, not a separate editor-only representation.

## 22. Content packs and mods

Content outside engine code should be packageable.

Conceptual packs:

```text
packs/
├── srd-5.2.1/
├── core-original-game/
├── campaign-example/
├── creatures-example/
└── community/
```

Pack manifest should eventually include:

- stable ID;
- display name;
- version;
- author/creator;
- license;
- dependencies;
- engine compatibility;
- ruleset compatibility;
- assets/content indexes;
- checksums/signatures where useful.

Treat packs as untrusted input and validate them before loading.

## 23. Testing strategy

Testing should emphasize rules correctness rather than only line coverage.

### Test layers

- pure unit tests for value objects and rule/effect primitives;
- schema/golden tests for canonical data;
- importer fixtures;
- conformance tests tied to supported rules behavior;
- deterministic encounter replay tests;
- save/load/migration tests;
- headless spatial scenarios;
- Godot integration tests for rendering/client integration;
- end-to-end vertical-slice scenarios.

### Rules coverage reporting

Eventually report categories such as:

```text
Core resolution      100%
Combat                95%
Conditions            90%
Equipment             80%
Characters            75%
Spells                60%
Creatures             55%
```

Also distinguish:

- imported entities;
- executable entities;
- data-only entities;
- unsupported mechanics.

An unsupported mechanic is a visible engineering backlog item, not something to silently approximate.

## 24. Multiplayer architecture

Because authoritative state is already headless:

```text
Godot Client P1 ─┐
Godot Client P2 ─┼── Authoritative Server ─── Rules Engine
Godot Client P3 ─┤
Godot Client P4 ─┘
```

The network protocol should ultimately transport commands/events/snapshots and version compatibility metadata rather than scene-tree state.

Deterministic replays and event IDs also support reconnect, desync diagnosis, and server audit.

## 25. First vertical slice

Do not wait for complete rules coverage.

Build one small original adventure containing:

- one village or safe hub;
- one dungeon;
- exploration;
- dialogue;
- a skill check;
- a locked/conditional interaction;
- a trap or environmental hazard;
- treasure/equipment;
- three tactical encounters;
- one boss;
- one branching quest/consequence;
- four premade heroes;
- a deliberately small but representative set of character options, creatures, spells, items, and conditions.

Every feature in the slice must use the production engine boundaries. Avoid throwaway hardcoded systems that must later be rewritten.

## 26. Product and monetization direction

The licensed SRD itself is not the value proposition. Monetizable value comes from original content, tooling, convenience, hosting, and creator ecosystem.

Potential product layers:

### Base game

A paid original campaign and polished player experience.

### Expansion campaigns

Additional original campaigns/regions/storylines.

### Creator asset packs

Optional maps, environment kits, 3D characters/creatures, VFX, music, UI themes, and campaign-building assets.

### Creator Studio

Could be bundled or offered as a premium creator tool depending on product strategy.

### Hosted multiplayer

Local/self-hosted play can remain possible while a paid hosted option monetizes operational convenience, backups, uptime, and persistent campaigns.

### AI GM/narration

Prefer free/local inference support where possible. Optional cloud inference can be monetized as a usage/subscription service without making game rules dependent on a model.

### Campaign marketplace

Long-term creator marketplace can monetize through a platform revenue share while letting creators sell original campaigns/assets/content packs.

### Dedicated/persistent worlds

Hosted persistent campaign/world infrastructure can become a separate recurring service.

## 27. Legal/IP separation

Keep clear package boundaries:

```text
project/
├── engine/              project-owned license
├── apps/                project-owned license
├── original-content/    project-owned IP
└── content/srd/         licensed SRD-derived data + attribution/provenance
```

Do not brand the product as an official D&D game without separate permission. Use original setting/world names, characters, story, art, and trademarks.

See `docs/RULES_INGESTION.md` for rules-source policy.

## 28. Development sequence

The authoritative milestone sequence is maintained in `ROADMAP.md`:

1. v0.1 Project foundation
2. v0.2 Official SRD pipeline
3. v0.3 Rules runtime
4. v0.4 Character runtime
5. v0.5 Tactical combat
6. v0.6 Spatial authority
7. v0.7 Godot vertical slice
8. v0.8 Spell runtime
9. v0.9 Complete character creator
10. v1.0 Playable RPG
11. v1.1 SRD coverage/conformance
12. v1.2 Creator Studio
13. v1.3 Living world
14. v1.4 Advanced AI
15. v1.5 Multiplayer
16. v2.x Mod SDK, marketplace, dedicated servers, procedural generation, AI GM/NPC dialogue, community campaigns, persistent worlds, hosted multiplayer, creator monetization

`TODO.md` is the active implementation checklist. Roadmap scope and TODO state must stay consistent with code.

## 29. Architectural decisions to settle early

Create ADRs before implementation locks these down:

- engine implementation language/runtime and Godot boundary;
- command/event serialization format;
- save snapshot/event storage format;
- canonical rule schema format;
- stable identifier scheme;
- content pack manifest/dependency system;
- grid/spatial representation;
- Godot-to-engine IPC/binding strategy;
- deterministic RNG algorithm/versioning policy;
- localization representation;
- mod security model;
- multiplayer authority and protocol versioning.

## 30. Definition of success

The project is on track when it can demonstrate all of the following without architectural exceptions:

- the same seed and command history reproduce the same simulation results;
- Godot displays outcomes but cannot invent them;
- a rules entity can be traced to an approved licensed source/version/hash;
- custom mechanics can be created using generic rule/effect primitives;
- movement/LOS/cover/AoE can be tested headlessly;
- campaign state can be reconstructed from snapshots/events;
- AI submits legal typed commands rather than mutating state;
- Creator Studio writes the same content format the runtime consumes;
- TODO, changelog, roadmap, docs, tests, and code tell the same story.
