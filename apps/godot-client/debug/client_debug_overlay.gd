class_name ClientDebugOverlay
extends PanelContainer

var _state: ClientStateCoordinator
var _bridge: EngineBridge
var _bridge_version := 0
var _capabilities := PackedStringArray()
var _bridge_status := "not connected"
var _pending_count := 0
var _pending_started_msec := -1
var _last_request_latency_msec := -1
var _diagnostic_accumulator := 0.0

@onready var _label: Label = $Margin/Label


func _ready() -> void:
    set_process(true)


func _process(delta: float) -> void:
    _diagnostic_accumulator += delta
    if _diagnostic_accumulator >= 0.5:
        _diagnostic_accumulator = 0.0
        refresh()


func bind(state: ClientStateCoordinator, bridge: EngineBridge) -> void:
    unbind()
    _state = state
    _bridge = bridge
    if _state != null:
        _state.authoritative_changed.connect(_on_state_changed)
        _state.pending_changed.connect(_on_pending_changed)
        _state.presentation.scene_changed.connect(_on_scene_changed)
        _pending_count = _state.interaction.pending_count()
        if _pending_count > 0:
            _pending_started_msec = Time.get_ticks_msec()
    if _bridge != null:
        _bridge.bridge_ready.connect(_on_bridge_ready)
        _bridge.bridge_disconnected.connect(_on_bridge_disconnected)
        _bridge.bridge_incompatible.connect(_on_bridge_incompatible)
    refresh()


func unbind() -> void:
    if _state != null:
        _disconnect_if_connected(_state.authoritative_changed, _on_state_changed)
        _disconnect_if_connected(_state.pending_changed, _on_pending_changed)
        _disconnect_if_connected(_state.presentation.scene_changed, _on_scene_changed)
    if _bridge != null:
        _disconnect_if_connected(_bridge.bridge_ready, _on_bridge_ready)
        _disconnect_if_connected(_bridge.bridge_disconnected, _on_bridge_disconnected)
        _disconnect_if_connected(_bridge.bridge_incompatible, _on_bridge_incompatible)
    _state = null
    _bridge = null
    _pending_count = 0
    _pending_started_msec = -1


func refresh() -> void:
    if not is_node_ready() or _label == null:
        return
    var sequence := 0
    var has_snapshot := false
    var pending := 0
    var active_scene := ""
    if _state != null:
        sequence = _state.authoritative.sequence()
        has_snapshot = _state.authoritative.has_snapshot()
        pending = _state.interaction.pending_count()
        active_scene = _state.presentation.active_scene_id()
    var capability_text := ", ".join(_capabilities)
    if capability_text.is_empty():
        capability_text = "none"
    var presentation_scene := active_scene if not active_scene.is_empty() else "none"
    var latency_text := "n/a"
    if pending > 0 and _pending_started_msec >= 0:
        latency_text = "%d ms pending" % (Time.get_ticks_msec() - _pending_started_msec)
    elif _last_request_latency_msec >= 0:
        latency_text = "%d ms last batch" % _last_request_latency_msec
    _label.text = "\n".join(PackedStringArray([
        "Client diagnostics",
        "Bridge: %s" % _bridge_status,
        "Protocol version: %d" % _bridge_version,
        "Capabilities: %s" % capability_text,
        "Authoritative sequence: %d" % sequence,
        "Snapshot loaded: %s" % str(has_snapshot),
        "Pending requests: %d" % pending,
        "Bridge latency: %s" % latency_text,
        "FPS: %d" % Engine.get_frames_per_second(),
        "Presentation scene: %s" % presentation_scene,
    ]))


func diagnostic_text() -> String:
    if not is_node_ready() or _label == null:
        return ""
    return _label.text


func _on_bridge_ready(version: int, capabilities: PackedStringArray) -> void:
    _bridge_status = "ready"
    _bridge_version = version
    _capabilities = capabilities.duplicate()
    refresh()


func _on_bridge_disconnected(reason: String) -> void:
    _bridge_status = "disconnected: %s" % reason
    refresh()


func _on_bridge_incompatible(reason: String) -> void:
    _bridge_status = "incompatible: %s" % reason
    refresh()


func _on_state_changed(_sequence: int) -> void:
    refresh()


func _on_pending_changed(pending_count: int) -> void:
    var now := Time.get_ticks_msec()
    if pending_count > 0 and _pending_count == 0:
        _pending_started_msec = now
    elif pending_count == 0 and _pending_count > 0 and _pending_started_msec >= 0:
        _last_request_latency_msec = now - _pending_started_msec
        _pending_started_msec = -1
    _pending_count = pending_count
    refresh()


func _on_scene_changed(_active_scene_id: String, _loading_scene_id: String) -> void:
    refresh()


func _disconnect_if_connected(signal_value: Signal, callable: Callable) -> void:
    if signal_value.is_connected(callable):
        signal_value.disconnect(callable)
