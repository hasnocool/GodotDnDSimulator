extends SceneTree

var _failures := 0


func _initialize() -> void:
    call_deferred("_run")


func _run() -> void:
    var packed := load("res://ui/hud/tactical_hud.tscn") as PackedScene
    _check(packed != null, "tactical HUD scene loads")
    if packed == null:
        quit(1)
        return
    var hud = packed.instantiate()
    root.add_child(hud)
    await process_frame

    hud.call(
        "apply_selected_actor",
        {
            "actor_id": "actor:test",
            "name": "Status Tester",
            "hit_points": {"current": 12, "maximum": 18, "temporary": 3},
            "armor_class": 15,
            "conditions": [
                {"condition_id": "condition:restrained", "name": "Restrained"},
                "condition:marked",
            ],
            "resources": [
                {"resource_id": "resource:focus", "name": "Focus", "current": 1, "maximum": 2},
            ],
            "economy": {
                "action_available": false,
                "bonus_action_available": true,
                "reaction_available": true,
                "movement_remaining": 10,
            },
        },
    )
    var selected: Label = hud.get_node("SelectedPanel/SelectedMargin/SelectedVBox/SelectedLabel")
    var status: Label = hud.get_node("SelectedPanel/SelectedMargin/SelectedVBox/StatusLabel")
    _check(selected.text.contains("Temp 3"), "selected actor row shows authoritative temporary HP")
    _check(status.text.contains("Restrained"), "status row renders authoritative named condition")
    _check(status.text.contains("condition:marked"), "status row renders authoritative condition ID")
    _check(status.text.contains("Action spent"), "resource row renders spent authoritative action")
    _check(status.text.contains("Bonus ready"), "resource row renders available bonus action")
    _check(status.text.contains("Reaction ready"), "resource row renders available reaction")
    _check(status.text.contains("Focus 1/2"), "resource row renders generic authoritative resource")

    root.remove_child(hud)
    hud.queue_free()
    await process_frame
    if _failures == 0:
        print("Godot tactical HUD tests: PASS")
        quit(0)
    push_error("Godot tactical HUD tests: %d failure(s)" % _failures)
    quit(1)


func _check(condition: bool, message: String) -> void:
    if condition:
        return
    _failures += 1
    push_error("FAIL: %s" % message)
