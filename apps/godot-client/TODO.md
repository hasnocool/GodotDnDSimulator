# Godot Client TODO

This is the detailed execution backlog for `apps/godot-client/`.

It is subordinate to the repository-root `ROADMAP.md`, `TODO.md`, and `AGENTS.md`. Client agents must
also follow `apps/godot-client/AGENTS.md`. A checked item here means the observable client behavior
exists and applicable validation has been performed; planning or scaffolding alone is not completion.

## Client product goal

Build a polished Godot 4.x 3D orthographic/isometric client that:

- renders authoritative engine/campaign/combat/spatial state;
- turns player input into typed engine intents/commands;
- presents legal movement, targeting, LOS, cover, AoE, resources, turn state, and outcomes without
  becoming the rules authority;
- maps resolved engine events to animation, VFX, sound, camera, and HUD feedback;
- supports the v0.7 tactical vertical slice first, then grows into exploration, character creation,
  inventory, dialogue, quests, creator tooling, multiplayer, and other roadmap clients;
- stays usable headlessly for integration testing and replay-driven presentation tests.

## Dependency rule

Do not fake missing engine features in GDScript merely to unblock a screen.

- v0.5 owns tactical combat authority.
- v0.6 owns spatial legality and spatial query authority.
- v0.7 owns the first production Godot tactical vertical slice.
- v0.8 may add spell-specific UI/previews on top of generic rule/spatial APIs.
- v0.9 owns the complete rules-driven character-creator UX.
- v1.0 owns full exploration/RPG shell UX.

Client scaffolding may be built earlier, but authoritative behavior must wait for or help define the
correct engine contract.

---

## C0 — Existing scaffold and client governance

### Existing baseline

- [x] Godot project exists under `apps/godot-client/`.
- [x] Main scene is a 3D scene with an orthographic `Camera3D` rig.
- [x] Project identifies the Godot client as presentation-only in existing comments.
- [x] Headless Godot project validation exists in repository CI.

### Client governance

- [x] Add `apps/godot-client/AGENTS.md` with client-specific authority, bridge, testing, and UX rules.
- [x] Add this detailed `apps/godot-client/TODO.md` client backlog.
- [x] Keep root `AGENTS.md` wired to require the local client contract/TODO for client work.
- [x] Keep Claude, Gemini, and Copilot repository adapters wired to the local client contract/TODO.
- [ ] Keep root `TODO.md` v0.7 pointing to this detailed client backlog.
- [ ] Add client-specific validation to governance tooling if plain documentation references prove too
      easy to drift.

### Planned client source organization

Create these only as implementation needs them; empty directory scaffolding is not completion.

- [ ] `autoload/` for presentation app shell/bridge registry/settings only.
- [x] `bridge/` for typed engine transport/protocol adapters.
- [ ] `state/` for authoritative mirror, interaction state, and presentation state.
- [ ] `camera/` for tactical camera controllers/config.
- [ ] `input/` for input mapping and interaction modes.
- [ ] `scenes/shell/` for startup/loading/root composition.
- [ ] `scenes/tactical/` for battle-map presentation.
- [ ] `scenes/actors/` for reusable actor presentation.
- [ ] `ui/hud/`, `ui/actions/`, `ui/panels/`, `ui/common/` as corresponding UI arrives.
- [ ] `presentation/` for event-to-animation/VFX/audio mapping.
- [ ] `debug/` for authoritative tactical/debug overlays.
- [x] `tests/` for headless Godot client tests.

---

## C1 — Client/engine bridge foundation

**Roadmap ownership:** prerequisite for v0.7 and reusable by later clients.

Implementation is present on the C1 feature branch. Exact repository CI validation remains open
because the current GitHub-hosted run terminates before creating any job steps.

### Contract

