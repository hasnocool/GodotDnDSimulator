# Godot Client TODO

This is the detailed execution backlog for `apps/godot-client/`. It is subordinate to the root
`ROADMAP.md`, `TODO.md`, and `AGENTS.md`, and client work must also follow
`apps/godot-client/AGENTS.md`.

A checked implementation item means observable client behavior exists in code/tests. Exact-head
execution, manual desktop acceptance, profiling-dependent optimization, and conditional future
product work remain separate rather than being silently treated as implementation gaps.

## Client product goal

Build a polished Godot 4.x 3D orthographic/isometric client that renders authoritative engine state,
turns player input into typed intents, presents engine-computed legality/results, and never becomes
the authority for rules, spatial legality, combat, randomness, or campaign state.

Detailed evidence for the final backlog sweep is recorded in `docs/TODO_BACKLOG_COMPLETION.md`.

---

## Completed client architecture and implementation

### C0-C3 — Governance, bridge, state, shell, and input

- [x] Client-local AGENTS/TODO governance and root/tool-adapter wiring.
- [x] Client-specific governance validation in `scripts/check_governance.py`.
- [x] Transport-independent versioned bridge with capability negotiation, categorized errors,
      cancellation/timeouts, stale-result rejection, reconnect/resync, local TCP transport, and
      deterministic fake transport.
- [x] Read-only authoritative mirror, separate interaction/presentation state, lifecycle-aware app
      shell, asynchronous scene loading, presentation settings, diagnostics, and clean shutdown.
- [x] Semantic keyboard/mouse/controller input, remapping, centralized cancellable interaction modes,
      modal/focus safety, and single-submit command intent handling.

### C4 — Orthographic/isometric tactical camera

- [x] Reusable true-3D orthographic tactical camera.
- [x] Semantic/drag pan, bounded smooth zoom, exact 90-degree rotation, selected/current focus,
      reduced-motion behavior, and map bounds.
- [x] Aspect-ratio-aware focus padding so extreme widescreen/narrow viewports do not expose unusable
      void beyond tactical bounds.
- [x] Headless camera/controller state coverage.

### C5 — Tactical map/environment presentation

- [x] Visual map geometry remains separate from authoritative spatial IDs/cells/regions.
- [x] Original Sunken Courtyard presentation with terrain, elevation, movement/LOS-blocking visuals,
      lighting/readability, and camera metadata.
- [x] Reusable presentation-only exploration/map-entry spawn-anchor resources for all six Lanterns
      Below areas.
- [x] Diagnostics for authoritative actor positions that cannot map to the visual grid.

### C6 — Actor presentation

- [x] Stable-ID actor presentation spawned/despawned only from authoritative mirror changes.
- [x] HP/AC/name/position, selection, hover, current-turn, and placeholder primitive presentation.
- [x] Non-color team/faction emblem hooks.
- [x] Dedicated condition/status presentation slots.
- [x] Debug labels directly expose stable actor and authoritative condition/rule IDs.
- [x] Actor visual lifetime cannot mutate authoritative actor state.
- [ ] Pool/reuse actor visuals only after profiling demonstrates a measurable benefit.

### C7 — Picking, selection, inspection, highlighting

- [x] Pointer ray picking resolves to stable actor IDs/logical cells.
- [x] Click selection, hover inspection, selected summary, semantic controller traversal, and stable
      selection across rerenders.
- [x] Faded/hidden presentation occluders cannot intercept actor/tactical-surface picking because
      occlusion geometry is presentation-only and has no picking collision bodies.

### C8 — Movement query/path preview

- [x] Reachable-space/path previews come from authoritative spatial queries.
- [x] Path, cost, remaining movement, and rejection reason presentation.
- [x] Authoritative per-segment terrain/elevation/movement-mode cost breakdown when rendering path
      details; Godot does not derive segment legality/cost.
- [x] Typed move commands carry actor/destination/mode and current expected sequence.
- [x] Active movement previews automatically re-request after unrelated authoritative updates.
- [x] Mode/selection/generation changes cancel or reject stale preview work.

