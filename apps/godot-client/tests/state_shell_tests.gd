extends SceneTree

const Protocol = preload("res://bridge/bridge_protocol.gd")
const EngineBridgeScript = preload("res://bridge/engine_bridge.gd")
const FakeTransportScript = preload("res://bridge/fake_engine_transport.gd")
const MirrorScript = preload("res://state/authoritative_mirror.gd")
const InteractionScript = preload("res://state/interaction_state.gd")
const PresentationScript = preload("res://state/presentation_state.gd")
const CoordinatorScript = preload("res://state/client_state_coordinator.gd")
const AppShellScene = preload("res://scenes/shell/app_shell.tscn")

var _failures := 0


func _initialize() -> void:
    call_deferred("_run")


func _run() -> void:
    ClientSettings.reset_defaults(false)
    ClientLog.clear()
    _test_authoritative_mirror_is_read_only()
    _test_interaction_state_is_separate_and_explicit()
    _test_presentation_activity_does_not_gate_authority()
    _test_coordinator_cancels_pending_requests()
    await _test_app_shell_lifecycle_and_scene_reconstruction()
    ClientSettings.reset_defaults(false)
    if _failures == 0:
        print("Godot client state/shell tests: PASS")
        quit(0)
    else:
        push_error("Godot client state/shell tests: %d failure(s)" % _failures)
        quit(1)


func _test_authoritative_mirror_is_read_only() -> void:
    var mirror = MirrorScript.new()
    var source := _fixture_snapshot()
    _check(mirror.ingest_snapshot(source), "authoritative snapshot is accepted")
    _check(mirror.has_snapshot(), "mirror records snapshot presence")
    _check(mirror.sequence() == 0, "mirror starts at snapshot sequence")

    var copy := mirror.snapshot()
    copy["state"]["sequence"] = 99
    _check(mirror.sequence() == 0, "returned snapshot cannot mutate mirror sequence")
    _check(
        int(mirror.snapshot()["state"]["sequence"]) == 0,
        "returned snapshot is a deep copy",
    )

    _check(
        not mirror.ingest_events([{"sequence": 2, "event_type": "test.gap"}]),
        "mirror rejects event gaps without partial mutation",
    )
    _check(mirror.sequence() == 0, "rejected event gap leaves mirror unchanged")
    _check(
        mirror.ingest_events([{"sequence": 1, "event_type": "test.accepted"}]),
        "contiguous authoritative event is accepted",
    )
    _check(mirror.sequence() == 1, "accepted event advances mirror sequence")


func _test_interaction_state_is_separate_and_explicit() -> void:
    var interaction = InteractionScript.new()
    interaction.set_selected_actor("actor:hero")
    interaction.set_hovered_actor("actor:npc")
    interaction.set_targeted_actor("actor:target")
    _check(interaction.selected_actor_id() == "actor:hero", "selected actor ID is explicit")
    _check(interaction.hovered_actor_id() == "actor:npc", "hovered actor ID is explicit")
    _check(interaction.targeted_actor_id() == "actor:target", "target actor ID is explicit")
    _check(interaction.generation() == 3, "interaction changes advance generation")

    _check(
        interaction.track_pending(
            "client-request:state-test",
            "preview",
            "interaction:path",
            interaction.generation(),
        ),
        "pending request is tracked explicitly",
    )
    var pending := interaction.pending_requests()
    pending.clear()
    _check(interaction.pending_count() == 1, "pending request view is copied")
    _check(interaction.clear_pending("client-request:state-test"), "pending request can clear")
    _check(interaction.pending_count() == 0, "pending state clears independently")


func _test_presentation_activity_does_not_gate_authority() -> void:
    var mirror = MirrorScript.new()
    var presentation = PresentationScript.new()
    _check(mirror.ingest_snapshot(_fixture_snapshot()), "presentation test snapshot loads")
    presentation.begin_presentation()
    _check(presentation.active_presentations() == 1, "presentation activity is explicit")
    _check(
        mirror.ingest_events([{"sequence": 1, "event_type": "test.while_animating"}]),
        "authoritative event advances while presentation is busy",
    )
    _check(mirror.sequence() == 1, "presentation completion does not gate authority")
    presentation.finish_presentation()
    _check(presentation.active_presentations() == 0, "presentation activity can finish later")


func _test_coordinator_cancels_pending_requests() -> void:
    var bridge = EngineBridgeScript.new()
    var transport = FakeTransportScript.new()
    var coordinator = CoordinatorScript.new()
    coordinator.bind_bridge(bridge)
    _check(bridge.initialize(transport) == OK, "test bridge initializes")
    _accept_hello(bridge, transport)

    var request_id := coordinator.request_query(
        "bridge.capabilities",
        {},
        "interaction:pending",
    )
    _check(not request_id.is_empty(), "coordinator submits query through bridge")
    _check(coordinator.interaction.pending_count() == 1, "coordinator tracks pending query")
    _check(coordinator.cancel_pending(request_id), "coordinator cancels pending query")
    _check(coordinator.interaction.pending_count() == 0, "cancel clears interaction pending state")
    _check(
        str(transport.sent_messages.back().get("kind", "")) == "request.cancel",
        "cancellation is forwarded to bridge transport",
    )
    coordinator.unbind_bridge()
    bridge.shutdown()


