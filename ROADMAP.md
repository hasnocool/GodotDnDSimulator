# Roadmap

This roadmap defines the intended evolution of GodotDnDSimulator. Milestones are architectural commitments, not just version labels. Implementation work should normally map to one milestone and keep `TODO.md` and `CHANGELOG.md` synchronized.

## Product direction

GodotDnDSimulator is intended to become a deterministic isometric RPG platform with:

- a headless authoritative simulation engine;
- a Godot 4.x 3D orthographic client;
- licensed SRD rules ingestion and compilation;
- event-sourced saves/replays;
- tactical spatial authority independent of rendering;
- data-driven characters, abilities, spells, items, creatures, quests, and dialogue;
- campaign creation and mod/content-pack tooling;
- optional multiplayer and AI-driven narration/GM tooling that cannot bypass rules validation.

## v0.x — Foundation to first complete playable RPG

### v0.1 — Project foundation

Goal: establish the permanent architecture and developer workflow before feature growth.

- repository structure for apps/engine/content/schemas/tools/tests/docs;
- Godot 4.x project bootstrap;
- headless simulation package;
- typed command/event protocol;
- deterministic RNG/dice abstraction;
- state/snapshot/event serialization foundations;
- schema/version identifiers;
- logging and diagnostics conventions;
- CI for formatting, linting, tests, schema validation, and docs/governance checks;
- contribution, TODO, changelog, and Git workflow enforcement.

Exit criteria: a headless deterministic command can produce a reproducible event/state transition and CI validates it.

### v0.2 — Official SRD pipeline

Goal: create a reproducible, legally bounded rules ingestion pipeline.

- source allowlist;
- fetch approved SRD source;
- archive source metadata and hashes;
- extraction/normalization pipeline;
- heading/table/entity parsing;
- canonical schemas;
- provenance on every imported entity;
- validation and deterministic export;
- version-to-version diff tooling;
- licensing/attribution generation;
- unsupported-mechanic reporting;
- no runtime dependency on scraping or parsing source documents.

Exit criteria: the selected SRD can be transformed reproducibly into validated canonical data with provenance and a meaningful import report.

### v0.3 — Rules runtime

Goal: execute reusable rule primitives rather than prose or name-specific scripts.

- ability scores and modifiers;
- proficiency;
- d20 tests;
- advantage/disadvantage;
- difficulty classes;
- saving throws;
- generic modifiers;
- resources/costs;
- triggers;
- effects;
- durations;
- conditions;
- typed resolution contexts/outcomes;
- reaction/event hooks;
- ruleset capability declarations.

Exit criteria: representative imported mechanics execute through generic primitives with deterministic tests.

### v0.4 — Character runtime

Goal: represent playable and non-playable actors using the same core model.

- actor identity;
- ability scores;
- skills/proficiencies;
- hit points and temporary hit points;
- armor class and defenses;
- speeds/movement modes;
- senses;
- equipment/inventory;
- conditions/effects;
- resources;
- class/species/background data;
- features and advancement model;
- initial character creation domain API.

Exit criteria: a character can be created, serialized, loaded, modified by rules, and tested without Godot UI.

### v0.5 — Tactical combat

Goal: implement a deterministic encounter loop.

- initiative;
- rounds/turns;
- action economy;
- movement accounting;
- attacks;
- damage/healing;
- resistances/immunities/vulnerabilities where licensed rules require them;
- reactions and reaction windows;
- conditions in combat;
- incapacitation/death-state handling;
- encounter lifecycle;
- combat log/events;
- replay fixtures.

Exit criteria: representative multi-round combats replay to identical results from the same seed/events.

### v0.6 — Spatial authority

Goal: make tactical legality independent of rendering/navigation implementation.

- logical grid/space abstraction;
- occupancy;
- distance/reach;
- path legality;
- movement cost;
- difficult terrain;
- elevation;
- collision boundaries;
- line of sight;
- cover;
- areas of effect;
- climbing/swimming/flying abstractions;
- threat/opportunity interaction inputs;
- adapters between Godot navigation and logical spatial state.

Exit criteria: movement, targeting, LOS, cover, and AoE scenarios are testable headlessly.

### v0.7 — Godot vertical slice

Goal: make the architecture visibly playable without bypassing the engine.

- Godot 4.x 3D project;
- orthographic isometric camera;
- pan/zoom/rotation;
- one small tactical map;
- actors rendered from engine state;
- selection and movement preview;
- command submission to engine;
- turn/combat HUD;
- action bar;
- basic animations, VFX, audio hooks;
- roof/wall occlusion strategy;
- debug overlays for grid, path, LOS, cover, and engine IDs.

Exit criteria: a complete small battle can be played through Godot while outcomes remain engine-authoritative.

### v0.8 — Spell runtime

Goal: support spells through generic mechanics instead of spell-name conditionals.

- spell resources/slots;
- preparation/known-spell model as required by supported content;
- spell attacks and saves;
- target selectors;
- shapes/areas;
- durations;
- concentration;
- ongoing/triggered effects;
- scaling/upcasting representation;
- spell UI and previews;
- conformance coverage for representative effect families.

Exit criteria: a broad sample of imported spells executes using reusable effect primitives.

### v0.9 — Complete character creator

Goal: provide a rules-driven character creation and advancement flow.

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

### v2.3 — Procedural world generation

- deterministic seeds;
- generated encounters/locations;
- content constraints;
- authored + generated hybrid workflows.

### v2.4 — AI Dungeon Master

- typed read/query tools;
- legal command submission;
- encounter/dialogue suggestions;
- narration;
- strict separation from authoritative state mutation;
- local-model support where practical.

### v2.5 — AI NPC dialogue

- bounded character knowledge;
- memories/relationships;
- structured dialogue outcomes;
- content moderation/safety boundaries;
- deterministic game-state consequences through commands only.

### v2.6 — Community campaigns

- pack discovery;
- dependency installation;
- compatibility checks;
- save isolation;
- migration support.

### v2.7 — Persistent worlds

- long-running world simulation;
- scheduled world events;
- shard/instance strategy;
- persistent faction/NPC state.

### v2.8 — Hosted multiplayer

- deployable hosted service architecture;
- tenancy and campaign isolation;
- operational metrics;
- backups/restore;
- quotas and billing hooks.

### v2.9 — Creator monetization

- marketplace transaction interfaces;
- creator revenue metadata;
- entitlement hooks;
- premium campaign/DLC support;
- optional hosted/AI service monetization.

## First playable vertical slice

Before broad SRD coverage, prove the architecture with:

- one small original village;
- one dungeon;
- one exploration/investigation path;
- one dialogue/skill-check interaction;
- one trap or environmental obstacle;
- one locked/conditional interaction;
- three tactical encounters;
- one boss encounter;
- one quest with at least one branch/consequence;
- four premade heroes;
- a small representative subset of classes/creatures/spells/items/conditions.

The slice must use production architecture: no throwaway rules engine, UI-owned combat outcomes, or hardcoded spell-name logic.

## Roadmap change policy

A roadmap change should explain:

- why the current plan is insufficient;
- what milestone ownership changes;
- compatibility/migration impact;
- whether it increases or reduces near-term scope;
- required TODO/documentation updates.

Do not silently move unfinished work to later versions to make a milestone appear complete.
