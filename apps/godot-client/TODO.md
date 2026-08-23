# Godot Client TODO

This is the detailed execution backlog for `apps/godot-client/`.

It is subordinate to the repository-root `ROADMAP.md`, `TODO.md`, and `AGENTS.md`. Client agents must
also follow `apps/godot-client/AGENTS.md`. A checked implementation item here means the observable
client behavior exists in code; phase validation/exit items remain separately unchecked until the
exact implementation is executed through the required headless/playable gates.

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
- [x] Main client path includes a 3D scene with an orthographic `Camera3D` rig.
- [x] Project identifies the Godot client as presentation-only in existing comments.
- [x] Headless Godot project validation exists in repository CI.

### Client governance

- [x] Add `apps/godot-client/AGENTS.md` with client-specific authority, bridge, testing, and UX rules.
- [x] Add this detailed `apps/godot-client/TODO.md` client backlog.
- [x] Keep root `AGENTS.md` wired to require the local client contract/TODO for client work.
- [x] Keep Claude, Gemini, and Copilot repository adapters wired to the local client contract/TODO.
- [x] Keep root `TODO.md` v0.7 pointing to this detailed client backlog.
- [ ] Add client-specific validation to governance tooling if plain documentation references prove too
      easy to drift.

### Planned client source organization

Create these only as implementation needs them; empty directory scaffolding is not completion.

- [x] `autoload/` for presentation app shell/bridge registry/settings only.
- [x] `bridge/` for typed engine transport/protocol adapters.
- [x] `state/` for authoritative mirror, interaction state, and presentation state.
- [x] `camera/` for tactical camera controllers/config.
- [x] `input/` for input mapping and interaction modes.
- [x] `scenes/shell/` for startup/loading/root composition.
- [x] `scenes/tactical/` for battle-map presentation entry points.
- [x] `scenes/actors/` for reusable actor presentation.
- [x] `ui/hud/` as the first tactical UI surface.
- [x] `presentation/` for event-to-animation/VFX/audio mapping and occlusion presentation.
- [x] `debug/` for authoritative tactical/debug overlays.
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
- [x] Add a Godot headless bridge test script and wire it into the local CI script.

### C1 validation / exit criterion

- [ ] Confirm Ruff, strict Mypy, full Python pytest/coverage, governance/schema checks, Godot 4.7.1
      project parsing, and `res://tests/bridge_tests.gd` on the exact PR head.
- [ ] Demonstrate the real Godot `TcpJsonTransport` negotiating with the Python localhost host in an
      executable integration run before v0.7 gameplay depends on the live bridge.
- [ ] Mark C1 complete only after the executable bridge checks pass without adding client-side rule
      authority.

---

## C2 — Client state architecture and app shell

Implementation is present on the C2 feature branch. It keeps the authoritative mirror, interaction
state, and presentation state separate and replaces the one-script bootstrap with a lifecycle-aware
application shell. Exact Godot CI execution remains a separate validation gate.

### State separation

- [x] Implement read-only authoritative mirror state derived from engine snapshots/events.
- [x] Implement interaction state separate from authoritative state.
- [x] Implement presentation state separate from authoritative state.
- [x] Make selected/hovered/targeted actor IDs explicit interaction data.
- [x] Make pending command/request state explicit and cancellable.
- [x] Ensure scene reload can reconstruct visuals from authoritative mirror without hidden gameplay
      state stored only in nodes.
- [x] Ensure animation/VFX completion is not required for authoritative progression.
- [x] Keep the mirror as snapshot + ordered post-snapshot events rather than adding a client gameplay
      reducer.

### Shell

- [x] Replace the single-script bootstrap with a small app-shell composition.
- [x] Add startup/loading state.
- [x] Add bridge initialization and authoritative synchronization states.
- [x] Add incompatible/error state with a retry path.
- [x] Add tactical-scene loading entry point without implementing C5 map behavior.
- [x] Load the first tactical PackedScene asynchronously rather than blocking the frame loop on disk.
- [x] Add clean shutdown/bridge disposal behavior.
- [x] Add local settings store for presentation/input/accessibility only.

### Diagnostics

