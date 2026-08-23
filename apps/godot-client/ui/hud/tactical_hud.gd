class_name TacticalHUD
extends Control

signal move_requested()
signal strike_requested()
signal end_turn_requested()
signal area_debug_requested()

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


func _ready() -> void:
    _move_button.pressed.connect(func() -> void: move_requested.emit())
    _strike_button.pressed.connect(func() -> void: strike_requested.emit())
    _end_turn_button.pressed.connect(func() -> void: end_turn_requested.emit())
    _area_button.pressed.connect(func() -> void: area_debug_requested.emit())


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
    apply_selected_actor(_actor_by_id(tactical, selected_actor_id))


func apply_selected_actor(actor: Dictionary) -> void:
    if actor.is_empty():
        _selected_label.text = "No actor selected"
        _status_label.text = "Conditions · none\nResources · —"
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
    _status_label.text = "%s\n%s" % [
        _conditions_text(actor.get("conditions", [])),
        _resources_text(actor, economy),
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


func set_preview_text(text: String) -> void:
    _preview_label.text = text


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
