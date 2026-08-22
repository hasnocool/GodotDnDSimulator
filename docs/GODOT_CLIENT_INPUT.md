# Godot Client Input and Interaction Modes

C3 establishes the device-neutral input and interaction layer for the Godot client. It builds on the
C1 engine bridge and C2 client-state/app-shell architecture without adding camera, map, targeting, or
rules authority to Godot.

## Authority boundary

Input code turns player intent into client interaction state and, when explicitly armed with a typed
command, routes one confirmed intent through `ClientStateCoordinator` to `EngineBridge`.

It does not decide:

- whether movement is legal or what it costs;
- whether a target is legal;
- attack, damage, save, condition, or resource outcomes;
- LOS, cover, reach, terrain, elevation, or AoE membership;
- any random gameplay result.

Future C8/C9 code must obtain those facts from authoritative engine/spatial queries before using this
interaction layer to confirm a command.

## Semantic actions

`apps/godot-client/input/input_actions.gd` defines stable semantic actions instead of gameplay code
checking physical keys/buttons directly.

Camera-facing actions reserved for C4 are:

- `camera_pan_up`
- `camera_pan_down`
- `camera_pan_left`
- `camera_pan_right`
- `camera_zoom_in`
- `camera_zoom_out`
- `camera_rotate_left`
- `camera_rotate_right`
- `camera_focus`

Interaction actions are:

- `interaction_select`
- `interaction_confirm`
- `interaction_cancel`
- `interaction_context`

`ClientInputBindings` installs keyboard/mouse and controller-capable defaults through Godot's
`InputMap`. Joypad reference events use the all-devices mapping so the tactical client does not assume
a particular controller index.

C4 should consume the semantic camera actions rather than add key checks to its controller.

## Default binding intent

The defaults provide a usable development baseline, not an immutable control scheme.

- Camera pan: WASD/arrows, D-pad, left stick.
- Zoom: keyboard +/- equivalents, mouse wheel, stick buttons.
- Rotate: Q/E and shoulder buttons.
- Focus: F and controller Y/top face button.
- Select: primary mouse button and controller A/bottom face button.
- Confirm: Enter/Space and controller A/bottom face button.
- Cancel: Escape, secondary mouse button, controller B/right face button.
- Context: C, middle mouse button, controller X/left face button.

Some devices intentionally share a physical control between select and confirm. The interaction mode
resolves that ambiguity: transient move/target/shape modes prefer confirmation; inspect/select modes
prefer selection.

## Remapping architecture

`ClientInputBindings` exposes:

- `action_events()`
- `replace_events()`
- `reset_action()` / `reset_all()`
- `descriptors()`
- `apply_descriptors()`
- `save_overrides()` / `load_overrides()`

Bindings are serialized as small dictionaries instead of storing gameplay logic or opaque scene
state. Supported descriptor families are keyboard key, mouse button, joypad button, and joypad axis.
Overrides are stored at `user://input_bindings.cfg`, separate from campaign/authoritative saves.

A later settings/remapping UI can use this API without changing tactical scenes or interaction
controllers.

## Interaction modes

`InteractionModes` defines one centralized mode enum:

1. `inspect`
2. `select`
3. `move`
4. `target`
5. `shape_preview`
6. `ui_modal`

The active mode is stored in C2 `InteractionState`. Mode changes advance the existing interaction
generation, which means delayed C1 query/preview responses from an older interaction can be rejected
as stale.

Move, target, and shape-preview modes are explicitly cancellable before an authoritative command is
submitted. Cancelling them:

- cancels mode-scoped read-only bridge queries/previews on a best-effort basis;
- clears the unsubmitted command intent;
- clears transient targeted-actor state;
- returns to `select` if an actor remains selected, otherwise `inspect`.

A submitted authoritative command is deliberately **not** registered as a cancellable mode request.
Once confirmation sends the command, Cancel, mode changes, and modal entry are consumed/blocked until
an authoritative response or request-level failure arrives. This prevents the client from discarding
a late accepted response for a command the engine may already have executed. Authoritative results
always win and continue through the normal bridge/state path.

