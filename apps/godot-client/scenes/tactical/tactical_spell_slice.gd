class_name TacticalSpellSlice
extends "res://scenes/tactical/tactical_vertical_slice.gd"

var _spell_state: ClientStateCoordinator
var _active_spell: Dictionary = {}
var _active_slot_level := 0
var _spell_preview_request_id := ""
var _armed_spell_targets: Array[String] = []
var _armed_spell_point: Dictionary = {}
var _spell_direction := Vector2.RIGHT

@onready var _spell_palette: SpellPalette = $HUD/SpellPalette


func _ready() -> void:
    super._ready()
    _spell_palette.visible = false
    _spell_palette.spell_selected.connect(_on_spell_selected)


func bind_client_state(state: ClientStateCoordinator) -> void:
    _unbind_spell_state()
    super.bind_client_state(state)
    _spell_state = state
    if _spell_state == null:
        _spell_palette.clear()
        _spell_palette.visible = false
        return
    _spell_state.query_completed.connect(_on_spell_query_completed)
    _spell_state.preview_completed.connect(_on_spell_preview_completed)
    _request_spells()


func _exit_tree() -> void:
    _unbind_spell_state()
    super._exit_tree()


func _request_actions() -> void:
    super._request_actions()
    _request_spells()


func _on_select_requested() -> void:
    if _active_spell.is_empty() or _controller == null:
        super._on_select_requested()
        return
    var mode := _controller.current_mode()
    var hit := _pick(get_viewport().get_mouse_position())
    if mode == InteractionModes.Mode.TARGET:
        var target_id := _actor_from_hit(hit)
        if target_id.is_empty():
            return
        if _armed_spell_targets == [target_id]:
            _controller.confirm_current_intent()
        else:
            _request_spell_preview([target_id], {})
        return
    if mode == InteractionModes.Mode.SHAPE_PREVIEW:
        var cell := _cell_from_hit(hit)
        if cell.is_empty():
            return
        if cell == _armed_spell_point:
            _controller.confirm_current_intent()
        else:
            _request_spell_preview([], cell)
        return
    super._on_select_requested()


func _on_confirm_requested(mode: int) -> void:
    if _active_spell.is_empty():
        super._on_confirm_requested(mode)
        return
    if mode == InteractionModes.Mode.TARGET:
        _hud.set_preview_text("Choose an engine-approved spell target before confirming")
    elif mode == InteractionModes.Mode.SHAPE_PREVIEW:
        _hud.set_preview_text("Choose a spell origin/area before confirming")
    else:
        _hud.set_preview_text("Wait for the authoritative spell preview before confirming")


func _on_controller_mode_changed(mode: int, mode_name: String) -> void:
    super._on_controller_mode_changed(mode, mode_name)
    if mode == InteractionModes.Mode.INSPECT or mode == InteractionModes.Mode.UI_MODAL:
        _clear_spell_intent()


func _on_command_completed(
    correlation_id: String,
    accepted: bool,
    user_message: String,
    debug_detail: String,
) -> void:
    super._on_command_completed(correlation_id, accepted, user_message, debug_detail)
    if correlation_id.begins_with("v08-spell-cast:") and accepted:
        _clear_spell_intent()
        _request_spells()


func _on_spell_selected(spell: Dictionary, slot_level: int) -> void:
    if _state == null or _controller == null or not _spell_palette.visible:
        return
    var caster_id := _state.interaction.selected_actor_id()
    if caster_id.is_empty():
        return
    _controller.clear_command_intent()
    _overlay.clear_all()
    _active_spell = spell.duplicate(true)
    _active_slot_level = slot_level
    _armed_spell_targets.clear()
    _armed_spell_point.clear()
    var target_kind := str(_active_spell.get("target_kind", "creature"))
    match target_kind:
        "self":
            if not _controller.transition_to(InteractionModes.Mode.SELECT):
                return
            _request_spell_preview([], {})
            _hud.set_preview_text("Previewing self-target spell through the engine")
        "creature":
            if not _controller.transition_to(InteractionModes.Mode.TARGET):
                return
            _hud.set_preview_text("Choose a target; range and LOS are engine-authoritative")
        "point", "area":
            if not _controller.transition_to(InteractionModes.Mode.SHAPE_PREVIEW):
                return
            _hud.set_preview_text("Choose an origin; AoE membership comes from spatial authority")
        _:
            _hud.set_error("Unsupported spell target mode", target_kind)
            _clear_spell_intent()


func _request_spells() -> void:
    if _spell_state == null:
        return
    if not _tactical.has("spellcasting"):
        _spell_palette.clear()
        _spell_palette.visible = false
        return
    _spell_palette.visible = true
    var actor_id := _spell_state.interaction.selected_actor_id()
    if actor_id.is_empty():
        _spell_palette.clear()
        return
    _spell_state.request_query(
        "spells.available",
        {"actor_id": actor_id},
        "v08-spells:%s" % actor_id,
    )


