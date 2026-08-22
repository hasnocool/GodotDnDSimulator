# Godot Client TODO

This is the detailed execution backlog for `apps/godot-client/`.

It is subordinate to root `ROADMAP.md`, `TODO.md`, and `AGENTS.md`. Client agents must also follow `apps/godot-client/AGENTS.md`. A checked item means observable behavior exists and applicable validation has been performed; planning/scaffolding alone is not completion.

## Client product goal

Build a polished Godot 4.x 3D orthographic/isometric client that:

- renders authoritative engine/campaign/combat/spatial state;
- turns player input into typed engine commands/queries/previews;
- presents legal movement, targeting, LOS, cover, AoE, resources, turn state, and outcomes without becoming rules authority;
- maps resolved engine events to animation, VFX, audio, camera, HUD, and logs;
- supports the v0.7 tactical vertical slice first, then exploration, character creation, inventory, dialogue, quests, creator tooling, and multiplayer;
- remains usable headlessly for integration and replay-driven presentation tests.

## Dependency rule

Do not fake missing engine features in GDScript merely to unblock a screen.

- v0.5 owns tactical combat authority.
- v0.6 owns spatial legality/query authority.
- v0.7 owns the first production Godot tactical vertical slice.
- v0.8 adds spell runtime/UI on generic rule/spatial APIs.
- v0.9 owns the complete rules-driven character-creator UX.
- v1.0 owns the full exploration/RPG shell UX.

---

## C0 — Existing scaffold and client governance

### Existing baseline

- [x] Godot project exists under `apps/godot-client/`.
- [x] Main scene is a 3D scene with an orthographic `Camera3D` rig.
- [x] Existing bootstrap explicitly identifies the client as presentation-only.
- [x] Headless Godot project validation exists in repository CI.

### Client governance

- [x] Add `apps/godot-client/AGENTS.md` with client-specific authority, bridge, testing, and UX rules.
- [x] Add this detailed `apps/godot-client/TODO.md` client backlog.
- [ ] Keep root `AGENTS.md` wired to require the local client contract/TODO for client work.
- [ ] Keep Claude, Gemini, and Copilot adapters wired to the local client contract/TODO.
- [ ] Keep root `TODO.md` v0.7 pointing to this detailed client backlog.
- [ ] Add client-specific governance automation if plain documentation references prove too easy to drift.

### Planned client source organization

Create folders only when implementation needs them; empty scaffolding is not completion.

- [ ] `autoload/` for presentation app shell/bridge registry/settings only.
- [x] `bridge/` for typed engine transport/protocol adapters.
- [ ] `state/` for authoritative mirror, interaction state, and presentation state.
- [ ] `camera/` for tactical camera controllers/config.
- [ ] `input/` for input mapping and interaction modes.
- [ ] `scenes/shell/` for startup/loading/root composition.
- [ ] `scenes/tactical/` for battle-map presentation.
- [ ] `scenes/actors/` for reusable actor presentation.
- [ ] `ui/hud/`, `ui/actions/`, `ui/panels/`, `ui/common/` as UI arrives.
- [ ] `presentation/` for event-to-animation/VFX/audio mapping.
- [ ] `debug/` for authoritative tactical/debug overlays.
- [x] `tests/` for headless Godot client tests.

---

## C1 — Client/engine bridge foundation

**Roadmap ownership:** prerequisite for v0.7 and reusable by later clients.

### Contract

- [x] Define a Godot-facing engine bridge interface with no scene-specific dependencies.
- [x] Define versioned JSON bridge envelope with request ID, correlation ID, generation, payload, and error model.
- [x] Define typed client command submission carrying the existing authoritative command envelope.
- [x] Define command accepted/rejected response handling.
- [x] Define authoritative snapshot/state ingestion contract.
- [x] Define ordered domain-event ingestion contract with duplicate/gap handling.
- [x] Define read-only query interface for legal actions and engine facts.
- [x] Define generation-scoped preview interface for future v0.6 movement/targeting/spatial queries.
- [x] Define bridge version/protocol/capability negotiation.
- [x] Define explicit incompatible-version failure behavior.
- [x] Define categorized errors with user-facing message plus debug detail.
- [x] Add repository JSON Schema for bridge message v1.
- [x] Document protocol/lifecycle in `docs/GODOT_CLIENT_BRIDGE.md`.

