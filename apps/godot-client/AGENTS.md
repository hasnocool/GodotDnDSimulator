# Godot Client Agent Contract

This file extends the repository-root `AGENTS.md` for every task that touches
`apps/godot-client/**`. The root contract remains authoritative; this file may tighten client
requirements but must never weaken repository architecture, determinism, licensing, testing,
TODO, changelog, or Git rules.

## Mandatory reading for client work

Before editing anything under `apps/godot-client/`, read in this order:

1. `/AGENTS.md`
2. `/ROADMAP.md`
3. `/TODO.md`
4. `/CHANGELOG.md`
5. `/docs/ARCHITECTURE.md`
6. `/docs/PROJECT_PLAN.md`
7. `/apps/godot-client/AGENTS.md` (this file)
8. `/apps/godot-client/TODO.md`
9. the Godot scenes/scripts/tests directly related to the task

If client work crosses into rules, content, saves, networking, or Git workflow, also read the
corresponding repository documentation required by the root `AGENTS.md`.

## Client mission

The Godot client is a **presentation, input, and UX adapter** over authoritative headless engine
state. It should make the deterministic RPG feel polished without creating a second rules engine.

Conceptually:

```text
player input
    |
    v
Godot intent / typed command request
    |
    v
engine bridge
    |
    v
AUTHORITATIVE HEADLESS ENGINE
command -> validation -> resolution -> events -> reducer -> state
    |
    v
snapshot / events / query results
    |
    v
Godot presentation state
    |
    +-> scenes / meshes / UI / animation / VFX / audio / debug overlays
```

## Non-negotiable authority boundary

Godot may:

- render authoritative actors, maps, spatial data, HUD values, previews, and event history;
- gather keyboard, mouse, controller, and UI intent;
- request legal-action/query data from the engine;
- submit typed commands through the engine bridge;
- predict or preview only when the result is clearly non-authoritative and reconciled to engine
  output;
- animate already-resolved domain events;
- cache presentation-only state such as camera position, hovered object, open panel, local settings,
  animation progress, and selected visual theme.

Godot must not:

- decide whether an attack hits, damage amounts, saves, resource costs, conditions, initiative,
  movement legality, path cost, LOS, cover, targeting legality, AoE membership, or other rules
  outcomes;
- directly mutate authoritative actor/campaign/combat/spatial state;
- maintain an independent authoritative copy of game rules in GDScript;
- use Godot navigation as the rules authority for movement legality;
- invent random gameplay outcomes with Godot RNG APIs;
- hardcode named spell/item/monster behavior into UI scripts.

If the client needs information it cannot obtain cleanly, extend the typed engine/query/preview
contract instead of duplicating the rule in Godot.

## Client state model

Keep three state categories visibly separate:

1. **Authoritative mirror** — immutable/read-only client representation of engine snapshots/events.
2. **Interaction state** — selection, hover, targeting mode, pending intent, drag state, open menus.
3. **Presentation state** — camera, animation, particles, audio, interpolation, occlusion fades,
   local accessibility/settings.

Never write interaction or presentation state back into the authoritative mirror as if it were a
resolved game outcome.

## Engine bridge rules

The engine bridge is the only normal path between Godot and authoritative simulation.

It must eventually support:

- typed command submission with correlation IDs;
- snapshot/state ingestion;
- ordered domain-event ingestion;
- legal-action and rule-query APIs;
- spatial/path/LOS/cover/AoE preview queries once v0.6 exists;
- version/capability negotiation;
- explicit errors/rejections surfaced to UI;
- deterministic test fixtures that can drive the client without a live campaign;
- a transport boundary that can later support in-process/local and remote/server implementations
  without rewriting scenes.

Do not let individual Control/Node3D scripts call arbitrary engine internals. Prefer a small bridge
plus presentation stores/controllers.

## Scene and source ownership

As the client grows, prefer this separation:

```text
apps/godot-client/
  AGENTS.md
  TODO.md
  project.godot
  main.tscn
  autoload/       # app shell, bridge registration, settings; no rules authority
  bridge/         # engine transport/protocol adapters
  state/          # authoritative mirror + presentation/interaction stores
  scenes/
    shell/        # startup/loading/root composition
    tactical/     # battle map and encounter presentation
    actors/       # reusable actor presentation scenes
    world/        # exploration/world presentation when later milestones require it
  ui/
    hud/          # tactical HUD, turn order, resources
    actions/      # action bar, targeting prompts
    panels/       # character/inventory/journal/etc. as future milestones arrive
    common/       # reusable controls
  camera/         # orthographic rig/input behavior
  input/          # intent mapping and interaction modes
  presentation/   # event -> animation/VFX/audio mapping
  debug/          # grid/path/LOS/cover/IDs/performance overlays
  assets/         # project-owned or properly licensed client assets
  tests/          # headless Godot presentation/integration tests
```

Do not create these directories merely to satisfy the diagram; add them when a scoped TODO requires
them. Avoid giant scene scripts and global autoloads that become implicit game-state owners.

## Input and command flow

Input should move through explicit intent states rather than directly mutating scenes.

Preferred flow:

