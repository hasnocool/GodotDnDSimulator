class_name AppShell
extends Node

enum ShellState {
    STARTUP,
    BRIDGE_INITIALIZING,
    SYNCHRONIZING,
    LOADING,
    READY,
    INCOMPATIBLE,
    ERROR,
    SHUTDOWN,
}

signal shell_state_changed(state: int, message: String)
signal tactical_scene_ready(scene: Node)

@export var auto_start_bridge := true
@export var bridge_host := "127.0.0.1"
@export var bridge_port := 4765
@export_file("*.tscn") var tactical_scene_path := (
    "res://scenes/tactical/tactical_vertical_slice.tscn"
)

var transport_override: EngineTransport

var _shell_state := ShellState.STARTUP
var _status_message := "Starting client"
var _bridge: EngineBridge
var _transport: EngineTransport
var _client_state := ClientStateCoordinator.new()
var _input_bindings := ClientInputBindings.new()
var _interaction_controller: ClientInteractionController
var _tactical_scene_resource: PackedScene
var _scene_load_pending := false
var _current_tactical_scene: Node

@onready var _content_root: Node3D = $ContentRoot
@onready var _status_panel: PanelContainer = $ShellUI/StatusPanel
@onready var _status_label: Label = $ShellUI/StatusPanel/Margin/VBox/Status
@onready var _retry_button: Button = $ShellUI/StatusPanel/Margin/VBox/Retry
@onready var _debug_overlay: ClientDebugOverlay = $ShellUI/ClientDebugOverlay


func _ready() -> void:
    _retry_button.pressed.connect(retry_bridge)
    ClientSettings.setting_changed.connect(_on_setting_changed)
    _setup_input()
    _apply_local_settings()
    _set_shell_state(ShellState.STARTUP, "Starting client")
    if auto_start_bridge:
        start_bridge()


func _process(delta: float) -> void:
    if _shell_state == ShellState.SHUTDOWN:
        return
    if _bridge != null:
        _bridge.poll(delta)
    if _scene_load_pending:
        _poll_tactical_scene_load()


func shell_state() -> int:
    return _shell_state


func status_message() -> String:
    return _status_message


func client_state() -> ClientStateCoordinator:
    return _client_state


func engine_bridge() -> EngineBridge:
    return _bridge


func input_bindings() -> ClientInputBindings:
    return _input_bindings


func interaction_controller() -> ClientInteractionController:
    return _interaction_controller


func tactical_content() -> Node:
    return _current_tactical_scene


func start_bridge() -> void:
    if _shell_state == ShellState.SHUTDOWN:
        return
    _dispose_bridge()
    _bridge = EngineBridge.new()
    _connect_bridge_signals()
    _client_state.bind_bridge(_bridge)
    _debug_overlay.bind(_client_state, _bridge)
    _transport = transport_override if transport_override != null else TcpJsonTransport.new()
    _set_shell_state(ShellState.BRIDGE_INITIALIZING, "Connecting to authoritative engine")
    ClientLog.write(
        "bridge",
        "Initializing client bridge",
        "%s:%d" % [bridge_host, bridge_port],
    )
    var error := _bridge.initialize(
        _transport,
        {"host": bridge_host, "port": bridge_port},
    )
    if error != OK:
        _fail_shell(
            "Unable to initialize engine bridge",
            "EngineBridge.initialize returned %s" % error_string(error),
        )


func retry_bridge() -> void:
    if _shell_state not in [ShellState.ERROR, ShellState.INCOMPATIBLE]:
        return
    start_bridge()


func reload_tactical_scene() -> bool:
    if _tactical_scene_resource == null or not _client_state.authoritative.has_snapshot():
        return false
    _set_shell_state(ShellState.LOADING, "Reloading tactical presentation")
    _client_state.presentation.set_loading_scene("tactical")
    return _instantiate_tactical_scene()