- [x] Add structured client logging categories: bridge, state, input, tactical, UI, presentation,
      performance.
- [x] Make current snapshot/event sequence visible in debug mode.
- [x] Make bridge version/capabilities visible in debug mode.
- [x] Expose pending-request count and active presentation scene in the debug overlay.

### Fixtures/testing

- [x] Add headless tests for mirror deep-copy/read-only behavior and sequence rejection.
- [x] Add headless tests for explicit interaction IDs/generation and pending request cancellation.
- [x] Prove authoritative sequence can advance while presentation activity remains in flight.
- [x] Test shell hello -> snapshot synchronization -> asynchronous tactical load -> ready flow.
- [x] Test tactical scene reconstruction from the same snapshot-plus-event mirror after scene reload.
- [x] Test debug sequence/version/capability display and clean shutdown.
- [x] Wire `res://tests/state_shell_tests.gd` into the local CI script after the C1 bridge suite.
- [x] Document C2 ownership, lifecycle, reconstruction, settings, diagnostics, and C3 handoff.

### C2 validation / exit criterion

- [ ] Confirm Godot 4.7.1 project parsing, `res://tests/bridge_tests.gd`, and
      `res://tests/state_shell_tests.gd` execute successfully on the exact C2 PR head.
- [ ] Confirm the stacked C1 Python/Ruff/Mypy/coverage/governance checks execute successfully on the
      exact integrated head rather than failing before job step 1.
- [ ] Mark C2 complete only after executable checks pass with no gameplay/rules/spatial authority in
      Godot state or shell code.

---

## C3 — Input system and interaction modes

Implementation is present on the C3 feature branch. It establishes semantic device-neutral input,
remappable bindings, centralized interaction modes, modal/focus safety, and single-submit command
intent handling without implementing C4 camera behavior or C8/C9 spatial/targeting authority.

### Input map

- [x] Define semantic input actions rather than hardcoded key checks in gameplay scripts.
- [x] Map keyboard/mouse camera pan/zoom/rotate/focus.
- [x] Map select/confirm/cancel/context actions.
- [x] Keep controller-equivalent actions structurally supported.
- [x] Add input remapping architecture before binding proliferation.
- [x] Ensure UI focus/navigation does not unintentionally issue tactical commands.
- [x] Persist remapping descriptors separately from authoritative campaign/save state.

### Interaction controller

- [x] Define interaction modes: inspect, select, move, target, AoE/shape preview, UI/modal.
- [x] Make all targeting/movement modes cancellable.
- [x] Centralize mode transitions instead of scattering booleans through scene scripts.
- [x] Make interaction-mode changes advance the existing generation used for stale response rejection.
- [x] Ensure only one authoritative command submission occurs for one confirmed intent.
- [x] Ignore/reconcile duplicate rapid confirmations while a command is pending.
- [x] Keep rejected command intents available for correction/retry.
- [x] Return accepted transient commands to select/inspect only after authoritative acceptance.
- [x] Preserve selection appropriately after authoritative updates.
- [x] Keep one persistent interaction controller in the app shell across tactical scene reloads.
- [x] Disable tactical input while the shell is not ready.

### Fixtures/testing

- [x] Add `res://tests/input_interaction_tests.gd` for semantic bindings and mode transitions.
- [x] Test keyboard/mouse/controller defaults and descriptor-based remapping.
- [x] Test UI focus blocks raw tactical confirmation while explicit UI actions share the same path.
- [x] Test move/target/shape cancellation and UI modal suspend/restore.
- [x] Test duplicate-confirm suppression, rejection retry, and accepted-command reconciliation.
- [x] Test mode-scoped preview cancellation and selection preservation across authoritative refresh.
- [x] Wire the C3 input/interaction suite into the local CI script after the C1/C2 suites.
- [x] Document C3 authority, semantic actions, bindings, modes, modal behavior, command lifecycle, and
      C4 handoff in `docs/GODOT_CLIENT_INPUT.md`.

### C3 validation / exit criterion

- [ ] Confirm Godot 4.7.1 project parsing and `res://tests/input_interaction_tests.gd` execute
      successfully on the exact C3 PR head alongside the existing C1/C2 suites.
