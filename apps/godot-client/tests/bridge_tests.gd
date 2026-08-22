extends SceneTree

const Protocol = preload("res://bridge/bridge_protocol.gd")
const EngineBridgeScript = preload("res://bridge/engine_bridge.gd")
const FakeTransportScript = preload("res://bridge/fake_engine_transport.gd")

var _failures := 0


func _initialize() -> void:
    _test_protocol_validation()
    _test_command_acceptance_and_authoritative_events()
    _test_command_rejection()
    _test_stale_generation_is_ignored()
    _test_event_gap_requests_resync()
    _test_disconnect_reconnect_requests_resync()
    _test_timeout_and_cancellation()
    _test_incompatible_version_fails_closed()
    if _failures == 0:
        print("Godot client bridge tests: PASS")
        quit(0)
    else:
        push_error("Godot client bridge tests: %d failure(s)" % _failures)
        quit(1)


func _test_protocol_validation() -> void:
    var hello := Protocol.make_hello("client-request:test")
    _check(Protocol.validate_message(hello).is_empty(), "hello validates")
    var broken := hello.duplicate(true)
    broken.erase("generation")
    _check(
        Protocol.validate_message(broken) == "bridge message missing field: generation",
        "missing protocol field is rejected",
    )


func _test_command_acceptance_and_authoritative_events() -> void:
    var pair := _ready_bridge()
    var bridge = pair["bridge"]
    var transport = pair["transport"]
    var accepted: Array = []
    var event_batches: Array = []
    bridge.command_accepted.connect(
        func(correlation_id: String, payload: Dictionary) -> void:
            accepted.append([correlation_id, payload])
    )
    bridge.authoritative_events.connect(
        func(events: Array) -> void:
            event_batches.append(events)
    )

    var request_id := bridge.submit_command(
        _command("command:bridge-accepted"),
        "interaction:accepted",
    )
    _check(not request_id.is_empty(), "command request is submitted")
    var request: Dictionary = transport.sent_messages.back()
    var events: Array = _fixture_events()
    transport.queue_message(
        Protocol.make_response(
            "command.accepted",
            str(request["request_id"]),
            str(request["correlation_id"]),
            int(request["generation"]),
            true,
            {"events": [events[0]]},
        )
    )
    bridge.poll(0.0)
    _check(accepted.size() == 1, "accepted command emits command_accepted")
    _check(event_batches.size() == 1, "accepted command ingests authoritative events")
    _check(bridge.authoritative_sequence() == 1, "event ingestion advances sequence")


func _test_command_rejection() -> void:
    var pair := _ready_bridge()
    var bridge = pair["bridge"]
    var transport = pair["transport"]
    var rejected: Array = []
    bridge.command_rejected.connect(
        func(
            correlation_id: String,
            category: int,
            user_message: String,
            debug_detail: String,
        ) -> void:
            rejected.append([correlation_id, category, user_message, debug_detail])
    )
    bridge.submit_command(_command("command:bridge-rejected"), "interaction:rejected")
    var request: Dictionary = transport.sent_messages.back()
    transport.queue_message(
        Protocol.make_response(
            "command.rejected",
            str(request["request_id"]),
            str(request["correlation_id"]),
            int(request["generation"]),
            false,
            {},
            Protocol.make_error(
                Protocol.ErrorCategory.VALIDATION,
                "That action is no longer legal",
                "expected sequence 2, actual 3",
            ),
        )
    )
    bridge.poll(0.0)
    _check(rejected.size() == 1, "rejected command emits command_rejected")
    _check(
        rejected[0][1] == Protocol.ErrorCategory.VALIDATION,
        "rejection preserves error category",
    )


func _test_stale_generation_is_ignored() -> void:
    var pair := _ready_bridge()
    var bridge = pair["bridge"]
    var transport = pair["transport"]
    var previews: Array = []
    var stale: Array = []
    bridge.preview_result.connect(
        func(correlation_id: String, generation: int, payload: Dictionary) -> void:
            previews.append([correlation_id, generation, payload])
    )
    bridge.stale_response_ignored.connect(
        func(request_id: String, reason: String) -> void:
            stale.append([request_id, reason])
    )
    var request_id := bridge.request_preview(
        "movement.path",
        {"destination": "cell:2,3"},
        "interaction:path",
        7,
    )
    var request: Dictionary = transport.sent_messages.back()
    transport.queue_message(
        Protocol.make_response(
            "preview.result",
            str(request["request_id"]),
            str(request["correlation_id"]),
            6,
            true,
            {"path": []},
        )
    )
    bridge.poll(0.0)
    _check(previews.is_empty(), "stale preview generation is not presented")
    _check(stale.size() == 1, "stale preview is reported")
    _check(bridge.cancel_request(request_id), "stale pending request remains cancellable")


func _test_event_gap_requests_resync() -> void:
    var pair := _ready_bridge()
    var bridge = pair["bridge"]
    var transport = pair["transport"]
    var resync_reasons: Array[String] = []
    bridge.resync_required.connect(
        func(reason: String) -> void:
            resync_reasons.append(reason)
    )
    var events: Array = _fixture_events()
    transport.queue_message(
        Protocol.make_envelope(
            "authoritative.events",
            "",
            "",
            0,
            {"events": [events[1]]},
        )
    )
    bridge.poll(0.0)
    _check(bridge.authoritative_sequence() == 0, "event gap does not partially advance state")
    _check(resync_reasons.size() == 1, "event gap requests resync")