- [x] Define a Godot-facing engine bridge interface with no scene-specific dependencies.
- [x] Define typed client command request shape with command ID/correlation ID.
- [x] Define command accepted/rejected response handling.
- [x] Define authoritative snapshot/state ingestion contract.
- [x] Define ordered domain-event ingestion contract.
- [x] Define query interface for legal actions and read-only engine facts.
- [x] Define preview interface for movement/targeting/spatial queries once v0.6 contracts exist.
- [x] Define bridge version/capability negotiation.
- [x] Define explicit incompatible-version behavior.
- [x] Define error categories suitable for user-facing messaging plus debug detail.
- [x] Add versioned client bridge JSON Schema.
- [x] Document the bridge protocol, authority boundary, transport, resync, and local host.

### Transport separation

- [x] Implement a transport-independent `EngineBridge` abstraction.
- [x] Implement a local/dev transport suitable for the vertical slice.
- [x] Keep transport shape capable of later remote/server use without rewriting tactical scenes.
- [x] Ensure transport/network/disk work never blocks the Godot frame loop.
- [x] Add cancellation/timeouts for requests that can outlive an interaction mode.
- [x] Reject stale command/preview responses using correlation/generation IDs where applicable.
- [x] Reject authoritative event sequence gaps and require resynchronization rather than guessing state.
- [x] Renegotiate capabilities and request authoritative resync after reconnect.
- [x] Add a standard-library `asyncio` localhost host over the authoritative Python engine.
- [x] Expose the local host through the `godot-dnd-client-bridge` CLI entry point.

### Fixtures/testing

- [x] Add deterministic recorded snapshot/event fixtures for client tests.
- [x] Add a fake/test bridge that can drive scenes without a live engine process.
- [x] Test accepted command -> authoritative update flow.
- [x] Test rejected command -> UI error/reconciliation flow.
- [x] Test out-of-order/stale response rejection.
- [x] Test bridge disconnect/reconnect/resync behavior at the presentation boundary.
- [x] Add Python bridge protocol/session tests including a real localhost TCP round-trip test.
- [x] Add a Godot headless bridge test script and wire it into the Godot CI job.

### C1 validation / exit criterion

- [ ] Confirm Ruff, strict Mypy, full Python pytest/coverage, governance/schema checks, Godot 4.7.1
      project parsing, and `res://tests/bridge_tests.gd` on the exact PR head.
- [ ] Demonstrate the real Godot `TcpJsonTransport` negotiating with the Python localhost host in an
      executable integration run before v0.7 gameplay depends on the live bridge.
- [ ] Mark C1 complete only after the executable bridge checks pass without adding client-side rule
      authority.

---

## C2 — Client state architecture and app shell

### State separation

- [ ] Implement read-only authoritative mirror state derived from engine snapshots/events.
- [ ] Implement interaction state separate from authoritative state.
- [ ] Implement presentation state separate from authoritative state.
- [ ] Make selected/hovered/targeted actor IDs explicit interaction data.
- [ ] Make pending command/request state explicit and cancellable.
- [ ] Ensure scene reload can reconstruct visuals from authoritative mirror without hidden gameplay
      state stored only in nodes.
- [ ] Ensure animation/VFX completion is not required for authoritative progression.

### Shell

- [ ] Replace the single-script bootstrap with a small app-shell composition.
- [ ] Add startup/loading state.
- [ ] Add bridge initialization state.
- [ ] Add incompatible/error state.
- [ ] Add tactical-scene loading entry point.
- [ ] Add clean shutdown/bridge disposal behavior.
- [ ] Add local settings store for presentation/input/accessibility only.

### Diagnostics

- [ ] Add structured client logging categories: bridge, state, input, tactical, UI, presentation,
      performance.
- [ ] Make current snapshot/event sequence visible in debug mode.
- [ ] Make bridge version/capabilities visible in debug mode.

---

## C3 — Input system and interaction modes

### Input map