- [ ] Confirm the repository Python/governance checks execute successfully on the exact integrated
      head rather than failing before job step 1.
- [ ] Mark C3 complete only after executable checks pass with all command outcomes and spatial/rules
      authority remaining outside Godot input code.

---

## C4 — Orthographic/isometric tactical camera

**Root v0.7:** orthographic isometric camera rig + pan/zoom/90-degree rotation.

- [x] Extract the current camera rig into a reusable tactical camera scene/controller.
- [x] Preserve true 3D orthographic projection.
- [x] Add keyboard/semantic-action pan.
- [x] Add pointer drag/middle-button pan.
- [x] Decide edge pan is not enabled for the v0.7 baseline; semantic pan and drag remain the supported desktop controls.
- [x] Add smooth bounded orthographic zoom.
- [x] Add exact 90-degree view rotation around a tactical pivot.
- [x] Keep rotation state discrete even if visual interpolation is smooth.
- [x] Add focus-on-selected/current actor.
- [x] Add map-defined camera bounds.
- [ ] Add explicit aspect-ratio-aware padding so extreme widescreen/narrow layouts never reveal unusable voids.
- [x] Add reduced-motion behavior for camera easing/automatic focus.
- [x] Add headless/controller camera state tests that do not require pixel matching.

---

## C5 — Tactical map scene and environment presentation

**Root v0.7:** one small tactical 3D map.

### Map contract

- [x] Define tactical map presentation contract in `docs/V0.7_GODOT_VERTICAL_SLICE.md`.
- [x] Separate visual geometry from authoritative spatial IDs/cells/regions.
- [x] Define mapping from visual map objects to engine grid coordinates/stable actor IDs.
- [x] Add one small original Sunken Courtyard tactical map suitable for the vertical-slice encounter.
- [x] Add terrain/material layers for open, difficult, elevated, blocking, and LOS-blocking cells.
- [ ] Add reusable exploration/map-entry spawn-anchor resources; v0.7 actors currently enter only from authoritative tactical placements.
- [x] Support camera bounds/focus metadata as presentation data.

### Environment

- [x] Establish lighting/environment baseline readable from all four tactical rotations.
- [x] Establish floor/grid readability without requiring the debug overlay.
- [x] Define visual/collider ownership versus headless spatial boundaries in v0.7 docs.
- [x] Log an explicit diagnostic warning when an authoritative actor position cannot map to the visual grid.

---

## C6 — Actor presentation from engine state

**Root v0.7:** actors rendered from engine state.

- [x] Create reusable actor presentation scene keyed by stable engine actor ID.
- [x] Spawn/despawn actor visuals only from authoritative mirror changes.
- [x] Update actor transform from authoritative spatial state; facing remains future data when the engine exposes it.
- [x] Bind display name and HP/AC tactical status from actor/combat state.
- [x] Add selection indicator.
- [x] Add hover indicator distinct from selection.
- [x] Add current-turn indicator.
- [ ] Add non-color team/faction emblem/icon hooks; current placeholder team distinction still uses material color plus text identity.
- [ ] Add dedicated condition/status presentation slots; conditions are present in snapshot data but not yet rendered as badges.
- [x] Ensure actor visual deletion does not delete/mutate engine actor state.
- [x] Support placeholder primitive model/material without optional art assets.
- [ ] Pool/reuse actor visuals only after profiling shows benefit.

---

## C7 — Picking, selection, inspection, and highlighting

**Root v0.7:** selection/highlighting.

- [x] Implement pointer ray picking for actors and tactical surfaces.
- [x] Resolve picked visual object to stable engine actor ID or logical cell coordinates.
- [x] Add click select/deselect.
- [x] Add hover inspection/highlighting.
- [x] Add selected actor summary HUD binding.
- [x] Add keyboard/controller selection traversal through the semantic Context action.
- [ ] Add explicit click-through filtering for faded/hidden occluders beyond current actor/surface collider separation.
- [x] Keep inspection possible when no command is legal.
- [x] Preserve stable selected actor ID across authoritative actor refresh/re-render.

---

## C8 — Movement query and path preview