### Transport separation

- [x] Implement transport-independent `EngineTransport` abstraction.
- [x] Implement non-blocking newline-delimited JSON/TCP transport for local development.
- [x] Default local transport to `127.0.0.1:4765` while keeping host/port configurable for later remote use.
- [x] Keep tactical/scene code independent of transport details through `EngineBridge`.
- [x] Ensure socket connect/read/write is polled rather than run in a blocking frame-loop wait.
- [x] Add request cancellation.
- [x] Add per-request timeout tracking.
- [x] Reject stale responses by request/correlation/generation identity.
- [x] Reject event sequence gaps and request authoritative resync instead of guessing.
- [x] Renegotiate on reconnect and automatically request resync after prior authoritative state was observed.

### Fixtures/testing

- [x] Add deterministic recorded v1 snapshot/event fixtures.
- [x] Add `FakeEngineTransport` for client tests without a live Python process.
- [x] Test compatible hello/capability negotiation.
- [x] Test accepted command -> authoritative event update flow.
- [x] Test rejected command -> categorized UI/debug error flow.
- [x] Test stale generation rejection.
- [x] Test out-of-order/gapped event resync behavior.
- [x] Test disconnect/reconnect -> renegotiation/resync behavior.
- [x] Test request timeout and cancellation.
- [x] Test incompatible bridge version fails closed.
- [ ] Confirm the bridge test script parses and passes under the repository Godot 4.7.1 CI runner on this PR head.

### C1 exit criterion

- [ ] CI parses the Godot project and executes `res://tests/bridge_tests.gd` successfully on the exact PR head.
- [ ] A real local authoritative engine host can speak bridge v1 over the TCP transport before v0.7 depends on live gameplay. The transport/protocol is complete here; the production host process may be delivered with the engine-facing integration slice.

---

## C2 — Client state architecture and app shell

### State separation

- [ ] Implement read-only authoritative mirror state derived from engine snapshots/events.
- [ ] Implement interaction state separate from authoritative state.
- [ ] Implement presentation state separate from authoritative state.
- [ ] Make selected/hovered/targeted actor IDs explicit interaction data.
- [ ] Make pending command/request state explicit and cancellable.
- [ ] Ensure scene reload reconstructs visuals from authoritative mirror without hidden gameplay state stored only in nodes.
- [ ] Ensure animation/VFX completion is not required for authoritative progression.

### Shell

- [ ] Replace the single-script bootstrap with a small app-shell composition.
- [ ] Add startup/loading state.
- [ ] Add bridge initialization/negotiation state.
- [ ] Add incompatible/error state.
- [ ] Add tactical-scene loading entry point.
- [ ] Add clean shutdown/bridge disposal behavior.
- [ ] Add local settings store for presentation/input/accessibility only.

### Diagnostics

- [ ] Add structured client logging categories: bridge, state, input, tactical, UI, presentation, performance.
- [ ] Make current authoritative snapshot/event sequence visible in debug mode.
- [ ] Make bridge version/capabilities visible in debug mode.

---

## C3 — Input system and interaction modes

- [ ] Define semantic input actions rather than hardcoded key checks.
- [ ] Map keyboard/mouse camera pan/zoom/rotate/focus.
- [ ] Map select/confirm/cancel/context actions.
- [ ] Preserve controller-equivalent action structure.
- [ ] Add remapping architecture before binding proliferation.
- [ ] Define interaction modes: inspect, select, move, target, AoE/shape preview, UI/modal.
- [ ] Make movement/targeting modes cancellable.
- [ ] Centralize mode transitions instead of scattering booleans through scenes.
- [ ] Ensure one confirmed intent creates at most one authoritative command.
- [ ] Reconcile duplicate rapid confirmation while a command is pending.

