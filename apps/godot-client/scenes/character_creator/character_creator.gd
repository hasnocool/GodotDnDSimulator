class_name CharacterCreatorView
extends CanvasLayer

signal close_requested()

const ABILITIES := [
    "strength",
    "dexterity",
    "constitution",
    "intelligence",
    "wisdom",
    "charisma",
]

var _state: ClientStateCoordinator
var _schema: Dictionary = {}
var _steps: Array[String] = []
var _step_index := 0
var _selected_choice_ids: Array[String] = []
var _ability_scores: Dictionary = {}
var _created_actor_id := ""
var _level_choice_ids: Array[String] = []

@onready var _step_title: Label = %StepTitle
@onready var _step_counter: Label = %StepCounter
@onready var _options: VBoxContainer = %Options
@onready var _actor_id: LineEdit = %ActorId
@onready var _name: LineEdit = %CharacterName
@onready var _biography: TextEdit = %Biography
@onready var _personality: TextEdit = %Personality
@onready var _appearance: VBoxContainer = %AppearanceFields
@onready var _status: Label = %Status
@onready var _back: Button = %Back
@onready var _next: Button = %Next
@onready var _create: Button = %Create
@onready var _level_up: Button = %LevelUp
@onready var _close: Button = %Close


func _ready() -> void:
    _back.pressed.connect(_previous_step)
    _next.pressed.connect(_next_step)
    _create.pressed.connect(_submit_create)
    _level_up.pressed.connect(_request_level_up_choices)
    _close.pressed.connect(func() -> void: close_requested.emit())
    _create.disabled = true
    _level_up.visible = false


func bind_client_state(state: ClientStateCoordinator) -> void:
    _unbind_state()
    _state = state
    if _state == null:
        return
    _state.query_completed.connect(_on_query_completed)
    _state.command_payload_received.connect(_on_command_payload)
    _state.command_completed.connect(_on_command_completed)
    _request_schema()


func show_creator() -> void:
    visible = true
    _request_schema()


func hide_creator() -> void:
    visible = false


func creator_schema() -> Dictionary:
    return _schema.duplicate(true)


func selected_choice_ids() -> Array[String]:
    return _selected_choice_ids.duplicate()


func current_step() -> String:
    if _steps.is_empty():
        return ""
    return _steps[_step_index]


func build_draft() -> Dictionary:
    return {
        "actor_id": _actor_id.text.strip_edges(),
        "name": _name.text.strip_edges(),
        "selected_choice_ids": _selected_choice_ids.duplicate(),
        "ability_method_id": _ability_method_id(),
        "ability_scores": _ability_scores.duplicate(true),
        "appearance": _appearance_values(),
        "biography": _biography.text,
        "personality": _personality.text,
    }


func apply_schema(payload: Dictionary) -> void:
    _schema = payload.duplicate(true)
    _steps.clear()
    var steps_value: Variant = _schema.get("steps", [])
    if typeof(steps_value) == TYPE_ARRAY:
        for step_value in steps_value:
            _steps.append(str(step_value))
    _initialize_abilities()
    _build_appearance_fields()
    _step_index = clampi(_step_index, 0, maxi(0, _steps.size() - 1))
    _render_step()


func apply_preview(payload: Dictionary) -> void:
    var legal := bool(payload.get("legal", false))
    _create.disabled = not legal or current_step() != "review"
    if legal:
        var summary: Dictionary = payload.get("summary", {})
        _status.text = _summary_text(summary)
        return
    var errors_value: Variant = payload.get("errors", [])
    var errors: Array[String] = []
    if typeof(errors_value) == TYPE_ARRAY:
        for error_value in errors_value:
            errors.append(str(error_value))
    _status.text = "Engine validation: %s" % "; ".join(errors)


func _request_schema() -> void:
    if _state == null:
        return
    _state.request_query("characters.creator.schema", {}, "creator:schema")


func _request_preview() -> void:
    if _state == null or _schema.is_empty():
        return
    _state.request_query(
        "characters.creator.preview",
        {"draft": build_draft()},
        "creator:preview",
    )


func _render_step() -> void:
    _clear_options()
    if _steps.is_empty():
        _step_title.text = "Character Creator"
        _step_counter.text = ""
        return
    var step := current_step()
    _step_title.text = step.replace("_", " ").capitalize()
    _step_counter.text = "%d / %d" % [_step_index + 1, _steps.size()]
    _back.disabled = _step_index == 0
    _next.disabled = _step_index >= _steps.size() - 1
    _create.visible = step == "review"
    _actor_id.visible = step == "identity"
    _name.visible = step == "identity"
    _biography.visible = step == "biography"
    _personality.visible = step == "biography"
    _appearance.visible = step == "appearance"
    match step:
        "species", "background", "class", "skills", "equipment", "spells_features":
            _render_choice_step(step)
        "abilities":
            _render_abilities()
        "review":
            _request_preview()
        _:
            _status.text = "Enter %s information." % step.replace("_", " ")


