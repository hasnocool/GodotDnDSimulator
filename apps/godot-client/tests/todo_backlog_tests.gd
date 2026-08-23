extends SceneTree

const ActorScene = preload("res://scenes/actors/tactical_actor_view.tscn")
const MapScript = preload("res://scenes/tactical/tactical_map_view.gd")
const OverlayScript = preload("res://scenes/tactical/tactical_overlay.gd")
const EventPresenterScript = preload("res://presentation/tactical_event_presenter.gd")
const VFXScript = preload("res://presentation/tactical_vfx_presenter.gd")

const SPAWN_ANCHORS := [
    "res://resources/spawn_anchors/reedhollow_square.tres",
    "res://resources/spawn_anchors/market_row.tres",
    "res://resources/spawn_anchors/old_road.tres",
    "res://resources/spawn_anchors/quarry_mouth.tres",
    "res://resources/spawn_anchors/underworks.tres",
    "res://resources/spawn_anchors/lantern_vault.tres",
]

var _failures := 0


func _initialize() -> void:
    call_deferred("_run")


func _run() -> void:
    _test_spawn_anchor_resources()
    await _test_actor_and_debug_layers()
    _test_event_dedup_and_vfx_routing()
    await _test_vfx_primitives()
    if _failures == 0:
        print("Godot TODO backlog tests: PASS")
        quit(0)
    push_error("Godot TODO backlog tests: %d failure(s)" % _failures)
    quit(1)


func _test_spawn_anchor_resources() -> void:
    var areas: Dictionary = {}
    for path in SPAWN_ANCHORS:
        var anchor = load(path)
        _check(anchor != null, "spawn anchor loads: %s" % path)
        if anchor == null:
            continue
        _check(anchor.call("is_valid"), "spawn anchor validates: %s" % path)
        var payload: Dictionary = anchor.call("presentation_payload")
        _check(not str(payload.get("anchor_id", "")).is_empty(), "anchor has stable ID")
        var area_id := str(payload.get("area_id", ""))
        _check(not areas.has(area_id), "one default spawn anchor is defined per area")
        areas[area_id] = true
    _check(areas.size() == 6, "Lanterns Below has six reusable map-entry anchors")


func _test_actor_and_debug_layers() -> void:
    var actor = ActorScene.instantiate()
    root.add_child(actor)
    await process_frame
    actor.bind_actor(
        {
            "actor_id": "actor:test-party",
            "name": "Test Hero",
            "team": "party",
            "hit_points": {"current": 9, "maximum": 12},
            "armor_class": 14,
            "conditions": [
                {"condition_id": "condition:hindered", "name": "Hindered"},
            ],
        },
        Vector3.ZERO,
        true,
    )
    actor.set_debug_identity_visible(true)
    _check(actor.team_marker_text().contains("PARTY"), "actor uses non-color party emblem")
    _check(actor.condition_text().contains("Hindered"), "actor has dedicated condition/status slot")
    _check(actor.debug_identity_text() == "actor:test-party", "actor debug label uses stable ID")

    var map = MapScript.new()
    var overlay = OverlayScript.new()
    root.add_child(map)
    root.add_child(overlay)
    await process_frame
    overlay.bind_map(map)
    map.apply_authoritative_space(
        {
            "space_id": "space:test",
            "width": 3,
            "height": 2,
            "cell_size_feet": 5,
            "terrain": [
                {"x": 1, "y": 0, "terrain_id": "terrain:test", "difficult": true},
            ],
        }
    )
    map.set_debug_labels_visible(true)
    _check(map.debug_label_count() == 6, "spatial debug labels cover every rendered cell")
    overlay.show_reachable(
        {"cells": [{"cell": {"x": 0, "y": 0}}, {"cell": {"x": 1, "y": 0}}]}
    )
    overlay.show_path(
        {"legal": true, "path": [{"x": 0, "y": 0}, {"x": 1, "y": 0}]}
    )
    overlay.show_area({"cells": [{"x": 1, "y": 0}, {"x": 1, "y": 1}]})
    overlay.show_occupancy(
        [
            {"actor_id": "actor:a", "position": {"x": 0, "y": 0}},
            {"actor_id": "actor:b", "position": {"x": 2, "y": 1}},
        ],
        true,
    )
    _check(overlay.reachable_marker_count() == 2, "reachable overlay marker content is inspectable")
    _check(overlay.path_marker_count() == 2, "path overlay marker content is inspectable")
    _check(overlay.area_marker_count() == 2, "AoE overlay marker content is inspectable")
    _check(overlay.occupancy_marker_count() == 2, "dedicated occupancy debug layer renders actors")

    root.remove_child(actor)
    actor.queue_free()
    root.remove_child(overlay)
    overlay.queue_free()
    root.remove_child(map)
    map.queue_free()
    await process_frame


