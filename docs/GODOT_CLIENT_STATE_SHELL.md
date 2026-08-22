# Godot Client State Architecture and App Shell

C2 introduces the first persistent client-side application architecture on top of the C1 engine
bridge. The goal is to make the Godot client reconstructable, testable, and explicit about which
state it owns without creating a second gameplay authority.

## Ownership model

The client now keeps three distinct state layers:

```text
AUTHORITATIVE ENGINE
        |
        | snapshots + ordered events
        v
+-----------------------------+
| AuthoritativeMirror         |
| read-only reconstruction    |
+-----------------------------+
        |
        +--------------------------+
        |                          |
        v                          v
+---------------------+   +----------------------+
| InteractionState    |   | PresentationState    |
| selection / intent  |   | scene / animation /  |
| pending requests    |   | local display state  |
+---------------------+   +----------------------+
```

These layers are coordinated by `ClientStateCoordinator`, but they remain separate objects with
separate responsibilities.

### Authoritative mirror

`state/authoritative_mirror.gd` stores only engine-produced data:

- the most recent full authoritative snapshot;
- ordered authoritative events received after that snapshot;
- the highest accepted authoritative sequence.

The mirror does **not** run combat, rule, spatial, or campaign reducers in Godot. A scene that needs
to reconstruct itself receives a deep-copied reconstruction view containing the snapshot plus any
post-snapshot events. The authoritative Python engine remains responsible for the meaning and
resolution of those events.

Returned snapshot/event dictionaries are deep copies so scene code cannot mutate the stored mirror
through a shared reference.

The mirror rejects regressing snapshots and non-contiguous new event batches. C1 already validates
bridge ordering; the mirror keeps the same fail-closed boundary at the presentation-store layer so a
bad caller cannot partially advance it.

### Interaction state

`state/interaction_state.gd` contains temporary user/client interaction data only:

- selected actor ID;
- hovered actor ID;
- targeted actor ID;
- interaction generation;
- pending command/query/preview request metadata.

Selection/hover/target changes advance the generation used by C1 to reject delayed responses from an
older interaction. Pending requests are explicit and cancellable.

No interaction field is written into the authoritative mirror.

### Presentation state

`state/presentation_state.gd` contains presentation-only state:

- active/loading presentation scene identifiers;
- number of in-flight presentation activities;
- reduced-motion preference;
- UI scale preference;
- debug-overlay visibility.

Presentation activity is deliberately independent from authoritative progression. A long animation,
VFX sequence, or future camera emphasis may still be active while new authoritative events are
accepted. C12 will define how resolved events map to animation/VFX/audio; C2 only establishes the
separation needed to make that safe.

## Client state coordinator

`ClientStateCoordinator` is the narrow adapter between the C1 `EngineBridge` and client stores.

It:

- subscribes authoritative snapshots/events into `AuthoritativeMirror`;
- delegates commands, queries, and previews to `EngineBridge`;
- records returned request IDs in `InteractionState`;
- clears pending interaction metadata on accepted/rejected/completed/failed responses;
- forwards cancellation to the bridge;
- clears presentation-side pending metadata when the bridge disconnects.

It does not decide whether a command is legal or how an authoritative event changes gameplay.

## Application shell

The old single-script `main.gd` bootstrap is replaced by a small scene composition:

```text
main.tscn
  -> scenes/shell/app_shell.tscn
       -> ContentRoot
       -> startup/error UI
       -> client debug overlay
```

`AppShell` owns the lifetime of:

- the current `EngineBridge`;
- the selected transport;
- `ClientStateCoordinator`;
- the active tactical presentation scene;
- presentation startup/error/debug UI.

### Shell states

The shell exposes explicit states:

- `STARTUP`
- `BRIDGE_INITIALIZING`
- `SYNCHRONIZING`
- `LOADING`
- `READY`
- `INCOMPATIBLE`
- `ERROR`
- `SHUTDOWN`

Normal startup is:

```text
STARTUP
  -> BRIDGE_INITIALIZING
  -> C1 bridge hello/version/capability negotiation
  -> SYNCHRONIZING
  -> bridge.snapshot query
  -> authoritative mirror receives snapshot
  -> LOADING
  -> asynchronous tactical PackedScene load
  -> READY
```

Bridge/version failures enter explicit `INCOMPATIBLE` or `ERROR` states rather than letting tactical
scenes run against unknown authority.

The retry button reinitializes the bridge boundary. Clean shutdown cancels tracked pending requests,
unbinds state subscriptions, shuts the bridge down, and removes the active tactical presentation.

## Tactical presentation entry point

C2 adds `scenes/tactical/tactical_stub.tscn` as the first tactical presentation entry scene.

This is **not** the v0.7 tactical map. It intentionally contains only the existing orthographic
camera scaffold and a state-binding hook. Camera controls remain C4; maps remain C5; actor visuals
remain C6.

The shell loads the first tactical PackedScene with `ResourceLoader.load_threaded_request()` rather
than synchronously performing disk work in the frame loop.

After the scene resource is cached, `reload_tactical_scene()` can destroy and recreate the
presentation node while preserving `ClientStateCoordinator`. The new scene binds to the same
snapshot-plus-event reconstruction view, demonstrating that gameplay state is not hidden inside scene
nodes.

## Local client settings

`autoload/client_settings.gd` persists only presentation/input/accessibility-facing client settings
under `user://client_settings.cfg`.

Current C2 settings are:

- UI scale;
- reduced motion;
- debug-overlay visibility;
- master-volume dB.

They are explicitly local presentation preferences and are not written to authoritative campaign
state. Later milestones may add settings UI and input remapping without changing this boundary.

## Structured diagnostics

`autoload/client_log.gd` provides bounded structured client log entries with these categories:

- `bridge`
- `state`
- `input`
- `tactical`
- `ui`
- `presentation`
- `performance`

The debug overlay exposes, when enabled:

- bridge readiness/status;
- negotiated bridge protocol version;
- negotiated capabilities;
- current authoritative sequence;
- whether a snapshot is loaded;
- pending request count;
- active presentation scene.

This data is diagnostic only and cannot mutate engine state.

## Tests

`res://tests/state_shell_tests.gd` covers:

- deep-copy/read-only mirror behavior;
- snapshot/event sequence handling;
- explicit selected/hovered/targeted IDs;
- interaction-generation changes;
- pending request tracking and cancellation;
- authoritative progression while presentation activity remains in flight;
- shell hello negotiation and initial snapshot request;
- shell transition through synchronization/loading/ready states;
- asynchronous tactical presentation loading;
- scene reconstruction from the same snapshot-plus-event mirror;
- debug sequence/version/capability display;
- clean shutdown.

The Godot CI job now runs this suite after the C1 bridge suite.

## Deliberate non-goals

C2 does not add:

- tactical input modes or key bindings — C3;
- camera controls — C4;
- production tactical map/environment — C5;
- actor rendering — C6;
- picking/selection UI behavior — C7;
- movement/path legality — v0.6 engine authority + C8 presentation;
- LOS/cover/AoE logic — v0.6 engine authority + C9 presentation;
- action bar/HUD — C10;
- animation/VFX/audio routing — C12.

The state/shell architecture is intended to let those phases attach without moving gameplay authority
into Godot or turning scene nodes into hidden persistence stores.

## C3 handoff

C3 can now build semantic input actions and a centralized interaction controller against
`InteractionState` and `ClientStateCoordinator`.

Input modes should advance/cancel interaction generations as appropriate, submit through the same
coordinator/bridge path, and leave the authoritative mirror read-only.
