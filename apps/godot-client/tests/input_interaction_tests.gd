extends SceneTree

const Protocol = preload("res://bridge/bridge_protocol.gd")
const EngineBridgeScript = preload("res://bridge/engine_bridge.gd")
const FakeTransportScript = preload("res://bridge/fake_engine_transport.gd")
const CoordinatorScript = preload("res://state/client_state_coordinator.gd")
const InputBindingsScript = preload("res://input/input_bindings.gd")
const InteractionControllerScript = preload("res://input/interaction_controller.gd")

var _failures := 0


func _initialize() -> void:
    call_deferred("_run")


func _run() -> void:
    _test_semantic_actions_and_remapping()
    _test_mode_transitions_and_cancellation()
    await _test_ui_focus_blocks_raw_tactical_input()
    _test_duplicate_confirm_and_authoritative_reconciliation()
    _test_mode_scoped_request_cancellation()
    _test_stale_generation_results_are_not_reemitted()
    _test_authoritative_updates_preserve_selection()
    if _failures == 0:
        print("Godot client input/interaction tests: PASS")
        quit(0)
    push_error("Godot client input/interaction tests: %d failure(s)" % _failures)
    quit(1)


func _test_semantic_actions_and_remapping() -> void:
    var bindings = InputBindingsScript.new()
    bindings.install_defaults()
    for action in ClientInputActions.all_actions():
        _check(InputMap.has_action(action), "semantic action is registered: %s" % action)
        _check(
            not InputMap.action_get_events(action).is_empty(),
            "semantic action has a default binding: %s" % action,
        )

    _check(
        _action_has_type(ClientInputActions.CONFIRM, "InputEventJoypadButton"),
        "confirm has controller-equivalent binding",
    )
    _check(
        _action_has_type(ClientInputActions.CAMERA_PAN_UP, "InputEventJoypadMotion"),
        "camera pan has analog controller binding",
    )

    var custom_key := InputEventKey.new()
    custom_key.physical_keycode = KEY_P
    var custom_events: Array[InputEvent] = [custom_key]
    _check(
        bindings.replace_events(ClientInputActions.CONTEXT, custom_events),
        "binding API accepts a replacement event set",
    )
    var descriptors := bindings.descriptors(ClientInputActions.CONTEXT)
    _check(descriptors.size() == 1, "replacement binding serializes to one descriptor")
    _check(
        int(descriptors[0].get("physical_keycode", 0)) == KEY_P,
        "binding descriptor preserves physical key",
    )
    _check(
        bindings.apply_descriptors(ClientInputActions.CONTEXT, descriptors),
        "descriptor-based remapping round-trips",
    )
    _check(bindings.reset_action(ClientInputActions.CONTEXT), "default binding can be restored")
    _check(
        InputMap.action_get_events(ClientInputActions.CONTEXT).size() >= 3,
        "context defaults restore keyboard/mouse/controller choices",
    )


func _test_mode_transitions_and_cancellation() -> void:
    var state = CoordinatorScript.new()
    var controller = InteractionControllerScript.new()
    root.add_child(controller)
    controller.bind_state(state)
    controller.set_input_enabled(true)

    state.interaction.set_selected_actor("actor:hero")
    _check(
        controller.transition_to(InteractionModes.Mode.MOVE),
        "controller enters move mode",
    )
    _check(
        state.interaction.mode() == InteractionModes.Mode.MOVE,
        "move mode is stored in interaction state",
    )
    _check(controller.cancel_active_mode(), "move mode is cancellable")
    _check(
        state.interaction.mode() == InteractionModes.Mode.SELECT,
        "cancel returns to select when an actor remains selected",
    )
    _check(
        state.interaction.selected_actor_id() == "actor:hero",
        "mode cancellation preserves actor selection",
    )

    _check(
        controller.transition_to(InteractionModes.Mode.TARGET),
        "controller enters target mode",
    )
    _check(controller.set_ui_modal_active(true), "UI modal mode can suspend tactical input")
    _check(
        state.interaction.mode() == InteractionModes.Mode.UI_MODAL,
        "UI modal is explicit interaction state",
    )
    _check(controller.set_ui_modal_active(false), "closing modal restores previous mode")
    _check(
        state.interaction.mode() == InteractionModes.Mode.TARGET,
        "target mode restores after modal closes",
    )
    _check(controller.cancel_active_mode(), "target mode is cancellable")

    _check(
        controller.transition_to(InteractionModes.Mode.SHAPE_PREVIEW),
        "controller enters shape preview mode",
    )
    _check(controller.cancel_active_mode(), "shape preview mode is cancellable")

    controller.unbind_state()
    root.remove_child(controller)
    controller.queue_free()