func shutdown() -> void:
    if _shell_state == ShellState.SHUTDOWN:
        return
    _set_shell_state(ShellState.SHUTDOWN, "Shutting down")
    _scene_load_pending = false
    _client_state.cancel_all_pending()
    _dispose_bridge()
    if is_instance_valid(_interaction_controller):
        _interaction_controller.set_input_enabled(false)
        _interaction_controller.unbind_state()
        _interaction_controller.queue_free()
    _interaction_controller = null
    if is_instance_valid(_current_tactical_scene):
        _content_root.remove_child(_current_tactical_scene)
        _current_tactical_scene.queue_free()
    _current_tactical_scene = null
    set_process(false)


func _exit_tree() -> void:
    if ClientSettings.setting_changed.is_connected(_on_setting_changed):
        ClientSettings.setting_changed.disconnect(_on_setting_changed)
    shutdown()


func _setup_input() -> void:
    _input_bindings.install_defaults()
    _input_bindings.load_overrides()
    _interaction_controller = ClientInteractionController.new()
    _interaction_controller.name = "InteractionController"
    add_child(_interaction_controller)
    _interaction_controller.bind_state(_client_state)
    _interaction_controller.set_input_enabled(false)
    ClientLog.write("input", "Semantic input map initialized")


func _connect_bridge_signals() -> void:
    _bridge.bridge_ready.connect(_on_bridge_ready)
    _bridge.bridge_incompatible.connect(_on_bridge_incompatible)
    _bridge.bridge_disconnected.connect(_on_bridge_disconnected)
    _bridge.request_failed.connect(_on_bridge_request_failed)
    _client_state.authoritative_changed.connect(_on_authoritative_changed)


func _dispose_bridge() -> void:
    if _client_state.authoritative_changed.is_connected(_on_authoritative_changed):
        _client_state.authoritative_changed.disconnect(_on_authoritative_changed)
    if _debug_overlay != null:
        _debug_overlay.unbind()
    _client_state.unbind_bridge()
    if _bridge != null:
        _bridge.shutdown()
    _bridge = null
    _transport = null


func _on_bridge_ready(version: int, capabilities: PackedStringArray) -> void:
    ClientLog.write(
        "bridge",
        "Bridge negotiation complete",
        "version=%d capabilities=%s" % [version, ",".join(capabilities)],
    )
    _set_shell_state(ShellState.SYNCHRONIZING, "Synchronizing authoritative state")
    var snapshot_query := (
        "tactical.snapshot"
        if capabilities.has("tactical.vertical-slice.v1")
        else "bridge.snapshot"
    )
    var request_id := _client_state.request_query(
        snapshot_query,
        {},
        "shell-initial-snapshot",
    )
    if request_id.is_empty():
        _fail_shell(
            "Unable to request authoritative state",
            "%s request was not submitted" % snapshot_query,
        )


func _on_bridge_incompatible(reason: String) -> void:
    ClientLog.write("bridge", "Incompatible bridge", reason, "error")
    _set_shell_state(
        ShellState.INCOMPATIBLE,
        "Engine/client versions are incompatible",
        reason,
    )


func _on_bridge_disconnected(reason: String) -> void:
    if _shell_state == ShellState.SHUTDOWN:
        return
    ClientLog.write("bridge", "Bridge disconnected", reason, "warning")
    _set_shell_state(ShellState.ERROR, "Authoritative engine disconnected", reason)


func _on_bridge_request_failed(
    _request_id: String,
    correlation_id: String,
    _category: int,
    user_message: String,
    debug_detail: String,
) -> void:
    ClientLog.write(
        "bridge",
        "Bridge request failed",
        "%s: %s" % [correlation_id, debug_detail],
        "warning",
    )
    if _shell_state in [
        ShellState.BRIDGE_INITIALIZING,
        ShellState.SYNCHRONIZING,
    ]:
        _set_shell_state(ShellState.ERROR, user_message, debug_detail)


func _on_authoritative_changed(sequence: int) -> void:
    ClientLog.write("state", "Authoritative mirror advanced", "sequence=%d" % sequence)
    if not _client_state.authoritative.has_snapshot():
        return
    if _shell_state in [ShellState.BRIDGE_INITIALIZING, ShellState.SYNCHRONIZING]:
        _begin_tactical_scene_load()


