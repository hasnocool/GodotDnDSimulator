# AGENTS.md

This file is the canonical operating contract for every coding agent working in this repository. Tool-specific instruction files may add guidance, but they must not weaken or contradict this file.

## Mission

Build GodotDnDSimulator as a deterministic, testable, data-driven isometric tabletop-RPG platform with:

- an authoritative headless rules/simulation engine;
- a Godot 4.x 3D orthographic client;
- an appropriately licensed SRD rules ingestion and compilation pipeline;
- original game setting, art, story, quests, maps, and characters;
- replayable/event-sourced campaign state;
- moddable content packs and creator tooling;
- strict provenance for imported rules content.

The long-term architecture matters more than shortcuts that make one demo work.

## Read before every task

Before changing code or content, read:

1. `README.md`
2. `ROADMAP.md`
3. `TODO.md`
4. `CHANGELOG.md`
5. `docs/PROJECT_PLAN.md`
6. `docs/ARCHITECTURE.md`
7. `docs/RULES_INGESTION.md` when touching rules/content
8. `docs/GIT_WORKFLOW.md` when creating commits or PRs

Then inspect the code and tests related to the task. Never assume a TODO is still accurate without checking the implementation.

## Before every task

Answer these questions internally before editing:

1. What roadmap milestone does this belong to?
2. What existing subsystem should own the behavior?
3. Does this preserve deterministic simulation?
4. Is game/rules state staying outside presentation code?
5. Does this add or change an externally observable behavior that needs tests?
6. Does this affect save/replay compatibility?
7. Does this change rule/content provenance or licensing obligations?
8. Does this require a `TODO.md` update?
9. Does this require a `CHANGELOG.md` entry?
10. Is the work small enough for one focused PR?

If the task does not map to the roadmap, either document why it is an intentional change of direction or add it to the roadmap before implementation.

## Architecture rules

### Authoritative simulation

The simulation/rules engine is authoritative. Godot renders state, gathers player intent, and submits commands.

Use this conceptual flow:

`Command -> Validation -> Resolution -> Events -> Reducer -> New State`

Do not let UI, animation, scene nodes, or VFX directly decide rule outcomes or mutate authoritative campaign state.

### Determinism

All randomness must use the project RNG/dice abstraction. Never call ad-hoc random APIs from rules code.

A random outcome must be reproducible from recorded state/seed and should capture enough context for replay and debugging.

### Event sourcing

Prefer durable domain events over hidden mutations. Campaign state should be reconstructable from a snapshot plus ordered events.

When introducing a new state mutation, define:

- command/input;
- validation;
- emitted event(s);
- reducer/state transition;
- serialization/versioning impact;
- replay tests.

### Data-driven mechanics

Do not implement official or custom abilities as large name-based `if/elif` or `match` chains.

Prefer reusable primitives such as:

- triggers;
- requirements;
- target selectors;
- rolls/checks;
- modifiers;
- resources/costs;
- effects;
- durations;
- reactions;
- event hooks.

If a mechanic cannot be represented, extend the generic rule/effect model and add tests rather than special-casing one named spell, monster, or item.

### Spatial separation

Godot navigation answers whether a physical path exists. The rules/spatial authority answers whether a specific actor may legally traverse it under current rules.

Logical grid/space, occupancy, movement cost, terrain, cover, line of sight, elevation, reach, threat, and areas of effect must be testable without rendering a Godot scene.

### Async and I/O

Never block an async/event-loop thread with disk, subprocess, database, network, or CPU-heavy work. Use non-blocking APIs, worker threads/processes, queues, or Godot's appropriate threaded/task mechanisms. Shared state must use thread-safe operations.

## Rules and licensing rules

The official import target is the appropriately licensed D&D SRD content selected in `docs/RULES_INGESTION.md` (initially SRD 5.2.1 under CC BY 4.0).

Agents MUST NOT:

- scrape or copy D&D Beyond Basic Rules as a substitute for the SRD;
- import Player's Handbook, Monster Manual, Dungeon Master's Guide, setting-book, adventure-book, or other non-SRD text unless a compatible license is explicitly documented in-repo;
- assume trademark permission from a copyright license;
- remove required attribution or provenance metadata;
- silently paraphrase unlicensed content into the repository.

Every imported rule entity must preserve source/version/license/provenance metadata and a source hash or equivalent reproducibility record.

Original setting material should use project-owned names and IP rather than protected D&D settings/branding.

## Source layout principles

Keep these concerns separable even if exact folders evolve:

- `apps/` - Godot client, editors, browsers;
- `engine/` - headless domain/rules/simulation code;
- `content/` - generated/imported/original content packs;
- `schemas/` - canonical content/rule schemas;
- `tools/` - importers, compilers, validators, migration tooling;
- `tests/` - deterministic unit, integration, conformance, replay tests;
- `docs/` - architecture, rules, decisions, workflows.

Do not move logic into a more convenient layer if it weakens these boundaries.

