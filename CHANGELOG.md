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
- Typed v0.3 rules runtime with ability scores, proficiency, generic D20 tests, DC/save resolution, and deterministic advantage/disadvantage.
- Generic deterministic modifier pipeline with explicit set/add/minimum/maximum operations, priority, stacking groups, and applied/suppressed audit output.
- Immutable lightweight rule subject/world state with bounded resources, atomic resource costs, generic requirements, deterministic target selectors, and ruleset capability declarations.
- Generic effect pipeline for resource deltas and condition application/removal, including unique/refresh/stack semantics and deterministic duration expiry.
- Trigger and reaction-hook matching with requirement gating and deterministic reaction priority.
- Representative v0.2 `CanonicalEntity`-shaped conformance fixtures that drive v0.3 executable mechanics without runtime dependency on importer code.
- `docs/V0.3_RULES_RUNTIME.md` documenting runtime boundaries, stacking/effect semantics, determinism, conformance, and the v0.4 handoff.
- Shared immutable v0.4 `ActorState` for heroes, NPCs, and creatures with abilities, HP/temp HP/AC, skills, saves, generic proficiencies, movement, senses, inventory/equipment, resources, conditions, options, and tags.
- Actor adapters that reuse the v0.3 `RuleSubjectState`/effect pipeline for deterministic resource and condition updates without duplicating rules logic.
- Data-driven character options and choice groups with cardinality, requirement, conflict, and granted-tag validation.
- Initial headless `CharacterCreationSpec`/`CharacterCreationRequest`/`create_character()` API.
- Versioned actor serialization (`schema_version: 1`), `schemas/v1/actor.schema.json`, canonical JSON output, and explicit v0-to-v1 migration support.
- v0.4 actor/character regression coverage for shared state, effects, choices, creation, serialization, migrations, and malformed-input rejection.
- `docs/V0.4_CHARACTER_RUNTIME.md` documenting the shared actor model, rule adapters, creation API, serialization, and v0.5/v0.6 handoff.
- Deterministic v0.5 tactical-combat runtime with encounter lifecycle, initiative, rounds/turns, action economy, movement-budget accounting, reaction windows, abstract attacks, damage/healing, defenses, conditions, and supported zero-HP state transitions.
- Versioned `CombatEvent` v1 contract, pure reducer, canonical JSON/JSONL event serialization, and snapshot-independent deterministic combat replay from a preparing encounter state.
- Generic defense profiles for data-driven resistance, immunity, and vulnerability handling plus explicit temporary-hit-point replacement choice.
- Combat regression coverage using real `pcg32-v1` seeds for initiative, attack-roll edge cases, damage/healing, death-save state, reactions, malformed inputs, event serialization, and replay parity.
- `schemas/v1/combat-event.schema.json` and `docs/V0.5_TACTICAL_COMBAT.md` documenting the combat/event boundary and v0.6 spatial handoff.
- Godot-client-local `AGENTS.md` defining the presentation/engine authority boundary, bridge/state/input architecture, testing rules, performance guidance, UX/accessibility expectations, and client PR definition of done.
- Detailed `apps/godot-client/TODO.md` covering client architecture and execution from the v0.7 tactical vertical slice through spell UI, complete character creation, and the v1.0 RPG shell.
- Versioned Godot client bridge v1 with request/correlation/generation IDs, capability negotiation, categorized failures, timeout/cancellation handling, ordered authoritative snapshot/event ingestion, and reconnect/resync semantics.
- Transport-independent Godot `EngineBridge`, deterministic fake transport, and non-blocking newline-delimited JSON/TCP local transport.
- Standard-library `asyncio` authoritative bridge host over `SimulationEngine`, exposed as `godot-dnd-client-bridge`, with command submission plus snapshot/resync/capability queries.
- Client bridge v1 JSON Schema, deterministic snapshot/event fixtures, Python localhost TCP tests, and headless Godot bridge lifecycle tests.
- `docs/GODOT_CLIENT_BRIDGE.md` documenting the client/engine authority boundary, bridge protocol, transport, synchronization, errors, local host, and v0.6/v0.7 extension path.
- C2 Godot client state architecture with deep-copy `AuthoritativeMirror`, explicit `InteractionState`, presentation-only `PresentationState`, and a bridge-backed `ClientStateCoordinator`.
- Lifecycle-aware Godot `AppShell` with startup, bridge initialization, synchronization, loading, ready, incompatible, error, retry, and shutdown states.
- Asynchronous tactical presentation entry loading, scene reconstruction from snapshot-plus-event mirror state, local presentation/accessibility settings, structured client diagnostics, and a debug overlay for bridge/state visibility.
- Headless C2 state/shell tests covering state separation, cancellation, presentation independence, shell startup/synchronization, scene reconstruction, diagnostics, and shutdown.
- `docs/GODOT_CLIENT_STATE_SHELL.md` documenting C2 ownership, lifecycle, reconstruction, settings, diagnostics, deliberate non-goals, and C3 handoff.
- Deterministic v0.6 headless spatial authority with a backend-independent logical-space protocol, bounded square-grid implementation, multi-cell footprints, occupancy, collision, distance/reach, terrain, elevation, movement modes, path legality, pathfinding, movement cost, and reachable-space queries.
- Elevation-aware logical LOS, explicit cover classifications, and reusable sphere/cube/cylinder/cone/line area queries with no named ability special cases.
- Geometric threat-zone entry/exit inputs, a Godot/navigation proposal contract that remains subordinate to engine validation, and a JSON-shaped `SpatialQueryService` for client/tool integration.
- Versioned `SpatialEvent` v1 movement facts, pure reducer, canonical JSON/JSONL serialization, deterministic spatial replay, and `schemas/v1/spatial-event.schema.json`.
- Narrow v0.5/v0.6 movement integration that validates the spatial route first and spends the exact authoritative cost through the existing combat movement-budget API.
- Headless spatial conformance, adversarial validation, replay, query, navigation-proposal, and combat-integration test suites plus `docs/V0.6_SPATIAL_AUTHORITY.md`.
- C3 semantic Godot input actions with keyboard, mouse, D-pad, analog-stick, and controller-button defaults plus descriptor-based persistent remapping under `user://`.
- Centralized C3 `ClientInteractionController` with inspect/select/move/target/shape/modal modes, generation-scoped transitions, mode-owned cancellation, UI-focus protection, and single-submit command intents.
- Authoritative command-completion reconciliation so rejected intents remain correctable/retryable while accepted transient interactions return to selection only after engine acceptance.
- Headless C3 input/interaction tests covering remapping, modal/focus safety, cancellation, duplicate confirmations, rejection retry, acceptance reconciliation, and selection preservation.
- `docs/GODOT_CLIENT_INPUT.md` documenting C3 semantic actions, remapping, interaction modes, UI focus/modal behavior, command lifecycle, authority boundary, and C4 handoff.
- v0.7 authoritative Godot tactical vertical slice with isometric camera, tactical map, actor rendering, movement/path previews, targeting, action HUD, presentation events, occlusion, and a complete small battle that delegates gameplay legality to the Python engine.
- v0.8 generic spellcasting domain with known/prepared spell state, levelled spell slots, spell attack/save metadata, generic target selectors, duration/concentration state, ongoing effects, and upcasting/scaling representation.
- `SpellRuntime` composition over the existing v0.3 rules, v0.4 actors, v0.5 combat, and v0.6 spatial authority for deterministic spell attacks, saves, damage, healing, conditions, range, LOS, and AoE membership.
- Versioned `SpellEvent` v1 serialization with RNG checkpoints and `schemas/v1/spell-event.schema.json` for deterministic random-stream continuation.
- Transport-neutral `SpellQueryService`, spell-enabled tactical session/bridge capabilities, and authoritative `spells.available` / `spells.preview` / `tactical.cast_spell` contracts.
- Godot spell palette and tactical spell interaction layer generated from engine-provided spell/slot metadata, with engine-approved creature/point/AoE previews required before command submission.
- Original representative spell fixtures and Python/Godot regression coverage for attack, save-for-half, healing, concentration, conditions, ongoing durations, area membership, and upcasting.
- `docs/V0.8_SPELL_RUNTIME.md` documenting v0.8 mechanics, authority boundaries, bridge/UI contracts, determinism, and validation expectations.
- v0.9 authoritative character creator domain with data-driven creation steps, groups, choice requirements/conflicts, ability-score policies, profile metadata, and level-up choices.
- `CharacterCreatorRuntime` that composes validated creation selections into the existing immutable v0.4 `ActorState` and advances level/proficiency/HP/options without introducing Godot authority.
- `CharacterCreatorService` plus additive `characters.creator.v1`, `characters.creator.commands.v1`, and `characters.levelup.v1` bridge capabilities for schema, preview, create, record, and level-up flows.
- External creator-catalog serialization/deserialization adapters so audited canonical rules data and original content packs can drive the same runtime without code or Godot changes.
- Capability-gated Godot character creator overlay with engine-generated species/background/class/skill/equipment/spell-feature controls, ability assignment, appearance hooks, biography/personality, review validation, creation, and level-up UI.
- `schemas/v1/character-record.schema.json`, Python creator/bridge/schema regressions, and `res://tests/character_creator_tests.gd` headless client coverage.
- `docs/V0.9_CHARACTER_CREATOR.md` documenting creator authority, data contracts, bridge/UI flow, validation, and v1.0 handoff.
- Restored `.github/workflows/ci.yml` with Python/governance and Godot headless jobs so future PR heads can be validated when repository Actions runners execute normally.