- [ ] Define semantic input actions rather than hardcoded key checks in gameplay scripts.
- [ ] Map keyboard/mouse camera pan/zoom/rotate/focus.
- [ ] Map select/confirm/cancel/context actions.
- [ ] Keep controller-equivalent actions structurally supported.
- [ ] Add input remapping architecture before binding proliferation.
- [ ] Ensure UI focus/navigation does not unintentionally issue tactical commands.

### Interaction controller

- [ ] Define interaction modes: inspect, select, move, target, AoE/shape preview, UI/modal.
- [ ] Make all targeting/movement modes cancellable.
- [ ] Centralize mode transitions instead of scattering booleans through scene scripts.
- [ ] Ensure only one authoritative command submission occurs for one confirmed intent.
- [ ] Ignore/reconcile duplicate rapid confirmations while a command is pending.
- [ ] Preserve selection appropriately after authoritative updates.

---

## C4 — Orthographic/isometric tactical camera

**Root v0.7:** orthographic isometric camera rig + pan/zoom/90-degree rotation.

- [ ] Extract the current camera rig into a reusable tactical camera scene/controller.
- [ ] Preserve true 3D orthographic projection.
- [ ] Add keyboard pan.
- [ ] Add pointer drag/middle-button pan or equivalent ergonomic desktop control.
- [ ] Decide whether edge pan is enabled by default; make it configurable if implemented.
- [ ] Add smooth bounded orthographic zoom.
- [ ] Add exact 90-degree view rotation around a tactical pivot.
- [ ] Keep rotation state discrete even if visual interpolation is smooth.
- [ ] Add focus-on-selected/current actor.
- [ ] Add map-defined camera bounds.
- [ ] Handle widescreen/narrow aspect ratios without revealing unusable voids where practical.
- [ ] Add reduced-motion option for camera easing/automatic focus.
- [ ] Add headless/controller tests for camera state transitions that do not require pixel matching.

---

## C5 — Tactical map scene and environment presentation

**Root v0.7:** one small tactical 3D map.

### Map contract

- [ ] Define tactical map presentation resource/scene contract.
- [ ] Separate visual geometry from authoritative spatial IDs/cells/regions.
- [ ] Define mapping from visual map objects to engine spatial identifiers.
- [ ] Add one small original tactical test map suitable for the vertical-slice encounter.
- [ ] Add terrain/material layers needed for readable tactical presentation.
- [ ] Add map entry/spawn anchors that reference engine IDs rather than owning placement rules.
- [ ] Support camera bounds/focus metadata as presentation data.

### Environment

- [ ] Establish lighting/environment baseline readable from all four tactical rotations.
- [ ] Establish floor/grid readability without making debug grid mandatory for normal play.
- [ ] Define props/environment collision ownership versus headless spatial boundaries.
- [ ] Add obvious diagnostic visualization when Godot geometry and authoritative spatial state disagree.

---

## C6 — Actor presentation from engine state

**Root v0.7:** actors rendered from engine state.

- [ ] Create reusable actor presentation scene keyed by stable engine actor ID.
- [ ] Spawn/despawn actor visuals only from authoritative mirror changes.
- [ ] Update transform/facing from authoritative spatial state once available.
- [ ] Bind display name and basic tactical status from actor/combat state.
- [ ] Add selection indicator.
- [ ] Add hover indicator distinct from selection.
- [ ] Add current-turn indicator.
- [ ] Add team/faction/readability hooks without relying only on color.
- [ ] Add condition/status presentation slots driven by authoritative conditions.
- [ ] Ensure actor visual deletion does not delete/mutate engine actor state.
- [ ] Support placeholder model/material when an optional asset is unavailable.
- [ ] Pool/reuse actor visuals only after profiling shows benefit.

---

## C7 — Picking, selection, inspection, and highlighting

**Root v0.7:** selection/highlighting.

