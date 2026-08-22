# TODO

This is the active execution backlog for `ROADMAP.md`. Keep it synchronized with implementation. Do not check an item merely because partial scaffolding exists.

## Current focus: v0.1 Project foundation

### Repository and governance

- [x] Bootstrap repository.
- [x] Add canonical `AGENTS.md` governance.
- [x] Add roadmap, TODO, changelog, architecture, rules-ingestion, and Git workflow documentation.
- [x] Add tool-specific agent instruction adapters.
- [ ] Add `CONTRIBUTING.md` derived from the Git/agent workflow.
- [ ] Add issue and pull-request templates.
- [ ] Add repository labels for roadmap milestones, subsystem, type, and priority.
- [ ] Add governance CI that verifies required files and changelog/TODO discipline where practical.
- [ ] Decide and document release/versioning policy before first tagged release.

### Project structure

- [ ] Create top-level `apps/`, `engine/`, `content/`, `schemas/`, `tools/`, `tests/`, and `docs/adr/` structure.
- [ ] Add a minimal Godot 4.x project under `apps/godot-client/`.
- [ ] Add a headless engine package with no Godot rendering dependency.
- [ ] Decide the engine implementation language/runtime and document the rationale in an ADR.
- [ ] Define stable project IDs/namespaces for rules, actors, effects, events, and content packs.

### Deterministic simulation foundations

- [ ] Define typed command envelope.
- [ ] Define typed domain event envelope.
- [ ] Define immutable/controlled game-state transition boundary.
- [ ] Implement deterministic seeded RNG service.
- [ ] Implement dice expression/value objects on top of the RNG service.
- [ ] Record raw rolls, modifiers, reason/context, actor/target IDs, and final results.
- [ ] Add deterministic RNG/dice regression tests.
- [ ] Define reducer/application interface from event(s) to state.
- [ ] Add a minimal command -> validation -> event -> reducer integration test.

### State, events, saves, replay

- [ ] Define event ordering and unique event IDs.
- [ ] Define campaign/session IDs.
- [ ] Define snapshot format and schema version.
- [ ] Define event serialization format and schema version.
- [ ] Define save compatibility policy.
- [ ] Implement snapshot + event-log reconstruction proof of concept.
- [ ] Add replay determinism test.
- [ ] Add corrupted/invalid save input validation tests.

### Developer tooling and CI

- [ ] Choose formatting/linting/static-analysis tools for engine code.
- [ ] Add Godot project validation/headless test job.
- [ ] Add engine unit/integration test job.
- [ ] Add schema validation job.
- [ ] Add generated-content determinism check once generation exists.
- [ ] Add secret scanning/dependency security checks where supported.
- [ ] Add artifact/cache ignores for Godot/editor/build/test outputs.

### v0.1 exit criterion

- [ ] Demonstrate a headless deterministic command producing a reproducible event and state transition in CI.

---

## Next: v0.2 Official SRD pipeline

### Legal/source boundary

- [ ] Create an explicit rules-source allowlist.
- [ ] Record selected SRD version, official source URL, license, retrieval date, and checksum.
- [ ] Add `LICENSES/` and attribution output structure.
- [ ] Document which D&D sources are intentionally excluded from ingestion.
- [ ] Add importer guardrails that reject unknown/unapproved source identifiers.

### Fetch/archive

- [ ] Implement approved-source fetcher.
- [ ] Make fetcher resumable/idempotent where practical.
- [ ] Store source metadata/checksum separately from generated canonical data.
- [ ] Detect upstream source changes and require explicit review.
- [ ] Ensure network/disk work does not block async/event-loop execution.

### Extract/normalize

- [ ] Implement document extraction layer for the approved source format.
- [ ] Normalize headings, paragraphs, lists, and tables without discarding provenance.
- [ ] Preserve source section/page/anchor information where available.
- [ ] Add extraction fixtures for representative text and tables.

### Canonical schemas

- [ ] Define common entity envelope with ID/version/source/license/provenance.
- [ ] Define rule schema.
- [ ] Define action/reaction schema.
- [ ] Define ability/skill/save schema.
- [ ] Define condition/effect/modifier/resource schema.
- [ ] Define class/species/background/feature/feat schema.
- [ ] Define spell schema.
- [ ] Define item/weapon/armor/equipment schema.
- [ ] Define creature/monster schema.
- [ ] Define movement/vision/sense/terrain primitives.
- [ ] Version all schemas.

### Compile/validate/export

- [ ] Build normalized-document -> canonical-entity compiler.
- [ ] Validate all generated entities against schemas.
- [ ] Detect duplicate/unstable IDs.
- [ ] Generate deterministic sorted output.
- [ ] Produce unsupported-mechanic report.
- [ ] Produce import summary/coverage report.
- [ ] Produce attribution/license bundle from provenance metadata.

### Version diffing

- [ ] Add canonical entity diff by SRD/source version.
- [ ] Report added/changed/removed/unchanged entities.
- [ ] Distinguish prose-only changes from executable/mechanical changes where possible.
- [ ] Store enough metadata to review upstream errata safely.

