class_name TacticalMapView
extends Node3D

signal map_rebuilt(width: int, height: int)

var _space: Dictionary = {}
var _cell_nodes: Dictionary = {}
var _cell_size_feet := 5
var _world_cell_size := 1.0
var _debug_labels_visible := false


func apply_authoritative_space(space_data: Dictionary) -> void:
    _space = space_data.duplicate(true)
    _cell_size_feet = maxi(1, int(_space.get("cell_size_feet", 5)))
    _clear_map()
    var width := maxi(1, int(_space.get("width", 1)))
    var height := maxi(1, int(_space.get("height", 1)))
    var terrain_by_key: Dictionary = {}
    var terrain_value: Variant = _space.get("terrain", [])
    if typeof(terrain_value) == TYPE_ARRAY:
        for raw in terrain_value:
            if typeof(raw) != TYPE_DICTIONARY:
                continue
            var terrain: Dictionary = raw
            terrain_by_key[_cell_key(int(terrain.get("x", -1)), int(terrain.get("y", -1)))] = terrain
    for y in range(height):
        for x in range(width):
            var key := _cell_key(x, y)
            var terrain: Dictionary = terrain_by_key.get(key, {})
            _create_cell(x, y, terrain)
    map_rebuilt.emit(width, height)


func set_debug_labels_visible(value: bool) -> void:
    _debug_labels_visible = value
    for cell_value in _cell_nodes.values():
        if not (cell_value is Node3D):
            continue
        var cell := cell_value as Node3D
        var label := cell.get_node_or_null("DebugIdentity") as Label3D
        if label != null:
            label.visible = value


func debug_label_count() -> int:
    var count := 0
    for cell_value in _cell_nodes.values():
        if cell_value is Node3D and (cell_value as Node3D).has_node("DebugIdentity"):
            count += 1
    return count


func cell_to_world(cell: Dictionary) -> Vector3:
    var x := int(cell.get("x", 0))
    var y := int(cell.get("y", 0))
    var elevation := 0
    var key := _cell_key(x, y)
    if _cell_nodes.has(key):
        var cell_node: Node3D = _cell_nodes[key]
        elevation = int(cell_node.get_meta("elevation_feet", 0))
    return Vector3(
        float(x) * _world_cell_size,
        _elevation_to_world(elevation) + 0.08,
        float(y) * _world_cell_size,
    )


func world_to_cell(world_position: Vector3) -> Dictionary:
    return {
        "x": int(round(world_position.x / _world_cell_size)),
        "y": int(round(world_position.z / _world_cell_size)),
    }


func camera_bounds() -> Rect2:
    var width := maxi(1, int(_space.get("width", 1)))
    var height := maxi(1, int(_space.get("height", 1)))
    return Rect2(
        Vector2(0.0, 0.0),
        Vector2(float(width - 1), float(height - 1)),
    )


func contains_cell(cell: Dictionary) -> bool:
    return _cell_nodes.has(_cell_key(int(cell.get("x", -1)), int(cell.get("y", -1))))


func _create_cell(x: int, y: int, terrain: Dictionary) -> void:
    var root := Node3D.new()
    root.name = "Cell_%d_%d" % [x, y]
    var elevation_feet := int(terrain.get("elevation_feet", 0))
    var terrain_id := str(terrain.get("terrain_id", "terrain:open"))
    root.position = Vector3(
        float(x) * _world_cell_size,
        _elevation_to_world(elevation_feet),
        float(y) * _world_cell_size,
    )
    root.set_meta("grid_x", x)
    root.set_meta("grid_y", y)
    root.set_meta("elevation_feet", elevation_feet)
    root.set_meta("terrain_id", terrain_id)
    add_child(root)

    var floor_mesh := MeshInstance3D.new()
    var box := BoxMesh.new()
    box.size = Vector3(0.94, 0.08, 0.94)
    floor_mesh.mesh = box
    var material := StandardMaterial3D.new()
    material.albedo_color = _terrain_color(terrain)
    material.roughness = 0.9
    floor_mesh.material_override = material
    root.add_child(floor_mesh)

    var body := StaticBody3D.new()
    body.set_meta("grid_x", x)
    body.set_meta("grid_y", y)
    body.set_meta("tactical_surface", true)
    var collision := CollisionShape3D.new()
    var shape := BoxShape3D.new()
    shape.size = Vector3(0.94, 0.08, 0.94)
    collision.shape = shape
    body.add_child(collision)
    root.add_child(body)

    if bool(terrain.get("blocks_movement", false)):
        var obstacle := MeshInstance3D.new()
        var obstacle_mesh := BoxMesh.new()
        obstacle_mesh.size = Vector3(0.68, 0.7, 0.68)
        obstacle.mesh = obstacle_mesh
        obstacle.position.y = 0.39
        var obstacle_material := StandardMaterial3D.new()
        obstacle_material.albedo_color = Color(0.32, 0.30, 0.27)
        obstacle.material_override = obstacle_material
        root.add_child(obstacle)
        if bool(terrain.get("blocks_los", false)):
            obstacle.add_to_group("tactical_occluder")

    var debug_label := Label3D.new()
    debug_label.name = "DebugIdentity"
    debug_label.text = "%d,%d\n%s" % [x, y, terrain_id]
    debug_label.position = Vector3(0.0, 0.16, 0.0)
    debug_label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
    debug_label.no_depth_test = true
    debug_label.font_size = 9
    debug_label.visible = _debug_labels_visible
    root.add_child(debug_label)

    _cell_nodes[_cell_key(x, y)] = root


func _terrain_color(terrain: Dictionary) -> Color:
    if bool(terrain.get("blocks_movement", false)):
        return Color(0.42, 0.40, 0.36)
    if bool(terrain.get("difficult", false)):
        return Color(0.24, 0.45, 0.56)
    if int(terrain.get("elevation_feet", 0)) > 0:
        return Color(0.55, 0.50, 0.40)
    return Color(0.29, 0.34, 0.28)


func _elevation_to_world(feet: int) -> float:
    return float(feet) / float(_cell_size_feet) * 0.45


func _cell_key(x: int, y: int) -> String:
    return "%d:%d" % [x, y]


func _clear_map() -> void:
    for child in get_children():
        child.queue_free()
    _cell_nodes.clear()
