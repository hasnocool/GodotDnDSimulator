class_name TacticalOverlay
extends Node3D

var _map: TacticalMapView
var _reachable_root: Node3D
var _path_root: Node3D
var _area_root: Node3D
var _occupancy_root: Node3D
var _navigation_compare_root: Node3D
var _target_line: MeshInstance3D


func _ready() -> void:
    _reachable_root = _new_layer("Reachable")
    _path_root = _new_layer("Path")
    _area_root = _new_layer("Area")
    _occupancy_root = _new_layer("OccupancyDebug")
    _navigation_compare_root = _new_layer("NavigationComparisonDebug")
    _target_line = MeshInstance3D.new()
    _target_line.name = "TargetLine"
    add_child(_target_line)


func bind_map(map_view: TacticalMapView) -> void:
    _map = map_view


func clear_all() -> void:
    _clear_layer(_reachable_root)
    _clear_layer(_path_root)
    _clear_layer(_area_root)
    _target_line.mesh = null


func clear_debug() -> void:
    _clear_layer(_occupancy_root)
    _clear_layer(_navigation_compare_root)


func show_reachable(payload: Dictionary) -> void:
    _clear_layer(_reachable_root)
    if _map == null:
        return
    var value: Variant = payload.get("cells", [])
    if typeof(value) != TYPE_ARRAY:
        return
    for raw in value:
        if typeof(raw) != TYPE_DICTIONARY:
            continue
        var row: Dictionary = raw
        var cell_value: Variant = row.get("cell", {})
        if typeof(cell_value) == TYPE_DICTIONARY:
            _add_marker(
                _reachable_root,
                cell_value,
                Color(0.25, 0.72, 0.95, 0.25),
                0.42,
            )


func show_path(payload: Dictionary) -> void:
    _clear_layer(_path_root)
    if _map == null or not bool(payload.get("legal", false)):
        return
    var value: Variant = payload.get("path", [])
    if typeof(value) != TYPE_ARRAY:
        return
    for raw in value:
        if typeof(raw) == TYPE_DICTIONARY:
            _add_marker(
                _path_root,
                raw,
                Color(0.98, 0.82, 0.22, 0.68),
                0.22,
            )


func show_area(payload: Dictionary) -> void:
    _clear_layer(_area_root)
    if _map == null:
        return
    var value: Variant = payload.get("cells", [])
    if typeof(value) != TYPE_ARRAY:
        return
    for raw in value:
        if typeof(raw) == TYPE_DICTIONARY:
            _add_marker(
                _area_root,
                raw,
                Color(0.86, 0.30, 0.72, 0.30),
                0.36,
            )


func show_occupancy(actors: Variant, visible: bool) -> void:
    _clear_layer(_occupancy_root)
    if not visible or _map == null or typeof(actors) != TYPE_ARRAY:
        return
    for raw in actors:
        if typeof(raw) != TYPE_DICTIONARY:
            continue
        var actor: Dictionary = raw
        var position_value: Variant = actor.get("position", {})
        if typeof(position_value) != TYPE_DICTIONARY:
            continue
        var cell: Dictionary = position_value
        if not _map.contains_cell(cell):
            continue
        var root := Node3D.new()
        root.name = "Occupied_%s" % str(actor.get("actor_id", "actor")).replace(":", "_")
        root.position = _map.cell_to_world(cell) + Vector3.UP * 0.08
        _occupancy_root.add_child(root)

        var marker := MeshInstance3D.new()
        var mesh := CylinderMesh.new()
        mesh.top_radius = 0.48
        mesh.bottom_radius = 0.48
        mesh.height = 0.02
        marker.mesh = mesh
        var material := StandardMaterial3D.new()
        material.albedo_color = Color(1.0, 1.0, 1.0, 0.18)
        material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
        material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
        marker.material_override = material
        root.add_child(marker)

        var label := Label3D.new()
        label.text = "%s @ %d,%d" % [
            str(actor.get("actor_id", "actor")),
            int(cell.get("x", 0)),
            int(cell.get("y", 0)),
        ]
        label.position.y = 0.12
        label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
        label.no_depth_test = true
        label.font_size = 11
        root.add_child(label)