### v0.2 exit criterion

- [ ] Reproduce a validated canonical rules dataset from the selected licensed SRD source with provenance, checksums, attribution, and a deterministic import report.

---

## v0.3 Rules runtime

- [ ] Ability score/modifier primitives.
- [ ] Proficiency primitives.
- [ ] Generic d20 test API.
- [ ] Advantage/disadvantage resolution.
- [ ] Difficulty class and save resolution.
- [ ] Typed resolution context/outcome.
- [ ] Generic modifier pipeline with precedence/stacking semantics.
- [ ] Resource/cost primitives.
- [ ] Trigger/requirement model.
- [ ] Target selector model.
- [ ] Effect pipeline.
- [ ] Duration/expiry model.
- [ ] Condition model.
- [ ] Reaction/event hook model.
- [ ] Ruleset capability declarations.
- [ ] Representative imported-rule conformance tests.

## v0.4 Character runtime

- [ ] Shared actor model for heroes/NPCs/creatures.
- [ ] HP/temp HP/AC/defense state.
- [ ] Skills/proficiencies.
- [ ] Speeds/movement modes.
- [ ] Senses/vision data.
- [ ] Equipment/inventory.
- [ ] Conditions/resources/effects on actors.
- [ ] Character options and choice constraints.
- [ ] Character serialization/migration tests.
- [ ] Initial headless character-creation API.

## v0.5 Tactical combat

- [ ] Encounter lifecycle.
- [ ] Initiative/round/turn order.
- [ ] Action economy.
- [ ] Movement accounting.
- [ ] Attack resolution.
- [ ] Damage/healing pipeline.
- [ ] Defense/resistance/immunity/vulnerability hooks.
- [ ] Reaction windows.
- [ ] Combat conditions.
- [ ] Incapacitation/death-state rules supported by licensed content.
- [ ] Deterministic combat log/replay fixtures.

## v0.6 Spatial authority

- [ ] Logical grid/space interface.
- [ ] Occupancy.
- [ ] Distance/reach.
- [ ] Movement cost/path legality.
- [ ] Terrain/elevation.
- [ ] LOS/visibility.
- [ ] Cover.
- [ ] AoE/shape queries.
- [ ] Movement mode adapters.
- [ ] Godot navigation adapter contract.
- [ ] Headless spatial conformance scenarios.

## v0.7 Godot vertical slice

- [ ] Orthographic isometric camera rig.
- [ ] Pan/zoom/90-degree rotation.
- [ ] One tactical 3D map.
- [ ] Engine-state actor rendering.
- [ ] Selection/highlighting.
- [ ] Reachable-movement preview.
- [ ] Path preview/cost display.
- [ ] LOS/cover/AoE debug overlays.
- [ ] Engine command submission bridge.
- [ ] Turn order/combat HUD/action bar.
- [ ] Basic animation/VFX/audio event mapping.
- [ ] Roof/foreground occlusion handling.
- [ ] Complete playable encounter without client-side rule authority.

## v0.8 Spell runtime

- [ ] Spell resource/slot model.
- [ ] Known/prepared spell model as required by supported rules.
- [ ] Spell attack/save resolution.
- [ ] Generic target/range/area primitives.
- [ ] Duration/concentration model.
- [ ] Scaling/upcasting representation.
- [ ] Ongoing/triggered effects.
- [ ] Spell UI/previews.
- [ ] Conformance matrix by effect family.

## v0.9 Character creator

- [ ] Identity step.
- [ ] Species step.
- [ ] Background step.
- [ ] Class step.
- [ ] Ability score step.
- [ ] Skills/proficiencies step.
- [ ] Equipment step.
- [ ] Spell/feature choice step.
- [ ] Appearance hooks.
- [ ] Biography/personality metadata.
- [ ] Review/validation step.
- [ ] Level-up flow.
- [ ] UI choices sourced from engine APIs/data, not hardcoded lists.

## v1.0 Playable RPG

- [ ] Exploration loop.
- [ ] Dialogue system.
- [ ] Quest state machine/branching consequences.
- [ ] Inventory/equipment UI.
- [ ] Trade/shop flow.
- [ ] Rest flow.
- [ ] Travel/area transitions.
- [ ] Journal/map/party screens.
- [ ] Production save/load UX.
- [ ] Original village area.
- [ ] Original dungeon area.
- [ ] Skill-check interaction.
- [ ] Trap/environment interaction.
- [ ] Three tactical encounters.
- [ ] Boss encounter.
- [ ] One branching quest.
- [ ] Four premade heroes.
- [ ] Release packaging/attribution/credits.
- [ ] End-to-end campaign completion test.

---

## Future milestones

Detailed scope for v1.1-v2.9 lives in `ROADMAP.md`. Add actionable items here when a future milestone becomes near-term; do not duplicate the entire roadmap as unchecked backlog noise.

## Backlog hygiene

When agents discover follow-up work:

- add it to the correct milestone;
- make it outcome-oriented;
- avoid vague items such as “improve combat”;
- include migration/testing/doc implications where they are the core of the work;
- do not silently increase the active milestone scope.
