class_name SpellPalette
extends PanelContainer

signal spell_selected(spell: Dictionary, slot_level: int)

var _spell_rows: Array[Dictionary] = []

@onready var _title: Label = %SpellTitle
@onready var _slots: Label = %SlotSummary
@onready var _concentration: Label = %ConcentrationLabel
@onready var _active_effects: Label = %ActiveEffectsLabel
@onready var _spell_list: VBoxContainer = %SpellList


func apply_available(payload: Dictionary) -> void:
    _spell_rows.clear()
    _clear_buttons()
    var actor_id := str(payload.get("actor_id", ""))
    _title.text = "Spells · %s" % actor_id
    _slots.text = _slot_text(payload.get("slots", []))
    _concentration.text = _concentration_text(payload.get("concentration"))
    _active_effects.text = _active_effects_text(payload.get("active_effects", []))
    var spells_value: Variant = payload.get("spells", [])
    if typeof(spells_value) != TYPE_ARRAY:
        return
    for spell_value in spells_value:
        if typeof(spell_value) != TYPE_DICTIONARY:
            continue
        _spell_rows.append((spell_value as Dictionary).duplicate(true))
    _render_grouped_buttons()


func clear() -> void:
    _spell_rows.clear()
    _clear_buttons()
    _title.text = "Spells"
    _slots.text = ""
    _concentration.text = ""
    _active_effects.text = ""


func spell_rows() -> Array[Dictionary]:
    return _spell_rows.duplicate(true)


func group_titles() -> Array[String]:
    var titles: Array[String] = []
    for child in _spell_list.get_children():
        if child is Label and child.has_meta("spell_group"):
            titles.append((child as Label).text)
    return titles


func _render_grouped_buttons() -> void:
    var by_level: Dictionary = {}
    var unavailable: Array[Dictionary] = []
    for spell in _spell_rows:
        var levels_value: Variant = spell.get("slot_levels", [])
        if typeof(levels_value) != TYPE_ARRAY or (levels_value as Array).is_empty():
            unavailable.append(spell)
            continue
        for level_value in levels_value:
            if typeof(level_value) != TYPE_INT and typeof(level_value) != TYPE_FLOAT:
                continue
            var level := int(level_value)
            if not by_level.has(level):
                by_level[level] = []
            var rows: Array = by_level[level]
            rows.append(spell)
            by_level[level] = rows

    var levels: Array = by_level.keys()
    levels.sort()
    for level_value in levels:
        var level := int(level_value)
        _add_group_header("Cantrips" if level == 0 else "Level %d slots" % level)
        var rows: Array = by_level[level]
        for spell_value in rows:
            if typeof(spell_value) == TYPE_DICTIONARY:
                _add_spell_button(spell_value as Dictionary, level)

    if not unavailable.is_empty():
        _add_group_header("Unavailable")
        for spell in unavailable:
            var button := Button.new()
            button.text = str(spell.get("name", "Spell"))
            button.disabled = true
            button.tooltip_text = "No legal slot or preparation available"
            _spell_list.add_child(button)


func _add_group_header(text: String) -> void:
    var label := Label.new()
    label.text = text
    label.set_meta("spell_group", true)
    label.tooltip_text = "Actions grouped by engine-provided legal cast slot"
    _spell_list.add_child(label)


func _add_spell_button(spell: Dictionary, level: int) -> void:
    var button := Button.new()
    button.text = _button_text(spell, level)
    button.disabled = not bool(spell.get("castable", false))
    button.tooltip_text = _tooltip(spell, level)
    button.pressed.connect(
        func() -> void:
            spell_selected.emit(spell.duplicate(true), level)
    )
    _spell_list.add_child(button)


func _button_text(spell: Dictionary, level: int) -> String:
    var suffix := "Cantrip" if level == 0 else "Slot %d" % level
    return "%s · %s" % [str(spell.get("name", "Spell")), suffix]


func _tooltip(spell: Dictionary, level: int) -> String:
    var parts: Array[String] = [
        "Level %d" % int(spell.get("level", 0)),
        str(spell.get("resolution", "automatic")),
        str(spell.get("target_kind", "creature")),
        "range %d ft" % int(spell.get("range_feet", 0)),
    ]
    if bool(spell.get("concentration", false)):
        parts.append("concentration")
    var duration_value: Variant = spell.get("duration_rounds")
    if duration_value != null:
        parts.append("duration %d rounds" % int(duration_value))
    var area_shape := str(spell.get("area_shape", ""))
    if not area_shape.is_empty():
        parts.append("%s %d ft" % [area_shape, int(spell.get("area_size_feet", 0))])
    if level > int(spell.get("level", 0)):
        parts.append("upcast at %d" % level)
    return " · ".join(parts)


func _slot_text(value: Variant) -> String:
    if typeof(value) != TYPE_ARRAY:
        return ""
    var parts: Array[String] = []
    for slot_value in value:
        if typeof(slot_value) != TYPE_DICTIONARY:
            continue
        var slot: Dictionary = slot_value
        parts.append(
            "L%d %d/%d" % [
                int(slot.get("level", 0)),
                int(slot.get("current", 0)),
                int(slot.get("maximum", 0)),
            ]
        )
    return "Slots · %s" % " · ".join(parts) if not parts.is_empty() else "Cantrips only"


func _concentration_text(value: Variant) -> String:
    if value == null:
        return "Concentration · none"
    if typeof(value) != TYPE_DICTIONARY:
        return ""
    var concentration: Dictionary = value
    var rounds: Variant = concentration.get("remaining_rounds")
    var suffix := ""
    if rounds != null:
        suffix = " · %d rounds" % int(rounds)
    return "Concentration · %s%s" % [str(concentration.get("spell_id", "")), suffix]


func _active_effects_text(value: Variant) -> String:
    if typeof(value) != TYPE_ARRAY or (value as Array).is_empty():
        return "Active effects · none"
    var parts: Array[String] = []
    for effect_value in value:
        if typeof(effect_value) != TYPE_DICTIONARY:
            continue
        var effect: Dictionary = effect_value
        var text := str(effect.get("spell_id", effect.get("effect_id", "effect")))
        var rounds: Variant = effect.get("remaining_rounds")
        if rounds != null:
            text += " · %d rounds" % int(rounds)
        if bool(effect.get("concentration", false)):
            text += " · concentration"
        parts.append(text)
    return "Active effects · %s" % "; ".join(parts) if not parts.is_empty() else "Active effects · none"


func _clear_buttons() -> void:
    for child in _spell_list.get_children():
        _spell_list.remove_child(child)
        child.queue_free()