func _test_disconnect_reconnect_requests_resync() -> void:
    var pair := _ready_bridge()
    var bridge = pair["bridge"]
    var transport = pair["transport"]
    var snapshot: Dictionary = _fixture_snapshot()
    var events: Array = _fixture_events()
    transport.queue_message(
        Protocol.make_envelope(
            "authoritative.snapshot",
            "",
            "",
            0,
            {"snapshot": snapshot},
        )
    )
    transport.queue_message(
        Protocol.make_envelope(
            "authoritative.events",
            "",
            "",
            0,
            {"events": [events[0]]},
        )
    )
    bridge.poll(0.0)
    _check(bridge.authoritative_sequence() == 1, "fixture state is ingested before reconnect")

    transport.simulate_disconnect("network test")
    transport.simulate_reconnect()
    var hello: Dictionary = transport.sent_messages.back()
    _check(hello["kind"] == "bridge.hello", "reconnect renegotiates bridge")
    transport.queue_message(_hello_accepted(hello))
    bridge.poll(0.0)
    var resync: Dictionary = transport.sent_messages.back()
    _check(resync["kind"] == "query.request", "reconnect submits resync query")
    _check(
        resync["payload"]["query_type"] == "bridge.resync",
        "reconnect uses bridge.resync query",
    )
    _check(
        resync["payload"]["query"]["after_sequence"] == 1,
        "resync starts after last authoritative sequence",
    )


func _test_timeout_and_cancellation() -> void:
    var pair := _ready_bridge()
    var bridge = pair["bridge"]
    var failures: Array = []
    bridge.request_failed.connect(
        func(
            correlation_id: String,
            category: int,
            user_message: String,
            debug_detail: String,
        ) -> void:
            failures.append([correlation_id, category, user_message, debug_detail])
    )
    var request_id := bridge.request_query(
        "actor.inspect",
        {"actor_id": "actor:test"},
        "interaction:timeout",
        0,
        1,
    )
    bridge._expire_requests(Time.get_ticks_msec() + 100)
    _check(not request_id.is_empty(), "timeout request was initially accepted")
    _check(failures.size() == 1, "expired request emits request_failed")
    _check(failures[0][1] == Protocol.ErrorCategory.TIMEOUT, "timeout is categorized")

    failures.clear()
    request_id = bridge.request_query(
        "actor.inspect",
        {"actor_id": "actor:test"},
        "interaction:cancel",
    )
    _check(bridge.cancel_request(request_id), "pending request can be cancelled")
    _check(failures.size() == 1, "cancel emits request_failed")
    _check(failures[0][1] == Protocol.ErrorCategory.CANCELLED, "cancel is categorized")


func _test_incompatible_version_fails_closed() -> void:
    var bridge = EngineBridgeScript.new()
    var transport = FakeTransportScript.new()
    var incompatible: Array[String] = []
    bridge.bridge_incompatible.connect(
        func(reason: String) -> void:
            incompatible.append(reason)
    )
    _check(bridge.initialize(transport) == OK, "incompatible test transport initializes")
    var hello: Dictionary = transport.sent_messages.back()
    var response := _hello_accepted(hello)
    response["bridge_version"] = Protocol.PROTOCOL_VERSION + 1
    transport.queue_message(response)
    bridge.poll(0.0)
    _check(not bridge.is_ready(), "incompatible bridge never becomes ready")
    _check(incompatible.size() == 1, "incompatible bridge emits explicit signal")


func _ready_bridge() -> Dictionary:
    var bridge = EngineBridgeScript.new()
    var transport = FakeTransportScript.new()
    _check(bridge.initialize(transport) == OK, "fake transport initializes")
    _check(transport.sent_messages.size() == 1, "bridge sends hello on connect")
    var hello: Dictionary = transport.sent_messages.back()
    transport.queue_message(_hello_accepted(hello))
    bridge.poll(0.0)
    _check(bridge.is_ready(), "bridge becomes ready after compatible hello")
    return {"bridge": bridge, "transport": transport}


func _hello_accepted(hello: Dictionary) -> Dictionary:
    return Protocol.make_response(
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


func _command(command_id: String) -> Dictionary:
    return {
        "command_id": command_id,
        "campaign_id": "campaign:bridge-fixture",
        "session_id": "session:bridge-fixture",
        "command_type": "simulation.advance_tick",
        "payload": {"amount": 1},
        "version": 1,
        "actor_id": null,
        "expected_sequence": 0,
    }


func _fixture_snapshot() -> Dictionary:
    var parsed: Variant = JSON.parse_string(
        FileAccess.get_file_as_string("res://tests/fixtures/snapshot_v1.json")
    )
    _check(typeof(parsed) == TYPE_DICTIONARY, "snapshot fixture parses")
    return parsed


func _fixture_events() -> Array:
    var parsed: Variant = JSON.parse_string(
        FileAccess.get_file_as_string("res://tests/fixtures/events_v1.json")
    )
    _check(typeof(parsed) == TYPE_ARRAY, "event fixture parses")
    return parsed


func _check(condition: bool, label: String) -> void:
    if condition:
        return
    _failures += 1
    push_error("bridge test failed: %s" % label)
