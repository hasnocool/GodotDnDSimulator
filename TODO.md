# TODO

This is the active execution backlog for `ROADMAP.md`. Keep it synchronized with implementation.
Do not check an item merely because scaffolding exists, and do not leave implemented work unchecked
when repository tests/code provide direct evidence.

## Current focus: v1.0 Playable RPG

The v0.1 foundation through v1.0 playable-RPG implementation are present. The v1.0 world campaign
now launches four distinct authored tactical encounters using the actual selected party rather than
reusing the Sunken Courtyard proxy. Remaining open work is limited to repository administration,
full official-source audit/provenance, exact-head executable evidence, manual desktop acceptance,
profiling-dependent optimization, and explicitly conditional future save-product requirements.

Implementation/evidence details for the final code-backed backlog sweep are in
`docs/TODO_BACKLOG_COMPLETION.md`.

---

## Implemented milestone summary

### v0.1 Project foundation

- [x] Repository/governance/documentation foundation.
- [x] Headless Python 3.12 engine and Godot 4.x presentation project structure.
- [x] Typed command/event/state contracts, deterministic RNG/dice, reducer boundary, snapshots,
      replay, schemas, validation, developer tooling, CI definitions, and security checks.

### v0.2 Official SRD pipeline implementation

- [x] Approved-source allowlist and licensing/attribution boundary.
- [x] Async resumable fetch/cache/checksum infrastructure.
- [x] PDF extraction/normalization with provenance.
- [x] Versioned canonical schemas and deterministic compiler/export/reporting/diff pipeline.
- [x] Mocked source/policy/extraction/compiler/schema/report/diff/tamper regression coverage.
- [x] Deterministic importer fixture smoke build.

### v0.3 Rules runtime

- [x] Typed deterministic D20/modifier/resource/requirement/target/effect/duration/condition/reaction
      runtime with capability declarations and canonical-entity-shaped conformance fixtures.

### v0.4 Character runtime

- [x] Shared immutable hero/NPC/creature actor model, stats, HP/AC, skills, movement, senses,
      inventory/equipment, conditions/resources/effects, choices, creation, serialization, and
      migration coverage.

### v0.5 Tactical combat

- [x] Deterministic event-sourced encounter lifecycle, initiative/turns, action economy, movement
      accounting, attacks, damage/healing, defenses, reactions, conditions, zero-HP policy, replay,
      schemas, and adversarial coverage.

### v0.6 Spatial authority

- [x] Grid/occupancy/footprints, distance/reach, terrain/elevation, movement/pathfinding/reachable,
      LOS/cover, generic AoE shapes, movement modes, navigation proposals, threat transitions,
      spatial events/replay, read-only query service, and combat integration.
- [x] Validate `schemas/v1/spatial-event.schema.json` against representative serialized movement
      events in `tests/test_spatial_schema.py`.
- [x] Expose authoritative per-segment path cost, terrain, elevation delta, and movement-mode data
      for client previews with regression coverage.

### v0.7 Godot vertical slice

- [x] Orthographic/isometric tactical camera, pan/zoom/rotation/focus and aspect-ratio-aware bounds.
- [x] Original tactical map, authoritative actor rendering, selection/picking, movement/path previews,
      target/LOS/cover/AoE presentation, action HUD, combat log, VFX/audio hooks, occlusion, and debug
      overlays without client-side rules authority.
- [x] Headless bridge/state/input/camera/HUD/tactical integration suites are registered in local CI.

### v0.8 Spell runtime

- [x] Spell slots/known/prepared state, attack/save/healing/condition/ongoing/concentration/duration,
      targeting/AoE, upcasting/scaling, event serialization/RNG continuation, bridge queries/previews,
      and Godot spell UI.
- [x] Godot spell UI renders concentration and generic ongoing effects and groups actions by
      engine-provided legal slot level with data-driven tooltips.

### v0.9 Complete character creator

- [x] Engine-driven identity/species/background/class/abilities/skills/equipment/spell-feature steps,
      appearance/profile metadata, authoritative review/create, level-up, external catalog adapter,
      versioned record schema, bridge integration, and headless Godot creator UI.
- [x] Representative `CharacterRecord` schema regression exists in `tests/test_character_schema.py`.

### v1.0 Playable RPG