### Changed

- `README.md` documents the executable architecture and local validation workflow.
- Release policy is semantic repository versioning plus independent serialized-contract/RNG algorithm versions.
- Development version advances to `0.9.0.dev0`; validation now includes creator runtime, character-record schema, and headless creator interaction suites.
- Rules-source PDF caches are explicitly ignored so raw upstream documents are fetched and verified rather than committed accidentally.
- Active implementation advances through v0.9 complete character creator while unfinished earlier CI/full-source audit items remain tracked as carryover.
- v0.5 movement-budget accounting has a v0.6 integration path where headless spatial authority validates route legality/cost before `CombatRuntime` spends movement.
- Root agent governance plus Claude, Gemini, and Copilot adapters require the local Godot client contract and TODO to be read before editing `apps/godot-client/**`.
- Godot validation now includes the client bridge, state/shell, input/interaction, camera, v0.7 tactical slice, v0.8 spell interaction, and v0.9 character creator suites.
- The default `godot-dnd-client-bridge` entry point now uses the v0.9 character-aware host; `--core-only` disables tactical/spell providers while retaining character-creator services.

### Deprecated

- None yet.

### Removed

- The obsolete `apps/godot-client/scripts/main.gd` presentation bootstrap after replacement by the C2 app shell.

### Fixed

