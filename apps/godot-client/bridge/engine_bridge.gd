class_name EngineBridge
extends RefCounted

const Protocol = preload("res://bridge/bridge_protocol.gd")
const DEFAULT_TIMEOUT_MSEC := 5000

signal bridge_ready(version: int, capabilities: PackedStringArray)
signal bridge_incompatible(reason: String)
signal bridge_disconnected(reason: String)
signal authoritative_snapshot(snapshot: Dictionary)
signal authoritative_events(events: Array)
signal command_accepted(correlation_id: String, payload: Dictionary)
signal command_rejected(
    correlation_id: String,
    category: int,
    user_message: String,
    debug_detail: String,
)
signal query_result(correlation_id: String, generation: int, payload: Dictionary)
signal preview_result(correlation_id: String, generation: int, payload: Dictionary)
signal request_failed(
    request_id: String,
    correlation_id: String,
    category: int,
    user_message: String,
    debug_detail: String,
)
signal stale_response_ignored(request_id: String, reason: String)
signal resync_required(reason: String)

var _transport: EngineTransport
var _transport_config: Dictionary = {}
var _pending: Dictionary = {}
var _request_counter := 0
var _ready := false
var _capabilities := PackedStringArray()
var _authoritative_sequence := 0
var _has_authoritative_state := false
var _needs_resync := false


func initialize(transport: EngineTransport, config: Dictionary = {}) -> Error:
    if transport == null:
        return ERR_INVALID_PARAMETER
    if _transport != null:
        shutdown()
    _transport = transport
    _transport_config = config.duplicate(true)
    _transport.connected.connect(_on_transport_connected)
    _transport.disconnected.connect(_on_transport_disconnected)
    _transport.message_received.connect(_on_transport_message)
    _transport.transport_error.connect(_on_transport_error)
    return _transport.start(_transport_config)


func shutdown() -> void:
    if _transport != null:
        _transport.stop()
    _pending.clear()
    _ready = false
    _capabilities.clear()
    _transport = null


func poll(delta: float) -> void:
    if _transport != null:
        _transport.poll(delta)
    _expire_requests(Time.get_ticks_msec())


func is_ready() -> bool:
    return _ready


func capabilities() -> PackedStringArray:
    return _capabilities.duplicate()


func authoritative_sequence() -> int:
    return _authoritative_sequence


func submit_command(
    command: Dictionary,
    correlation_id: String,
    generation: int = 0,
    timeout_msec: int = DEFAULT_TIMEOUT_MSEC,
) -> String:
    if not _can_submit(correlation_id, generation, timeout_msec):
        return ""
    if not command.has("command_id") or typeof(command["command_id"]) != TYPE_STRING:
        _emit_validation_failure(correlation_id, "command must contain string command_id")
        return ""
    if str(command["command_id"]).is_empty():
        _emit_validation_failure(correlation_id, "command_id must not be empty")
        return ""
    var request_id := _next_request_id()
    var message := Protocol.make_command_request(
        request_id,
        correlation_id,
        generation,
        command,
    )
    return _send_tracked(
        message,
        "command",
        correlation_id,
        generation,
        timeout_msec,
        {},
    )


func request_query(
    query_type: String,
    query: Dictionary,
    correlation_id: String,
    generation: int = 0,
    timeout_msec: int = DEFAULT_TIMEOUT_MSEC,
) -> String:
    if not _can_submit(correlation_id, generation, timeout_msec):
        return ""
    if query_type.is_empty():
        _emit_validation_failure(correlation_id, "query_type must not be empty")
        return ""
    var request_id := _next_request_id()
    var message := Protocol.make_query_request(
        request_id,
        correlation_id,
        generation,
        query_type,
        query,
    )
    return _send_tracked(
        message,
        "query",
        correlation_id,
        generation,
        timeout_msec,
        {"query_type": query_type},
    )


func request_preview(
    preview_type: String,
    preview: Dictionary,
    correlation_id: String,
    generation: int,
    timeout_msec: int = DEFAULT_TIMEOUT_MSEC,
) -> String:
    if not _can_submit(correlation_id, generation, timeout_msec):
        return ""
    if preview_type.is_empty():
        _emit_validation_failure(correlation_id, "preview_type must not be empty")
        return ""
    var request_id := _next_request_id()
    var message := Protocol.make_preview_request(
        request_id,
        correlation_id,
        generation,
        preview_type,
        preview,
    )
    return _send_tracked(
        message,
        "preview",
        correlation_id,
        generation,
        timeout_msec,
        {"preview_type": preview_type},
    )


