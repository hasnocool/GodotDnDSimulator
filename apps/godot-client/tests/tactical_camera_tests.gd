extends SceneTree

const Actions = preload("res://input/input_actions.gd")

var _failures := 0


func _initialize() -> void:
    call_deferred("_run")


func _run() -> void:
    var packed := load("res://camera/tactical_camera.tscn") as PackedScene
    _check(packed != null, "tactical camera scene loads")
    if packed == null:
        quit(1)
        return
    var camera = packed.instantiate()
    root.add_child(camera)
    await process_frame

    camera.set_reduced_motion(true)
    camera.set_map_bounds(Rect2(Vector2.ZERO, Vector2(5.0, 4.0)))
    camera.focus_world_position(Vector3(9.0, 0.0, -3.0))
    _check(
        camera.focus_position().is_equal_approx(Vector3(2.5, 0.0, 2.0)),
        "maps smaller than the orthographic footprint stay centered instead of exposing void",
    )
    var compact_limits: Rect2 = camera.focus_limits()
    _check(
        is_equal_approx(compact_limits.size.x, 0.0) and is_equal_approx(compact_limits.size.y, 0.0),
        "small-map focus limits collapse to the authoritative map center",
    )

    camera.set_zoom(6.0)
    camera.set_map_bounds(Rect2(Vector2.ZERO, Vector2(80.0, 60.0)))
    var padded_limits: Rect2 = camera.focus_limits()
    _check(
        padded_limits.position.x > 0.0 and padded_limits.position.y > 0.0,
        "camera focus limits reserve aspect-aware padding from the minimum map edges",
    )
    _check(
        padded_limits.end.x < 80.0 and padded_limits.end.y < 60.0,
        "camera focus limits reserve aspect-aware padding from the maximum map edges",
    )
    camera.focus_world_position(Vector3(999.0, 0.0, 999.0))
    _check(
        camera.focus_position().x <= padded_limits.end.x
            and camera.focus_position().z <= padded_limits.end.y,
        "camera focus clamps inside the padded visible footprint",
    )

    camera.rotate_quarter(1)
    _check(camera.quarter_turn() == 1, "camera rotation advances by one exact quarter turn")
    camera.rotate_quarter(3)
    _check(camera.quarter_turn() == 2, "rotation direction normalizes to a single quarter step")
    camera.rotate_quarter(-1)
    _check(camera.quarter_turn() == 1, "camera supports exact counter-clockwise quarter turns")

    camera.set_zoom(1.0)
    _check(is_equal_approx(camera.zoom_size(), 6.0), "zoom clamps to configured minimum")
    camera.set_zoom(99.0)
    _check(is_equal_approx(camera.zoom_size(), 24.0), "zoom clamps to configured maximum")
    camera.handle_camera_action(Actions.CAMERA_ZOOM_IN)
    _check(camera.zoom_size() < 24.0, "semantic zoom action changes camera target")
    camera.handle_camera_action(Actions.CAMERA_ROTATE_RIGHT)
    _check(camera.quarter_turn() == 2, "semantic rotation action uses discrete state")

    root.remove_child(camera)
    camera.queue_free()
    await process_frame
    if _failures == 0:
        print("Godot tactical camera tests: PASS")
        quit(0)
    else:
        push_error("Godot tactical camera tests: %d failure(s)" % _failures)
        quit(1)


func _check(condition: bool, message: String) -> void:
    if condition:
        return
    _failures += 1
    push_error("FAIL: %s" % message)