### C9 — Targeting, LOS, cover, reach, AoE

- [x] Generic target mode uses engine preview approval/rejection and textual legality details.
- [x] Authoritative range/reach, LOS, cover, and AoE cell/entity presentation.
- [x] Generic sphere/cylinder/cone/line debug authoring controls support origin selection, shape kind,
      and quarter-turn direction without named-ability logic.
- [x] Active target/shape previews automatically refresh after unrelated authoritative state changes.
- [x] Controller-only target traversal is independent of pointer position.

### C10 — Tactical HUD/action bar

- [x] Encounter/round/initiative/current actor/selected HP-tempHP-AC-movement presentation.
- [x] Dedicated authoritative condition, action/bonus/reaction economy, resource, and ongoing-effect
      rows.
- [x] Engine-provided Move/Strike/End Turn availability/reasons and shared intent flow.
- [x] Data-driven spell/action slot grouping and detailed tooltips for broad spell catalogs.

### C11 — Combat log/messages/rejection UX

- [x] Resolved presentation events feed a readable combat log separate from authoritative state.
- [x] Existing user debug setting toggles an expanded combat-log form containing event sequence,
      event type, and stable actor/target IDs.
- [x] Command rejection preserves concise user wording plus technical detail.
- [x] Stable replay/resync de-duplication keys prevent duplicate long-lived visual log events.

### C12 — Presentation event pipeline

- [x] Presentation router remains separate from engine reducers/state.
- [x] Actor movement interpolation, attack/spell emphasis, audio cue IDs, camera hooks, and
      reduced-motion/instant behavior.
- [x] Generic movement, damage, healing, miss, status, and status-expiry VFX primitives.
- [x] Presentation completion never blocks authoritative progression and optional assets are not
      required.

### C13 — Roof/wall/foreground occlusion

- [x] Lightweight explicitly tagged foreground fade strategy.
- [x] Camera-to-actor occlusion refresh with instant reduced-motion-compatible alpha changes.
- [x] Presentation occlusion never changes authoritative collision/LOS and clears on scene exit.

### C14 — Tactical debug/developer overlays

- [x] Master debug toggle and authoritative logical grid presentation.
- [x] Dedicated occupancy debug layer.
- [x] Authoritative path, movement cost, target LOS/legality line, cover source, and AoE cell layers.
- [x] Debug labels directly show stable actor IDs, spatial coordinates, terrain/content IDs, and
      condition/rule IDs over scene objects.
- [x] Debug-only navigation-adapter versus authoritative-path comparison visualization, including
      matching, authority-only, and adapter-only cells.
- [x] Snapshot/event sequence, bridge version/capabilities, pending-request count, presentation scene,
      bridge request-batch timing, and FPS diagnostics.
- [x] Developer/debug controls remain presentation-only.

### C15 — Accessibility/settings/desktop baseline

- [x] Presentation-only UI scale model, reduced motion, master volume, input remapping, non-color
      legality/selection cues, standard Godot focus behavior, and persistence outside campaign saves.
- [ ] Validate all tactical HUD text at every supported UI scale in an executable desktop/UI pass.

### C16 — Client performance/lifecycle

- [x] Presentation queue diagnostics, actor-ID dictionary lookup, event-driven bindings, no per-frame
      JSON parsing, stale actor cleanup, and subscription cleanup.
- [x] Explicitly cancel every scene-owned preview on tactical-scene unload.
- [ ] Establish a measured representative tactical-scene frame-time baseline before optimization.
- [ ] Measure tactical map scene-load time on supported desktop hardware.
- [ ] Measure bridge query latency for movement/LOS/AoE previews in a real executing session; the
      debug overlay already exposes request-batch timing for this measurement.

### C17 — Headless Godot validation/test matrix

- [x] Tactical root load, camera, input modes, snapshot->map/actor rendering, current selection,
      accepted movement routing/reconciliation, rejected command recovery, movement previews,
      HUD/action binding, and presentation-event forwarding.
- [x] Assert rendered LOS/cover target-line and AoE marker contents from supplied authoritative
      preview fixtures.