func _test_ui_focus_blocks_raw_tactical_input() -> void:
    var bundle := _ready_bundle()
    var state = bundle["state"]
    var controller = bundle["controller"]
    var transport = bundle["transport"]

    state.interaction.set_selected_actor("actor:hero")
    controller.transition_to(InteractionModes.Mode.MOVE)
    _check(
        controller.set_command_intent(_command("command:focus-test"), "interaction:focus"),
        "test command intent is armed",
    )

    var button := Button.new()
    button.text = "Focused UI"
    button.focus_mode = Control.FOCUS_ALL
    root.add_child(button)
    button.grab_focus()
    await process_frame

    var confirm_event := InputEventAction.new()
    confirm_event.action = ClientInputActions.CONFIRM
    confirm_event.pressed = true
    controller._unhandled_input(confirm_event)
    _check(
        _count_sent_kind(transport, "command.submit") == 0,
        "focused UI prevents raw tactical confirmation",
    )

    _check(
        controller.handle_semantic_action(ClientInputActions.CONFIRM),
        "UI code can intentionally invoke the same semantic confirmation path",
    )
    _check(
        _count_sent_kind(transport, "command.submit") == 1,
        "explicit UI semantic action submits exactly once",
    )

    button.release_focus()
    root.remove_child(button)
    button.queue_free()
    _dispose_bundle(bundle)
    await process_frame


func _test_duplicate_confirm_and_authoritative_reconciliation() -> void:
    var bundle := _ready_bundle()
    var state = bundle["state"]
    var controller = bundle["controller"]
    var bridge = bundle["bridge"]
    var transport = bundle["transport"]

    state.interaction.set_selected_actor("actor:hero")
    controller.transition_to(InteractionModes.Mode.MOVE)
    _check(
        controller.set_command_intent(_command("command:move"), "interaction:move"),
        "move command intent is armed",
    )
    var first_request_id := controller.confirm_current_intent()
    _check(not first_request_id.is_empty(), "first confirmation submits command")
    _check(
        not controller.register_mode_request(first_request_id),
        "submitted command cannot become a cancellable mode request",
    )
    _check(
        controller.confirm_current_intent().is_empty(),
        "rapid duplicate confirmation is ignored while pending",
    )
    _check(
        _count_sent_kind(transport, "command.submit") == 1,
        "duplicate confirmation creates only one authoritative submission",
    )
    _check(
        controller.cancel_active_mode(),
        "cancel input is consumed while authoritative command is pending",
    )
    _check(
        state.interaction.mode() == InteractionModes.Mode.MOVE,
        "pending authoritative command keeps its interaction mode until resolution",
    )
    _check(
        state.interaction.pending_count() == 1,
        "pending authoritative command remains tracked after cancel input",
    )
    _check(
        _count_sent_kind(transport, "request.cancel") == 0,
        "cancel input never sends request.cancel for a submitted command",
    )
    _check(
        not controller.transition_to(InteractionModes.Mode.SELECT),
        "mode transition is locked while authoritative command is pending",
    )
    _check(
        not controller.set_ui_modal_active(true),
        "UI modal entry is locked while authoritative command is pending",
    )

    var first_request := _find_sent_request(transport, first_request_id)
    transport.queue_message(
        Protocol.make_response(
            "command.rejected",
            first_request_id,
            str(first_request["correlation_id"]),
            int(first_request["generation"]),
            false,
            {},
            Protocol.make_error(
                Protocol.ErrorCategory.CONFLICT,
                "State changed; try again",
                "test rejection",
            ),
        )
    )
    bridge.poll(0.0)
    _check(
        state.interaction.mode() == InteractionModes.Mode.MOVE,
        "rejected command keeps the current interaction mode for correction",
    )

    var retry_request_id := controller.confirm_current_intent()
    _check(not retry_request_id.is_empty(), "rejected command can be retried")
    _check(
        _count_sent_kind(transport, "command.submit") == 2,
        "retry creates one new authoritative submission",
    )
    var retry_request := _find_sent_request(transport, retry_request_id)
    transport.queue_message(
        Protocol.make_response(
            "command.accepted",
            retry_request_id,
            str(retry_request["correlation_id"]),
            int(retry_request["generation"]),
            true,
            {"events": []},
        )
    )
    bridge.poll(0.0)
    _check(
        state.interaction.mode() == InteractionModes.Mode.SELECT,
        "accepted transient command reconciles back to selection mode",
    )
    _check(
        state.interaction.selected_actor_id() == "actor:hero",
        "accepted command preserves actor selection",
    )

    _dispose_bundle(bundle)