## UI modal behavior

Opening a modal records the previous interaction mode and enters `ui_modal`. If the suspended mode
owns read-only query/preview requests, those requests are cancelled so their older-generation results
cannot be presented after the modal transition. Closing the modal restores the previous interaction
mode, which can issue fresh previews as needed.

Modal entry is rejected while an authoritative command submission is pending. This keeps the pending
command's interaction context stable until the engine resolves it.

Raw tactical input is ignored while a Godot `Control` owns GUI focus. This is deliberate: keyboard
or controller navigation inside menus must not also confirm a tactical command. Godot UI code that
intentionally represents a tactical action calls `handle_semantic_action()` on the same
`ClientInteractionController`, so buttons and hotkeys converge on one intent path.

The interaction controller uses `_unhandled_input()`, which complements Godot's normal GUI event
handling: UI that accepts an event prevents it from reaching the tactical unhandled-input layer.

## Command intent lifecycle

The interaction controller does not construct rules commands. Another client component arms it with:

- an already-typed command dictionary;
- a correlation ID identifying the interaction.

On confirm:

```text
semantic confirm
  -> ClientInteractionController
  -> ClientStateCoordinator.submit_command()
  -> EngineBridge
  -> authoritative engine
```

While that command is pending, further confirmations for the same armed intent are ignored. This
prevents rapid keyboard/mouse/controller input from creating duplicate authoritative submissions.
Pre-confirmation mode queries/previews are cancelled once the command is submitted because they are
no longer the source of truth.

When `ClientStateCoordinator` receives the bridge result it emits `command_completed`:

- rejection clears the pending lock but keeps the transient mode/intent available for correction and
  retry;
- request-level failure (for example timeout/transport failure) uses the same retryable failure path;
- acceptance clears the command intent and returns transient modes to `select`/`inspect` while
  preserving actor selection.

Selection is interaction state, so normal authoritative snapshot/event refreshes do not silently
clear it. Later actor-presentation work may explicitly reconcile a selection when the referenced
actor no longer exists.

## Mode-scoped queries and previews

`register_mode_request()` lets future C8/C9 controllers associate a read-only query/preview request
with the current move/target/shape interaction. Submitted commands are explicitly rejected by this
registration API.

Cancelling or suspending the interaction cancels only those read-only requests through
`ClientStateCoordinator`. This is lifecycle plumbing only: C3 does not implement movement paths,
legal targets, LOS, cover, or AoE calculations.

## App-shell ownership

C2 `AppShell` owns one persistent `ClientInteractionController` and one `ClientInputBindings`
instance. The controller is outside the tactical presentation scene, so a tactical scene reload does
not duplicate subscriptions or lose interaction infrastructure.

Input is enabled only while the shell is `READY`. Startup, bridge negotiation, synchronization,
loading, error, incompatibility, and shutdown states disable tactical input.

## Tests

`res://tests/input_interaction_tests.gd` covers:

- registration of every semantic action;
- keyboard/mouse/controller default coverage;
- descriptor-based rebind/reset round trip;
- move/target/shape cancellation;
- modal suspend/restore and stale-preview cancellation;
- UI focus blocking raw tactical confirmation;
- intentional UI use of the same semantic confirm API;
- duplicate-confirm suppression while a command is pending;
- submitted-command protection from Cancel/mode/modal cancellation;
- rejection -> retry behavior;
- acceptance -> transient-mode reconciliation;
- mode-scoped preview cancellation;
- selection preservation across authoritative snapshot refresh.

CI runs this suite after the C1/C2 Godot tests.

## C4 handoff

C4 should build the orthographic camera controller on these semantic actions. It should not add
physical key/button checks. Continuous pan/zoom sampling may use Godot `Input` with the semantic
action names, while discrete rotate/focus commands can consume the same action registry.

C4 remains presentation-only; camera state must stay outside authoritative gameplay state.
