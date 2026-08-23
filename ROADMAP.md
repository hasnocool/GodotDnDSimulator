# GodotDnDSimulator Roadmap

## Product direction

GodotDnDSimulator is intended to become a reusable isometric tabletop-RPG engine/platform with a
headless deterministic simulation core and a Godot presentation client. The roadmap is milestone
oriented: each version should leave behind a coherent, testable capability rather than a pile of
partially connected features.

The architecture and milestone work must continue to follow these boundaries:

- the Python simulation remains authoritative for rules, state, spatial legality, combat, and RNG;
- Godot remains presentation/input/UX and submits typed intent;
- rules/content come from reviewed original or appropriately licensed sources;
- deterministic replay and stable IDs remain first-class;
- AI policies may select only engine-supplied legal actions and may not mutate authoritative state.

## v0.x — Engine and client foundation

### v0.1 — Project foundation

Goal: establish the deterministic headless/runtime boundary and repository governance.

- Python 3.12 authoritative engine package;
- immutable typed command/event/state contracts;
- deterministic PCG32 RNG and dice service;
- pure reducer and snapshot/event replay;
- JSON schemas and stable IDs;
- minimal Godot 4.x project;
- CI, tests, governance, ADRs, contribution workflow.

Exit criteria: one deterministic command produces reproducible event/state output and the repository
checks execute successfully.

### v0.2 — Official SRD pipeline

Goal: turn approved licensed source material into deterministic canonical runtime data.

- approved-source allowlist;
- fetch/cache/checksum/provenance manifest;
- PDF extraction/normalization;
- canonical rule/content schemas;
- deterministic compiler/export;
- unsupported-mechanics and import reports;
- canonical entity diffing;
- attribution bundle;
- source/import regression coverage.

Exit criteria: a complete reviewed official source can be reproduced from its pinned source into a
schema-valid deterministic canonical dataset with provenance and attribution.

### v0.3 — Rules runtime

Goal: execute reusable mechanics independent of Godot and named content.

- D20 tests and saves;
- modifiers and stacking;
- resources and costs;
- requirements/selectors;
- effects and conditions;
- durations;
- triggers/reactions;
- capability declarations;
- canonical-data conformance fixtures.

Exit criteria: representative canonical mechanics execute deterministically through typed runtime
contracts.

### v0.4 — Character runtime

Goal: provide one shared actor foundation for heroes, NPCs, and creatures.

- abilities, HP/temp HP, AC;
- skills/saves/proficiencies;
- movement and senses;
- inventory/equipment;
- resources/conditions;
- reusable option/choice system;
- headless character creation;
- versioned actor serialization and migration.

Exit criteria: supported actors can be created, serialized, restored, and updated through reusable
runtime primitives.

### v0.5 — Tactical combat

Goal: provide deterministic event-sourced turn-based combat.

- encounter lifecycle;
- initiative/rounds/turns;
- action economy;
- movement budget accounting;
- attacks/damage/healing;
- defenses;
- reactions;
- conditions;
- zero-HP policies;
- combat events/replay/schema.

Exit criteria: a complete representative combat encounter can be replayed to identical final state.

### v0.6 — Spatial authority

Goal: make movement and spatial legality headless and reusable.

- logical spaces and square-grid backend;
- footprints/occupancy/collision;
- distance/reach;
- path legality/pathfinding/reachability;
- terrain/elevation/movement modes;
- LOS/cover;
- sphere/cube/cylinder/cone/line areas;
- threat transitions;
- navigation proposals subordinate to authority;
- spatial events/replay/query API.

Exit criteria: representative movement, LOS, cover, and AoE scenarios are reproducible without Godot.

### v0.7 — Godot tactical vertical slice

Goal: prove the client boundary with a small complete battle.

- true 3D orthographic/isometric camera;
- tactical map/actor presentation;
- pointer/controller selection;
- authoritative movement/path preview;
- target/LOS/cover/AoE preview;
- action HUD/combat log;
- presentation event/VFX/audio hooks;
- occlusion/debug overlays;
- headless client tests.

Exit criteria: the Sunken Courtyard battle can be completed through Godot while Python remains the
only gameplay authority.

### v0.8 — Spell runtime

Goal: add generic deterministic spellcasting without named-mechanic special cases.

- known/prepared spells;
- spell slots;
- attack/save/automatic resolution;
- creature/self/area targeting;
- damage/healing/conditions;
- duration/concentration/ongoing effects;
- upcasting/scaling;
- spell events/RNG continuation;
- query/preview/command bridge;
- data-driven Godot spell UI.

Exit criteria: representative spell families cast deterministically through the authoritative bridge.

### v0.9 — Complete character creator

Goal: create and advance supported characters entirely from engine-supplied options.

