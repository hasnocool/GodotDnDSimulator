class_name TacticalActorView
extends Node3D

signal presentation_motion_started(actor_id: String)
signal presentation_motion_finished(actor_id: String)

var actor_id := ""
var _team := "neutral"
var _selected := false
var _hovered := false
var _current_turn := false
var _body: MeshInstance3D
var _selection_disc: MeshInstance3D
var _hover_disc: MeshInstance3D
var _turn_marker: Label3D
var _name_label: Label3D
var _status_label: Label3D
var _pick_body: StaticBody3D
var _active_tween: Tween


func _ready() -> void:
    _build_visuals()


func bind_actor(data: Dictionary, world_position: Vector3, reduced_motion: bool) -> void:
    actor_id = str(data.get("actor_id", ""))
    _team = str(data.get("team", "neutral"))
    name = "Actor_%s" % actor_id.replace(":", "_")
    _pick_body.set_meta("actor_id", actor_id)
    _name_label.text = str(data.get("name", actor_id))
    apply_authoritative_state(data)
    set_authoritative_position(world_position, reduced_motion)


func apply_authoritative_state(data: Dictionary) -> void:
    _team = str(data.get("team", _team))
    var hp_value: Variant = data.get("hit_points", {})
    var hp: Dictionary = hp_value if typeof(hp_value) == TYPE_DICTIONARY else {}
    _status_label.text = "HP %d/%d · AC %d" % [
        int(hp.get("current", 0)),
        int(hp.get("maximum", 0)),
        int(data.get("armor_class", 0)),
    ]
    var material := _body.material_override as StandardMaterial3D
    if material != null:
        material.albedo_color = _team_color(_team)
    _refresh_indicators()


func set_authoritative_position(world_position: Vector3, reduced_motion: bool) -> void:
    if _active_tween != null and _active_tween.is_valid():
        _active_tween.kill()
    if reduced_motion or global_position.distance_to(world_position) < 0.01:
        global_position = world_position
        return
    presentation_motion_started.emit(actor_id)
    _active_tween = create_tween()
    _active_tween.set_trans(Tween.TRANS_QUAD)
    _active_tween.set_ease(Tween.EASE_OUT)
    _active_tween.tween_property(self, "global_position", world_position, 0.22)
    _active_tween.finished.connect(
        func() -> void:
            presentation_motion_finished.emit(actor_id)
    )


func set_selected(value: bool) -> void:
    _selected = value
    _refresh_indicators()


func set_hovered(value: bool) -> void:
    _hovered = value
    _refresh_indicators()


func set_current_turn(value: bool) -> void:
    _current_turn = value
    _refresh_indicators()


func _build_visuals() -> void:
    _body = MeshInstance3D.new()
    var capsule := CapsuleMesh.new()
    capsule.radius = 0.34
    capsule.height = 1.25
    _body.mesh = capsule
    _body.position.y = 0.65
    var body_material := StandardMaterial3D.new()
    body_material.albedo_color = _team_color(_team)
    body_material.roughness = 0.72
    _body.material_override = body_material
    add_child(_body)

    _selection_disc = _indicator_mesh(Color(0.95, 0.85, 0.25, 0.72), 0.70)
    add_child(_selection_disc)
    _hover_disc = _indicator_mesh(Color(0.35, 0.85, 1.0, 0.58), 0.55)
    _hover_disc.position.y = 0.03
    add_child(_hover_disc)

    _name_label = Label3D.new()
    _name_label.position = Vector3(0.0, 1.55, 0.0)
    _name_label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
    _name_label.no_depth_test = true
    _name_label.font_size = 22
    add_child(_name_label)

    _status_label = Label3D.new()
    _status_label.position = Vector3(0.0, 1.30, 0.0)
    _status_label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
    _status_label.no_depth_test = true
    _status_label.font_size = 15
    add_child(_status_label)

    _turn_marker = Label3D.new()
    _turn_marker.text = "TURN"
    _turn_marker.position = Vector3(0.0, 1.82, 0.0)
    _turn_marker.billboard = BaseMaterial3D.BILLBOARD_ENABLED
    _turn_marker.no_depth_test = true
    _turn_marker.font_size = 16
    add_child(_turn_marker)

    _pick_body = StaticBody3D.new()
    var collision := CollisionShape3D.new()
    var shape := CapsuleShape3D.new()
    shape.radius = 0.42
    shape.height = 1.3
    collision.shape = shape
    collision.position.y = 0.65
    _pick_body.add_child(collision)
    add_child(_pick_body)
    _refresh_indicators()


func _indicator_mesh(color: Color, radius: float) -> MeshInstance3D:
    var mesh_instance := MeshInstance3D.new()
    var cylinder := CylinderMesh.new()
    cylinder.top_radius = radius
    cylinder.bottom_radius = radius
    cylinder.height = 0.025
    mesh_instance.mesh = cylinder
    var material := StandardMaterial3D.new()
    material.albedo_color = color
    material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
    material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    mesh_instance.material_override = material
    return mesh_instance


func _refresh_indicators() -> void:
    if _selection_disc != null:
        _selection_disc.visible = _selected
    if _hover_disc != null:
        _hover_disc.visible = _hovered and not _selected
    if _turn_marker != null:
        _turn_marker.visible = _current_turn


func _team_color(team: String) -> Color:
    match team:
        "ember":
            return Color(0.88, 0.36, 0.20)
        "shale":
            return Color(0.34, 0.48, 0.74)
        _:
            return Color(0.62, 0.62, 0.62)
