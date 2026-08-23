class_name TacticalHUD
extends Control

signal move_requested()
signal strike_requested()
signal end_turn_requested()
signal area_debug_requested()
signal shape_kind_requested()
signal shape_rotate_requested()

var _log_lines: Array[String] = []

@onready var _round_label: Label = %RoundLabel
@onready var _turn_label: Label = %TurnLabel
@onready var _initiative_label: Label = %InitiativeLabel
@onready var _selected_label: Label = %SelectedLabel
@onready var _status_label: Label = %StatusLabel
@onready var _preview_label: Label = %PreviewLabel
@onready var _log_label: Label = %LogLabel
@onready var _move_button: Button = %MoveButton
@onready var _strike_button: Button = %StrikeButton
@onready var _end_turn_button: Button = %EndTurnButton
@onready var _area_button: Button = %AreaButton
@onready var _shape_kind_button: Button = %ShapeKindButton
@onready var _shape_rotate_button: Button = %ShapeRotateButton


func _ready() -> void:
    _move_button.pressed.connect(_on_move_button_pressed)
    _strike_button.pressed.connect(_on_strike_button_pressed)
    _end_turn_button.pressed.connect(_on_end_turn_button_pressed)
    _area_button.pressed.connect(_on_area_button_pressed)
    _shape_kind_button.pressed.connect(_on_shape_kind_button_pressed)
    _shape_rotate_button.pressed.connect(_on_shape_rotate_button_pressed)


func apply_tactical_state(tactical: Dictionary, selected_actor_id: String) -> void:
    _round_label.text = "Round %d" % int(tactical.get("round_number", 0))
    var current_actor_id := str(tactical.get("current_actor_id", ""))
    var current_actor := _actor_by_id(tactical, current_actor_id)
    _turn_label.text = "Turn · %s" % str(current_actor.get("name", current_actor_id))
    var initiative_names: Array[String] = []
    var initiative_value: Variant = tactical.get("initiative", [])
    if typeof(initiative_value) == TYPE_ARRAY:
        for row_value in initiative_value:
            if typeof(row_value) != TYPE_DICTIONARY:
                continue
            var row: Dictionary = row_value
            var actor_id := str(row.get("actor_id", ""))
            var actor := _actor_by_id(tactical, actor_id)
            initiative_names.append(
                "%s (%d)" % [str(actor.get("name", actor_id)), int(row.get("total", 0))]
            )
    _initiative_label.text = " → ".join(initiative_names)
    var spellcasting_value: Variant = tactical.get("spellcasting", {})
    var spellcasting: Dictionary = (
        spellcasting_value if typeof(spellcasting_value) == TYPE_DICTIONARY else {}
    )
    apply_selected_actor(
        _actor_by_id(tactical, selected_actor_id),
        spellcasting,
    )


func apply_selected_actor(actor: Dictionary, spellcasting: Dictionary = {}) -> void:
    if actor.is_empty():
        _selected_label.text = "No actor selected"
        _status_label.text = "Conditions · none\nResources · —\nEffects · none"
        return
    var hp_value: Variant = actor.get("hit_points", {})
    var hp: Dictionary = hp_value if typeof(hp_value) == TYPE_DICTIONARY else {}
    var economy_value: Variant = actor.get("economy", {})
    var economy: Dictionary = (
        economy_value if typeof(economy_value) == TYPE_DICTIONARY else {}
    )
    var temporary := int(hp.get("temporary", 0))
    var temp_text := "" if temporary <= 0 else " · Temp %d" % temporary
    _selected_label.text = "%s\nHP %d/%d%s · AC %d · Move %d ft" % [
        str(actor.get("name", actor.get("actor_id", ""))),
        int(hp.get("current", 0)),
        int(hp.get("maximum", 0)),
        temp_text,
        int(actor.get("armor_class", 0)),
        int(economy.get("movement_remaining", 0)),
    ]
    _status_label.text = "%s\n%s\n%s" % [
        _conditions_text(actor.get("conditions", [])),
        _resources_text(actor, economy),
        _effects_text(str(actor.get("actor_id", "")), spellcasting),
    ]


func apply_actions(payload: Dictionary) -> void:
    var actions_value: Variant = payload.get("actions", [])
    if typeof(actions_value) != TYPE_ARRAY:
        return
    for action_value in actions_value:
        if typeof(action_value) != TYPE_DICTIONARY:
            continue
        var action: Dictionary = action_value
        var action_id := str(action.get("action_id", ""))
        var enabled := bool(action.get("enabled", false))
        var reason := str(action.get("reason", ""))
        var button := _button_for_action(action_id)
        if button == null:
            continue
        button.disabled = not enabled
        button.tooltip_text = reason


func set_shape_debug_state(kind: String, direction: Vector2) -> void:
    _shape_kind_button.text = "Shape: %s" % kind.capitalize()
    _shape_kind_button.tooltip_text = "Cycle sphere, cylinder, cone, and line"
    _shape_rotate_button.text = "Rotate %s" % _direction_label(direction)
    _shape_rotate_button.tooltip_text = "Rotate cone/line direction by 90 degrees"