func cancel_request(request_id: String) -> bool:
    if not _pending.has(request_id):
        return false
    var metadata: Dictionary = _pending[request_id]
    _pending.erase(request_id)
    if _transport != null:
        _transport.cancel(request_id)
        if _transport._is_connected():
            var cancel_id := _next_request_id()
            _transport.send(
                Protocol.make_cancel_request(
                    cancel_id,
                    request_id,
                    str(metadata["correlation_id"]),
                    int(metadata["generation"]),
                )
            )
    request_failed.emit(
        request_id,
        str(metadata["correlation_id"]),
        Protocol.ErrorCategory.CANCELLED,
        "Request cancelled",
        "request_id=%s" % request_id,
    )
    return true


func request_resync(timeout_msec: int = DEFAULT_TIMEOUT_MSEC) -> String:
    if not _ready:
        return ""
    return request_query(
        "bridge.resync",
        {"after_sequence": _authoritative_sequence},
        "bridge-resync",
        0,
        timeout_msec,
    )


func _can_submit(correlation_id: String, generation: int, timeout_msec: int) -> bool:
    if not _ready or _transport == null or not _transport._is_connected():
        request_failed.emit(
            "",
            correlation_id,
            Protocol.ErrorCategory.TRANSPORT,
            "Engine bridge is not ready",
            "request attempted while bridge was disconnected or negotiating",
        )
        return false
    if correlation_id.is_empty():
        _emit_validation_failure(correlation_id, "correlation_id must not be empty")
        return false
    if generation < 0:
        _emit_validation_failure(correlation_id, "generation must be >= 0")
        return false
    if timeout_msec < 1:
        _emit_validation_failure(correlation_id, "timeout_msec must be >= 1")
        return false
    return true


func _send_tracked(
    message: Dictionary,
    request_kind: String,
    correlation_id: String,
    generation: int,
    timeout_msec: int,
    extra: Dictionary,
) -> String:
    var request_id := str(message["request_id"])
    var metadata := {
        "request_kind": request_kind,
        "correlation_id": correlation_id,
        "generation": generation,
        "deadline_msec": Time.get_ticks_msec() + timeout_msec,
    }
    metadata.merge(extra)
    _pending[request_id] = metadata
    var error := _transport.send(message)
    if error != OK:
        _pending.erase(request_id)
        request_failed.emit(
            request_id,
            correlation_id,
            Protocol.ErrorCategory.TRANSPORT,
            "Failed to send engine request",
            "transport send returned error %d" % error,
        )
        return ""
    return request_id


func _on_transport_connected() -> void:
    _ready = false
    _capabilities.clear()
    _send_hello()


func _send_hello() -> void:
    var request_id := _next_request_id()
    var message := Protocol.make_hello(request_id)
    _pending[request_id] = {
        "request_kind": "hello",
        "correlation_id": request_id,
        "generation": 0,
        "deadline_msec": Time.get_ticks_msec() + DEFAULT_TIMEOUT_MSEC,
    }
    var error := _transport.send(message)
    if error != OK:
        _pending.erase(request_id)
        request_failed.emit(
            request_id,
            request_id,
            Protocol.ErrorCategory.TRANSPORT,
            "Failed to negotiate engine bridge",
            "hello send returned error %d" % error,
        )


func _on_transport_disconnected(reason: String) -> void:
    _ready = false
    _needs_resync = _has_authoritative_state
    bridge_disconnected.emit(reason)


func _on_transport_error(category: int, user_message: String, debug_detail: String) -> void:
    request_failed.emit("", "bridge", category, user_message, debug_detail)


