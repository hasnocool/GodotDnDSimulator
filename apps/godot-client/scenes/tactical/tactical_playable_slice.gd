class_name TacticalPlayableSlice
extends "res://scenes/tactical/tactical_spell_slice.gd"


func _request_actions() -> void:
    if _state == null:
        return
    var actor_id := _current_actor_id()
    if actor_id.is_empty():
        return
    _state.request_query(
        "tactical.actions",
        {"actor_id": actor_id},
        "v07-actions:%s" % actor_id,
    )
    _request_spells()


func _request_spells() -> void:
    if _spell_state == null:
        return
    if not _tactical.has("spellcasting"):
        _spell_palette.clear()
        _spell_palette.visible = false
        return
    _spell_palette.visible = true
    var actor_id := _current_actor_id()
    if actor_id.is_empty():
        _spell_palette.clear()
        return
    _spell_state.request_query(
        "spells.available",
        {"actor_id": actor_id},
        "v08-spells:%s" % actor_id,
    )


func _on_move_requested() -> void:
    if not _select_current_actor_for_action():
        return
    _release_ui_focus_for_map_action()
    super._on_move_requested()


func _on_strike_requested() -> void:
    if not _select_current_actor_for_action():
        return
    _release_ui_focus_for_map_action()
    super._on_strike_requested()


func _on_area_debug_requested() -> void:
    _release_ui_focus_for_map_action()
    super._on_area_debug_requested()


func _on_spell_selected(spell: Dictionary, slot_level: int) -> void:
    if not _select_current_actor_for_action():
        return
    _release_ui_focus_for_map_action()
    super._on_spell_selected(spell, slot_level)


func _current_actor_id() -> String:
    var value: Variant = _tactical.get("current_actor_id")
    if typeof(value) != TYPE_STRING:
        return ""
    return str(value)


func _select_current_actor_for_action() -> bool:
    if _state == null or _controller == null:
        return false
    var actor_id := _current_actor_id()
    if actor_id.is_empty() or not _actor_views.has(actor_id):
        return false
    if _state.interaction.selected_actor_id() != actor_id:
        _state.interaction.set_selected_actor(actor_id)
    return true


func _release_ui_focus_for_map_action() -> void:
    if not is_inside_tree():
        return
    var focus_owner := get_viewport().gui_get_focus_owner()
    if focus_owner != null:
        focus_owner.release_focus()
