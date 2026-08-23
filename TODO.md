# TODO

This is the active execution backlog for `ROADMAP.md`. Keep it synchronized with implementation. Do not check an item merely because partial scaffolding exists.

## Current focus: v1.0 Playable RPG

The v0.1 foundation, v0.2 importer infrastructure, v0.3 rules runtime, v0.4 character runtime, v0.5 tactical combat, v0.6 spatial authority, v0.7 Godot vertical slice, v0.8 spell runtime, and v0.9 character-creator implementations have been merged. Outstanding repository/CI, full-official-source v0.2 audit, and exact-head acceptance items remain visible below as carryover; they must not be silently forgotten. v1.0 now turns those production foundations into the complete original campaign and RPG client loop while keeping world, character, combat, and inventory authority in the headless engine.

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

## v0.5 Tactical combat carryover

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

### v0.5 validation carryover

- [x] Reuse the repository `pcg32-v1` RNG/dice abstraction for initiative, attacks, damage dice, and death saves.
- [x] Keep combat mutations event-sourced through versioned `CombatEvent` records and a pure reducer.
- [x] Add canonical v1 combat-event JSON/JSONL serialization and schema validation surface.
- [x] Keep attacks/damage generic and data-driven; do not add named item/spell/monster conditionals.
- [x] Keep Godot presentation and v0.6 path/range/LOS/cover/terrain/AoE authority outside combat.
- [x] Add deterministic and adversarial tests for initiative, turns, actions, reactions, attacks, defenses, HP/state changes, conditions, malformed events, and replay parity.
- [x] Reach at least the repository coverage threshold for the combat package in local testing.
- [ ] Confirm Ruff, Mypy, full repository coverage, governance/schema, importer determinism, and Godot checks on the v0.5-compatible merged head in CI.

### v0.5 exit criterion carryover

- [ ] Demonstrate a complete deterministic headless encounter whose authoritative state is reproducible from the same preparing actors plus ordered v1 combat events, passing repository CI with no Godot spatial/rule authority.

---

## v0.6 Spatial authority carryover

- [x] Logical grid/space interface with a backend-independent `LogicalSpace` protocol and initial bounded square-grid implementation.
- [x] Multi-cell occupancy/footprints and collision validation.
- [x] Distance/reach with explicit grid, Manhattan, and Euclidean metrics.
- [x] Movement cost, deterministic pathfinding, proposed-path validation, and reachable-space queries.
- [x] Difficult terrain, per-cell movement-mode compatibility, and elevation-aware movement policy.
- [x] Logical LOS/visibility with terrain/placement blockers and elevation-aware obstacle height.
- [x] Explicit logical cover classification and source reporting.
- [x] Generic sphere/cube/cylinder/cone/line AoE/shape queries returning cells and entity membership.
- [x] Actor movement-mode adapters reusing v0.4 walk/climb/swim/fly/burrow speed records.
- [x] Godot/navigation proposal contract where navigation is an input and headless spatial validation remains authoritative.
- [x] Geometric threat-zone entry/exit inputs without taking over v0.5 reaction legality/spending.
- [x] Versioned spatial movement events, pure reducer, canonical JSON/JSONL serialization, schema, and deterministic replay.
- [x] JSON-shaped read-only `SpatialQueryService` for occupancy/distance/reach/path/reachable/LOS/cover/area/movement-mode/threat queries.
- [x] v0.5/v0.6 integration that validates a route/cost before spending the exact cost through `CombatRuntime`.
- [x] Headless spatial conformance, adversarial validation, replay, navigation-proposal, query, and combat-integration scenarios.
- [x] Document spatial ownership, movement/replay semantics, Godot adapter boundary, and v0.7 handoff in `docs/V0.6_SPATIAL_AUTHORITY.md`.

### v0.6 validation / exit criterion carryover

- [ ] Confirm Ruff, strict Mypy, full pytest/coverage, governance/schema, importer determinism, and Godot checks execute successfully on the exact v0.6-compatible integrated head.
- [ ] Validate `schemas/v1/spatial-event.schema.json` against representative serialized movement events in the executable suite.
- [ ] Demonstrate headless movement, targeting distance/reach, LOS, cover, and AoE scenarios on the exact integrated head with no Godot rule authority.
- [ ] Mark v0.6 complete only after the executable gates pass on an integrated head.

---

## v0.7 Godot vertical slice

Detailed client execution lives in `apps/godot-client/TODO.md`; keep root acceptance items synchronized with demonstrated behavior rather than duplicating client implementation details here.

