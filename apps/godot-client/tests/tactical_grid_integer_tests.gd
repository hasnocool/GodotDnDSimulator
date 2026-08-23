extends SceneTree

const PlayableSlice = preload("res://scenes/tactical/tactical_playable_slice.gd")

var _failures := 0


func _initialize() -> void:
    call_deferred("_run")


func _run() -> void:
    var normalized := PlayableSlice.normalize_grid_cell({"x": 2.0, "y": 3.0})
    _check(normalized == {"x": 2, "y": 3}, "integral float coordinates preserve values")
    _check(typeof(normalized.get("x")) == TYPE_INT, "normalized x is a Godot integer")
    _check(typeof(normalized.get("y")) == TYPE_INT, "normalized y is a Godot integer")

    var decoded_value: Variant = JSON.parse_string("{\"x\":4,\"y\":5}")
    _check(typeof(decoded_value) == TYPE_DICTIONARY, "JSON coordinate object decodes")
    if typeof(decoded_value) == TYPE_DICTIONARY:
        var decoded := PlayableSlice.normalize_grid_cell(decoded_value as Dictionary)
        _check(decoded == {"x": 4, "y": 5}, "JSON coordinates normalize to grid integers")
        _check(typeof(decoded.get("x")) == TYPE_INT, "JSON-normalized x is integer")
        _check(typeof(decoded.get("y")) == TYPE_INT, "JSON-normalized y is integer")

    _check(
        PlayableSlice.normalize_grid_cell({"x": 2.5, "y": 3.0}).is_empty(),
        "fractional x coordinate remains invalid",
    )
    _check(
        PlayableSlice.normalize_grid_cell({"x": 2.0, "y": 3.25}).is_empty(),
        "fractional y coordinate remains invalid",
    )
    _check(
        PlayableSlice.normalize_grid_cell({"x": true, "y": 3}).is_empty(),
        "boolean coordinate remains invalid",
    )

    if _failures == 0:
        print("Godot tactical grid integer tests: PASS")
        quit(0)
    push_error("Godot tactical grid integer tests: %d failure(s)" % _failures)
    quit(1)


func _check(condition: bool, message: String) -> void:
    if condition:
        return
    _failures += 1
    push_error("FAIL: %s" % message)
