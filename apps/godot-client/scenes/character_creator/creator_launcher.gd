class_name CharacterCreatorLauncher
extends Button

var _bound := false

@onready var _shell: AppShell = get_node("../..")
@onready var _creator: CharacterCreatorView = get_node("../../CharacterCreator")


func _ready() -> void:
    visible = false
    pressed.connect(_open_creator)
    _creator.close_requested.connect(_close_creator)
    _shell.shell_state_changed.connect(_on_shell_state_changed)
    _refresh_availability()


func _on_shell_state_changed(_state: int, _message: String) -> void:
    _refresh_availability()


func _refresh_availability() -> void:
    var bridge := _shell.engine_bridge()
    visible = (
        _shell.shell_state() == AppShell.ShellState.READY
        and bridge != null
        and bridge.capabilities().has("characters.creator.v1")
    )
    if visible and not _bound:
        _creator.bind_client_state(_shell.client_state())
        _bound = true
    if not visible:
        _creator.hide_creator()


func _open_creator() -> void:
    if visible:
        _creator.show_creator()


func _close_creator() -> void:
    _creator.hide_creator()