func _on_transport_message(message: Dictionary) -> void:
    var validation_error := Protocol.validate_message(message)
    if not validation_error.is_empty():
        request_failed.emit(
            "",
            "bridge",
            Protocol.ErrorCategory.VALIDATION,
            "Received invalid engine message",
            validation_error,
        )
        return
    if int(message["bridge_version"]) != Protocol.PROTOCOL_VERSION:
        _ready = false
        var reason := "unsupported bridge version %s; expected %s" % [
            message["bridge_version"],
            Protocol.PROTOCOL_VERSION,
        ]
        bridge_incompatible.emit(reason)
        return

    var kind := str(message["kind"])
    if kind == "authoritative.snapshot":
        _ingest_snapshot(message["payload"].get("snapshot", {}))
        return
    if kind == "authoritative.events":
        _ingest_events(message["payload"].get("events", []))
        return

    var request_id := str(message["request_id"])
    if not _pending.has(request_id):
        stale_response_ignored.emit(request_id, "request is no longer pending")
        return
    var metadata: Dictionary = _pending[request_id]
    if str(message["correlation_id"]) != str(metadata["correlation_id"]):
        stale_response_ignored.emit(request_id, "correlation_id mismatch")
        return
    if int(message["generation"]) != int(metadata["generation"]):
        stale_response_ignored.emit(request_id, "generation mismatch")
        return

    if str(metadata["request_kind"]) == "hello":
        _pending.erase(request_id)
        _handle_hello_response(message)
        return

    _pending.erase(request_id)
    var ok := bool(message.get("ok", false))
    if not ok:
        _handle_rejected_response(metadata, message)
        return

    var payload: Dictionary = message["payload"]
    _ingest_authoritative_payload(payload)
    match str(metadata["request_kind"]):
        "command":
            command_accepted.emit(str(metadata["correlation_id"]), payload.duplicate(true))
        "query":
            query_result.emit(
                str(metadata["correlation_id"]),
                int(metadata["generation"]),
                payload.duplicate(true),
            )
            if str(metadata.get("query_type", "")) == "bridge.resync":
                _needs_resync = false
        "preview":
            preview_result.emit(
                str(metadata["correlation_id"]),
                int(metadata["generation"]),
                payload.duplicate(true),
            )
        _:
            request_failed.emit(
                request_id,
                str(metadata["correlation_id"]),
                Protocol.ErrorCategory.INTERNAL,
                "Unknown pending bridge request",
                str(metadata["request_kind"]),
            )


func _handle_hello_response(message: Dictionary) -> void:
    if str(message["kind"]) != "bridge.hello.accepted" or not bool(message.get("ok", false)):
        var error := Protocol.response_error(message)
        _ready = false
        bridge_incompatible.emit(str(error["user_message"]))
        return
    var payload: Dictionary = message["payload"]
    if str(payload.get("protocol", "")) != Protocol.PROTOCOL_NAME:
        _ready = false
        bridge_incompatible.emit("engine reported an unexpected bridge protocol")
        return
    var raw_capabilities: Variant = payload.get("capabilities", [])
    var is_array := typeof(raw_capabilities) == TYPE_ARRAY or typeof(raw_capabilities) == TYPE_PACKED_STRING_ARRAY
    if not is_array:
        _ready = false
        bridge_incompatible.emit("engine capabilities must be an array")
        return
    _capabilities.clear()
    for capability in raw_capabilities:
        if typeof(capability) == TYPE_STRING:
            _capabilities.append(str(capability))
    _ready = true
    bridge_ready.emit(Protocol.PROTOCOL_VERSION, _capabilities.duplicate())
    if _needs_resync:
        request_resync()


func _handle_rejected_response(metadata: Dictionary, message: Dictionary) -> void:
    var error := Protocol.response_error(message)
    var correlation_id := str(metadata["correlation_id"])
    var category := Protocol.error_category(str(error["category"]))
    if str(metadata["request_kind"]) == "command":
        command_rejected.emit(
            correlation_id,
            category,
            str(error["user_message"]),
            str(error["debug_detail"]),
        )
    else:
        request_failed.emit(
            str(message["request_id"]),
            correlation_id,
            category,
            str(error["user_message"]),
            str(error["debug_detail"]),
        )


func _ingest_authoritative_payload(payload: Dictionary) -> bool:
    if payload.has("snapshot"):
        if typeof(payload["snapshot"]) != TYPE_DICTIONARY:
            _authoritative_validation_error("snapshot must be an object")
            return false
        if not _ingest_snapshot(payload["snapshot"]):
            return false
    if payload.has("events"):
        if typeof(payload["events"]) != TYPE_ARRAY:
            _authoritative_validation_error("events must be an array")
            return false
        if not _ingest_events(payload["events"]):
            return false
    return true


