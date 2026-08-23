extends SceneTree

const ActorScene = preload("res://scenes/actors/tactical_actor_view.tscn")
const MapScript = preload("res://scenes/tactical/tactical_map_view.gd")

var _failures := 0


func _initialize() -> void:
    call_deferred("_run")


func _run() -> void:
    var actor = ActorScene.instantiate()
    root.add_child(actor)
    await process_frame
    actor.bind_actor(
        {
            "actor_id": "actor:debug-hero",
            "name": "Debug Hero",
            "team": "party",
            "hit_points": {"current": 10, "maximum": 10},
            "armor_class": 13,
            "conditions": [
                {"condition_id": "condition:hindered", "name": "Hindered"},
            ],
        },
        Vector3.ZERO,
        true,
    )
    actor.set_debug_identity_visible(true)
    _check(
        actor.debug_label_text().contains("actor:debug-hero"),
        "actor debug label contains stable actor ID",
    )
    _check(
        actor.debug_label_text().contains("condition:hindered"),
        "actor debug label contains authoritative condition/rule ID",
    )

    var map = MapScript.new()
    root.add_child(map)
    await process_frame
    map.apply_authoritative_space(
        {
            "space_id": "space:debug",
            "width": 1,
            "height": 1,
            "cell_size_feet": 5,
            "terrain": [
                {"x": 0, "y": 0, "terrain_id": "terrain:difficult-rubble", "difficult": true},
            ],
        }
    )
    map.set_debug_labels_visible(true)
    var cell: Node3D = map.get_node("Cell_0_0")
    var label: Label3D = cell.get_node("DebugIdentity")
    _check(label.text.contains("0,0"), "map debug label contains stable spatial coordinate")
    _check(
        label.text.contains("terrain:difficult-rubble"),
        "map debug label contains authoritative terrain/content ID",
    )

    root.remove_child(map)
    map.queue_free()
    root.remove_child(actor)
    actor.queue_free()
    await process_frame
    if _failures == 0:
        print("Godot debug identity tests: PASS")
        quit(0)
    push_error("Godot debug identity tests: %d failure(s)" % _failures)
    quit(1)


func _check(condition: bool, message: String) -> void:
    if condition:
        return
    _failures += 1
    push_error("FAIL: %s" % message)
