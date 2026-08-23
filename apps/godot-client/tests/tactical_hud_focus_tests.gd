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

    await _check_button_releases_focus(
        hud.get_node("ActionPanel/ActionMargin/Actions/MoveButton") as Button,
        "Move",
    )
    await _check_button_releases_focus(
        hud.get_node("ActionPanel/ActionMargin/Actions/StrikeButton") as Button,
        "Strike",
    )
    await _check_button_releases_focus(
        hud.get_node("ActionPanel/ActionMargin/Actions/AreaButton") as Button,
        "Area Debug",
    )

    root.remove_child(hud)
    hud.queue_free()
    await process_frame

    if _failures == 0:
        print("Godot tactical HUD focus tests: PASS")
        quit(0)
    push_error("Godot tactical HUD focus tests: %d failure(s)" % _failures)
    quit(1)


func _check_button_releases_focus(button: Button, label: String) -> void:
    _check(button != null, "%s button exists" % label)
    if button == null:
        return
    button.grab_focus()
    await process_frame
    _check(button.has_focus(), "%s button can receive UI focus" % label)
    button.pressed.emit()
    await process_frame
    _check(
        not button.has_focus(),
        "%s releases UI focus so map click/confirm input can continue" % label,
    )


func _check(condition: bool, message: String) -> void:
    if condition:
        return
    _failures += 1
    push_error("FAIL: %s" % message)