func _test_event_dedup_and_vfx_routing() -> void:
    var presenter = EventPresenterScript.new()
    var log_rows: Array[String] = []
    var dedup_rows: Array[String] = []
    var vfx_rows: Array[String] = []
    presenter.combat_log_entry.connect(func(text: String) -> void: log_rows.append(text))
    presenter.event_deduplicated.connect(func(key: String) -> void: dedup_rows.append(key))
    presenter.vfx_cue_requested.connect(
        func(cue_id: String, _actor_id: String, _payload: Dictionary) -> void:
            vfx_rows.append(cue_id)
    )
    var damage_event := {
        "sequence": 7,
        "type": "tactical.attack_resolved",
        "actor_id": "actor:a",
        "target_id": "actor:b",
        "payload": {"hit": true, "damage": 4},
    }
    presenter.call("_on_presentation_events", [damage_event, damage_event])
    _check(log_rows.size() == 1, "replayed presentation event is logged once")
    _check(dedup_rows.size() == 1, "duplicate replay event emits dedup diagnostic")
    _check(log_rows[0].contains("[7] tactical.attack_resolved"), "combat log includes stable sequence/type")
    _check(vfx_rows == ["damage"], "attack event routes to generic damage VFX")

    presenter.call(
        "_on_presentation_events",
        [
            {
                "sequence": 8,
                "type": "tactical.spell_resolved",
                "actor_id": "actor:a",
                "payload": {
                    "spell_id": "spell:test-heal",
                    "effect_kinds": ["healing"],
                    "targets": [
                        {"target_id": "actor:a", "amounts": [5], "success": null},
                    ],
                },
            },
            {
                "sequence": 9,
                "type": "tactical.spell_resolved",
                "actor_id": "actor:a",
                "payload": {
                    "spell_id": "spell:test-status",
                    "effect_kinds": ["condition"],
                    "targets": [
                        {"target_id": "actor:b", "amounts": [], "success": false},
                    ],
                },
            },
        ],
    )
    _check(vfx_rows.has("healing"), "spell event routes healing family to healing VFX")
    _check(vfx_rows.has("status"), "spell event routes condition family to status VFX")


func _test_vfx_primitives() -> void:
    var actor = ActorScene.instantiate()
    var vfx = VFXScript.new()
    root.add_child(actor)
    root.add_child(vfx)
    await process_frame
    actor.bind_actor(
        {
            "actor_id": "actor:vfx",
            "name": "VFX Target",
            "team": "party",
            "hit_points": {"current": 10, "maximum": 10},
            "armor_class": 12,
            "conditions": [],
        },
        Vector3.ZERO,
        true,
    )
    vfx.present("healing", actor, {}, true)
    _check(vfx.last_cue_id() == "healing", "healing VFX primitive records cue")
    _check(vfx.last_actor_id() == "actor:vfx", "VFX primitive binds authoritative actor ID")
    _check(vfx.active_count() == 1, "VFX primitive creates one presentation effect")
    await create_timer(0.22).timeout
    _check(vfx.active_count() == 0, "reduced-motion VFX primitive self-cleans")
    root.remove_child(vfx)
    vfx.queue_free()
    root.remove_child(actor)
    actor.queue_free()
    await process_frame


func _check(condition: bool, message: String) -> void:
    if condition:
        return
    _failures += 1
    push_error("FAIL: %s" % message)