- [x] Orthographic isometric camera rig.
- [x] Pan/zoom/90-degree rotation.
- [x] One tactical 3D map.
- [x] Engine-state actor rendering.
- [x] Selection/highlighting.
- [x] Reachable-movement preview sourced from v0.6.
- [x] Path preview/cost display sourced from v0.6.
- [x] LOS/cover/AoE debug overlays sourced from v0.6/tactical previews.
- [x] Engine command submission bridge for move/attack/end-turn intent.
- [x] Turn order/combat HUD/action bar driven by authoritative state/queries.
- [x] Basic animation/VFX/audio event mapping from already-resolved presentation events.
- [x] Roof/foreground occlusion presentation handling without changing LOS authority.
- [x] Complete playable Sunken Courtyard encounter without client-side rule authority.
- [x] Deterministic Python vertical-slice and bridge regression suites.
- [x] Headless Godot camera and tactical-slice integration suites added to `scripts/local_ci.sh`.
- [x] Document v0.7 architecture, controls, bridge contracts, testing, and v0.8 handoff in `docs/V0.7_GODOT_VERTICAL_SLICE.md`.

### v0.7 validation / exit criterion

- [ ] Run Ruff, strict Mypy, full pytest/coverage, governance/schema/importer determinism, and every C1-C3/v0.7 Godot headless suite on the exact v0.7 PR head.
- [ ] Confirm the exact v0.7 head parses under the repository Godot version with no script/resource errors.
- [ ] Play the Sunken Courtyard battle through the Godot client from initial snapshot to encounter-ended state while all movement/target/combat outcomes remain engine-authoritative.
- [ ] Mark v0.7 complete only after those executable and playable acceptance gates pass.

## v0.8 Spell runtime

- [x] Spell resource/slot model.
- [x] Known/prepared spell model as required by supported rules.
- [x] Spell attack/save resolution.
- [x] Generic target/range/area primitives composed from v0.3 selectors and v0.6 spatial authority.
- [x] Duration/concentration model.
- [x] Scaling/upcasting representation.
- [x] Ongoing effect execution with authoritative round advancement.
- [x] Spell UI/previews driven by engine-provided spell/slot metadata and authoritative previews.
- [x] Conformance matrix by representative effect family with original test fixtures.
- [x] Versioned spell-event serialization/schema and RNG continuation checkpoints.
- [x] Spell-aware bridge/session integration and compatibility with core-only/v0.7 state.
- [x] Document v0.8 architecture and authority boundaries in `docs/V0.8_SPELL_RUNTIME.md`.

### v0.8 validation / exit criterion

- [ ] Run Ruff, strict Mypy, full pytest/coverage, governance/schema/importer determinism, and every Godot headless suite including `spell_ui_tests.gd` on the exact v0.8 head.
- [ ] Confirm the exact v0.8 head parses under the repository Godot version with no script/resource errors.
- [ ] Demonstrate attack, save, healing, concentration, duration, ongoing, AoE, and upcast spell families through the authoritative engine with deterministic replay/RNG continuation.
- [ ] Play spell casting through Godot from authoritative discovery/preview to accepted command without client-side rule authority.
- [ ] Mark v0.8 complete only after those executable gates pass on an integrated head.

## v0.9 Complete character creator

- [x] Identity step.
- [x] Species step driven by engine catalog data.
- [x] Background step driven by engine catalog data.
- [x] Class step driven by engine catalog data.
- [x] Ability score step using engine-provided assignment policy.
- [x] Skills/proficiencies step.
- [x] Equipment step.
- [x] Spell/feature choice step.
- [x] Appearance hooks kept separate from rules authority.
- [x] Biography/personality metadata.
- [x] Review/validation step with authoritative preview plus create-time revalidation.
- [x] Level-up choice and transition flow.
- [x] UI choices sourced from engine APIs/data, not hardcoded lists.
- [x] External catalog data adapter for canonical rules/content-pack integration.
- [x] Versioned character-record schema and record serialization boundary.
- [x] Python creator/runtime/service/bridge/schema regression coverage.
- [x] Headless Godot creator integration suite added to `scripts/local_ci.sh`.
- [x] Restore repository GitHub Actions workflow for Python/governance and Godot headless validation.
- [x] Document v0.9 architecture, authority boundary, data adapters, tests, and v1.0 handoff in `docs/V0.9_CHARACTER_CREATOR.md`.

### v0.9 validation / exit criterion

- [ ] Run Ruff, strict Mypy, full pytest/coverage, governance/schema/importer determinism, Godot project parsing, and every headless Godot suite including `character_creator_tests.gd` on the exact integrated v0.9 head.
- [ ] Validate representative `CharacterRecord` output against `schemas/v1/character-record.schema.json` in an executable repository run.
- [ ] Demonstrate catalog data roundtrip and character creation/level-up entirely from external catalog data on the exact integrated head.
- [ ] Replace/augment the original v0.9 demo catalog with the supported audited canonical rules/content dataset before claiming full production-rules completion.
- [ ] Mark v0.9 complete only after executable gates pass and the supported production catalog is backed by audited canonical rules/content data.

## v1.0 Playable RPG

- [ ] Exploration loop.
- [ ] Dialogue system.
- [ ] Quest state machine/branching consequences.
- [x] Inventory/equipment UI.
- [ ] Trade/shop flow.
- [ ] Rest flow.
- [ ] Travel/area transitions.
- [x] Journal/map/party screens.
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