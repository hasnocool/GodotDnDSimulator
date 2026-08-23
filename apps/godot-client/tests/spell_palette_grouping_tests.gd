extends SceneTree

const SpellPaletteScene = preload("res://ui/actions/spell_palette.tscn")

var _failures := 0


func _initialize() -> void:
    call_deferred("_run")


func _run() -> void:
    var palette = SpellPaletteScene.instantiate()
    root.add_child(palette)
    await process_frame
    palette.apply_available(
        {
            "actor_id": "actor:caster",
            "slots": [
                {"level": 1, "current": 2, "maximum": 3},
                {"level": 2, "current": 1, "maximum": 1},
            ],
            "concentration": null,
            "active_effects": [],
            "spells": [
                {
                    "spell_id": "spell:cantrip",
                    "name": "Arc Spark",
                    "level": 0,
                    "castable": true,
                    "slot_levels": [0],
                    "resolution": "attack",
                    "target_kind": "creature",
                    "range_feet": 60,
                    "concentration": false,
                },
                {
                    "spell_id": "spell:scaling",
                    "name": "Echo Burst",
                    "level": 1,
                    "castable": true,
                    "slot_levels": [1, 2],
                    "resolution": "save",
                    "target_kind": "area",
                    "range_feet": 30,
                    "area_shape": "sphere",
                    "area_size_feet": 10,
                    "concentration": false,
                },
                {
                    "spell_id": "spell:blocked",
                    "name": "Blocked Spell",
                    "level": 1,
                    "castable": false,
                    "slot_levels": [],
                    "resolution": "automatic",
                    "target_kind": "self",
                    "range_feet": 0,
                    "concentration": false,
                },
            ],
        }
    )
    _check(
        palette.group_titles() == ["Cantrips", "Level 1 slots", "Level 2 slots", "Unavailable"],
        "spell palette groups actions by authoritative legal slot level",
    )
    var spell_list: VBoxContainer = palette.get_node("Margin/VBox/SpellList")
    var tooltips: Array[String] = []
    for child in spell_list.get_children():
        if child is Button:
            tooltips.append((child as Button).tooltip_text)
    _check(
        tooltips.any(func(text: String) -> bool: return text.contains("upcast at 2")),
        "upcast button tooltip preserves authoritative slot-level context",
    )
    _check(
        tooltips.any(func(text: String) -> bool: return text.contains("sphere 10 ft")),
        "spell tooltip exposes engine-provided area metadata",
    )
    root.remove_child(palette)
    palette.queue_free()
    await process_frame

    if _failures == 0:
        print("Godot spell palette grouping tests: PASS")
        quit(0)
    push_error("Godot spell palette grouping tests: %d failure(s)" % _failures)
    quit(1)


func _check(condition: bool, message: String) -> void:
    if condition:
        return
    _failures += 1
    push_error("FAIL: %s" % message)
