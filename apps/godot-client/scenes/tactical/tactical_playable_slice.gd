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
    _hovered_cell.clear()
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


func _update_pointer_hover(pointer: Vector2) -> void:
    if _controller == null or _state == null:
        return
    if _controller.current_mode() != InteractionModes.Mode.MOVE:
        super._update_pointer_hover(pointer)
        return
    var hit := _pick(pointer)
    var cell := _cell_from_hit(hit)
    if cell.is_empty():
        _hovered_cell.clear()
        return
    if cell == _hovered_cell:
        return
    _hovered_cell = cell.duplicate(true)
    if _armed_cell.is_empty():
        _hud.set_preview_text(
            "Destination %d,%d · click to preview and arm movement" % [
                int(cell.get("x", 0)),
                int(cell.get("y", 0)),
            ]
        )


func _refresh_active_preview_after_state_change() -> void:
    if _state == null or _controller == null:
        return
    if _controller.current_mode() != InteractionModes.Mode.MOVE:
        super._refresh_active_preview_after_state_change()
        return
    var sequence := _state.authoritative.sequence()
    if sequence == _preview_authority_sequence:
        return
    _preview_authority_sequence = sequence
    if not _armed_cell.is_empty():
        _request_path(_armed_cell)
    else:
        _request_reachable_for_selected()


func _apply_path_preview(payload: Dictionary) -> void:
    _overlay.show_path(payload)
    if not bool(payload.get("legal", false)):
        _armed_cell.clear()
        _controller.clear_command_intent()
        _hud.set_preview_text(str(payload.get("reason", "Destination is not legal")))
        return
    var path_value: Variant = payload.get("path", [])
    if typeof(path_value) != TYPE_ARRAY or (path_value as Array).is_empty():
        return
    var path: Array = path_value
    var last_value: Variant = path[path.size() - 1]
    if typeof(last_value) != TYPE_DICTIONARY:
        return
    var normalized := normalize_grid_cell(last_value as Dictionary)
    if normalized.is_empty():
        _armed_cell.clear()
        _controller.clear_command_intent()
        _hud.set_error(
            "Engine returned an invalid movement destination",
            "Path destination x/y must be integral grid coordinates",
        )
        return
    _armed_cell = normalized
    var actor_id := _state.interaction.selected_actor_id()
    var segment_text := _segment_cost_text(payload.get("segments", []))
    _hud.set_preview_text(
        "Path %d ft%s · select again or Confirm to move" % [
            int(payload.get("cost_feet", 0)),
            segment_text,
        ]
    )
    _controller.set_command_intent(
        _command(
            "tactical.move",
            actor_id,
            {"destination": _armed_cell.duplicate(true), "movement_mode": "walk"},
        ),
        "v07-move:%d:%d:%d" % [
            _state.authoritative.sequence(),
            int(_armed_cell.get("x", 0)),
            int(_armed_cell.get("y", 0)),
        ],
    )


static func normalize_grid_cell(cell: Dictionary) -> Dictionary:
    if not cell.has("x") or not cell.has("y"):
        return {}
    var x_value: Variant = cell["x"]
    var y_value: Variant = cell["y"]
    if not _is_integral_grid_number(x_value) or not _is_integral_grid_number(y_value):
        return {}
    return {"x": int(x_value), "y": int(y_value)}


static func _is_integral_grid_number(value: Variant) -> bool:
    if typeof(value) == TYPE_INT:
        return true
    if typeof(value) != TYPE_FLOAT:
        return false
    return is_equal_approx(float(value), round(float(value)))


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
