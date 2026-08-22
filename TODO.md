# TODO

This is the active execution backlog for `ROADMAP.md`. Keep it synchronized with implementation. Do not check an item merely because partial scaffolding exists.

## Current focus: v0.2 Official SRD pipeline

The v0.1 executable foundation has been merged. Its remaining repository-administration and CI-proof items stay visible below as carryover; they do not block scoped v0.2 implementation work, but must not be silently forgotten.

### v0.1 carryover: repository and governance

- [x] Bootstrap repository.
- [x] Add canonical `AGENTS.md` governance.
- [x] Add roadmap, TODO, changelog, architecture, rules-ingestion, and Git workflow documentation.
- [x] Add tool-specific agent instruction adapters.
- [x] Add `CONTRIBUTING.md` derived from the Git/agent workflow.
- [x] Add issue and pull-request templates.
- [ ] Add repository labels for roadmap milestones, subsystem, type, and priority.
- [x] Add governance CI that verifies required files and changelog/TODO discipline where practical.
- [x] Decide and document release/versioning policy before first tagged release.

### v0.1 carryover: project structure

- [x] Create top-level `apps/`, `engine/`, `content/`, `schemas/`, `tools/`, `tests/`, and `docs/adr/` structure.
- [x] Add a minimal Godot 4.x project under `apps/godot-client/`.
- [x] Add a headless engine package with no Godot rendering dependency.
- [x] Decide the engine implementation language/runtime and document the rationale in an ADR.
- [x] Define stable project IDs/namespaces for rules, actors, effects, events, and content packs.

### v0.1 carryover: deterministic simulation foundations

- [x] Define typed command envelope.
- [x] Define typed domain event envelope.
- [x] Define immutable/controlled game-state transition boundary.
- [x] Implement deterministic seeded RNG service.
- [x] Implement dice expression/value objects on top of the RNG service.
- [x] Record raw rolls, modifiers, reason/context, actor/target IDs, and final results.
- [x] Add deterministic RNG/dice regression tests.
- [x] Define reducer/application interface from event(s) to state.
- [x] Add a minimal command -> validation -> event -> reducer integration test.

### v0.1 carryover: state, events, saves, replay

- [x] Define event ordering and unique event IDs.
- [x] Define campaign/session IDs.
- [x] Define snapshot format and schema version.
- [x] Define event serialization format and schema version.
- [x] Define save compatibility policy.
- [x] Implement snapshot + event-log reconstruction proof of concept.
- [x] Add replay determinism test.
- [x] Add corrupted/invalid save input validation tests.

### v0.1 carryover: developer tooling and CI

- [x] Choose formatting/linting/static-analysis tools for engine code.
- [x] Add Godot project validation/headless test job.
- [x] Add engine unit/integration test job.
- [x] Add schema validation job.
- [x] Add generated-content determinism check using the v0.2 importer fixture build.
- [ ] Add secret scanning/dependency security checks where supported.
- [x] Add artifact/cache ignores for Godot/editor/build/test/rules-source outputs.

### v0.1 exit criterion carryover

- [ ] Demonstrate a headless deterministic command producing a reproducible event and state transition in CI.

---

## v0.2 Official SRD pipeline

### Legal/source boundary

- [x] Create an explicit rules-source allowlist.
- [ ] Record the actual approved-source retrieval timestamp alongside the selected SRD version, official source URL, license, and pinned checksum during the first full official fetch.
- [x] Add `LICENSES/` and attribution output structure.
- [x] Document which D&D sources are intentionally excluded from ingestion.
- [x] Add importer guardrails that reject unknown/unapproved source identifiers and hosts.

### Fetch/archive

- [x] Implement approved-source fetcher.
- [x] Make fetcher resumable/idempotent where practical with ETag/Last-Modified cache validators.
- [x] Store source metadata/checksum separately from generated canonical data.
- [x] Detect upstream source changes through pinned SHA-256 verification and require explicit policy review.
- [x] Ensure network/disk work does not block async/event-loop execution.

### Extract/normalize

- [x] Implement PDF document extraction layer for the approved source format.
- [x] Normalize headings, paragraphs, lists, tables, Unicode whitespace, and dice notation without discarding provenance.
- [x] Preserve source section/page/bookmark information where available.
- [x] Add extraction fixtures for representative text, headings, lists, and tables.

### Canonical schemas

- [x] Define common entity envelope with ID/version/source/license/provenance.
- [x] Define rule schema.
- [x] Define action/reaction schema.
- [x] Define ability/skill/save schema family.
- [x] Define condition/effect/modifier/resource schema family.
- [x] Define class/species/background/feature/feat schema family.
- [x] Define spell schema.
- [x] Define item/weapon/armor/equipment schema family.
- [x] Define creature/monster schema.
- [x] Define movement/vision/sense/terrain primitive schema.
- [x] Version all schemas under `schemas/rules/v1/`.

### Compile/validate/export

- [x] Build normalized-document -> canonical-entity compiler.
- [x] Validate generated entities against versioned kind-specific JSON Schemas.
- [x] Detect duplicate/unstable IDs and fail rather than silently renumbering collisions.
- [x] Generate deterministic sorted JSONL output.
- [x] Produce unsupported-mechanic report.
- [x] Produce import summary/coverage report with canonical output checksum.
- [x] Produce attribution/license bundle from provenance/source policy metadata.
- [x] Re-hash cached source bytes immediately before parsing to detect post-manifest tampering.

### Version diffing

- [x] Add canonical entity diff by SRD/source version.
- [x] Report added/changed/removed/unchanged entities.
- [x] Distinguish prose-only changes from executable/mechanical changes where possible.
- [x] Store source version/license/hash/retrieval/importer metadata needed to review upstream errata safely.

### Validation before v0.2 completion

- [x] Add mocked HTTP, source-policy, PDF extraction, normalization, compiler, schema, report, diff, and tamper regression tests.
- [x] Add deterministic importer fixture smoke build that compares byte-for-byte output from two independent builds.
- [x] Keep raw source PDFs in ignored local cache rather than Git.
- [ ] Fetch the pinned official SRD 5.2.1 PDF with the production allowlist and record its retrieval manifest.
- [ ] Run the complete 364-page official source through extraction/normalization/compilation/schema validation.
- [ ] Review full-dataset stable-ID collisions, heading classification, entity counts, and unsupported/manual-review coverage.
- [ ] Decide whether audited generated SRD canonical output should be committed or rebuilt as a release artifact.

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