func set_preview_text(text: String) -> void:
    _preview_label.text = text


func preview_text() -> String:
    return _preview_label.text


func status_text() -> String:
    return _status_label.text


func set_error(user_message: String, debug_detail: String = "") -> void:
    _preview_label.text = (
        user_message
        if debug_detail.is_empty()
        else "%s\n%s" % [user_message, debug_detail]
    )


func append_log(text: String) -> void:
    if text.is_empty():
        return
    _log_lines.append(text)
    if _log_lines.size() > 8:
        _log_lines.pop_front()
    _log_label.text = "\n".join(_log_lines)


func log_text() -> String:
    return _log_label.text


func _on_move_button_pressed() -> void:
    _release_button_focus(_move_button)
    move_requested.emit()


func _on_strike_button_pressed() -> void:
    _release_button_focus(_strike_button)
    strike_requested.emit()


func _on_end_turn_button_pressed() -> void:
    _release_button_focus(_end_turn_button)
    end_turn_requested.emit()


func _on_area_button_pressed() -> void:
    _release_button_focus(_area_button)
    area_debug_requested.emit()


func _on_shape_kind_button_pressed() -> void:
    _release_button_focus(_shape_kind_button)
    shape_kind_requested.emit()


func _on_shape_rotate_button_pressed() -> void:
    _release_button_focus(_shape_rotate_button)
    shape_rotate_requested.emit()


func _release_button_focus(button: BaseButton) -> void:
    if button.has_focus():
        button.release_focus()


func _conditions_text(value: Variant) -> String:
    if typeof(value) != TYPE_ARRAY or (value as Array).is_empty():
        return "Conditions · none"
    var rows: Array[String] = []
    for condition_value in value:
        if typeof(condition_value) == TYPE_DICTIONARY:
            var condition: Dictionary = condition_value
            rows.append(
                str(
                    condition.get(
                        "name",
                        condition.get("condition_id", condition.get("id", "condition")),
                    )
                )
            )
        else:
            rows.append(str(condition_value))
    return "Conditions · %s" % ", ".join(rows)


func _resources_text(actor: Dictionary, economy: Dictionary) -> String:
    var rows: Array[String] = [
        "Action %s" % _availability(bool(economy.get("action_available", false))),
        "Bonus %s" % _availability(bool(economy.get("bonus_action_available", false))),
        "Reaction %s" % _availability(bool(economy.get("reaction_available", false))),
    ]
    var resources_value: Variant = actor.get("resources", [])
    if typeof(resources_value) == TYPE_ARRAY:
        for resource_value in resources_value:
            if typeof(resource_value) != TYPE_DICTIONARY:
                continue
            var resource: Dictionary = resource_value
            rows.append(
                "%s %d/%d" % [
                    str(resource.get("name", resource.get("resource_id", "Resource"))),
                    int(resource.get("current", 0)),
                    int(resource.get("maximum", 0)),
                ]
            )
    return "Resources · %s" % " · ".join(rows)


func _effects_text(actor_id: String, spellcasting: Dictionary) -> String:
    if actor_id.is_empty():
        return "Effects · none"
    var rows: Array[String] = []
    var effects_value: Variant = spellcasting.get("active_effects", [])
    if typeof(effects_value) == TYPE_ARRAY:
        for effect_value in effects_value:
            if typeof(effect_value) != TYPE_DICTIONARY:
                continue
            var effect: Dictionary = effect_value
            var target_ids_value: Variant = effect.get("target_ids", [])
            var target_ids: Array = (
                target_ids_value if typeof(target_ids_value) == TYPE_ARRAY else []
            )
            if str(effect.get("caster_id", "")) != actor_id and not target_ids.has(actor_id):
                continue
            var mode := "concentration" if bool(effect.get("concentration", false)) else "ongoing"
            rows.append(
                "%s · %s · %d round(s)" % [
                    str(effect.get("spell_id", effect.get("effect_id", "effect"))),
                    mode,
                    int(effect.get("remaining_rounds", 0)),
                ]
            )
    return "Effects · %s" % ("none" if rows.is_empty() else " · ".join(rows))


func _direction_label(direction: Vector2) -> String:
    if absf(direction.x) >= absf(direction.y):
        return "E" if direction.x >= 0.0 else "W"
    return "S" if direction.y >= 0.0 else "N"


func _availability(available: bool) -> String:
    return "ready" if available else "spent"


func _actor_by_id(tactical: Dictionary, actor_id: String) -> Dictionary:
    if actor_id.is_empty():
        return {}
    var actors_value: Variant = tactical.get("actors", [])
    if typeof(actors_value) != TYPE_ARRAY:
        return {}
    for actor_value in actors_value:
        if typeof(actor_value) != TYPE_DICTIONARY:
            continue
        var actor: Dictionary = actor_value
        if str(actor.get("actor_id", "")) == actor_id:
            return actor
    return {}


func _button_for_action(action_id: String) -> Button:
    match action_id:
        "move":
            return _move_button
        "training_strike":
            return _strike_button
        "end_turn":
            return _end_turn_button
        _:
            return null