---

## C4 — Orthographic/isometric tactical camera

- [ ] Extract current camera rig into reusable tactical camera scene/controller.
- [ ] Preserve true 3D orthographic projection.
- [ ] Add keyboard and pointer-drag pan.
- [ ] Add smooth bounded orthographic zoom.
- [ ] Add exact discrete 90-degree view rotations around a tactical pivot.
- [ ] Add focus-on-selected/current actor.
- [ ] Add map-defined camera bounds.
- [ ] Handle wide/narrow aspect ratios reasonably.
- [ ] Add reduced-motion behavior for optional camera easing.
- [ ] Add headless state-transition tests where pixel comparison is unnecessary.

---

## C5 — Tactical map scene/environment

- [ ] Define tactical map presentation contract.
- [ ] Separate visual geometry from authoritative spatial IDs/cells/regions.
- [ ] Map visual objects to engine spatial identifiers.
- [ ] Add one small original tactical test map.
- [ ] Add readable terrain/material/lighting baseline for all four rotations.
- [ ] Add presentation camera bounds/focus metadata.
- [ ] Add diagnostics for Godot geometry versus authoritative spatial disagreement.

---

## C6 — Actor presentation from engine state

- [ ] Create reusable actor presentation scene keyed by stable engine actor ID.
- [ ] Spawn/despawn visuals only from authoritative mirror changes.
- [ ] Update position/facing from authoritative spatial state when v0.6 data exists.
- [ ] Bind display name/basic tactical status.
- [ ] Add hover/selection/current-turn indicators.
- [ ] Add faction/readability hooks that do not rely only on color.
- [ ] Add condition/status presentation slots driven by authoritative conditions.
- [ ] Ensure deleting a visual never deletes/mutates the engine actor.

---

## C7 — Picking, selection, inspection, highlighting

- [ ] Pointer ray picking for actors/tactical surfaces.
- [ ] Resolve visuals to stable engine/spatial IDs.
- [ ] Click select/deselect and hover inspect.
- [ ] Selected actor summary binding.
- [ ] Keyboard/controller traversal strategy.
- [ ] Selection survives authoritative refresh/re-render.

---

## C8 — Movement query/path preview

**Dependency:** v0.6 spatial authority.

- [ ] Request reachable-space data from engine.
- [ ] Render returned reachable cells/regions.
- [ ] Request and render authoritative path preview.
- [ ] Display movement cost/remaining budget.
- [ ] Distinguish legal/unaffordable/blocked/unknown destinations.
- [ ] Never infer legality from Godot `NavigationServer` alone.
- [ ] Confirm movement through typed command.
- [ ] Cancel stale path queries on selection/mode/state generation change.

---

## C9 — Targeting, LOS, cover, reach, AoE previews

**Dependency:** v0.6 spatial authority; reusable by v0.8 spells.

- [ ] Generic target-selection mode from engine-provided legal targets.
- [ ] Legal/illegal target highlighting with reasons.
- [ ] Authoritative range/reach/LOS/cover previews.
- [ ] Generic shape/AoE renderer for authoritative shape results.
- [ ] Do not decide AoE membership in Godot.
- [ ] Make targeting prompts cancellable and keyboard/controller reachable.

---

## C10 — Tactical HUD/action bar

- [ ] Encounter status/round/current actor/initiative from engine state.
- [ ] Selected actor HP/temp HP/resources/conditions.
- [ ] Action/bonus/reaction/movement availability from combat state.
- [ ] Pending command/rejection feedback without presenting pending intent as resolved state.
- [ ] Populate actions from engine/canonical data, not hardcoded named lists.
- [ ] Support action -> target/preview -> confirm -> typed command flow.

---

## C11 — Combat log/messages/rejection UX

- [ ] Present ordered authoritative events in a readable combat log.
- [ ] Preserve event IDs/sequences in debug-expanded view.
- [ ] Keep presentation messages distinct from authoritative events.
- [ ] Map validation errors to concise user wording while preserving technical debug detail.
- [ ] Make replay/resync event presentation idempotent.