- Snapshot restore resumes the deterministic RNG stream instead of only restoring visible game state.
- Replaying events after an older snapshot advances RNG state through recorded event checkpoints before future commands execute.
- Raw tactical input no longer acts while a Godot UI control owns focus, and repeated confirmation while an authoritative command is pending cannot create a second submission from the same armed intent.
- Godot bridge and authoritative-mirror sequence validation accepts integral numbers decoded from JSON while rejecting fractional values, and standalone client tests no longer depend on editor class-cache or autoload compilation order.
- Bridge request failures reconcile interaction state by request ID so cancelling a correlated preview cannot reject or unlock a still-pending authoritative command.
- Submitted authoritative commands are never treated as mode-cancellable preview/query requests.
- Stale query/preview results are filtered against the current interaction generation before presentation receives them.
- Spell duration state retains the actual cast slot level so ongoing upcast effects do not silently fall back to the base spell level.
- Spell RNG consumption is checkpointed in the spell event stream so replay/resume tooling can restore the exact future deterministic random stream.
- Removed an unresolved changelog merge marker left from earlier integration history.
- Creator catalog deserialization converts malformed enum/content values into project validation errors instead of leaking raw enum exceptions across the content boundary.

### Security

- Added strict validation at command, event, snapshot, identifier, dice, and replay boundaries to reject malformed/untrusted input early.
- Rules ingestion rejects unallowlisted source IDs, non-official/incorrectly licensed policies, non-HTTPS or unexpected hosts, unexpected media types, checksum drift, cache-manifest mismatches, and post-manifest source tampering.
- Rules runtime primitives fail closed on malformed ability/DC/proficiency/resource/modifier/duration/condition/selector/effect/hook/capability inputs and preserve original immutable state when effect or cost resolution fails.
- Character runtime rejects malformed actor identity/state, duplicate abilities/proficiencies/movement/senses/resources/options, invalid inventory/equipment references, invalid option catalogs, and unsupported/corrupt actor serialization versions.
- Tactical combat rejects malformed encounter/event/attack/damage/reaction inputs, non-contiguous replay events, illegal turn ownership/resource use, and unsupported combat event schema versions.
- Client bridge validation rejects incompatible protocol versions, malformed envelopes/state payloads, regressing snapshots, stale/duplicate responses, and non-contiguous authoritative event batches rather than guessing client state.
- Client authoritative-mirror getters return deep copies and reject regressing snapshots/event gaps so presentation code cannot mutate stored engine state through shared dictionaries or partially advance reconstruction state.
- Spatial authority fails closed on malformed spaces, footprints, overlaps, movement modes, stale navigation proposals, blocked/over-budget paths, non-contiguous or corrupt movement events, invalid area shapes, and unsupported read-only spatial queries.
- Spell authority rejects unknown/unprepared spells, unavailable slots/actions, invalid target counts/selectors, out-of-range/non-visible targets, invalid points/shapes, stale sequence intent, and malformed spell event/checkpoint payloads rather than allowing Godot to infer legality.
- Character creator authority rejects unknown choices, invalid group cardinality, unmet requirements/conflicts, malformed ability assignments/catalog data, duplicate actor IDs, unsupported advancement choices, and invalid profile payloads before creating or advancing an actor.

<!--
Release process notes:
- Move applicable Unreleased entries into a versioned section when tagging a release.
- Add the release date in YYYY-MM-DD format.
- Never mark a feature as released before its tag/release exists.
- Do not rewrite historical sections except for factual corrections.
-->