func _begin_tactical_scene_load() -> void:
    if _tactical_scene_resource != null:
        _set_shell_state(ShellState.LOADING, "Loading tactical presentation")
        _client_state.presentation.set_loading_scene("tactical")
        _instantiate_tactical_scene()
        return
    if _scene_load_pending:
        return
    _set_shell_state(ShellState.LOADING, "Loading tactical presentation")
    _client_state.presentation.set_loading_scene("tactical")
    var error := ResourceLoader.load_threaded_request(tactical_scene_path, "PackedScene")
    if error != OK:
        _fail_shell(
            "Unable to load tactical presentation",
            "load_threaded_request returned %s for %s" % [
                error_string(error),
                tactical_scene_path,
            ],
        )
        return
    _scene_load_pending = true


func _poll_tactical_scene_load() -> void:
    var progress: Array = []
    var status := ResourceLoader.load_threaded_get_status(tactical_scene_path, progress)
    if status == ResourceLoader.THREAD_LOAD_IN_PROGRESS:
        return
    _scene_load_pending = false
    if status != ResourceLoader.THREAD_LOAD_LOADED:
        _fail_shell(
            "Unable to load tactical presentation",
            "threaded resource status=%d path=%s" % [status, tactical_scene_path],
        )
        return
    var loaded: Resource = ResourceLoader.load_threaded_get(tactical_scene_path)
    if not (loaded is PackedScene):
        _fail_shell(
            "Unable to load tactical presentation",
            "resource is not a PackedScene: %s" % tactical_scene_path,
        )
        return
    _tactical_scene_resource = loaded as PackedScene
    _instantiate_tactical_scene()


func _instantiate_tactical_scene() -> bool:
    if _tactical_scene_resource == null:
        return false
    var next_scene := _tactical_scene_resource.instantiate()
    if next_scene == null:
        _fail_shell("Unable to instantiate tactical presentation", tactical_scene_path)
        return false
    if is_instance_valid(_current_tactical_scene):
        _content_root.remove_child(_current_tactical_scene)
        _current_tactical_scene.queue_free()
    _current_tactical_scene = next_scene
    _content_root.add_child(_current_tactical_scene)
    if _current_tactical_scene.has_method("bind_client_state"):
        _current_tactical_scene.call("bind_client_state", _client_state)
    if _current_tactical_scene.has_method("bind_interaction_controller"):
        _current_tactical_scene.call(
            "bind_interaction_controller",
            _interaction_controller,
        )
    _client_state.presentation.set_active_scene("tactical")
    _set_shell_state(ShellState.READY, "Client ready")
    ClientLog.write(
        "tactical",
        "Tactical presentation ready",
        "authoritative_sequence=%d" % _client_state.authoritative.sequence(),
    )
    tactical_scene_ready.emit(_current_tactical_scene)
    return true


func _apply_local_settings() -> void:
    _client_state.presentation.apply_local_options(
        ClientSettings.reduced_motion(),
        ClientSettings.ui_scale(),
        ClientSettings.debug_overlay(),
    )
    if _debug_overlay != null:
        _debug_overlay.visible = ClientSettings.debug_overlay()


func _on_setting_changed(_key: String, _value: Variant) -> void:
    _apply_local_settings()


func _set_shell_state(state: int, message: String, detail: String = "") -> void:
    _shell_state = state
    _status_message = message
    if _interaction_controller != null:
        _interaction_controller.set_input_enabled(state == ShellState.READY)
    if _status_label != null:
        _status_label.text = (
            message if detail.is_empty() else "%s\n%s" % [message, detail]
        )
    if _status_panel != null:
        _status_panel.visible = state != ShellState.READY
    if _retry_button != null:
        _retry_button.visible = state in [ShellState.ERROR, ShellState.INCOMPATIBLE]
    shell_state_changed.emit(_shell_state, _status_message)


func _fail_shell(message: String, detail: String) -> void:
    ClientLog.write("ui", message, detail, "error")
    _set_shell_state(ShellState.ERROR, message, detail)
