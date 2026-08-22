class_name TacticalOverlay
extends Node3D

var _map: TacticalMapView
var _reachable_root: Node3D
var _path_root: Node3D
var _area_root: Node3D
var _target_line: MeshInstance3D


func _ready() -> void:
    _reachable_root = _new_layer("Reachable")
    _path_root = _new_layer("Path")
    _area_root = _new_layer("Area")
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


func _clear_layer(layer: Node3D) -> void:
    if layer == null:
        return
    for child in layer.get_children():
        child.queue_free()
