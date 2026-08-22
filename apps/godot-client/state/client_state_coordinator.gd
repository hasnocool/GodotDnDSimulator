class_name ClientStateCoordinator
extends RefCounted

signal authoritative_changed(sequence: int)
signal pending_changed(pending_count: int)
signal bridge_bound()
signal bridge_unbound()

var authoritative := AuthoritativeMirror.new()
var interaction := InteractionState.new()
var presentation := PresentationState.new()
var _bridge: EngineBridge


func _init() -> void:
    interaction.pending_changed.connect(
        func(count: int) -> void:
            pending_changed.emit(count)
    )


func bind_bridge(bridge: EngineBridge) -> void:
    if _bridge == bridge:
        return
    unbind_bridge()
    _bridge = bridge
    if _bridge == null:
        return
    _bridge.authoritative_snapshot.connect(_on_authoritative_snapshot)
    _bridge.authoritative_events.connect(_on_authoritative_events)
    _bridge.command_accepted.connect(_on_command_accepted)
    _bridge.command_rejected.connect(_on_command_rejected)
    _bridge.query_result.connect(_on_query_result)
    _bridge.preview_result.connect(_on_preview_result)
    _bridge.request_failed.connect(_on_request_failed)
    _bridge.bridge_disconnected.connect(_on_bridge_disconnected)
    bridge_bound.emit()


func unbind_bridge() -> void:
    if _bridge == null:
        return
    _disconnect_if_connected(_bridge.authoritative_snapshot, _on_authoritative_snapshot)
    _disconnect_if_connected(_bridge.authoritative_events, _on_authoritative_events)
    _disconnect_if_connected(_bridge.command_accepted, _on_command_accepted)
    _disconnect_if_connected(_bridge.command_rejected, _on_command_rejected)
    _disconnect_if_connected(_bridge.query_result, _on_query_result)
    _disconnect_if_connected(_bridge.preview_result, _on_preview_result)
    _disconnect_if_connected(_bridge.request_failed, _on_request_failed)
    _disconnect_if_connected(_bridge.bridge_disconnected, _on_bridge_disconnected)
    _bridge = null
    interaction.clear_all_pending()
    bridge_unbound.emit()


func submit_command(
    command: Dictionary,
    correlation_id: String,
    timeout_msec: int = EngineBridge.DEFAULT_TIMEOUT_MSEC,
) -> String:
    if _bridge == null:
        return ""
    var request_id := _bridge.submit_command(
        command,
        correlation_id,
        interaction.generation(),
        timeout_msec,
    )
    if request_id.is_empty():
        return ""
    interaction.track_pending(
        request_id,
        "command",
        correlation_id,
        interaction.generation(),
    )
    return request_id


func request_query(
    query_type: String,
    query: Dictionary,
    correlation_id: String,
    timeout_msec: int = EngineBridge.DEFAULT_TIMEOUT_MSEC,
) -> String:
    if _bridge == null:
        return ""
    var generation := interaction.generation()
    var request_id := _bridge.request_query(
        query_type,
        query,
        correlation_id,
        generation,
        timeout_msec,
    )
    if request_id.is_empty():
        return ""
    interaction.track_pending(request_id, "query", correlation_id, generation)
    return request_id


func request_preview(
    preview_type: String,
    preview: Dictionary,
    correlation_id: String,
    timeout_msec: int = EngineBridge.DEFAULT_TIMEOUT_MSEC,
) -> String:
    if _bridge == null:
        return ""
    var generation := interaction.generation()
    var request_id := _bridge.request_preview(
        preview_type,
        preview,
        correlation_id,
        generation,
        timeout_msec,
    )
    if request_id.is_empty():
        return ""
    interaction.track_pending(request_id, "preview", correlation_id, generation)
    return request_id


func cancel_pending(request_id: String) -> bool:
    if _bridge == null or not interaction.pending_requests().has(request_id):
        return false
    var cancelled := _bridge.cancel_request(request_id)
    if cancelled:
        interaction.clear_pending(request_id)
    return cancelled


func cancel_all_pending() -> int:
    var request_ids: Array = interaction.pending_requests().keys()
    var cancelled := 0
    for request_id_value in request_ids:
        if cancel_pending(str(request_id_value)):
            cancelled += 1
    return cancelled


func _on_authoritative_snapshot(snapshot: Dictionary) -> void:
    if authoritative.ingest_snapshot(snapshot):
        authoritative_changed.emit(authoritative.sequence())


func _on_authoritative_events(events: Array) -> void:
    if authoritative.ingest_events(events):
        authoritative_changed.emit(authoritative.sequence())


func _on_command_accepted(correlation_id: String, _payload: Dictionary) -> void:
    interaction.clear_pending_matching(correlation_id, "command")


func _on_command_rejected(
    correlation_id: String,
    _category: int,
    _user_message: String,
    _debug_detail: String,
) -> void:
    interaction.clear_pending_matching(correlation_id, "command")


func _on_query_result(
    correlation_id: String,
    _generation: int,
    _payload: Dictionary,
) -> void:
    interaction.clear_pending_matching(correlation_id, "query")


func _on_preview_result(
    correlation_id: String,
    _generation: int,
    _payload: Dictionary,
) -> void:
    interaction.clear_pending_matching(correlation_id, "preview")


func _on_request_failed(
    correlation_id: String,
    _category: int,
    _user_message: String,
    _debug_detail: String,
) -> void:
    interaction.clear_pending_matching(correlation_id)


func _on_bridge_disconnected(_reason: String) -> void:
    interaction.clear_all_pending()


func _disconnect_if_connected(signal_value: Signal, callable: Callable) -> void:
    if signal_value.is_connected(callable):
        signal_value.disconnect(callable)