func show_navigation_comparison(
    authoritative_path: Variant,
    adapter_path: Variant,
    visible: bool,
) -> void:
    _clear_layer(_navigation_compare_root)
    if not visible or _map == null:
        return
    var authoritative := _cell_key_set(authoritative_path)
    var adapter := _cell_key_set(adapter_path)
    var keys: Dictionary = {}
    for key in authoritative.keys():
        keys[key] = true
    for key in adapter.keys():
        keys[key] = true
    for key_value in keys.keys():
        var key := str(key_value)
        var parts := key.split(",")
        if parts.size() != 2:
            continue
        var cell := {"x": int(parts[0]), "y": int(parts[1])}
        var in_authority := authoritative.has(key)
        var in_adapter := adapter.has(key)
        var marker_color := Color(0.38, 0.90, 0.48, 0.38)
        var prefix := "MATCH"
        if in_authority and not in_adapter:
            marker_color = Color(0.98, 0.72, 0.20, 0.48)
            prefix = "AUTH ONLY"
        elif in_adapter and not in_authority:
            marker_color = Color(0.95, 0.30, 0.32, 0.48)
            prefix = "ADAPTER ONLY"
        _add_debug_labeled_marker(
            _navigation_compare_root,
            cell,
            marker_color,
            prefix,
        )


func navigation_comparison_marker_count() -> int:
    return (
        0
        if _navigation_compare_root == null
        else _navigation_compare_root.get_child_count()
    )


func show_target_line(
    source_world: Vector3,
    target_world: Vector3,
    preview: Dictionary,
) -> void:
    var immediate := ImmediateMesh.new()
    var material := StandardMaterial3D.new()
    material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    material.albedo_color = (
        Color(0.35, 0.95, 0.45)
        if bool(preview.get("legal", false))
        else Color(0.95, 0.35, 0.30)
    )
    immediate.surface_begin(Mesh.PRIMITIVE_LINES, material)
    immediate.surface_add_vertex(source_world + Vector3.UP * 0.55)
    immediate.surface_add_vertex(target_world + Vector3.UP * 0.55)
    immediate.surface_end()
    _target_line.mesh = immediate


func reachable_marker_count() -> int:
    return 0 if _reachable_root == null else _reachable_root.get_child_count()


func path_marker_count() -> int:
    return 0 if _path_root == null else _path_root.get_child_count()


func area_marker_count() -> int:
    return 0 if _area_root == null else _area_root.get_child_count()


func occupancy_marker_count() -> int:
    return 0 if _occupancy_root == null else _occupancy_root.get_child_count()


func target_line_visible() -> bool:
    return _target_line != null and _target_line.mesh != null


func _new_layer(layer_name: String) -> Node3D:
    var layer := Node3D.new()
    layer.name = layer_name
    add_child(layer)
    return layer


func _add_marker(
    layer: Node3D,
    cell: Dictionary,
    color: Color,
    radius: float,
) -> void:
    if _map == null or not _map.contains_cell(cell):
        return
    var marker := MeshInstance3D.new()
    var mesh := CylinderMesh.new()
    mesh.top_radius = radius
    mesh.bottom_radius = radius
    mesh.height = 0.025
    marker.mesh = mesh
    marker.position = _map.cell_to_world(cell) + Vector3.UP * 0.04
    var material := StandardMaterial3D.new()
    material.albedo_color = color
    material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
    material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    marker.material_override = material
    layer.add_child(marker)


func _add_debug_labeled_marker(
    layer: Node3D,
    cell: Dictionary,
    color: Color,
    label_text: String,
) -> void:
    if _map == null or not _map.contains_cell(cell):
        return
    var root := Node3D.new()
    root.position = _map.cell_to_world(cell) + Vector3.UP * 0.1
    layer.add_child(root)
    var marker := MeshInstance3D.new()
    var mesh := CylinderMesh.new()
    mesh.top_radius = 0.32
    mesh.bottom_radius = 0.32
    mesh.height = 0.025
    marker.mesh = mesh
    var material := StandardMaterial3D.new()
    material.albedo_color = color
    material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
    material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    marker.material_override = material
    root.add_child(marker)
    var label := Label3D.new()
    label.text = label_text
    label.position.y = 0.10
    label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
    label.no_depth_test = true
    label.font_size = 9
    root.add_child(label)


func _cell_key_set(value: Variant) -> Dictionary:
    var result: Dictionary = {}
    if typeof(value) != TYPE_ARRAY:
        return result
    for raw in value:
        if typeof(raw) != TYPE_DICTIONARY:
            continue
        var cell: Dictionary = raw
        result["%d,%d" % [int(cell.get("x", 0)), int(cell.get("y", 0))]] = true
    return result


func _clear_layer(layer: Node3D) -> void:
    if layer == null:
        return
    for child in layer.get_children():
        child.queue_free()