- [ ] Implement pointer ray picking for actors and tactical surfaces.
- [ ] Resolve picked visual object to stable engine/spatial ID.
- [ ] Add click select/deselect.
- [ ] Add hover inspection.
- [ ] Add selected actor summary surface/HUD binding.
- [ ] Add keyboard/controller selection traversal strategy.
- [ ] Prevent occluded/hidden presentation objects from stealing unintended selection where practical.
- [ ] Keep inspection possible when no command is legal.
- [ ] Test selection state survives authoritative actor refresh/re-render.

---

## C8 — Movement query and path preview

**Root v0.7:** reachable movement preview + path preview/cost display.
**Dependency:** v0.6 authoritative spatial query API.

- [ ] Request reachable-space data from spatial authority for the selected actor/current state.
- [ ] Render reachable cells/regions from returned authoritative query data.
- [ ] Request path preview for hovered destination.
- [ ] Render returned authoritative path.
- [ ] Display movement cost and remaining budget.
- [ ] Distinguish legal, unaffordable, blocked, and unknown destinations.
- [ ] Show difficult-terrain/elevation/movement-mode cost information when returned by engine.
- [ ] Do not infer path legality from Godot `NavigationServer` alone.
- [ ] Confirm move by submitting typed command with actor/destination/path reference as required by
      the engine contract.
- [ ] Reconcile preview immediately when authoritative state changes.
- [ ] Cancel stale path queries on selection/mode/state generation changes.

---

## C9 — Targeting, LOS, cover, reach, and AoE previews

**Root v0.7 debug overlay requirement; reusable for v0.8 spell UI.**
**Dependency:** v0.6 authoritative spatial query API.

- [ ] Add generic target-selection mode driven by engine-provided legal target data.
- [ ] Highlight legal/illegal targets distinctly.
- [ ] Display range/reach reason when supplied by the engine.
- [ ] Add LOS preview from authoritative query result.
- [ ] Add cover preview from authoritative query result.
- [ ] Add generic shape/AoE preview renderer for authoritative shape query results.
- [ ] Keep visual shape drawing independent from named spells/abilities.
- [ ] Support origin/target/rotation parameters without deciding AoE membership in Godot.
- [ ] Re-query/reconcile on camera-independent authoritative state changes.
- [ ] Make targeting prompts cancellable and keyboard/controller reachable.

---

## C10 — Tactical HUD and action bar

**Root v0.7:** turn order/combat HUD/action bar.

### HUD

- [ ] Show encounter status and round number from engine state.
- [ ] Show initiative/turn order from authoritative combat state.
- [ ] Clearly identify current actor.
- [ ] Show selected actor HP/temp HP and relevant resources from authoritative state.
- [ ] Show conditions/status effects from authoritative state.
- [ ] Show movement/action/bonus-action/reaction availability from engine combat state.
- [ ] Show pending command/rejection feedback without lying about resolved state.

### Action bar

- [ ] Populate available actions from engine/canonical action data, not UI-hardcoded named lists.
- [ ] Display unavailable actions with engine-provided reason when available.
- [ ] Route hotkeys/buttons/controller selection through the same intent path.
- [ ] Support action -> target/preview -> confirm -> typed command flow.
- [ ] Support cancel/back from every pre-confirmation stage.
- [ ] Prevent duplicate command submission while pending.
- [ ] Design slots/tooltips to later accommodate spells and features without rewriting the bar.

---

## C11 — Combat log, messages, and command rejection UX

- [ ] Present ordered combat/domain events in a readable combat log.
- [ ] Retain stable IDs/sequence in debug-expanded view.
- [ ] Distinguish informational presentation messages from authoritative domain events.
- [ ] Present command rejection in context near the relevant interaction when possible.
- [ ] Map validation errors to concise user wording while preserving technical reason in debug logs.
- [ ] Make repeated replay/resync events idempotent in visual log presentation.

---

## C12 — Presentation-event pipeline: animation, VFX, audio, camera emphasis

**Root v0.7:** basic animation/VFX/audio event mapping.

