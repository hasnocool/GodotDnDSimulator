extends "res://scenes/world/world_rpg_view.gd"

@onready var _save_load_panel: WorldSavePanel = %SaveLoad


func bind_client_state(state: ClientStateCoordinator) -> void:
    super.bind_client_state(state)
    _save_load_panel.bind_client_state(state)


func show_world() -> void:
    super.show_world()
    _save_load_panel.activate()


func _apply_snapshot(snapshot: Dictionary) -> void:
    super._apply_snapshot(snapshot)
    _save_load_panel.set_world_snapshot(snapshot)
