class_name TacticalOcclusionController
extends Node

@export var fade_alpha := 0.20
@export var corridor_radius := 0.75

var _faded: Dictionary = {}


func refresh(camera_position: Vector3, focus_position: Vector3) -> void:
    var tree := get_tree()
    if tree == null:
        return
    var desired: Dictionary = {}
    for value in tree.get_nodes_in_group("tactical_occluder"):
        if not (value is MeshInstance3D):
            continue
        var mesh := value as MeshInstance3D
        if _near_segment(mesh.global_position, camera_position, focus_position):
            desired[mesh.get_instance_id()] = mesh
            _set_faded(mesh, true)
    for id_value in _faded.keys():
        if desired.has(id_value):
            continue
        var previous: Variant = _faded[id_value]
        if is_instance_valid(previous):
            _set_faded(previous as MeshInstance3D, false)
    _faded = desired


func clear() -> void:
    for value in _faded.values():
        if is_instance_valid(value):
            _set_faded(value as MeshInstance3D, false)
    _faded.clear()


func _near_segment(point: Vector3, start: Vector3, finish: Vector3) -> bool:
    var segment := finish - start
    var length_squared := segment.length_squared()
    if length_squared <= 0.0001:
        return false
    var t := clampf((point - start).dot(segment) / length_squared, 0.0, 1.0)
    if t <= 0.08 or t >= 0.92:
        return false
    var closest := start + segment * t
    return point.distance_to(closest) <= corridor_radius


func _set_faded(mesh: MeshInstance3D, faded: bool) -> void:
    var material := mesh.material_override as StandardMaterial3D
    if material == null:
        return
    if not material.has_meta("occlusion_original_alpha"):
        material = material.duplicate() as StandardMaterial3D
        material.set_meta("occlusion_original_alpha", material.albedo_color.a)
        mesh.material_override = material
    var color := material.albedo_color
    color.a = (
        fade_alpha
        if faded
        else float(material.get_meta("occlusion_original_alpha", 1.0))
    )
    material.albedo_color = color
    material.transparency = (
        BaseMaterial3D.TRANSPARENCY_ALPHA
        if faded or color.a < 0.999
        else BaseMaterial3D.TRANSPARENCY_DISABLED
    )