**Root v0.7:** reachable movement preview + path preview/cost display.
**Dependency:** v0.6 authoritative spatial query API.

- [x] Request reachable-space data from spatial authority for the selected actor/current state.
- [x] Render reachable cells/regions from returned authoritative query data.
- [x] Request path preview for hovered destination.
- [x] Render returned authoritative path.
- [x] Display authoritative movement cost and current remaining budget in HUD/state.
- [x] Display engine rejection/reason for blocked/unaffordable/illegal destinations.
- [ ] Add per-segment difficult-terrain/elevation/movement-mode cost breakdown when the engine query contract exposes it.
- [x] Do not infer path legality from Godot `NavigationServer` or visual collision.
- [x] Confirm move by submitting a typed command with actor/destination/movement mode and expected authoritative sequence.
- [ ] Re-request active previews automatically after an unrelated authoritative state update while the player remains in Move mode.
- [x] Cancel stale path queries on selection/mode/generation changes through C3 request tracking and coordinator generation filtering.

---

## C9 — Targeting, LOS, cover, reach, and AoE previews

**Root v0.7 debug overlay requirement; reusable for v0.8 spell UI.**
**Dependency:** v0.6 authoritative spatial query API.

- [x] Add generic target-selection mode where each hovered target is approved/rejected by an engine preview.
- [x] Highlight legal/illegal target line distinctly and provide textual legality status.
- [x] Display range/reach reason when supplied by the engine.
- [x] Add LOS preview from authoritative query result.
- [x] Add cover preview from authoritative query result.
- [x] Add generic shape/AoE preview renderer for authoritative shape query results.
- [x] Keep visual shape drawing independent from named spells/abilities.
- [ ] Add full generic origin/target/rotation UI parameters for cone/line/cylinder authoring; v0.7 UI exercises a sphere debug query only.
- [ ] Re-query active target/shape previews automatically after unrelated authoritative state changes.
- [ ] Add controller-only target traversal independent of pointer position; C3 cancellation/controller semantics are already supported.

---

## C10 — Tactical HUD and action bar

**Root v0.7:** turn order/combat HUD/action bar.

### HUD

- [x] Show encounter status context and round number from engine state.
- [x] Show initiative/turn order from authoritative combat state.
- [x] Clearly identify current actor.
- [x] Show selected actor HP/temp HP, AC, and movement from authoritative state.
- [ ] Render authoritative conditions/resources as dedicated HUD badges/rows rather than leaving them only in snapshot data.
- [x] Show movement/action/bonus-action/reaction availability through authoritative actor/economy data and action queries.
- [x] Show pending command/rejection feedback without changing resolved state.

### Action bar

- [x] Populate Move/Strike/End Turn availability and labels from `tactical.actions` engine query results.
- [x] Display unavailable actions with engine-provided reason when available.
- [x] Route buttons/semantic input through the same C3 intent/controller path.
- [x] Support action -> target/preview -> confirm -> typed command flow.
- [x] Support cancel/back from every pre-confirmation mode through C3.
- [x] Prevent duplicate command submission while pending through C3.
- [ ] Add data-driven slot grouping/tooltips needed for broad v0.8 spell/feature catalogs.

---

## C11 — Combat log, messages, and command rejection UX

- [x] Present resolved tactical presentation events in a readable combat log.
- [ ] Add stable IDs/sequence in a user-toggleable debug-expanded combat-log view.
- [x] Distinguish informational presentation events from the authoritative snapshot/event stream.
- [x] Present command rejection in the tactical interaction/HUD context.
- [x] Preserve technical rejection detail while displaying concise user-facing wording.
- [ ] Add explicit replay/resync de-duplication keys for long-lived visual log history.

---

## C12 — Presentation-event pipeline: animation, VFX, audio, camera emphasis

**Root v0.7:** basic animation/VFX/audio event mapping.