func _request_spell_preview(target_ids: Array[String], point: Dictionary) -> void:
    if _state == null or _controller == null or _active_spell.is_empty():
        return
    var caster_id := _state.interaction.selected_actor_id()
    if caster_id.is_empty():
        return
    if not _spell_preview_request_id.is_empty():
        _state.cancel_pending(_spell_preview_request_id)
    var preview := {
        "caster_id": caster_id,
        "spell_id": str(_active_spell.get("spell_id", "")),
        "slot_level": _active_slot_level,
        "target_ids": target_ids.duplicate(),
    }
    if not point.is_empty():
        preview["point"] = point.duplicate(true)
        _spell_direction = _direction_to_cell(caster_id, point)
        preview["direction"] = {
            "x": _spell_direction.x,
            "y": _spell_direction.y,
        }
    _armed_spell_targets.clear()
    _armed_spell_point.clear()
    _controller.clear_command_intent()
    _spell_preview_request_id = _state.request_preview(
        "spells.preview",
        preview,
        "v08-spell-preview:%d" % _state.interaction.generation(),
    )
    _controller.register_mode_request(_spell_preview_request_id)


func _on_spell_query_completed(
    correlation_id: String,
    _generation: int,
    payload: Dictionary,
) -> void:
    if correlation_id.begins_with("v08-spells:"):
        _spell_palette.apply_available(payload)


func _on_spell_preview_completed(
    correlation_id: String,
    _generation: int,
    payload: Dictionary,
) -> void:
    if not correlation_id.begins_with("v08-spell-preview:"):
        return
    _spell_preview_request_id = ""
    var area_value: Variant = payload.get("area", {})
    if typeof(area_value) == TYPE_DICTIONARY:
        var area: Dictionary = area_value
        if not area.is_empty():
            _overlay.show_area(area)
    if not bool(payload.get("legal", false)):
        _hud.set_preview_text(str(payload.get("reason", "Spell target is not legal")))
        return
    _armed_spell_targets = _strings(payload.get("target_ids", []))
    var point_value: Variant = payload.get("point")
    if typeof(point_value) == TYPE_DICTIONARY:
        _armed_spell_point = (point_value as Dictionary).duplicate(true)
    _show_spell_target_line()
    _arm_spell_command(payload)
    var spell_name := str(_active_spell.get("name", _active_spell.get("spell_id", "Spell")))
    _hud.set_preview_text("%s · authoritative preview legal · Confirm to cast" % spell_name)


func _arm_spell_command(preview: Dictionary) -> void:
    if _state == null or _controller == null:
        return
    var caster_id := _state.interaction.selected_actor_id()
    var payload := {
        "spell_id": str(_active_spell.get("spell_id", "")),
        "slot_level": int(preview.get("slot_level", _active_slot_level)),
        "target_ids": _armed_spell_targets.duplicate(),
    }
    if not _armed_spell_point.is_empty():
        payload["point"] = _armed_spell_point.duplicate(true)
        payload["direction"] = {"x": _spell_direction.x, "y": _spell_direction.y}
    _controller.set_command_intent(
        _command("tactical.cast_spell", caster_id, payload),
        "v08-spell-cast:%d:%s" % [
            _state.authoritative.sequence(),
            str(_active_spell.get("spell_id", "")),
        ],
    )


func _show_spell_target_line() -> void:
    if _state == null or _armed_spell_targets.is_empty():
        return
    var caster := actor_view(_state.interaction.selected_actor_id())
    var target := actor_view(_armed_spell_targets[0])
    if caster != null and target != null:
        _overlay.show_target_line(caster.global_position, target.global_position, {"legal": true})


func _direction_to_cell(caster_id: String, point: Dictionary) -> Vector2:
    var actor := _actor_data(caster_id)
    var position_value: Variant = actor.get("position", {})
    if typeof(position_value) != TYPE_DICTIONARY:
        return Vector2.RIGHT
    var origin: Dictionary = position_value
    var direction := Vector2(
        float(int(point.get("x", 0)) - int(origin.get("x", 0))),
        float(int(point.get("y", 0)) - int(origin.get("y", 0))),
    )
    return Vector2.RIGHT if direction.is_zero_approx() else direction.normalized()


func _strings(value: Variant) -> Array[String]:
    var result: Array[String] = []
    if typeof(value) != TYPE_ARRAY:
        return result
    for item in value:
        if typeof(item) == TYPE_STRING and not str(item).is_empty():
            result.append(str(item))
    return result


func _clear_spell_intent() -> void:
    _active_spell.clear()
    _active_slot_level = 0
    _armed_spell_targets.clear()
    _armed_spell_point.clear()
    _spell_preview_request_id = ""


func _unbind_spell_state() -> void:
    if _spell_state == null:
        return
    if _spell_state.query_completed.is_connected(_on_spell_query_completed):
        _spell_state.query_completed.disconnect(_on_spell_query_completed)
    if _spell_state.preview_completed.is_connected(_on_spell_preview_completed):
        _spell_state.preview_completed.disconnect(_on_spell_preview_completed)
    _spell_state = null