func _test_mode_scoped_request_cancellation() -> void:
    var bundle := _ready_bundle()
    var state = bundle["state"]
    var controller = bundle["controller"]
    var transport = bundle["transport"]

    controller.transition_to(InteractionModes.Mode.TARGET)
    var request_id := state.request_preview(
        "targeting.preview",
        {},
        "interaction:target-preview",
    )
    _check(not request_id.is_empty(), "target mode can own a preview request")
    _check(controller.register_mode_request(request_id), "preview is registered to current mode")
    _check(controller.set_ui_modal_active(true), "modal entry suspends target mode")
    _check(
        state.interaction.mode() == InteractionModes.Mode.UI_MODAL,
        "modal entry changes explicit interaction mode",
    )
    _check(
        state.interaction.pending_count() == 0,
        "modal suspension cancels stale mode preview requests",
    )
    _check(
        _count_sent_kind(transport, "request.cancel") == 1,
        "modal suspension sends best-effort preview cancellation",
    )
    _check(controller.set_ui_modal_active(false), "modal close restores target mode")
    _check(
        state.interaction.mode() == InteractionModes.Mode.TARGET,
        "target mode restores without retaining stale preview",
    )

    var next_request_id := state.request_preview(
        "targeting.preview",
        {},
        "interaction:target-preview-2",
    )
    _check(controller.register_mode_request(next_request_id), "restored target mode owns new preview")
    _check(controller.cancel_active_mode(), "cancelling mode cancels registered requests")
    _check(state.interaction.pending_count() == 0, "mode cancellation clears pending request state")
    _check(
        _count_sent_kind(transport, "request.cancel") == 2,
        "mode cancellation sends best-effort bridge cancellation",
    )

    _dispose_bundle(bundle)


func _test_stale_generation_results_are_not_reemitted() -> void:
    var bundle := _ready_bundle()
    var state = bundle["state"]
    var bridge = bundle["bridge"]
    var transport = bundle["transport"]
    var completed: Array = []
    var stale: Array = []
    state.preview_completed.connect(
        func(correlation_id: String, generation: int, payload: Dictionary) -> void:
            completed.append([correlation_id, generation, payload])
    )
    state.stale_interaction_result_ignored.connect(
        func(correlation_id: String, response_generation: int, current_generation: int) -> void:
            stale.append([correlation_id, response_generation, current_generation])
    )

    state.interaction.set_selected_actor("actor:hero")
    var stale_request_id := state.request_preview(
        "targeting.preview",
        {},
        "interaction:stale-preview",
    )
    var stale_request := _find_sent_request(transport, stale_request_id)
    state.interaction.set_hovered_actor("actor:other")
    transport.queue_message(
        Protocol.make_response(
            "preview.result",
            stale_request_id,
            str(stale_request["correlation_id"]),
            int(stale_request["generation"]),
            true,
            {"preview": "stale"},
        )
    )
    bridge.poll(0.0)
    _check(completed.is_empty(), "older interaction generation is not re-emitted")
    _check(stale.size() == 1, "stale interaction result is reported")
    _check(state.interaction.pending_count() == 0, "stale result still clears its pending request")

    var fresh_request_id := state.request_preview(
        "targeting.preview",
        {},
        "interaction:fresh-preview",
    )
    var fresh_request := _find_sent_request(transport, fresh_request_id)
    transport.queue_message(
        Protocol.make_response(
            "preview.result",
            fresh_request_id,
            str(fresh_request["correlation_id"]),
            int(fresh_request["generation"]),
            true,
            {"preview": "fresh"},
        )
    )
    bridge.poll(0.0)
    _check(completed.size() == 1, "current interaction generation is re-emitted")
    _check(
        str(completed[0][2].get("preview", "")) == "fresh",
        "fresh preview payload is preserved",
    )

    _dispose_bundle(bundle)