- [x] Tactical scene teardown/reload regression verifies pending scene-owned previews are cancelled
      and reconstructed state does not duplicate subscriptions.
- [x] Backlog suites cover spawn anchors, faction/status presentation, stable debug IDs, occupancy,
      VFX primitives, combat-log de-duplication, navigation comparison, and spell slot grouping.

### C18 — v0.7 tactical vertical-slice implementation

- [x] Camera/map/actors/selection/movement/path/strike/HUD/LOS/cover/AoE/presentation/occlusion behavior
      exists with Python-engine authority.
- [x] Python acceptance coverage drives the typed tactical command loop to encounter completion.
- [x] Replay/resync presentation de-duplication is covered headlessly without issuing duplicate
      authoritative commands.

### C19 — v0.8 spell UI integration

- [x] Spell resources/availability, generic target/shape previews, action/rejection reuse,
      concentration/duration/generic ongoing-effect status, and engine-supplied upcast choices.
- [x] Spell actions are grouped by legal engine-provided cast slot with authoritative metadata
      tooltips.

### C20 — v0.9 character creator UX

- [x] Identity/species/background/class/abilities/skills/equipment/spell-feature/profile/review/create
      and level-up flows are driven by authoritative engine choices/validation.

### C21 — v1.0 RPG client shell

- [x] Exploration, dialogue, quest/journal, inventory/equipment, party, shop/trade, rest/travel, map,
      manual production save/load, and credits/attribution presentation.
- [x] Party records, equipment compatibility, shop state, exploration availability/reasons, and
      encounter intents remain engine supplied/validated.
- [x] Three fixed manual save slots use lossless engine snapshots, threaded bounded disk I/O,
      versioned envelopes, backup recovery, authoritative load validation, and disconnect recovery.

---

## Authored world encounter handoff

- [x] Road Ambush uses its own tactical template/map/enemies/terrain.
- [x] Quarry Watchers uses its own tactical template/map/enemies/terrain.
- [x] Underworks Swarm uses its own tactical template/map/enemies/terrain.
- [x] The Hollow Warden boss uses its own tactical template/map/enemies/terrain.
- [x] Tactical startup uses actual selected `CharacterRecord.actor` party members, not proxy heroes.
- [x] Fresh encounter startup returns an authoritative tactical snapshot for client resynchronization.
- [x] World encounter completion remains gated on authoritative `team:party` tactical victory.

---

## Remaining exact-head executable/manual evidence gates

The following are deliberately not checked from source inspection alone.

- [ ] Execute Ruff, strict Mypy, full Python pytest/coverage, governance/schema/importer determinism,
      and every registered Godot headless suite on the exact integrated head.
- [ ] Confirm the exact integrated client parses under the repository Godot version with no script or
      resource errors.
- [ ] Demonstrate the real Godot TCP transport negotiating/resynchronizing with the localhost Python
      host in an executable integration session.
- [ ] Demonstrate the complete tactical encounter interactively through the Godot desktop client.
- [ ] Demonstrate spell casting interactively from authoritative discovery/preview through accepted
      command.
- [ ] Validate tactical HUD/layout text at every supported UI scale in a real UI pass.

---

## Conditional future work

These are intentionally policy/profiling dependent rather than missing v1.0 implementation.

- [ ] Add actor-view pooling only if measured profiling shows it improves representative tactical
      scenes.
- [ ] Add autosave/checkpoint retention only after a product policy specifies checkpoint timing and
      retention; manual production save/load is complete.
- [ ] Add save migration/export/import when a future envelope-format change or cross-device workflow
      creates an actual compatibility requirement; v1 envelope semantics are frozen/versioned.

---

## Backlog hygiene

When client work is discovered:

- identify the owning roadmap milestone/dependency;
- describe observable behavior rather than vague improvement;
- keep rules/spatial/combat authority in the engine;
- update root `TODO.md` when root milestone state changes;
- keep this file, root agent files, changelog, docs, and tests synchronized;
- distinguish code completion from evidence that must actually execute.