func _render_choice_step(step: String) -> void:
    var choices_value: Variant = _schema.get("choices", [])
    if typeof(choices_value) != TYPE_ARRAY:
        return
    var choices_by_id: Dictionary = {}
    for choice_value in choices_value:
        if typeof(choice_value) == TYPE_DICTIONARY:
            var choice: Dictionary = choice_value
            choices_by_id[str(choice.get("choice_id", ""))] = choice
    var groups_value: Variant = _schema.get("groups", [])
    if typeof(groups_value) != TYPE_ARRAY:
        return
    for group_value in groups_value:
        if typeof(group_value) != TYPE_DICTIONARY:
            continue
        var group: Dictionary = group_value
        if str(group.get("step", "")) != step:
            continue
        var title := Label.new()
        title.text = "%s · choose %d..%d" % [
            str(group.get("group_id", "group")),
            int(group.get("minimum", 0)),
            int(group.get("maximum", 0)),
        ]
        _options.add_child(title)
        var ids_value: Variant = group.get("choice_ids", [])
        if typeof(ids_value) != TYPE_ARRAY:
            continue
        for choice_id_value in ids_value:
            var choice_id := str(choice_id_value)
            if not choices_by_id.has(choice_id):
                continue
            var choice: Dictionary = choices_by_id[choice_id]
            var check := CheckBox.new()
            check.text = str(choice.get("name", choice_id))
            var description := str(choice.get("description", ""))
            if not description.is_empty():
                check.tooltip_text = description
            check.button_pressed = _selected_choice_ids.has(choice_id)
            check.toggled.connect(
                func(enabled: bool) -> void:
                    _set_choice_selected(choice_id, enabled)
            )
            _options.add_child(check)


func _render_abilities() -> void:
    for ability in ABILITIES:
        var row := HBoxContainer.new()
        var label := Label.new()
        label.text = ability.capitalize()
        label.custom_minimum_size.x = 140.0
        row.add_child(label)
        var selector := OptionButton.new()
        var policy_values := _ability_policy_values()
        for value in policy_values:
            selector.add_item(str(value), value)
        var selected_value := int(_ability_scores.get(ability, 10))
        for index in range(selector.item_count):
            if selector.get_item_id(index) == selected_value:
                selector.select(index)
                break
        selector.item_selected.connect(
            func(index: int) -> void:
                _ability_scores[ability] = selector.get_item_id(index)
                _request_preview()
        )
        row.add_child(selector)
        _options.add_child(row)


func _set_choice_selected(choice_id: String, enabled: bool) -> void:
    if enabled and not _selected_choice_ids.has(choice_id):
        _selected_choice_ids.append(choice_id)
    elif not enabled:
        _selected_choice_ids.erase(choice_id)
    _selected_choice_ids.sort()
    _request_preview()


func _initialize_abilities() -> void:
    if not _ability_scores.is_empty():
        return
    var values := _ability_policy_values()
    for index in range(mini(ABILITIES.size(), values.size())):
        _ability_scores[ABILITIES[index]] = values[index]


func _ability_policy_values() -> Array[int]:
    var result: Array[int] = []
    var policies_value: Variant = _schema.get("ability_policies", [])
    if typeof(policies_value) != TYPE_ARRAY or policies_value.is_empty():
        return result
    var policy_value: Variant = policies_value[0]
    if typeof(policy_value) != TYPE_DICTIONARY:
        return result
    var values_value: Variant = (policy_value as Dictionary).get("values", [])
    if typeof(values_value) == TYPE_ARRAY:
        for value in values_value:
            result.append(int(value))
    return result


func _ability_method_id() -> String:
    var policies_value: Variant = _schema.get("ability_policies", [])
    if typeof(policies_value) != TYPE_ARRAY or policies_value.is_empty():
        return ""
    var policy_value: Variant = policies_value[0]
    if typeof(policy_value) != TYPE_DICTIONARY:
        return ""
    return str((policy_value as Dictionary).get("method_id", ""))


func _build_appearance_fields() -> void:
    for child in _appearance.get_children():
        child.queue_free()
    var fields_value: Variant = _schema.get("appearance_fields", [])
    if typeof(fields_value) != TYPE_ARRAY:
        return
    for field_value in fields_value:
        var key := str(field_value)
        var row := HBoxContainer.new()
        var label := Label.new()
        label.text = key.capitalize()
        label.custom_minimum_size.x = 120.0
        row.add_child(label)
        var edit := LineEdit.new()
        edit.name = key
        edit.set_meta("appearance_key", key)
        edit.size_flags_horizontal = Control.SIZE_EXPAND_FILL
        row.add_child(edit)
        _appearance.add_child(row)


func _appearance_values() -> Dictionary:
    var result: Dictionary = {}
    for row in _appearance.get_children():
        for child in row.get_children():
            if child is LineEdit and child.has_meta("appearance_key"):
                result[str(child.get_meta("appearance_key"))] = child.text.strip_edges()
    return result


func _next_step() -> void:
    if _steps.is_empty() or _step_index >= _steps.size() - 1:
        return
    _step_index += 1
    _render_step()