- [x] Define presentation event router separate from engine reducer/state.
- [x] Map actor movement snapshots/events to visual movement interpolation.
- [x] Map resolved attack events to generic log/emphasis hooks.
- [ ] Add dedicated damage/healing/status VFX primitives beyond the current attack/result emphasis.
- [x] Map resolved events to audio cue IDs without hardcoding outcomes in presentation.
- [x] Add optional actor/camera emphasis hooks.
- [x] Ensure skipping/cancelling visual interpolation cannot alter authoritative result.
- [x] Support reduced-motion/instant actor and camera presentation mode for tests/debugging.
- [x] Remain functional with no optional animation/VFX/audio assets by using primitive placeholders/cue hooks.
- [x] Avoid blocking authoritative event/snapshot ingestion on presentation completion.

---

## C13 — Roof, wall, and foreground occlusion

**Root v0.7:** roof/foreground occlusion handling.

- [x] Choose/document a lightweight foreground fade strategy for the v0.7 slice.
- [x] Tag occludable visual geometry explicitly with `tactical_occluder`.
- [x] Fade foreground objects that enter the camera-to-selected/current-actor presentation corridor.
- [x] Keep hidden/faded geometry completely separate from authoritative collision/LOS rules.
- [x] Refresh occlusion after camera quarter-turn/focus updates.
- [x] Use instant material alpha changes, so reduced-motion users are not forced through animated fades.
- [x] Clear faded occluder state when the tactical scene exits.

---

## C14 — Tactical debug and developer overlays

**Root v0.7:** grid/path/LOS/cover/AoE debug overlays plus engine IDs.

- [x] Retain the existing master client debug overlay toggle.
- [x] Render the authoritative logical tactical grid as the map surface layout.
- [ ] Add a dedicated occupancy debug layer beyond actor placement itself.
- [x] Show movement cost in path/HUD preview text.
- [x] Render current requested/returned authoritative path overlay.
- [x] Render target line/result from authoritative LOS/legality preview.
- [x] Show authoritative cover classification/source information in target preview text.
- [x] Render authoritative AoE membership/shape cell overlay.
- [ ] Add debug-only stable actor/spatial/rule ID labels directly over scene objects.
- [x] Keep snapshot/event sequence visible in the existing debug overlay.
- [ ] Add navigation/geometry comparison visualization for adapter disagreement diagnosis.
- [ ] Add bridge request timing/latency display.
- [ ] Add frame-time/FPS presentation diagnostics.
- [x] Keep developer-only area/debug controls separate from ordinary authoritative combat resolution.

---

## C15 — Accessibility, settings, and desktop UX baseline

- [x] Retain presentation-only UI scale setting/data model.
- [ ] Validate all new tactical HUD text at every supported UI scale in an executable UI pass.
- [x] Reduced motion affects optional camera/actor presentation easing.
- [x] Retain presentation-only master volume setting; richer bus controls remain future work.
- [x] Retain C3 input-remapping data model.
- [x] Pair color cues with labels/rings/textual legality messages rather than relying on color alone for selection/legal state.
- [x] Use standard Godot Button focus behavior for keyboard/controller HUD navigation.
- [x] Persist presentation/accessibility settings independently from authoritative campaign save.

---

## C16 — Client performance and lifecycle

- [ ] Establish measured representative tactical-scene frame-time baseline before optimization.
- [x] Expose presentation queue count in `TacticalEventPresenter` for later diagnostics.
- [x] Use actor-ID dictionary lookup instead of per-frame scene-tree scans.
- [x] Avoid per-frame JSON parsing/bridge serialization.
- [x] Use event-driven authoritative/HUD/actor binding; only camera motion is frame-updated.
- [ ] Measure tactical map scene-load time.
- [ ] Measure bridge query latency for movement/LOS/AoE previews.
- [ ] Cancel every scene-owned preview explicitly on tactical-scene unload; C3 mode cancellation and coordinator stale filtering already prevent application of stale results.
- [x] Disconnect tactical state/controller/event-presenter subscriptions on scene exit to avoid duplicate subscriptions.
- [x] Queue stale actor visuals for deletion when authoritative actors disappear.

---

## C17 — Headless Godot validation and client test matrix

