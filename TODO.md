# TODO

This is the active execution backlog for `ROADMAP.md`. Keep it synchronized with implementation. Do not check an item merely because partial scaffolding exists.

## Current focus: v0.5 Tactical combat

The v0.1 foundation, v0.2 importer infrastructure, v0.3 rules runtime, and v0.4 character runtime have been merged. Outstanding repository/CI and full-official-source v0.2 audit items remain visible below as carryover; they must not be silently forgotten, but v0.5 builds on the merged actor/rules runtime rather than duplicating it.

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

## v0.2 Official SRD pipeline carryover

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

## v0.3 Rules runtime carryover

- [x] Ability score/modifier primitives.
- [x] Proficiency primitives.
- [x] Generic d20 test API.
- [x] Advantage/disadvantage resolution.
- [x] Difficulty class and save resolution.
- [x] Typed resolution context/outcome.
- [x] Generic modifier pipeline with precedence/stacking semantics.
- [x] Resource/cost primitives.
- [x] Trigger/requirement model.
- [x] Target selector model.
- [x] Effect pipeline.
- [x] Duration/expiry model.
- [x] Condition model.
- [x] Reaction/event hook model.
- [x] Ruleset capability declarations.
- [x] Representative imported-rule conformance tests using v0.2 `CanonicalEntity`/provenance-shaped fixtures.

### v0.3 validation carryover

- [x] Keep all randomness behind the existing versioned deterministic RNG/dice abstraction.
- [x] Keep rule-state transforms immutable/pure so failed costs/effect batches cannot partially mutate caller state.
- [x] Add deterministic tests for modifier stacking, resources, requirements, targets, effects, conditions, durations, reactions, capability gating, and D20 outcomes.
- [x] Document which semantics are official SRD behavior versus project-defined generic runtime primitives.
- [ ] Confirm Ruff, Mypy, full repository coverage, importer determinism, governance, and Godot checks on a merged-v0.3-compatible CI run.

### v0.3 exit criterion carryover

- [ ] Demonstrate the complete v0.3 headless rules runtime passing repository CI with deterministic canonical-entity conformance and no Godot rule authority.

---

## v0.4 Character runtime carryover

- [x] Shared actor model for heroes/NPCs/creatures.
- [x] HP/temp HP/AC/defense state.
- [x] Skills/proficiencies.
- [x] Speeds/movement modes.
- [x] Senses/vision data.
- [x] Equipment/inventory.
- [x] Conditions/resources/effects on actors through v0.3 rule-state adapters.
- [x] Character options and choice constraints.
- [x] Character serialization/migration tests and v1 actor schema.
- [x] Initial headless character-creation API.

### v0.4 validation carryover

- [x] Keep the actor model immutable and independent of Godot scene state.
- [x] Reuse v0.3 resources/conditions/effects rather than adding a second mechanic pipeline.
- [x] Represent SRD skills and skill-to-ability mappings as typed structured data.
- [x] Reject duplicate/malformed actor collections, broken inventory/equipment references, invalid choices, and corrupt actor payloads.
- [x] Add focused hero/NPC/creature, rule-adapter, creation, serialization, migration, and adversarial validation tests.
- [x] Reach at least the repository coverage threshold for the new actor package in local testing.
- [ ] Confirm Ruff, Mypy, full repository coverage, governance/schema, importer determinism, and Godot checks on a merged-v0.4-compatible CI run.

### v0.4 exit criterion carryover

- [ ] Demonstrate the complete v0.4 character runtime passing repository CI with deterministic actor serialization/creation and no Godot rule authority.

---

## v0.5 Tactical combat

- [x] Encounter lifecycle.
- [x] Initiative/round/turn order.
- [x] Action economy.
- [x] Movement accounting without taking over v0.6 path/spatial legality.
- [x] Attack resolution using the existing deterministic v0.3 D20 runtime.
- [x] Damage/healing pipeline including temporary HP.
- [x] Defense/resistance/immunity/vulnerability hooks.
- [x] Reaction windows.
- [x] Combat conditions through data-driven restriction rules.
- [x] Incapacitation/death-state rules supported by licensed content through explicit zero-HP policy.
- [x] Deterministic combat event log/replay fixtures.

### v0.5 validation

- [x] Reuse the repository `pcg32-v1` RNG/dice abstraction for initiative, attacks, damage dice, and death saves.
- [x] Keep combat mutations event-sourced through versioned `CombatEvent` records and a pure reducer.
- [x] Add canonical v1 combat-event JSON/JSONL serialization and schema validation surface.
- [x] Keep attacks/damage generic and data-driven; do not add named item/spell/monster conditionals.
- [x] Keep Godot presentation and v0.6 path/range/LOS/cover/terrain/AoE authority outside combat.
- [x] Add deterministic and adversarial tests for initiative, turns, actions, reactions, attacks, defenses, HP/state changes, conditions, malformed events, and replay parity.
- [x] Reach at least the repository coverage threshold for the combat package in local testing.
- [ ] Confirm Ruff, Mypy, full repository coverage, governance/schema, importer determinism, and Godot checks on the v0.5 PR head in CI.

### v0.5 exit criterion

- [ ] Demonstrate a complete deterministic headless encounter whose authoritative state is reproducible from the same preparing actors plus ordered v1 combat events, passing repository CI with no Godot or v0.6 spatial rule authority.

---

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