func _previous_step() -> void:
    if _step_index <= 0:
        return
    _step_index -= 1
    _render_step()


func _submit_create() -> void:
    if _state == null or _create.disabled:
        return
    var state_view := _state.authoritative.state_view()
    var actor_id := _actor_id.text.strip_edges()
    var command := {
        "command_id": "command:creator-%d" % Time.get_ticks_msec(),
        "campaign_id": str(state_view.get("campaign_id", "campaign:local-dev")),
        "session_id": str(state_view.get("session_id", "session:local-dev")),
        "command_type": "characters.create",
        "payload": build_draft(),
        "version": 1,
        "actor_id": actor_id,
        "expected_sequence": _state.authoritative.sequence(),
    }
    _state.submit_command(command, "creator:create")


func _request_level_up_choices() -> void:
    if _state == null or _created_actor_id.is_empty():
        return
    _state.request_query(
        "characters.levelup.choices",
        {"actor_id": _created_actor_id},
        "creator:levelup-choices",
    )


func _render_level_choices(payload: Dictionary) -> void:
    _clear_options()
    _level_choice_ids.clear()
    _step_title.text = "Level Up"
    var choices_value: Variant = payload.get("choices", [])
    if typeof(choices_value) != TYPE_ARRAY:
        return
    for choice_value in choices_value:
        if typeof(choice_value) != TYPE_DICTIONARY:
            continue
        var choice: Dictionary = choice_value
        var choice_id := str(choice.get("choice_id", ""))
        var check := CheckBox.new()
        check.text = str(choice.get("name", choice_id))
        check.toggled.connect(
            func(enabled: bool) -> void:
                if enabled and not _level_choice_ids.has(choice_id):
                    _level_choice_ids.append(choice_id)
                elif not enabled:
                    _level_choice_ids.erase(choice_id)
        )
        _options.add_child(check)
    var confirm := Button.new()
    confirm.text = "Apply Level Up"
    confirm.pressed.connect(_submit_level_up)
    _options.add_child(confirm)


func _submit_level_up() -> void:
    if _state == null or _created_actor_id.is_empty():
        return
    var state_view := _state.authoritative.state_view()
    var command := {
        "command_id": "command:levelup-%d" % Time.get_ticks_msec(),
        "campaign_id": str(state_view.get("campaign_id", "campaign:local-dev")),
        "session_id": str(state_view.get("session_id", "session:local-dev")),
        "command_type": "characters.level_up",
        "payload": {
            "actor_id": _created_actor_id,
            "selected_choice_ids": _level_choice_ids.duplicate(),
        },
        "version": 1,
        "actor_id": _created_actor_id,
        "expected_sequence": _state.authoritative.sequence(),
    }
    _state.submit_command(command, "creator:levelup")


func _on_query_completed(correlation_id: String, _generation: int, payload: Dictionary) -> void:
    match correlation_id:
        "creator:schema":
            apply_schema(payload)
        "creator:preview":
            apply_preview(payload)
        "creator:levelup-choices":
            _render_level_choices(payload)


func _on_command_payload(correlation_id: String, payload: Dictionary) -> void:
    if correlation_id not in ["creator:create", "creator:levelup"]:
        return
    var result_value: Variant = payload.get("result", {})
    if typeof(result_value) != TYPE_DICTIONARY:
        return
    var record_value: Variant = (result_value as Dictionary).get("record", {})
    if typeof(record_value) != TYPE_DICTIONARY:
        return
    var record: Dictionary = record_value
    var actor_value: Variant = record.get("actor", {})
    if typeof(actor_value) != TYPE_DICTIONARY:
        return
    var actor: Dictionary = actor_value
    _created_actor_id = str(actor.get("actor_id", ""))
    _status.text = "Saved %s · level %d" % [
        str(actor.get("name", _created_actor_id)),
        int(actor.get("level", 1)),
    ]
    _level_up.visible = not _created_actor_id.is_empty()


func _on_command_completed(
    correlation_id: String,
    accepted: bool,
    user_message: String,
    debug_detail: String,
) -> void:
    if not correlation_id.begins_with("creator:"):
        return
    if not accepted:
        _status.text = "%s · %s" % [user_message, debug_detail]


func _summary_text(summary: Dictionary) -> String:
    if summary.is_empty():
        return "Ready for engine validation."
    return "%s · %s · %s · %s" % [
        str(summary.get("name", "Character")),
        str(summary.get("species_id", "")),
        str(summary.get("background_id", "")),
        str(summary.get("class_id", "")),
    ]


func _clear_options() -> void:
    for child in _options.get_children():
        _options.remove_child(child)
        child.queue_free()


func _unbind_state() -> void:
    if _state == null:
        return
    if _state.query_completed.is_connected(_on_query_completed):
        _state.query_completed.disconnect(_on_query_completed)
    if _state.command_payload_received.is_connected(_on_command_payload):
        _state.command_payload_received.disconnect(_on_command_payload)
    if _state.command_completed.is_connected(_on_command_completed):
        _state.command_completed.disconnect(_on_command_completed)
    _state = null