func _test_app_shell_lifecycle_and_scene_reconstruction() -> void:
    var shell = AppShellScene.instantiate()
    var transport = FakeTransportScript.new()
    shell.transport_override = transport
    root.add_child(shell)
    await process_frame

    _check(
        shell.shell_state() == shell.ShellState.BRIDGE_INITIALIZING,
        "shell exposes bridge initialization state",
    )
    _check(not transport.sent_messages.is_empty(), "shell begins bridge negotiation")
    var hello: Dictionary = transport.sent_messages.back()
    _check(str(hello.get("kind", "")) == "bridge.hello", "shell sends bridge hello")
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
    await process_frame

    _check(
        shell.shell_state() == shell.ShellState.SYNCHRONIZING,
        "shell exposes authoritative synchronization state",
    )
    var snapshot_request: Dictionary = transport.sent_messages.back()
    _check(
        str(snapshot_request.get("kind", "")) == "query.request",
        "shell requests initial authoritative snapshot",
    )
    _check(
        str(snapshot_request["payload"].get("query_type", "")) == "bridge.snapshot",
        "shell uses read-only bridge.snapshot query",
    )
    transport.queue_message(
        Protocol.make_response(
            "query.result",
            str(snapshot_request["request_id"]),
            str(snapshot_request["correlation_id"]),
            int(snapshot_request["generation"]),
            true,
            {"snapshot": _fixture_snapshot()},
        )
    )

    for _index in range(60):
        await process_frame
        if shell.shell_state() == shell.ShellState.READY:
            break
    _check(shell.shell_state() == shell.ShellState.READY, "shell reaches ready state")
    _check(shell.client_state().authoritative.has_snapshot(), "shell owns authoritative mirror")
    _check(shell.tactical_content() != null, "shell loads tactical presentation entry scene")
    _check(
        shell.tactical_content().call("bound_sequence") == 0,
        "tactical presentation binds to current mirror sequence",
    )

    shell.client_state().presentation.begin_presentation()
    transport.queue_message(
        Protocol.make_envelope(
            "authoritative.events",
            "",
            "",
            0,
            {"events": [{"sequence": 1, "event_type": "test.shell_event"}]},
        )
    )
    await process_frame
    _check(
        shell.client_state().authoritative.sequence() == 1,
        "shell mirror advances while presentation activity is pending",
    )
    _check(
        shell.tactical_content().call("bound_sequence") == 1,
        "loaded presentation observes authoritative sequence changes",
    )
    shell.client_state().presentation.finish_presentation()

    var old_scene: Node = shell.tactical_content()
    _check(shell.reload_tactical_scene(), "shell can reconstruct tactical scene from mirror")
    await process_frame
    var new_scene: Node = shell.tactical_content()
    _check(new_scene != null and new_scene != old_scene, "scene reload replaces presentation node")
    _check(
        new_scene.call("bound_sequence") == 1,
        "reloaded presentation reconstructs from existing authoritative mirror",
    )
    _check(
        shell.client_state().authoritative.sequence() == 1,
        "scene reload does not mutate authoritative state",
    )

    ClientSettings.set_value("debug_overlay", true, false)
    await process_frame
    var debug_overlay = shell.get_node("ShellUI/ClientDebugOverlay")
    _check(debug_overlay.visible, "debug mode reveals diagnostics overlay")
    var diagnostic_text := str(debug_overlay.call("diagnostic_text"))
    _check(
        diagnostic_text.contains("Authoritative sequence: 1"),
        "debug overlay exposes authoritative sequence",
    )
    _check(
        diagnostic_text.contains("Protocol version: 1"),
        "debug overlay exposes bridge protocol version",
    )
    _check(
        diagnostic_text.contains("commands.v1"),
        "debug overlay exposes negotiated capabilities",
    )

    shell.shutdown()
    _check(shell.shell_state() == shell.ShellState.SHUTDOWN, "shell exposes shutdown state")
    _check(shell.client_state().interaction.pending_count() == 0, "shutdown clears pending requests")
    root.remove_child(shell)
    shell.queue_free()
    await process_frame


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


func _fixture_snapshot() -> Dictionary:
    var file := FileAccess.open("res://tests/fixtures/snapshot_v1.json", FileAccess.READ)
    if file == null:
        _check(false, "snapshot fixture opens")
        return {}
    var parsed: Variant = JSON.parse_string(file.get_as_text())
    file.close()
    if typeof(parsed) != TYPE_DICTIONARY:
        _check(false, "snapshot fixture parses as object")
        return {}
    var snapshot: Dictionary = parsed
    return snapshot.duplicate(true)


func _check(condition: bool, message: String) -> void:
    if condition:
        return
    _failures += 1
    push_error("FAIL: %s" % message)
