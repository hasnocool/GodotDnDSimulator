# TODO

This is the active execution backlog for `ROADMAP.md`. Keep it synchronized with implementation.
Do not check an item merely because scaffolding exists, and do not leave implemented work unchecked
when repository tests/code provide direct evidence.

## Current focus: v1.0.1 Agent playtesting and observability

The v0.1 foundation through v1.0 playable RPG implementation are present. v1.0.1 adds a
provider-neutral AI/test-agent control boundary, deterministic full-campaign autoplay, structured
disk diagnostics, and an opt-in Godot UI automation API without moving rules or state authority out
of the Python engine.

The API and security/authority model are documented in `docs/AGENT_AUTOMATION_API.md` and
`docs/adr/0004-agent-control-and-ui-automation.md`.

---

## v1.0.1 implementation

### AI/player/NPC control boundary

- [x] Expose versioned structured `agent.observe`, `agent.actions`, and `agent.controllers` queries.
- [x] Generate fresh legal action tokens from authoritative world/tactical/spell queries rather than
      accepting arbitrary AI state mutations.
- [x] Bind every action token to the authoritative sequence and reject stale/unknown tokens before
      execution.
- [x] Route `agent.execute` back through the normal typed bridge command path so engine validation,
      sequencing, rules, spatial authority, combat, and RNG remain authoritative.
- [x] Support explicit per-actor `human` / `agent` control with policy IDs.
- [x] Default party members to human control and non-party tactical actors to agent control.
- [x] Allow the hero and any other known party character to be switched to AI control.
- [x] Expose legal world actions for dialogue, travel, interactions, encounters, shop trade,
      equipment, rest, and encounter completion.
- [x] Expose legal tactical attack, spell, movement, and end-turn actions using existing previews and
      availability queries.
- [x] Add `schemas/agent/v1/agent-observation.schema.json` and schema regression coverage.

### Automated end-to-end campaign testing

- [x] Add a provider-neutral deterministic baseline agent policy for regression use.
- [x] Switch all four premade heroes to agent control for the automated campaign run.
- [x] Exercise Warden dialogue, trade, equipment, rest, travel, skill/environment interactions, the
      Surveyor's Echo branch, all four authored tactical encounters, and final campaign completion.
- [x] Let tactical NPC/enemy turns run through the same agent-control API with a deterministic passive
      regression policy.
- [x] Prefer legal hostile tactical actions for party agents and never bypass tactical previews.
- [x] Add same-seed deterministic action-trace/final-observation parity coverage.
- [x] Add `godot-dnd-agent-autoplay` CLI and local/hosted CI smoke invocation.

### Structured observability

- [x] Add bounded background JSONL diagnostics for the Python bridge/agent/autoplay path.
- [x] Log bridge operation/result metadata without intentionally recording automation tokens or
      credentials as secrets.
- [x] Persist Godot `ClientLog` entries asynchronously to `user://logs/client-*.jsonl` while retaining
      bounded in-memory diagnostics.
- [x] Add agent/automation log categories and expose the live client log path.
- [x] Ignore repository-local `.logs/` output.

### Godot debugging-agent API

- [x] Add opt-in `UiAutomation` autoload disabled by default.
- [x] Bind the network API to `127.0.0.1` only with optional explicit local token authentication.
- [x] Bound request size and concurrent automation clients.
- [x] Expose visible control-tree snapshots with text, class, focus, bounds, shell state, and
      authoritative sequence diagnostics.
- [x] Expose narrow UI operations for inspect, focus, activation through viewport mouse input,
      coordinate click, editable text, and registered `InputMap` actions.
- [x] Expose recent structured client logs and screenshot capture.
- [x] Deliberately omit arbitrary method calls, script evaluation, arbitrary file access, and direct
      engine-state mutation from the UI API.
- [x] Add `schemas/client/v1/ui-automation-request.schema.json`.
- [x] Add loopback-only Python `UiAutomationClient` plus `godot-dnd-ui-automation` CLI.
- [x] Add headless Godot automation tests and Python client framing tests.

### Documentation/governance

- [x] Add v1.0.1 roadmap milestone and ADR.
- [x] Document external-agent loop, API examples, diagnostics paths, UI-debug workflow, and security
      boundary.
- [x] Register the new Python/Godot suites in local and hosted CI.

---

## v1.0.1 executable evidence still required

These are deliberately not inferred from source inspection.

- [ ] Execute Ruff, strict Mypy, full pytest/coverage, governance/schema/importer checks, agent
      autoplay smoke, project parse, and every registered Godot headless suite on the exact integrated
      head using a runner where jobs actually execute.
- [ ] Run the live Python bridge and Godot client together, connect a debugging agent through the
      loopback UI RPC, and record a real snapshot -> interaction -> logs -> screenshot reproduction.
- [ ] Demonstrate a complete desktop Godot campaign/debug session driven by an automation agent where
      the agent uses UI actions for presentation/input debugging and the engine API for legal gameplay
      decisions.

---

## Implemented milestone summary

### v0.1-v0.6 engine foundation

- [x] Repository governance, deterministic headless engine, typed command/event/state contracts,
      PCG32 RNG/dice, reducers/snapshots/replay, schemas/stable IDs, source importer, rules runtime,
      shared actor model, tactical combat, and spatial authority.

### v0.7-v0.9 client/spells/creator

- [x] Godot bridge/state/input architecture and tactical vertical slice.
- [x] Generic deterministic spell runtime with data-driven Godot spell UI.
- [x] Complete engine-driven character creator and level-up flow.

### v1.0 playable RPG

- [x] Exploration, dialogue, branching quest state, inventory/equipment, trade, rest, travel,
      journal/map/party, production manual save/load, original village/dungeon content, interactions,
      three authored regular tactical encounters, authored boss encounter, four premade heroes,
      release packaging/credits, and end-to-end campaign completion coverage.

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

## Remaining earlier exact-head executable evidence gates

These require an integrated checkout where the commands actually execute. GitHub-hosted jobs have
repeatedly terminated before step 1, and the current agent container cannot resolve GitHub to clone
the repository, so they remain unchecked rather than being inferred from test definitions.

- [ ] Demonstrate a headless deterministic v0.1 command producing reproducible event/state output in
      an executing CI/local-CI run.
- [ ] Confirm v0.3-v0.9 Ruff, strict Mypy, pytest/coverage, importer determinism, schemas/governance,
      and registered Godot checks on an integrated head.
- [ ] Execute all v0.7-v1.0 Godot headless suites and confirm project/script/resource parsing under
      the repository Godot version.

---

## Remaining manual/production-data acceptance gates

- [ ] Play the Sunken Courtyard encounter interactively through Godot from initial snapshot to
      encounter-ended state with engine-authoritative movement/target/combat outcomes.
- [ ] Play spell casting through Godot from authoritative discovery/preview through accepted command.
- [ ] Replace/augment the original v0.9 demo creator catalog with the supported audited canonical
      production rules/content dataset before claiming production-rules completion.

---

## Future milestones

Detailed scope for v1.1-v2.9 lives in `ROADMAP.md`. Advanced utility AI, planning, perception,
memories, social behavior, and richer LLM policies remain v1.4+ work and should consume the v1.0.1
legal-action boundary rather than gaining direct state mutation access.

## Backlog hygiene

When agents discover follow-up work:

- add it to the correct milestone;
- make it outcome-oriented;
- avoid vague items such as “improve combat”;
- include migration/testing/doc implications where they are the core of the work;
- do not silently increase the active milestone scope;
- distinguish missing implementation from evidence that must actually be executed.