- [x] Exploration loop.
- [x] Dialogue system.
- [x] Quest state machine/branching consequences.
- [x] Inventory/equipment UI.
- [x] Trade/shop flow.
- [x] Rest flow.
- [x] Travel/area transitions.
- [x] Journal/map/party screens.
- [x] Production manual save/load UX.
- [x] Original village area.
- [x] Original dungeon area.
- [x] Skill-check interaction.
- [x] Trap/environment interaction.
- [x] Three authored tactical encounters bound to distinct world encounter gates.
- [x] Authored boss tactical encounter bound to the boss gate.
- [x] One branching quest.
- [x] Four premade heroes.
- [x] Release packaging/attribution/credits.
- [x] End-to-end world-campaign completion test including save/restore continuation.

### v1.0 implementation evidence

- `engine/src/godot_dnd_engine/world/tactical_templates.py` defines deterministic Road Ambush,
  Quarry Watchers, Underworks Swarm, and Hollow Warden tactical templates with distinct maps,
  enemies, terrain, placements, and selected-party combatants.
- `tests/test_world_tactical_templates.py` verifies template uniqueness, actual party identity, no
  proxy actors, and deterministic same-seed snapshots.
- `tests/test_v1_completion.py` verifies the original campaign loop, authoritative world/tactical
  handoff, branch choice, save/restore parity, encounter progression, and final campaign-complete
  state.
- `apps/godot-client/tests/world_rpg_completion_tests.gd` verifies the Adventure presentation and
  intent boundary.
- `scripts/package_v1_release.py` builds the deterministic tracked-file release source bundle with
  attribution and development-addon exclusions.

---

## Remaining repository/admin work

- [ ] Add repository labels for roadmap milestones, subsystem, type, and priority. The currently
      connected GitHub actions can apply existing labels but do not expose label creation.

---

## Remaining v0.2 official-source audit/provenance gates

- [ ] Record the actual approved-source retrieval timestamp alongside the selected SRD version,
      official source URL, license, and pinned checksum during the first full official fetch.
- [ ] Fetch the pinned official SRD 5.2.1 PDF with the production allowlist and record its retrieval
      manifest.
- [ ] Run the complete 364-page official source through extraction/normalization/compilation/schema
      validation.
- [ ] Review full-dataset stable-ID collisions, heading classification, entity counts, and
      unsupported/manual-review coverage.
- [ ] Decide whether audited generated SRD canonical output should be committed or rebuilt as a
      release artifact.
- [ ] Reproduce a validated canonical rules dataset from the selected licensed SRD source with
      provenance, checksums, attribution, and a deterministic import report.

---

## Remaining exact-head executable evidence gates

These require an integrated checkout where the commands actually execute. GitHub-hosted jobs have
repeatedly terminated before step 1, and the current agent container cannot resolve GitHub to clone
the repository, so they remain unchecked rather than being inferred from test definitions.

- [ ] Demonstrate a headless deterministic v0.1 command producing reproducible event/state output in
      an executing CI/local-CI run.
- [ ] Confirm v0.3 Ruff, strict Mypy, full pytest/coverage, importer determinism, governance/schema,
      and Godot checks on an integrated head.
- [ ] Confirm v0.4 character-runtime deterministic serialization/creation and repository checks on an
      integrated head.
- [ ] Confirm v0.5 deterministic tactical encounter/replay and repository checks on an integrated
      head.
- [ ] Execute the v0.6 repository checks plus headless movement, distance/reach, LOS, cover, and AoE
      scenarios on the integrated head.
- [ ] Execute all C1-C3/v0.7 Godot headless suites and confirm project/script/resource parsing under
      the repository Godot version.
- [ ] Execute the v0.8 Python/Godot suites and demonstrate attack, save, healing, concentration,
      duration, ongoing, AoE, and upcast families with deterministic replay/RNG continuation.
- [ ] Execute the v0.9 Python/Godot/schema suites and external-catalog creation/level-up roundtrip on
      the integrated head.

---

## Remaining manual/production-data acceptance gates

- [ ] Play the Sunken Courtyard encounter interactively through Godot from initial snapshot to
      encounter-ended state with engine-authoritative movement/target/combat outcomes.
- [ ] Play spell casting through Godot from authoritative discovery/preview through accepted command.
- [ ] Replace/augment the original v0.9 demo creator catalog with the supported audited canonical
      production rules/content dataset before claiming production-rules completion.

---

## Future milestones

Detailed scope for v1.1-v2.9 lives in `ROADMAP.md`. Add actionable items here when a future milestone
becomes near-term; do not duplicate the entire roadmap as unchecked backlog noise.

## Backlog hygiene

When agents discover follow-up work:

- add it to the correct milestone;
- make it outcome-oriented;
- avoid vague items such as “improve combat”;
- include migration/testing/doc implications where they are the core of the work;
- do not silently increase the active milestone scope;
- distinguish missing implementation from evidence that must actually be executed.