func _test_authoritative_updates_preserve_selection() -> void:
    var bundle := _ready_bundle()
    var state = bundle["state"]
    var bridge = bundle["bridge"]
    var transport = bundle["transport"]

    state.interaction.set_selected_actor("actor:hero")
    transport.queue_message(
        Protocol.make_envelope(
            "authoritative.snapshot",
            "",
            "",
            0,
            {"snapshot": _snapshot()},
        )
    )
    bridge.poll(0.0)
    _check(
        state.interaction.selected_actor_id() == "actor:hero",
        "authoritative refresh does not discard client selection",
    )

    _dispose_bundle(bundle)


func _ready_bundle() -> Dictionary:
    var state = CoordinatorScript.new()
    var bridge = EngineBridgeScript.new()
    var transport = FakeTransportScript.new()
    var controller = InteractionControllerScript.new()
    root.add_child(controller)
    controller.bind_state(state)
    controller.set_input_enabled(true)
    state.bind_bridge(bridge)
    _check(bridge.initialize(transport) == OK, "test bridge initializes")
    _accept_hello(bridge, transport)
    return {
        "state": state,
        "bridge": bridge,
        "transport": transport,
        "controller": controller,
    }


func _dispose_bundle(bundle: Dictionary) -> void:
    var controller = bundle["controller"]
    var state = bundle["state"]
    var bridge = bundle["bridge"]
    controller.set_input_enabled(false)
    controller.unbind_state()
    state.unbind_bridge()
    bridge.shutdown()
    if controller.get_parent() != null:
        controller.get_parent().remove_child(controller)
    controller.queue_free()


func _accept_hello(bridge, transport) -> void:
    var hello: Dictionary = transport.sent_messages.back()
    transport.queue_message(
        Protocol.make_response(
            "bridge.hello.accepted",
            str(hello["request_id"]),
            str(hello["correlation_id"]),
            int(hello["generation"]),
            true,
            {
                "protocol": Protocol.PROTOCOL_NAME,
                "capabilities": Array(Protocol.CAPABILITIES),
            },
        )
    )
    bridge.poll(0.0)


func _command(command_id: String) -> Dictionary:
    return {
        "command_id": command_id,
        "campaign_id": "campaign:input-test",
        "session_id": "session:input-test",
        "command_type": "simulation.advance_tick",
        "payload": {"amount": 1},
        "version": 1,
        "actor_id": null,
        "expected_sequence": 0,
    }


func _snapshot() -> Dictionary:
    return {
        "schema_version": 1,
        "state": {
            "schema_version": 1,
            "campaign_id": "campaign:input-test",
            "session_id": "session:input-test",
            "sequence": 0,
            "tick": 0,
            "counters": {},
        },
        "rng": {
            "algorithm": "pcg32-v1",
            "state": 1,
            "increment": 3,
        },
    }


func _find_sent_request(transport, request_id: String) -> Dictionary:
    for message in transport.sent_messages:
        if str(message.get("request_id", "")) == request_id:
            return message
    return {}


func _count_sent_kind(transport, kind: String) -> int:
    var count := 0
    for message in transport.sent_messages:
        if str(message.get("kind", "")) == kind:
            count += 1
    return count


func _action_has_type(action: StringName, class_name_value: String) -> bool:
    for event in InputMap.action_get_events(action):
        if event.get_class() == class_name_value:
            return true
    return false


func _check(condition: bool, message: String) -> void:
    if condition:
        return
    _failures += 1
    push_error("FAIL: %s" % message)
