class_name SpellPalette
extends PanelContainer

signal spell_selected(spell: Dictionary, slot_level: int)

var _spell_rows: Array[Dictionary] = []

@onready var _title: Label = %SpellTitle
@onready var _slots: Label = %SlotSummary
@onready var _concentration: Label = %ConcentrationLabel
@onready var _spell_list: VBoxContainer = %SpellList


func apply_available(payload: Dictionary) -> void:
    _clear_buttons()
    var actor_id := str(payload.get("actor_id", ""))
    _title.text = "Spells · %s" % actor_id
    _slots.text = _slot_text(payload.get("slots", []))
    _concentration.text = _concentration_text(payload.get("concentration"))
    var spells_value: Variant = payload.get("spells", [])
    if typeof(spells_value) != TYPE_ARRAY:
        return
    for spell_value in spells_value:
        if typeof(spell_value) != TYPE_DICTIONARY:
            continue
        var spell: Dictionary = (spell_value as Dictionary).duplicate(true)
        _spell_rows.append(spell)
        _add_spell_buttons(spell)


func clear() -> void:
    _spell_rows.clear()
    _clear_buttons()
    _title.text = "Spells"
    _slots.text = ""
    _concentration.text = ""


func spell_rows() -> Array[Dictionary]:
    return _spell_rows.duplicate(true)


func _add_spell_buttons(spell: Dictionary) -> void:
    var levels_value: Variant = spell.get("slot_levels", [])
    if typeof(levels_value) != TYPE_ARRAY:
        return
    var levels: Array = levels_value
    if levels.is_empty():
        var unavailable := Button.new()
        unavailable.text = "%s · unavailable" % str(spell.get("name", "Spell"))
        unavailable.disabled = true
        unavailable.tooltip_text = "No legal slot or preparation available"
        _spell_list.add_child(unavailable)
        return
    for level_value in levels:
        if typeof(level_value) != TYPE_INT and typeof(level_value) != TYPE_FLOAT:
            continue
        var level := int(level_value)
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


func _clear_buttons() -> void:
    for child in _spell_list.get_children():
        _spell_list.remove_child(child)
        child.queue_free()
