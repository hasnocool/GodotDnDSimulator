# Changelog

All notable changes to this project will be documented in this file.

The format follows the spirit of [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the
project uses semantic versioning as documented in `docs/adr/0002-versioning.md`.

## [Unreleased]

### Fixed

- Tactical Move, Strike, End Turn, and spell actions now follow the authoritative current-turn actor
  instead of the actor selected only for inspection, preventing the whole action bar from becoming
  disabled when selection and initiative differ.

## [1.0.0] - 2026-08-23

### Added

- Python 3.12 authoritative headless simulation engine with typed commands/events/state, immutable
  reducers, versioned deterministic `pcg32-v1` RNG/dice, snapshot/event replay, schemas, and strict
  validation.
- Licensed SRD 5.2.1 ingestion infrastructure with source allowlisting, async resumable fetch/cache,
  pinned checksums, PDF extraction/normalization with provenance, versioned canonical rule schemas,
  deterministic compiler/export/reporting, attribution output, source-version diffing, and mocked
  regression coverage.
- Typed v0.3 rules runtime for D20 resolution, modifiers, resources/costs, requirements, selectors,
  effects, conditions, durations, reactions, and capability declarations.
- Shared immutable v0.4 actor runtime for heroes/NPCs/creatures with stats, HP/AC, skills,
  proficiencies, movement, senses, inventory/equipment, resources/effects/conditions, character
  options, creation, serialization, and migrations.
- Deterministic event-sourced v0.5 tactical combat with initiative/turns, action economy, attacks,
  damage/healing, defenses, reactions, conditions, zero-HP policy, event replay, and combat schemas.
- Authoritative v0.6 spatial runtime with occupancy/footprints, distance/reach, terrain/elevation,
  movement/pathfinding/reachable queries, LOS/cover, generic sphere/cube/cylinder/cone/line areas,
  movement modes, navigation proposals, threat transitions, spatial events/replay, and combat
  integration.
- Authoritative `spatial.path` segment metadata including per-step cost, terrain ID, difficult-terrain
  state, elevation delta, and movement mode for client presentation without local cost inference.
- Versioned Godot client bridge with capability negotiation, typed command/query/preview requests,
  cancellation/timeouts, stale-response rejection, reconnect/resync, fake transport, and non-blocking
  localhost TCP transport.
- Godot client state architecture with separate authoritative mirror, interaction state, presentation
  state, lifecycle-aware app shell, asynchronous scene loading, settings, and diagnostics.
- Semantic remappable keyboard/mouse/controller input plus centralized cancellable interaction modes
  and duplicate-safe command intent submission.
- v0.7 Godot tactical vertical slice with true 3D orthographic/isometric camera, aspect-ratio-aware
  bounds, tactical map/terrain presentation, stable-ID actors, selection/picking, movement/path and
  target/LOS/cover/AoE previews, engine-driven HUD/action bar, presentation events, VFX/audio hooks,
  foreground occlusion, and developer overlays.
- Reusable presentation-only map-entry spawn-anchor resources for all six Lanterns Below areas.
- Non-color actor faction emblems, dedicated condition/status presentation slots, and debug labels
  for stable actor IDs plus authoritative condition/rule IDs.
- Automatic movement, target, and shape preview refresh after unrelated authoritative state updates,
  controller-only target traversal, and generic sphere/cylinder/cone/line origin/rotation controls.
- Tactical HUD rows for authoritative conditions, action/bonus/reaction economy, generic resources,
  and ongoing spell effects.
- User-debug-toggle-expanded combat log with event sequence/type/stable IDs plus replay/resync
  de-duplication keys.
- Generic movement, damage, healing, miss, status, and status-expiry tactical VFX primitives.
- Occupancy, stable-ID, FPS, request-latency, and navigation-adapter-versus-authoritative-path debug
  diagnostics.
- v0.8 spell runtime with slots, known/prepared spells, attacks/saves/healing/conditions,
  concentration/duration/ongoing effects, authoritative targeting/AoE previews, upcasting/scaling,
  event serialization, RNG continuation, and Godot spell interaction.
- Spell palette grouping by engine-provided legal cast slot with data-driven range, target, area,
  duration, concentration, and upcast tooltips.
- v0.9 engine-driven character creator with identity/species/background/class/abilities/skills/
  equipment/spell-feature choices, profile metadata, authoritative review/create, level-up, external
  catalog adapters, record schema, and Godot UI.
- v1.0 deterministic world/campaign runtime and Godot Adventure shell covering exploration, travel,
  dialogue, quests, interactions, rest, shops, party/inventory/equipment, journal/map/party screens,
  credits, and world snapshot/replay integration.
- Production Godot manual save/load with three fixed slots, engine-produced lossless snapshot JSON,
  threaded bounded disk I/O, versioned envelopes, temporary/backup replacement, recovery, and
  authoritative `world.load` validation.
- Engine-owned equipment compatibility and legal equipment-option queries, two-way Buy/Sell shop UX,
  authoritative exploration availability/reasons, and encounter begin/completion intent controls.
- Four deterministic authored v1.0 world tactical templates: Road Ambush, Quarry Watchers,
  Underworks Swarm, and The Hollow Warden. Each has distinct map/terrain/enemy/placement data and
  uses the actual selected `CharacterRecord.actor` party instead of Ember/Shale proxy heroes.
- Deterministic source-release packaging with credits, tracked attribution files, SHA-256 manifest,
  sensitive/untracked file exclusion, and exclusion of the development Godot MCP addon.
- Expanded Python and Godot headless regression matrix for authored encounters, spatial path segment
  metadata, tactical backlog presentation, navigation comparison, stable debug identities, spell
  slot grouping, v1.0 campaign completion, and save/load.
- `docs/TODO_BACKLOG_COMPLETION.md` documenting completed code-backed TODOs and the remaining
  execution/provenance/profiling/conditional evidence gates.

### Changed

- Development version is `1.0.0.dev0`, with v0.1-v1.0 implementation present and active TODOs now
  focused on evidence/provenance/admin/conditional work rather than stale implementation checkboxes.
- Root and Godot-client TODOs were compacted into implemented milestone summaries plus every genuine
  remaining open obligation.
- World encounter startup now returns a fresh tactical snapshot, preserves monotonically advancing
  tactical mirror sequence handoff, uses distinct authored tactical templates, and binds tactical
  victory to `team:party`.
- `world.actions` and equipment/shop surfaces expose presentation-safe authoritative choices,
  availability, ownership, stock, and rejection reasons while leaving legality in Python.
- Godot tactical teardown explicitly cancels scene-owned previews and disconnects subscriptions so a
  reconstructed scene cannot apply stale results or duplicate event handlers.
- Local CI now registers all bridge/state/input/camera/HUD/tactical/spell/creator/world/save suites,
  including the new TODO-backlog diagnostic and spell-grouping regressions.

### Removed

- The obsolete `apps/godot-client/scripts/main.gd` bootstrap after replacement by the lifecycle-aware
  C2 app shell.
- Reliance on the Sunken Courtyard Ember/Shale proxy session for v1.0 world encounter gates.

### Fixed

- Godot TCP bridge negotiation now accepts integral JSON numbers parsed as floats, preventing valid
  Python bridge responses from being rejected before capability negotiation.
- Snapshot restore and replay preserve exact deterministic RNG continuation rather than restoring
  visible state alone.
- Client bridge/mirror sequencing rejects stale/gapped authority while accepting integral JSON
  numbers safely.
- Pending query/preview/command state reconciles correctly across cancellation, rejection,
  disconnect, reconnect, and scene teardown.
- Godot production saves preserve 64-bit RNG integers by persisting engine-owned canonical snapshot
  text and never optimistically applying local file contents.
- Tactical encounter startup resynchronizes the client mirror with the newly created authoritative
  encounter instead of leaving the previous ended tactical state visible.
- World travel/rest/dialogue/interaction/shop/equipment changes and world save loading are blocked
  while an active tactical encounter would make the world/tactical streams inconsistent.
- Older otherwise-compatible world hosts that do not advertise equipment-option capability retain a
  usable legacy slot-ID fallback instead of disabling equipment completely.
- Release packaging derives input from tracked allowlisted files, rejects unsafe paths/symlinks, and
  cannot accidentally publish local `.env`, export, signing, cache, or development-addon files.
- Active previews re-query after unrelated authority changes and use the refreshed authoritative
  sequence when arming commands.

### Security

- Strict validation is applied at command, event, snapshot, identifier, replay, rules, actor, combat,
  spatial, spell, creator, world, equipment, and save/load boundaries.
- Rules ingestion rejects unapproved sources/hosts/licenses, checksum drift, cache-manifest mismatch,
  unexpected media types, and source tampering.
- Release packaging uses tracked-file allowlisting and explicit exclusions rather than recursively
  archiving the developer working directory.
- Godot save/load accepts only fixed slot IDs, bounds files to the bridge-compatible limit, validates
  a versioned envelope, and still requires authoritative engine validation before displayed state
  changes.
- Secret scanning, dependency audit workflow, and Dependabot configuration are part of repository
  validation/security maintenance.

<!--
Release process notes:
- Move applicable Unreleased entries into a versioned section when tagging a release.
- Add the release date in YYYY-MM-DD format.
- Never mark a feature as released before its tag/release exists.
- Do not rewrite historical released sections except for factual corrections.
-->