- [ ] Define presentation event router separate from engine reducer/state.
- [ ] Map actor movement events to visual movement/interpolation.
- [ ] Map attack/action events to generic animation hooks.
- [ ] Map damage/healing/status events to generic VFX/UI hooks.
- [ ] Map domain events to audio cue IDs without hardcoding rules outcomes.
- [ ] Add optional camera focus/emphasis hooks.
- [ ] Ensure skipping/cancelling animations cannot alter authoritative result.
- [ ] Support fast replay/instant presentation mode for tests/debugging.
- [ ] Recover cleanly when optional animation/VFX/audio asset is missing.
- [ ] Avoid blocking event ingestion on long animation sequences.

---

## C13 — Roof, wall, and foreground occlusion

**Root v0.7:** roof/foreground occlusion handling.

- [ ] Choose and document tactical occlusion strategy: fade, hide layers, cutaway, or hybrid.
- [ ] Tag occludable visual geometry explicitly.
- [ ] Fade/hide foreground objects that obscure selected/current actor or interaction focus.
- [ ] Avoid making hidden geometry change authoritative collision/spatial rules.
- [ ] Restore occluders correctly across 90-degree rotations.
- [ ] Add accessibility option to reduce/disable animated fades where practical.
- [ ] Test occlusion state does not leak across map reloads.

---

## C14 — Tactical debug and developer overlays

**Root v0.7:** grid/path/LOS/cover/AoE debug overlays plus engine IDs.

- [ ] Master debug overlay toggle.
- [ ] Authoritative logical grid/space overlay.
- [ ] Occupancy overlay.
- [ ] Movement-cost overlay.
- [ ] Current requested/returned path overlay.
- [ ] LOS ray/result overlay.
- [ ] Cover classification overlay.
- [ ] AoE membership/shape overlay.
- [ ] Actor/spatial/rule stable-ID labels.
- [ ] Snapshot/event sequence display.
- [ ] Navigation/geometry comparison overlay to diagnose adapter disagreements.
- [ ] Bridge request timing display.
- [ ] Basic frame-time/FPS presentation diagnostics.
- [ ] Keep debug overlays out of normal release UX unless explicitly enabled.

---

## C15 — Accessibility, settings, and desktop UX baseline

- [ ] UI scale setting.
- [ ] Text remains usable at supported UI scales.
- [ ] Reduced motion setting affects optional camera/UI/presentation easing.
- [ ] Volume controls by useful buses/categories.
- [ ] Input remapping UI or at minimum remapping-ready data model before v1.0.
- [ ] Avoid color-only distinction for selected/hostile/legal/illegal states.
- [ ] Provide readable focus states for keyboard/controller UI navigation.
- [ ] Persist presentation/accessibility settings independently from authoritative campaign save.

---

## C16 — Client performance and lifecycle

- [ ] Establish representative tactical-scene frame-time baseline before optimization.
- [ ] Add optional debug counters for actor count and presentation queue depth.
- [ ] Avoid per-frame scene-tree scans for actor lookup.
- [ ] Avoid per-frame JSON parsing/bridge serialization.
- [ ] Use event-driven state binding where practical.
- [ ] Measure map scene-load time.
- [ ] Measure bridge query latency for movement/LOS/AoE previews.
- [ ] Cancel work/queries when tactical scene unloads.
- [ ] Confirm repeated enter/exit of tactical scene does not duplicate bridge subscriptions/signals.
- [ ] Confirm no stale actor visuals remain after encounter/map teardown.

---

## C17 — Headless Godot validation and client test matrix

- [ ] Tactical root scene loads headlessly without parse/resource errors.
- [ ] Camera controller state tests.
- [ ] Input-mode transition tests.
- [ ] Fake bridge snapshot -> actor/map rendering smoke test.
- [ ] Selection/highlight test.
- [ ] Accepted command routing test.
- [ ] Rejected command/reconciliation test.
- [ ] Movement preview test from recorded authoritative spatial fixture.
- [ ] LOS/cover/AoE overlay tests from recorded fixtures.
- [ ] HUD binding test from recorded combat fixture.
- [ ] Presentation event router test with animations disabled/instant.
- [ ] Scene teardown/reload signal-subscription regression test.
- [ ] No client test should require duplicating an engine rule to establish expected legality.

