# Godot Client Agent Contract

This file extends the repository-root `AGENTS.md` for every task that touches `apps/godot-client/**`. The root contract remains authoritative; this file may tighten client requirements but must never weaken repository architecture, determinism, licensing, testing, TODO, changelog, or Git rules.

## Mandatory reading for client work

Before editing anything under `apps/godot-client/`, read in this order:

1. `/AGENTS.md`
2. `/ROADMAP.md`
3. `/TODO.md`
4. `/CHANGELOG.md`
5. `/docs/ARCHITECTURE.md`
6. `/docs/PROJECT_PLAN.md`
7. `/apps/godot-client/AGENTS.md`
8. `/apps/godot-client/TODO.md`
9. the scenes/scripts/tests directly related to the task

When client work crosses rules, content, saves, networking, or Git workflow, also read the corresponding repository documentation required by root `AGENTS.md`.

## Client mission

The Godot client is a **presentation, input, and UX adapter** over authoritative headless engine state. It should make the deterministic RPG feel polished without creating a second rules engine.

```text
player input
    |
    v
Godot intent / typed request
    |
    v
client engine bridge
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
- request legal-action/query/preview data from the engine;
- submit typed commands through the engine bridge;
- cache presentation-only state such as camera, hover, selection, panels, settings, and animation progress;
- animate already-resolved domain events.

Godot must not:

- decide attacks, damage, saves, resource costs, conditions, initiative, movement legality, path cost, LOS, cover, targeting legality, AoE membership, or other rule outcomes;
- directly mutate authoritative actor/campaign/combat/spatial state;
- maintain an independent authoritative rules copy in GDScript;
- use Godot navigation as spatial-rules authority;
- invent gameplay randomness with Godot RNG APIs;
- hardcode named spell/item/monster mechanics into UI scripts.

If the client needs information it cannot obtain cleanly, extend the typed engine command/query/preview contract instead of duplicating the rule in Godot.

## State separation

Keep three concepts distinct:

1. **Authoritative mirror** — read-only client representation of engine snapshots/events.
2. **Interaction state** — local intent such as selected/hovered actor, targeting mode, pending request, and generation IDs.
3. **Presentation state** — camera, animation, VFX, audio, UI layout/settings, and other non-authoritative visuals.

Never hide authoritative gameplay state only in scene nodes. Scene reload/reconstruction must be possible from authoritative state plus presentation settings.

## Bridge rules

Client bridge work must follow `docs/GODOT_CLIENT_BRIDGE.md` when that document exists.

- Scene scripts depend on a transport-independent bridge abstraction, not sockets/processes directly.
- Every request has a request ID and correlation ID.
- Preview/query work that can become stale must carry a generation ID.
- Command accepted/rejected outcomes are explicit.
- Authoritative snapshots/events are sequence-validated before presentation.
- Event sequence gaps require resync; never guess missing state.
- Version/capability mismatches fail closed with a visible incompatible state.
- Transport/network/disk work must not block the frame loop.
- Long-lived requests need cancellation/timeouts.
- Reconnect requires renegotiation and resynchronization.
- Later remote/server transports must not require tactical scene rewrites.

## Spatial boundary

Godot navigation may provide geometry/navigation observations, but v0.6 headless spatial authority owns legality, distance/reach, occupancy, movement cost, terrain, LOS, cover, elevation, and AoE membership.

Movement/targeting UI renders engine query results. It does not recreate spatial rules locally.

## Presentation events

Animations, VFX, audio, floating text, camera emphasis, and combat-log formatting consume authoritative events. They may lag, be skipped, or run in reduced-motion/instant modes without changing authoritative progression.

Do not gate engine progress on animation completion unless a future explicit presentation synchronization protocol says otherwise.

## Input and UI

- Prefer semantic input actions over hardcoded key checks.
- Keep interaction modes explicit and cancellable.
- One confirmed intent must submit at most one authoritative command.
- Disable/reconcile duplicate rapid confirmations while a command is pending.
- Engine-provided legal actions and rejection reasons drive action availability; UI lists are not a second rules database.
- Keyboard/controller accessibility should remain structurally possible as mouse UX grows.
- Important states must not rely on color alone.

## Godot implementation rules

- Prefer small reusable scenes/scripts over monolithic scene controllers.
- Keep scene composition declarative where practical.
- Do not put blocking socket/process/file/database work in `_process`, `_physics_process`, input callbacks, or UI signal handlers.
- Avoid per-frame allocations and repeated tree searches in hot paths when a stable reference/cache works.
- Keep stable engine IDs explicit in presentation objects; do not use node paths as domain identity.
- Treat bridge/network/content data as untrusted and validate before use.
- Keep optional asset failure recoverable with placeholders/fallbacks.

## Testing

Behavioral client changes need tests at the narrowest useful layer.

Prefer:

- headless GDScript tests for bridge/state/input/controller logic;
- deterministic recorded snapshot/event fixtures;
- fake bridge transports for scene tests;
- replay-driven presentation tests for event routing;
- Godot integration tests only where engine-independent pure tests are insufficient.

Every bridge bug should gain a regression test when practical. Do not weaken authoritative ordering/version checks to make presentation tests easier.

## Client TODO discipline

`apps/godot-client/TODO.md` is the detailed client execution backlog. Root `ROADMAP.md` and root `TODO.md` remain milestone authority.

When beginning client work:

- identify the owning client phase/item;
- verify dependencies on engine milestones are actually available;
- split oversized items before coding;
- do not mark scaffolding as complete behavior.

When finishing:

- mark only observed/tested outcomes complete;
- add discovered follow-ups under the correct client phase;
- keep root TODO/changelog/docs synchronized when milestone-visible behavior changes.

## Client PR definition of done

A client PR is not complete until applicable items are true:

- root and client agent contracts were followed;
- work maps to a root milestone and client TODO item;
- Godot remains non-authoritative;
- bridge/state/spatial boundaries are preserved;
- blocking frame-loop I/O was not introduced;
- tests/fixtures were added or updated and results reported;
- client TODO is accurate;
- root TODO/changelog/docs are updated when required;
- final diff contains no unrelated editor/cache/generated artifacts;
- compatibility/version implications are documented.

If this file conflicts with root `/AGENTS.md`, root `AGENTS.md` wins.