```text
raw input -> input mapping -> interaction controller -> preview/query -> typed command -> engine
                                                                  |
                                                                  v
                                                         rejection / events
                                                                  |
                                                                  v
                                                            presentation
```

Keyboard/mouse/controller bindings belong in reusable input mappings. UI buttons and hotkeys for
the same action should converge on the same intent/command path.

## Spatial-client boundary

For v0.6+ integration:

- Godot physics/navigation may provide geometry/nav observations to an adapter.
- The headless spatial authority decides occupancy, legal movement, cost, range/reach, LOS, cover,
  terrain effects, elevation rules, and AoE membership.
- Movement/path previews displayed by Godot must be based on engine/spatial query results.
- Debug overlays should be able to show both rendered/nav geometry and authoritative logical data so
  disagreements are diagnosable.

## Presentation events

Animations, VFX, sound, floating text, camera emphasis, and UI transitions should subscribe to
resolved events/presentation messages. They may delay or interpolate visuals but must not delay or
change authoritative state.

Event presentation must tolerate:

- replay at accelerated speed;
- skipped/cancelled animations;
- save/load into the middle of an encounter;
- reconnect/resynchronization later;
- missing optional art/audio assets;
- duplicate visual refresh without duplicate authoritative commands.

## Camera baseline

The intended tactical camera is true 3D orthographic/isometric. The client TODO owns the concrete
implementation, but agents should preserve these design goals:

- pan with keyboard and pointer/edge or drag input as appropriate;
- bounded, smooth orthographic zoom;
- deterministic 90-degree view rotation around the tactical focus/pivot;
- focus selected/current actor without transferring gameplay authority to the camera;
- map-defined bounds and sensible behavior at different aspect ratios;
- camera motion that can be disabled/reduced for accessibility.

## UI/UX rules

- UI displays engine-derived facts and available actions; it does not infer hidden rule legality.
- Disable or annotate unavailable actions from engine-provided reasons rather than reproducing rules.
- Maintain clear selected/hovered/targeted states.
- Keep targeting modes cancellable.
- Surface engine command rejection/error details in a user-friendly form and retain technical detail
  in debug tooling/logs.
- Design for keyboard/mouse first while keeping controller navigation and remapping structurally
  possible.
- Avoid relying on color alone for tactical meaning.
- Keep text/layout usable under UI scaling.

## Godot coding rules

- Target the repository-pinned Godot 4.x version unless the version is intentionally updated in the
  same PR.
- Prefer typed GDScript, explicit return types, and small scripts with one ownership role.
- Prefer signals/callable interfaces over deep `get_node("../../...")` coupling.
- Use groups only for presentation discovery, not as hidden rule-state databases.
- Avoid per-frame polling when signals/event-driven updates can do the work.
- Avoid allocations, scene-tree scans, JSON parsing, disk/network I/O, or heavy computation in
  `_process()` / `_physics_process()` hot paths.
- Cache stable node references.
- Do not commit `.godot/`, editor caches, imported transient outputs, credentials, or debugging junk.
- Keep assets source-controlled only when their license/provenance permits redistribution.

## Testing requirements for client changes

Use the cheapest layer that proves the behavior:

- engine/headless tests for rules and spatial legality;
- pure GDScript tests for presentation-state/controller logic where practical;
- headless Godot scene tests for scene wiring, command routing, camera/input behavior, HUD binding,
  overlays, and event presentation;
- golden/screenshot tests only when they are stable and genuinely useful;
- a vertical-slice smoke test that can load the tactical scene headlessly without parse/import errors.

Every bug fix should add a regression test when practical. Never fix a client failure by moving rule
logic into Godot.

## Performance targets and diagnostics

Do not optimize blindly, but build observability early. Track or make inspectable when relevant:

- frame time/FPS;
- rendered actor count;
- draw calls/visible geometry where useful;
- bridge request latency;
- queued presentation events;
- scene-load time;
- path/LOS/overlay query latency;
- avoidable per-frame allocations.

Prefer graceful degradation of optional effects over changing simulation behavior.

## Client TODO discipline

`apps/godot-client/TODO.md` is the detailed execution backlog for this client. Root `/TODO.md` and
`/ROADMAP.md` remain milestone authority.

For every client task:

- select or add a scoped item in `apps/godot-client/TODO.md` before implementation;
- keep the item under the correct client phase and root roadmap milestone;
- mark it complete only when the observable behavior and applicable validation exist;
- update root `/TODO.md` when a root milestone checkbox changes state;
- update `/CHANGELOG.md` for meaningful client workflow or behavior changes;
- record newly discovered client follow-ups in the client TODO rather than silently expanding scope.

## Definition of done for client PRs

In addition to the root definition of done:

- `apps/godot-client/TODO.md` accurately reflects completed and follow-up work;
- authoritative versus presentation ownership is obvious in the diff;
- new interactions go through the intended bridge/intent path;
- client-side previews are clearly non-authoritative and reconciled to engine results;
- headless Godot validation/tests run when applicable;
- scene/resource paths are valid;
- no editor cache/generated junk is committed;
- keyboard/mouse/controller/accessibility implications were considered for user-facing interaction;
- performance-sensitive frame paths were reviewed for unnecessary polling/allocation;
- the PR explains any new client-engine contract or future compatibility implication.