---

## C18 — v0.7 tactical vertical-slice acceptance

This section mirrors and expands the root v0.7 exit work. Root `TODO.md` should only be checked when
the corresponding behavior here is genuinely demonstrated.

- [ ] Camera supports pan, bounded zoom, focus, and exact 90-degree rotation.
- [ ] One original tactical 3D map loads through the production client shell.
- [ ] Actors render from authoritative engine state using stable actor IDs.
- [ ] Player can select/inspect an actor.
- [ ] Reachable movement preview comes from spatial authority.
- [ ] Path/cost preview comes from spatial authority.
- [ ] Player can submit a movement command through the engine bridge and see authoritative result.
- [ ] Player can choose and submit at least one combat action through the action bar.
- [ ] Turn order/HUD updates from authoritative combat state/events.
- [ ] LOS/cover/AoE debug overlays visualize authoritative queries.
- [ ] Basic animation/VFX/audio hooks react to resolved events.
- [ ] Roof/foreground occlusion keeps tactical focus readable through all four camera rotations.
- [ ] Combat can be completed without any Godot script deciding a rules outcome.
- [ ] The same recorded encounter can drive a replay/presentation smoke flow without issuing duplicate
      authoritative commands.
- [ ] Headless Godot validation passes for the tactical client.

### v0.7 client exit criterion

- [ ] A complete small tactical encounter is playable through Godot while authoritative rules,
      combat, spatial legality, randomness, and state mutation remain outside the presentation layer.

---

## C19 — Post-v0.7 spell UI integration (v0.8)

Do not implement named-spell special cases ahead of v0.8 engine capability.

- [ ] Display spell resources/availability from engine data.
- [ ] Reuse generic target/shape/AoE preview modes.
- [ ] Reuse action bar and engine rejection flow.
- [ ] Show concentration/duration/ongoing status from authoritative state.
- [ ] Support upcast/scaling choices supplied by engine/canonical data.

---

## C20 — Complete character creator UX (v0.9)

- [ ] Identity step.
- [ ] Species step sourced from engine choices.
- [ ] Background step sourced from engine choices.
- [ ] Class step sourced from engine choices.
- [ ] Ability score step.
- [ ] Skills/proficiencies step.
- [ ] Equipment step.
- [ ] Spell/feature choice step.
- [ ] Appearance hooks that do not alter rules state except through typed character data.
- [ ] Biography/personality metadata.
- [ ] Review/validation step using engine validation.
- [ ] Level-up flow using engine-generated legal choices.

---

## C21 — v1.0 RPG client shell

Add actionable detail when v1.0 becomes near-term rather than prematurely implementing it during
v0.7.

- [ ] Exploration HUD and interaction prompts.
- [ ] Dialogue UI.
- [ ] Quest/journal UI.
- [ ] Inventory/equipment UI.
- [ ] Party/character screens.
- [ ] Shop/trade UI.
- [ ] Rest/travel/area-transition UX.
- [ ] Map screen.
- [ ] Production save/load UX.
- [ ] Credits/attribution presentation.

---

## Client backlog hygiene

When a client task is discovered:

- put it in the owning client phase above;
- identify the root roadmap milestone/dependency;
- prefer an observable result over vague tasks such as “improve UI”;
- do not check engine-owned rules/spatial work here;
- do not implement future screens just because a reusable control could theoretically support them;
- update root `TODO.md` only when a root milestone state changes or when the root backlog needs a
  cross-reference;
- keep this file, root agent files, and `CHANGELOG.md` synchronized when client workflow changes.