func _ingest_snapshot(snapshot_value: Variant) -> bool:
    if typeof(snapshot_value) != TYPE_DICTIONARY:
        _authoritative_validation_error("snapshot must be an object")
        return false
    var snapshot: Dictionary = snapshot_value
    var state_value: Variant = snapshot.get("state", {})
    if typeof(state_value) != TYPE_DICTIONARY:
        _authoritative_validation_error("snapshot.state must be an object")
        return false
    var state: Dictionary = state_value
    var seq_val: Variant = state.get("sequence")
    var sequence := _parse_sequence(seq_val, 0)
    if sequence < 0:
        _authoritative_validation_error("snapshot state sequence must be an integer >= 0")
        return false
    if _has_authoritative_state and sequence < _authoritative_sequence:
        stale_response_ignored.emit("snapshot:%d" % sequence, "snapshot would regress state")
        return false
    _authoritative_sequence = sequence
    _has_authoritative_state = true
    authoritative_snapshot.emit(snapshot.duplicate(true))
    return true


func _ingest_events(events_value: Variant) -> bool:
    if typeof(events_value) != TYPE_ARRAY:
        _authoritative_validation_error("events must be an array")
        return false
    var events: Array = events_value
    var accepted: Array = []
    var expected := _authoritative_sequence + 1
    for raw_event in events:
        if typeof(raw_event) != TYPE_DICTIONARY:
            _authoritative_validation_error("event entries must be objects")
            return false
        var event: Dictionary = raw_event
        var seq_val: Variant = event.get("sequence")
        var sequence := _parse_sequence(seq_val, 1)
        if sequence < 1:
            _authoritative_validation_error("event sequence must be an integer >= 1")
            return false
        if sequence <= _authoritative_sequence:
            stale_response_ignored.emit("event:%d" % sequence, "duplicate or stale event")
            continue
        if sequence != expected:
            _needs_resync = true
            resync_required.emit(
                "event sequence gap: expected %d, received %d" % [expected, sequence]
            )
            return false
        accepted.append(event.duplicate(true))
        expected += 1
    if accepted.is_empty():
        return true
    _authoritative_sequence = expected - 1
    _has_authoritative_state = true
    authoritative_events.emit(accepted)
    return true


func _parse_sequence(value: Variant, minimum: int) -> int:
    if typeof(value) == TYPE_INT:
        var integer_value := int(value)
        return integer_value if integer_value >= minimum else -1
    if typeof(value) != TYPE_FLOAT:
        return -1
    var float_value := float(value)
    if not is_finite(float_value) or float_value != floor(float_value):
        return -1
    var integer_value := int(float_value)
    return integer_value if integer_value >= minimum else -1


func _authoritative_validation_error(debug_detail: String) -> void:
    _needs_resync = true
    request_failed.emit(
        "",
        "authoritative-state",
        Protocol.ErrorCategory.VALIDATION,
        "Received invalid authoritative state",
        debug_detail,
    )
    resync_required.emit(debug_detail)


func _expire_requests(now_msec: int) -> void:
    var expired: Array[String] = []
    for request_id in _pending:
        var metadata: Dictionary = _pending[request_id]
        if now_msec >= int(metadata["deadline_msec"]):
            expired.append(str(request_id))
    for request_id in expired:
        var metadata: Dictionary = _pending[request_id]
        _pending.erase(request_id)
        if _transport != null:
            _transport.cancel(request_id)
        request_failed.emit(
            request_id,
            str(metadata["correlation_id"]),
            Protocol.ErrorCategory.TIMEOUT,
            "Engine request timed out",
            "request_id=%s" % request_id,
        )


func _emit_validation_failure(correlation_id: String, detail: String) -> void:
    request_failed.emit(
        "",
        correlation_id,
        Protocol.ErrorCategory.VALIDATION,
        "Invalid engine request",
        detail,
    )


func _next_request_id() -> String:
    _request_counter += 1
    return "client-request:%016d" % _request_counter
