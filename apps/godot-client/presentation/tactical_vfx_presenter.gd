class_name TacticalVFXPresenter
extends Node3D

var _last_cue_id := ""
var _last_actor_id := ""
var _active_count := 0


func present(
    cue_id: String,
    actor_view: TacticalActorView,
    payload: Dictionary,
    reduced_motion: bool,
) -> void:
    if actor_view == null or cue_id.is_empty():
        return
    _last_cue_id = cue_id
    _last_actor_id = actor_view.actor_id
    var root := Node3D.new()
    root.name = "VFX_%s" % cue_id.replace(":", "_")
    root.global_position = actor_view.global_position + Vector3.UP * 0.72
    add_child(root)
    _active_count += 1

    var ring := MeshInstance3D.new()
    var mesh := TorusMesh.new()
    mesh.inner_radius = 0.20
    mesh.outer_radius = 0.38
    ring.mesh = mesh
    var material := StandardMaterial3D.new()
    material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
    material.albedo_color = _cue_color(cue_id)
    ring.material_override = material
    root.add_child(ring)

    var label := Label3D.new()
    label.text = _cue_label(cue_id, payload)
    label.position.y = 0.28
    label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
    label.no_depth_test = true
    label.font_size = 15
    root.add_child(label)

    if reduced_motion:
        get_tree().create_timer(0.18).timeout.connect(
            func() -> void:
                _finish_effect(root)
        )
        return
    var tween := create_tween()
    tween.set_parallel(true)
    tween.tween_property(root, "scale", Vector3(1.5, 1.5, 1.5), 0.32)
    tween.tween_property(root, "position:y", root.position.y + 0.18, 0.32)
    tween.finished.connect(
        func() -> void:
            _finish_effect(root)
    )


func last_cue_id() -> String:
    return _last_cue_id


func last_actor_id() -> String:
    return _last_actor_id


func active_count() -> int:
    return _active_count


func _finish_effect(root: Node3D) -> void:
    if is_instance_valid(root):
        root.queue_free()
    _active_count = maxi(0, _active_count - 1)


func _cue_color(cue_id: String) -> Color:
    match cue_id:
        "healing":
            return Color(0.35, 0.95, 0.52, 0.78)
        "damage":
            return Color(0.95, 0.34, 0.28, 0.78)
        "status", "status_expired":
            return Color(0.72, 0.42, 0.95, 0.78)
        "miss":
            return Color(0.74, 0.78, 0.82, 0.55)
        _:
            return Color(0.35, 0.75, 0.95, 0.65)


func _cue_label(cue_id: String, payload: Dictionary) -> String:
    match cue_id:
        "damage":
            var damage := int(payload.get("damage", 0))
            return "DAMAGE%s" % (" %d" % damage if damage > 0 else "")
        "healing":
            return "HEAL"
        "status_expired":
            return "STATUS ENDED"
        "status":
            return "STATUS"
        "miss":
            return "MISS"
        _:
            return cue_id.to_upper()