- identity;
- species;
- background;
- class;
- ability scores;
- skills/proficiencies;
- starting equipment;
- spells/features;
- appearance hooks;
- biography/personality metadata;
- validation/review;
- level-up flow;
- engine-generated available choices rather than UI-hardcoded options.

Exit criteria: supported characters can be created and leveled entirely from canonical rules/content data.

### v1.0 — Playable RPG

Goal: ship one complete original adventure using the final architecture.

- exploration;
- tactical combat;
- dialogue;
- inventory/equipment;
- quests and branching state;
- shops/trade;
- rest;
- travel/area transitions;
- save/load;
- journal/map/party UI;
- original village + dungeon vertical campaign;
- multiple encounters including a boss;
- original characters, setting, art direction, and narrative;
- release packaging and attribution.

Exit criteria: a player can create/load a party and finish a small original campaign from beginning to end.

### v1.0.1 — Agent playtesting and observability

Goal: make the complete v1.0 campaign controllable and diagnosable by automated agents without
relaxing engine authority.

- provider-neutral structured agent observations;
- freshly computed legal-action tokens with stale-state protection;
- per-actor `human` / `agent` ownership, including AI-controlled heroes;
- tactical AI control for party members and NPC/enemy combatants;
- deterministic baseline policy that completes Lanterns Below end to end;
- structured asynchronous JSONL engine/agent logging;
- persistent structured Godot `ClientLog` JSONL output;
- opt-in loopback-only Godot UI automation/debug RPC;
- UI control-tree inspection, focus, activation/clicks, text input, mapped input, logs, screenshots;
- Python UI automation client/CLI for debugging agents;
- versioned agent/UI automation schemas and regression coverage.

Exit criteria: a deterministic agent can complete the test campaign through the authoritative action
API, and a debugging agent has a narrow localhost API capable of observing and operating the real
Godot UI while correlating client and engine disk logs.

## v1.x — Platform depth

### v1.1 — SRD coverage and conformance

- expand canonical coverage;
- close unsupported effect families;
- rules-conformance dashboard/report;
- content coverage by category;
- import/replay regression corpus;
- source-version migration tooling.

### v1.2 — Creator Studio

- campaign editor;
- map editor;
- character/NPC editor;
- creature editor;
- encounter editor;
- item/spell/ability editor;
- dialogue graph editor;
- quest graph editor;
- faction/loot tools;
- pack validation and export.

### v1.3 — Living world

- NPC schedules;
- perception;
- relationships;
- factions;
- reputation;
- world events;
- local economies;
- persistent consequences;
- durable NPC memory/state.

### v1.4 — Advanced AI

- utility AI;
- behavior/planning layers;
- tactical action scoring;
- group tactics;
- goals;
- perception-driven decisions;
- persistent memories;
- only legal actions supplied by the authoritative engine.

### v1.5 — Multiplayer

- authoritative game server;
- deterministic command/event synchronization;
- reconnect/resume;
- party ownership/permissions;
- spectators;
- campaign hosting;
- network version compatibility.

## v2.x — RPG creation platform

### v2.0 — Mod SDK

- stable content-pack schema;
- dependency/version resolution;
- safe extension points;
- documentation/examples;
- compatibility validation.

### v2.1 — Campaign marketplace foundations

- pack metadata;
- signatures/checksums;
- creator identity metadata;
- discovery/installation interfaces;
- licensing declarations;
- rating/review hooks without coupling the engine to one store.

### v2.2 — Dedicated servers

- standalone deployment;
- persistent campaign storage;
- backups;
- admin/observability interfaces;
- resource limits.

### v2.3 — Replay and spectator platform

- replay browser;
- timeline scrubbing;
- branch-from-replay tooling;
- spectator overlays;
- exportable deterministic scenario fixtures.

### v2.4 — AI dungeon-master integrations

- constrained world/encounter planning;
- narrative suggestions;
- encounter pacing inputs;
- rules-aware proposal validation;
- transparent human override;
- no direct authoritative-state mutation.

### v2.5 — AI NPC dialogue and character behavior

- persona/context interfaces;
- conversation policy hooks;
- goal/memory inputs;
- moderation/safety boundaries;
- deterministic state-changing choices routed through engine commands.

### v2.6 — Large campaigns and world streaming

- scalable campaign partitions;
- streamed area/content loading;
- long-lived event/history storage;
- incremental save/load;
- migration tooling.

### v2.7 — Cross-client/platform hardening

- alternate clients;
- dedicated-server compatibility;
- mobile/desktop presentation tiers;
- controller/touch accessibility refinements;
- protocol compatibility matrices.

### v2.8 — Creator collaboration

- collaborative editing;
- content review flows;
- pack dependency visualization;
- merge/conflict tooling;
- publish validation.

### v2.9 — Creator monetization foundations

- optional commerce integration boundaries;
- entitlement metadata;
- hosted-content policy hooks;
- creator payout/accounting interfaces outside the simulation core;
- offline/local content remains first-class.