---

## C12 — Presentation event pipeline

- [ ] Separate presentation event router from engine reducer/state.
- [ ] Map movement/action/damage/healing/status events to generic visual/audio hooks.
- [ ] Add optional camera emphasis hooks.
- [ ] Animation skip/cancel must not alter authoritative results.
- [ ] Support fast/instant presentation mode for tests/debugging.
- [ ] Missing optional assets must degrade gracefully.

---

## C13 — Roof/wall/foreground occlusion

- [ ] Choose/document tactical occlusion strategy.
- [ ] Tag occludable visual geometry.
- [ ] Fade/hide foreground objects obstructing focus.
- [ ] Hidden visuals must not change authoritative collision/spatial rules.
- [ ] Restore occluders correctly across camera rotations/map reloads.

---

## C14 — Tactical debug overlays

- [ ] Master debug overlay toggle.
- [ ] Authoritative grid/occupancy/movement-cost/path overlays.
- [ ] LOS/cover/AoE overlays.
- [ ] Actor/spatial/rule stable-ID labels.
- [ ] Snapshot/event sequence and bridge capabilities display.
- [ ] Navigation/geometry disagreement diagnostics.
- [ ] Request timing and basic frame-time/FPS diagnostics.

---

## C15 — Accessibility/settings

- [ ] UI scale.
- [ ] Reduced motion.
- [ ] Useful volume buses/categories.
- [ ] Input remapping-ready model/UI.
- [ ] Important states not color-only.
- [ ] Keyboard/controller reachable core tactical flow.

---

## C16 — Performance/lifecycle

- [ ] Profile before optimizing.
- [ ] No blocking bridge/disk/network/process work in frame-critical callbacks.
- [ ] Avoid unnecessary per-frame allocations/tree searches.
- [ ] Clean scene/map reload and resource disposal.
- [ ] Diagnostics for bridge latency and expensive presentation paths.

---

## C17 — Headless Godot client test matrix

- [x] Bridge protocol/lifecycle headless test script exists.
- [ ] CI executes bridge test script.
- [ ] State-mirror tests.
- [ ] Interaction-mode tests.
- [ ] Camera state tests.
- [ ] Selection tests.
- [ ] Replay-driven presentation tests.
- [ ] Tactical vertical-slice integration test.

---

## C18 — v0.7 vertical-slice acceptance

- [ ] One complete small battle playable through Godot.
- [ ] Camera pan/zoom/90-degree rotation.
- [ ] Tactical map and actors from engine state.
- [ ] Selection/movement/target previews from authoritative queries.
- [ ] Typed command submission/rejection/resync UX.
- [ ] Turn order/combat HUD/action bar.
- [ ] Basic animation/VFX/audio mapping.
- [ ] Occlusion strategy.
- [ ] Debug overlays for grid/path/LOS/cover/AoE/IDs.
- [ ] No client-side rules authority.

---

## C19 — v0.8 spell UI integration

- [ ] Generic spell action listing from engine/canonical data.
- [ ] Generic target/range/shape previews from engine queries.
- [ ] Resource/concentration/duration presentation.
- [ ] No spell-name mechanics in GDScript.

## C20 — v0.9 character creator UX

- [ ] Identity/species/background/class/ability/skills/equipment/spell-feature steps.
- [ ] Appearance/biography hooks.
- [ ] Review/validation and level-up flow.
- [ ] All available choices sourced from engine APIs/data.

## C21 — v1.0 RPG client shell

- [ ] Exploration loop and area transitions.
- [ ] Dialogue/quest/journal/map/party surfaces.
- [ ] Inventory/equipment and trade/shop UX.
- [ ] Rest/travel/save/load UX.
- [ ] End-to-end original campaign completion flow.

## Backlog hygiene

When client work discovers follow-ups:

- add them to the correct client phase and root milestone when milestone-visible;
- describe observable outcomes;
- include compatibility/testing implications when they matter;
- do not move authoritative engine work into Godot to make a client checkbox appear complete.