- [x] Add tactical root-scene load path to a headless FakeEngineTransport integration suite.
- [x] Add camera controller state tests.
- [x] Retain C3 input-mode transition tests.
- [x] Add fake-bridge snapshot -> actor/map rendering smoke test.
- [x] Add stable current-actor selection smoke test.
- [x] Add accepted typed movement command routing/reconciliation test.
- [x] Retain C3 rejected-command/reconciliation tests.
- [x] Add movement reachable/path preview tests using authoritative fake responses.
- [ ] Add assertions against rendered LOS/cover/AoE marker contents rather than only request routing/status.
- [x] Exercise HUD/action-query binding through the tactical scene flow.
- [x] Test presentation-event forwarding with reduced-motion/instant presentation.
- [ ] Add v0.7 tactical scene teardown/reload subscription regression beyond the existing C2 stub reload test.
- [x] Keep client expectations based on supplied authoritative fixture results rather than reimplementing engine legality.

---

## C18 — v0.7 tactical vertical-slice acceptance

This section mirrors and expands the root v0.7 exit work. Root `TODO.md` tracks implementation separately
from exact-head executable acceptance.

- [x] Camera implementation supports pan, bounded zoom, focus, and exact 90-degree rotation.
- [x] One original tactical 3D map loads through the capability-selected production client shell.
- [x] Actors render from authoritative engine state using stable actor IDs.
- [x] Player can select/inspect an actor.
- [x] Reachable movement preview comes from spatial authority.
- [x] Path/cost preview comes from spatial authority.
- [x] Player can submit a movement command through the engine bridge and reconcile the authoritative snapshot.
- [x] Player can choose and submit the demo Strike combat action through the action bar/interaction controller.
- [x] Turn order/HUD updates from authoritative combat snapshots/events.
- [x] LOS/cover/AoE debug presentation consumes authoritative queries/previews.
- [x] Basic animation/VFX/audio hooks react only to resolved events/snapshots.
- [x] Foreground occlusion keeps the selected/current actor readable without affecting engine LOS.
- [x] Python acceptance coverage drives the same typed command loop to encounter completion with no Godot-side rules decisions.
- [ ] Demonstrate the complete encounter interactively through the Godot client on the exact v0.7 head.
- [ ] Demonstrate recorded/replay-driven presentation smoke without issuing duplicate authoritative commands.
- [ ] Execute all headless Godot validation successfully on the exact v0.7 head.

### v0.7 client exit criterion

- [ ] A complete small tactical encounter is demonstrated through Godot while authoritative rules,
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

- [x] Identity step.
- [x] Species step sourced from engine choices.
- [x] Background step sourced from engine choices.
- [x] Class step sourced from engine choices.
- [x] Ability score step.
- [x] Skills/proficiencies step.
- [x] Equipment step.
- [x] Spell/feature choice step.
- [x] Appearance hooks that do not alter rules state except through typed character data.
- [x] Biography/personality metadata.
- [x] Review/validation step using engine validation.
- [x] Level-up flow using engine-generated legal choices.

---

## C21 — v1.0 RPG client shell

v1.0 is now active. Keep this section aligned with observable Godot behavior while leaving exact-head
validation and broader campaign acceptance work separate.

- [ ] Exploration HUD and interaction prompts.
- [x] Dialogue UI.
- [x] Quest/journal UI.
- [x] Inventory/equipment UI.
- [x] Party/character screens.
- [ ] Shop/trade UI.
- [ ] Rest/travel/area-transition UX.
- [x] Map screen.
- [ ] Production save/load UX.
- [ ] Credits/attribution presentation.

### Current v1.0 management phase

- [x] Restore Journal, Map, Party, and Inventory tabs on the integrated world view.
- [x] Render party cards from authoritative `characters.get` records rather than actor IDs alone.
- [x] Render inventory ownership, currency, and current equipment only from world snapshot/query data.
- [x] Submit `inventory.equip` through the bridge with the isolated world sequence and reconcile after acceptance.
- [x] Keep world snapshots and character presentation records separate from the tactical/core authoritative mirror.
- [x] Extend the FakeEngineTransport headless suite to verify character queries, rendered party data, and equipment command routing.
- [ ] Replace the opaque equipment-slot text field with engine-provided legal slot/item compatibility choices when that query contract exists.
- [ ] Add sell/trade inventory controls without duplicating price, stock, or ownership rules in Godot.

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