## Testing requirements

Every behavioral change needs appropriate automated tests.

Prefer:

- pure unit tests for rule/effect primitives;
- golden/schema tests for generated content;
- deterministic replay fixtures for encounters;
- property/invariant tests for core resolution when useful;
- Godot integration tests only for presentation/integration behavior that cannot be tested headlessly.

A bug fix must include a regression test when practical.

Do not delete or weaken a test merely to make CI pass unless the requirement itself changed and that change is documented.

## TODO discipline

`TODO.md` is the active execution backlog, not a dumping ground.

When starting work:

- choose an existing TODO or add a scoped item under the correct milestone;
- mark only work actually completed as done;
- split oversized items before coding;
- add newly discovered work in the correct milestone instead of silently expanding scope.

When finishing work:

- check completed items;
- add follow-up items discovered during implementation;
- keep roadmap milestone status accurate;
- do not leave stale TODO claims that contradict code.

TODO items should describe an observable outcome and, when useful, name the owning subsystem.

## Changelog discipline

Use `CHANGELOG.md` with an `Unreleased` section following Keep-a-Changelog style categories where applicable:

- Added
- Changed
- Deprecated
- Removed
- Fixed
- Security

Every user-visible feature, behavior change, compatibility change, rules/content update, migration, or meaningful developer workflow change must be represented in `Unreleased` within the same PR.

Pure typo-only changes may omit changelog entries.

Do not rewrite historical released sections except to correct factual errors.

## Documentation discipline

Documentation is part of the implementation.

Update docs in the same PR when changing:

- architecture boundaries;
- schemas or file formats;
- commands/tools;
- imported content provenance;
- save/replay compatibility;
- build/test instructions;
- milestone scope.

Prefer documenting durable decisions in `docs/` rather than burying them in PR text.

## Git rules

Never do substantive work directly on `main`.

Use focused branches such as:

- `feat/<short-topic>`
- `fix/<short-topic>`
- `docs/<short-topic>`
- `refactor/<short-topic>`
- `chore/<short-topic>`

Use Conventional Commit-style messages, for example:

- `feat(engine): add deterministic dice service`
- `fix(spatial): account for difficult terrain`
- `docs(rules): document SRD provenance model`
- `test(combat): add concentration replay fixture`

Rules:

- keep commits logically coherent;
- do not mix unrelated refactors into feature commits;
- never force-push shared branches unless explicitly required and safe;
- never rewrite `main` history;
- never commit secrets, API keys, generated caches, editor junk, or copyrighted source documents that are not allowed to be redistributed;
- prefer pull requests for all substantive changes;
- keep PR scope aligned with one roadmap goal or clearly related slice.

## Pull request definition of done

A PR is not done until all applicable items are true:

- implementation matches the intended roadmap/TODO scope;
- architectural boundaries are preserved;
- tests were added/updated and pass;
- deterministic behavior remains replayable;
- schema/save compatibility was considered;
- `TODO.md` is accurate;
- `CHANGELOG.md` is updated;
- docs are updated;
- generated content was regenerated by documented tooling rather than hand-edited when applicable;
- licensing/provenance is valid for imported content;
- no unrelated files or debug artifacts are included;
- PR description explains what changed, why, testing, and follow-ups.

## Scope control / preventing project drift

Do not add a feature merely because it is interesting.

A proposed change should satisfy at least one of:

- required by the current milestone;
- removes a blocker for the next milestone;
- fixes correctness, safety, licensing, data-loss, or maintainability risk;
- materially strengthens the reusable engine/platform architecture.

Otherwise record it under a future milestone instead of implementing it immediately.

When a task expands materially beyond its original intent, stop expanding scope, capture follow-ups in `TODO.md`, and finish the smallest coherent slice.

## Generated/imported files

Treat generated rules/content as build artifacts with provenance.

- Never hand-edit generated files when a generator owns them.
- Update the source schema/compiler/importer instead.
- Generated output must be deterministic where practical.
- Import tooling should be idempotent.
- Store hashes/version metadata so upstream changes are auditable.

## Performance rules

Correctness and determinism come first, then measured optimization.

For performance-sensitive work:

- profile before optimizing;
- avoid blocking I/O;
- batch disk/database/network operations;
- avoid per-frame allocations in hot Godot paths;
- keep expensive simulation work headless/testable;
- document benchmarks for significant optimizations.

## Security and robustness

Treat campaign packs, mods, imported documents, network clients, and AI-generated tool calls as untrusted input.

Validate schemas, paths, identifiers, versions, sizes, and permissions. Avoid arbitrary code execution in content packs by default.

AI/LLM integrations may request legal actions through typed tools/commands; they must not directly mutate authoritative state.

## Agent completion report

At the end of a task, report:

- roadmap/TODO item addressed;
- files/subsystems changed;
- tests run and result;
- TODO/changelog/docs updates;
- compatibility or migration notes;
- remaining follow-up work;
- branch/PR information if GitHub access is available.
