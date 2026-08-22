class_name WorldRPGLauncher
extends Button

var _bound := false

@onready var _shell: AppShell = get_node("../..")
@onready var _world: WorldRPGView = get_node("../../WorldRPG")


func _ready() -> void:
    visible = false
    pressed.connect(_open_world)
    _world.close_requested.connect(_close_world)
    _shell.shell_state_changed.connect(_on_shell_state_changed)
    _refresh_availability()


func _on_shell_state_changed(_state: int, _message: String) -> void:
    _refresh_availability()


func _refresh_availability() -> void:
    var bridge := _shell.engine_bridge()
    visible = (
        _shell.shell_state() == AppShell.ShellState.READY
        and bridge != null
        and bridge.capabilities().has("world.runtime.v1")
    )
    if visible and not _bound:
        _world.bind_client_state(_shell.client_state())
        _bound = true
    if not visible:
        _world.hide_world()


func _open_world() -> void:
    if visible:
        _world.show_world()


func _close_world() -> void:
    _world.hide_world()
