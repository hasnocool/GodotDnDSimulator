# TODO Backlog Completion

This document records the implementation sweep that follows the v1.0 playable-RPG client work.
It distinguishes repository/code completion from evidence gates that cannot be satisfied merely by
checking in more code.

## v1.0 authored tactical encounters

The world bridge no longer reuses the Sunken Courtyard proxy for every campaign encounter.
`engine/src/godot_dnd_engine/world/tactical_templates.py` defines deterministic authored tactical
specifications for:

- `encounter:road-ambush` / `space:old-road-ambush`;
- `encounter:quarry-watchers` / `space:quarry-mouth-watch`;
- `encounter:underworks-swarm` / `space:flooded-underworks-swarm`;
- `encounter:vault-warden` / `space:lantern-vault-warden`.

Each template has distinct enemy IDs, terrain, placements, display metadata, and seeded tactical
state. Encounter startup uses the actual `CharacterRecord.actor` values selected in the active world
party, tags those combatants as `team:party`, returns the fresh tactical snapshot to the client, and
keeps world completion gated on an authoritative tactical victory by that party team.

`tests/test_world_tactical_templates.py` checks template uniqueness, party identity, absence of the
old proxy actors, and deterministic same-seed snapshots. `tests/test_v1_completion.py` checks that a
world encounter starts the correct authored template and resynchronizes the tactical stream.

## Godot client backlog implemented in this sweep

The presentation layer gained the remaining code-backed tactical polish without taking authority
from the engine:

- reusable map-entry spawn-anchor resources for all six Lanterns Below areas;
- aspect-ratio-aware camera padding for extreme viewport shapes;
- non-color team/faction emblems plus dedicated actor condition/status presentation;
- debug labels for stable actor IDs, condition/rule IDs, spatial coordinates, and terrain/content IDs;
- pointer picking that is not intercepted by presentation-only faded occluders;
- automatic movement, target, and shape preview refresh after unrelated authoritative updates;
- authoritative per-segment path cost/terrain/elevation/movement-mode metadata;
- generic sphere/cylinder/cone/line origin and rotation controls using `spatial.area` previews;
- controller-only target traversal through the shared semantic Context action;
- dedicated HUD condition, action-economy, resource, and ongoing-effect rows;
- spell actions grouped by engine-provided legal slot level with detailed data-driven tooltips;
- replay/resync de-duplication keys and a debug-toggle-expanded combat log showing event sequence,
  event type, and stable IDs;
- generic movement, damage, healing, miss, status, and status-expiry VFX primitives;
- occupancy and stable-ID debug layers;
- debug-only navigation adapter versus authoritative-path disagreement visualization;
- bridge request-batch latency and FPS diagnostics;
- explicit cancellation of scene-owned previews during tactical teardown;
- headless marker-content and tactical scene teardown/reload regressions.

The client still never decides path legality, target legality, cover, LOS, AoE membership, action
availability, spell legality, or combat outcomes.

## Local validation wiring

`scripts/local_ci.sh` now includes the additional headless suites for the backlog work, including:

- `todo_backlog_tests.gd`;
- `navigation_debug_tests.gd`;
- `debug_identity_tests.gd`;
- `spell_palette_grouping_tests.gd`;
- the expanded tactical vertical-slice and HUD suites.

Python regression coverage also includes authored world tactical templates and authoritative spatial
path-segment metadata.

## Items intentionally still open

The following categories are not missing implementation and must not be checked merely because this
sweep exists:

1. **Exact-head executable gates.** They require Ruff/Mypy/pytest/governance/importer and Godot to
   actually execute on the integrated head. The hosted repository runner has repeatedly terminated
   before job step 1, and the current agent execution container cannot resolve GitHub to obtain a
   local checkout.
2. **Manual/interactive acceptance.** Interactive Godot playthrough and supported UI-scale visual
   passes need a real Godot desktop session.
3. **Measured optimization gates.** Actor pooling, frame-time baselines, scene-load timing, and
   measured preview latency must be driven by profiling evidence rather than guessed optimization.
4. **Official SRD production audit.** The pinned official-source fetch, complete 364-page production
   import/audit, and production-catalog replacement remain provenance/audit work rather than client
   implementation work.
5. **Repository administration.** Repository label creation depends on GitHub administrative tooling
   not exposed by the current connected actions.
6. **Conditional save-product work.** Autosave retention policy and future save migration/export/
   import remain conditional on an explicit product/format requirement; the current v1 manual save
   envelope is already versioned and production-safe.

These open evidence/conditional items remain visible in the root/client TODOs rather than being
misrepresented as completed code.
