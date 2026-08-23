extends SceneTree

var _failures := 0
var _pressed := false


func _initialize() -> void:
    call_deferred("_run")


func _run() -> void:
    var fixture := Control.new()
    fixture.name = "AutomationFixture"
    fixture.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    root.add_child(fixture)

    var button := Button.new()
    button.name = "ActionButton"
    button.text = "Human-like action"
    button.position = Vector2(20, 20)
    button.size = Vector2(180, 44)
    button.pressed.connect(func() -> void: _pressed = true)
    fixture.add_child(button)

    var line_edit := LineEdit.new()
    line_edit.name = "NameField"
    line_edit.position = Vector2(20, 84)
    line_edit.size = Vector2(220, 40)
    fixture.add_child(line_edit)
    await process_frame

    var snapshot: Dictionary = UiAutomation.dispatch_for_test("ui.snapshot")
    _check(bool(snapshot.get("ok", false)), "UI snapshot request succeeds while network API is disabled")
    var snapshot_result: Dictionary = snapshot.get("result", {})
    var controls: Array = snapshot_result.get("controls", [])
    _check(
        controls.any(
            func(row: Variant) -> bool:
                return typeof(row) == TYPE_DICTIONARY and row.get("path") == str(button.get_path())
        ),
        "UI snapshot exposes visible button path",
    )
    _check(
        not str(snapshot_result.get("client_log_path", "")).is_empty(),
        "UI snapshot exposes persistent client log path",
    )

    var focus: Dictionary = UiAutomation.dispatch_for_test(
        "ui.focus",
        {"path": str(button.get_path())},
    )
    _check(bool(focus.get("ok", false)), "automation can focus a visible control")
    _check(button.has_focus(), "focused control owns Godot GUI focus")

    var activate: Dictionary = UiAutomation.dispatch_for_test(
        "ui.activate",
        {"path": str(button.get_path())},
    )
    _check(bool(activate.get("ok", false)), "automation can activate a visible button")
    await process_frame
    _check(_pressed, "button activation travels through viewport input")

    var edit: Dictionary = UiAutomation.dispatch_for_test(
        "ui.set_text",
        {"path": str(line_edit.get_path()), "text": "Agent Debugger"},
    )
    _check(bool(edit.get("ok", false)), "automation can edit a LineEdit")
    _check(line_edit.text == "Agent Debugger", "automation edit updates live UI control")

    var invalid: Dictionary = UiAutomation.dispatch_for_test(
        "ui.inspect",
        {"path": "/root/does-not-exist"},
    )
    _check(not bool(invalid.get("ok", true)), "unknown UI paths fail closed")

    var logs: Dictionary = UiAutomation.dispatch_for_test("ui.logs", {"limit": 10})
    _check(bool(logs.get("ok", false)), "automation can retrieve structured client diagnostics")

    root.remove_child(fixture)
    fixture.queue_free()
    await process_frame
    if _failures == 0:
        print("Godot UI automation tests: PASS")
        quit(0)
    push_error("Godot UI automation tests: %d failure(s)" % _failures)
    quit(1)


func _check(condition: bool, message: String) -> void:
    if condition:
        return
    _failures += 1
    push_error("FAIL: %s" % message)
