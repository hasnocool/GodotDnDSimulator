extends SceneTree

const MapScript = preload("res://scenes/tactical/tactical_map_view.gd")
const OverlayScript = preload("res://scenes/tactical/tactical_overlay.gd")

var _failures := 0


func _initialize() -> void:
    call_deferred("_run")


func _run() -> void:
    var map = MapScript.new()
    var overlay = OverlayScript.new()
    root.add_child(map)
    root.add_child(overlay)
    await process_frame
    overlay.bind_map(map)
    map.apply_authoritative_space(
        {
            "space_id": "space:navigation-debug",
            "width": 4,
            "height": 3,
            "cell_size_feet": 5,
            "terrain": [],
        }
    )
    overlay.show_navigation_comparison(
        [{"x": 0, "y": 0}, {"x": 1, "y": 0}, {"x": 2, "y": 0}],
        [{"x": 0, "y": 0}, {"x": 1, "y": 1}, {"x": 2, "y": 0}],
        true,
    )
    _check(
        overlay.navigation_comparison_marker_count() == 4,
        "comparison layer includes matching and disagreeing cells",
    )
    var layer: Node3D = overlay.get_node("NavigationComparisonDebug")
    var labels: Array[String] = []
    for marker_root in layer.get_children():
        for child in marker_root.get_children():
            if child is Label3D:
                labels.append((child as Label3D).text)
    _check(labels.has("AUTH ONLY"), "comparison identifies authority-only cells")
    _check(labels.has("ADAPTER ONLY"), "comparison identifies adapter-only cells")
    _check(labels.has("MATCH"), "comparison identifies matching cells")
    overlay.show_navigation_comparison([], [], false)
    await process_frame
    _check(
        overlay.navigation_comparison_marker_count() == 0,
        "comparison visualization clears when debug display is disabled",
    )
    root.remove_child(overlay)
    overlay.queue_free()
    root.remove_child(map)
    map.queue_free()
    await process_frame

    if _failures == 0:
        print("Godot navigation debug tests: PASS")
        quit(0)
    push_error("Godot navigation debug tests: %d failure(s)" % _failures)
    quit(1)


func _check(condition: bool, message: String) -> void:
    if condition:
        return
    _failures += 1
    push_error("FAIL: %s" % message)
