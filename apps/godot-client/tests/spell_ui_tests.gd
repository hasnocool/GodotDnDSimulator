extends SceneTree

const Protocol = preload("res://bridge/bridge_protocol.gd")
const FakeTransportScript = preload("res://bridge/fake_engine_transport.gd")
const InteractionModes = preload("res://input/interaction_modes.gd")

var _failures := 0


func _initialize() -> void:
    call_deferred("_run")


func _run() -> void:
    var settings: Node = root.get_node("ClientSettings")
    settings.reset_defaults(false)
    settings.set_value("reduced_motion", true, false)
    await _test_spell_ui_uses_authoritative_previews()
    settings.reset_defaults(false)
    if _failures == 0:
        print("Godot spell UI tests: PASS")
        quit(0)
    else:
        push_error("Godot spell UI tests: %d failure(s)" % _failures)
        quit(1)


func _test_spell_ui_uses_authoritative_previews() -> void:
    var shell_scene := load("res://scenes/shell/app_shell.tscn") as PackedScene
    _check(shell_scene != null, "app shell scene loads for spell UI test")
    if shell_scene == null:
        return
    var shell = shell_scene.instantiate()
    var transport = FakeTransportScript.new()
    shell.transport_override = transport
    root.add_child(shell)
    await process_frame

    var hello := _last_message(transport, "bridge.hello")
    _check(not hello.is_empty(), "spell UI shell sends bridge hello")
    transport.queue_message(
        Protocol.make_response(
            "bridge.hello.accepted",
            str(hello["request_id"]),
            str(hello["correlation_id"]),
            int(hello["generation"]),
            true,
            {
                "protocol": Protocol.PROTOCOL_NAME,
                "capabilities": [
                    "commands.v1",
                    "queries.v1",
                    "previews.v1",
                    "snapshots.v1",
                    "events.v1",
                    "request-cancel.v1",
                    "request-generation.v1",
                    "tactical.vertical-slice.v1",
                    "tactical.commands.v1",
                    "tactical.queries.v1",
                    "spatial.queries.v1",
                    "spatial.previews.v1",
                    "spells.runtime.v1",
                    "spells.commands.v1",
                    "spells.queries.v1",
                    "spells.previews.v1",
                ],
            },
        )
    )
    await process_frame

    var snapshot_request := _last_query(transport, "tactical.snapshot")
    _check(not snapshot_request.is_empty(), "spell-capable session requests tactical snapshot")
    transport.queue_message(
        Protocol.make_response(
            "query.result",
            str(snapshot_request["request_id"]),
            str(snapshot_request["correlation_id"]),
            int(snapshot_request["generation"]),
            true,
            {"snapshot": _snapshot(0)},
        )
    )
    for _index in range(60):
        await process_frame
        if shell.tactical_content() != null:
            break
    var scene = shell.tactical_content()
    _check(scene != null, "spell-capable tactical scene loads")
    if scene == null:
        shell.shutdown()
        return

    var spell_query := _last_query(transport, "spells.available")
    _check(not spell_query.is_empty(), "spell palette requests engine-provided available spells")
    transport.queue_message(
        Protocol.make_response(
            "query.result",
            str(spell_query["request_id"]),
            str(spell_query["correlation_id"]),
            int(spell_query["generation"]),
            true,
            _available_spells(),
        )
    )
    await process_frame
    var palette = scene.get_node("HUD/SpellPalette")
    _check(palette.visible, "spell palette is visible only with authoritative spell state")
    _check(palette.call("spell_rows").size() == 2, "palette renders engine spell rows")

    var lance: Dictionary = _available_spells()["spells"][0]
    scene.call("_on_spell_selected", lance, 0)
    _check(
        shell.interaction_controller().current_mode() == InteractionModes.Mode.TARGET,
        "creature spell enters shared C3 target mode",
    )
    scene.call("_request_spell_preview", ["actor:shale"], {})
    var creature_preview := _last_preview(transport, "spells.preview")
    _check(not creature_preview.is_empty(), "creature spell requests authoritative preview")
    _check(
        _last_message(transport, "command.submit").is_empty(),
        "spell selection alone does not submit an authoritative command",
    )
    transport.queue_message(
        Protocol.make_response(
            "preview.result",
            str(creature_preview["request_id"]),
            str(creature_preview["correlation_id"]),
            int(creature_preview["generation"]),
            true,
            {
                "legal": true,
                "reason": "",
                "spell_id": "spell:arc-lance",
                "slot_level": 0,
                "target_ids": ["actor:shale"],
                "point": null,
                "area": {},
                "concentration_will_replace": false,
            },
        )
    )
    await process_frame
    var cast_request_id: String = shell.interaction_controller().confirm_current_intent()
    _check(not cast_request_id.is_empty(), "legal spell preview arms a confirmable command")
    var cast := _last_message(transport, "command.submit")
    _check(
        str(cast["payload"]["command"].get("command_type", "")) == "tactical.cast_spell",
        "confirmed spell uses typed tactical.cast_spell command",
    )
    _check(
        cast["payload"]["command"]["payload"].get("target_ids", []) == ["actor:shale"],
        "command target list comes from authoritative preview",
    )

    transport.queue_message(
        Protocol.make_response(
            "command.accepted",
            str(cast["request_id"]),
            str(cast["correlation_id"]),
            int(cast["generation"]),
            true,
            {
                "snapshot": _snapshot(1),
                "presentation_events": [
                    {
                        "sequence": 1,
                        "type": "tactical.spell_resolved",
                        "actor_id": "actor:ember",
                        "payload": {
                            "spell_id": "spell:arc-lance",
                            "slot_level": 0,
                            "targets": [
                                {
                                    "target_id": "actor:shale",
                                    "attack_total": 16,
                                    "save_total": null,
                                    "success": true,
                                    "amounts": [5],
                                },
                            ],
                        },
                    },
                ],
                "result": {"spell_id": "spell:arc-lance", "outcome_count": 1},
            },
        )
    )
    await process_frame
    _check(
        shell.client_state().authoritative.sequence() == 1,
        "accepted spell reconciles to fresh authoritative snapshot",
    )

    var area_spell: Dictionary = _available_spells()["spells"][1]
    scene.call("_on_spell_selected", area_spell, 1)
    _check(
        shell.interaction_controller().current_mode() == InteractionModes.Mode.SHAPE_PREVIEW,
        "area spell reuses shared shape-preview interaction mode",
    )
    scene.call("_request_spell_preview", [], {"x": 5, "y": 3})
    var area_preview := _last_preview(transport, "spells.preview")
    transport.queue_message(
        Protocol.make_response(
            "preview.result",
            str(area_preview["request_id"]),
            str(area_preview["correlation_id"]),
            int(area_preview["generation"]),
            true,
            {
                "legal": true,
                "reason": "",
                "spell_id": "spell:echo-burst",
                "slot_level": 1,
                "target_ids": ["actor:shale"],
                "point": {"x": 5, "y": 3},
                "area": {
                    "cells": [{"x": 5, "y": 3}, {"x": 6, "y": 3}],
                    "entity_ids": ["actor:shale"],
                },
                "concentration_will_replace": false,
            },
        )
    )
    await process_frame
    var area_layer = scene.get_node("TacticalOverlay/Area")
    _check(
        area_layer.get_child_count() == 2,
        "area overlay renders exactly the cells returned by spatial authority",
    )
    var area_cast_id: String = shell.interaction_controller().confirm_current_intent()
    _check(not area_cast_id.is_empty(), "authoritative area preview arms spell command")
    var area_cast := _last_message(transport, "command.submit")
    _check(
        area_cast["payload"]["command"]["payload"].get("point", {}) == {"x": 5, "y": 3},
        "area command carries player-selected point rather than local AoE membership",
    )

    shell.shutdown()
    root.remove_child(shell)
    shell.queue_free()
    await process_frame


func _available_spells() -> Dictionary:
    return {
        "actor_id": "actor:ember",
        "slots": [{"level": 1, "current": 3, "maximum": 3}],
        "concentration": null,
        "spells": [
            {
                "spell_id": "spell:arc-lance",
                "name": "Arc Lance",
                "level": 0,
                "castable": true,
                "prepared": false,
                "slot_levels": [0],
                "resolution": "attack",
                "target_kind": "creature",
                "range_feet": 60,
                "max_targets": 1,
                "concentration": false,
                "duration_rounds": null,
                "area_shape": null,
                "area_size_feet": null,
                "tags": [],
            },
            {
                "spell_id": "spell:echo-burst",
                "name": "Echo Burst",
                "level": 1,
                "castable": true,
                "prepared": true,
                "slot_levels": [1],
                "resolution": "save",
                "target_kind": "area",
                "range_feet": 30,
                "max_targets": 1,
                "concentration": false,
                "duration_rounds": null,
                "area_shape": "sphere",
                "area_size_feet": 10,
                "tags": [],
            },
        ],
    }


func _snapshot(sequence: int) -> Dictionary:
    return {
        "schema_version": 1,
        "state": {
            "campaign_id": "campaign:v08-client",
            "session_id": "session:v08-client",
            "sequence": sequence,
            "tick": sequence,
            "mode": "tactical_vertical_slice",
            "tactical": {
                "slice_id": "vertical-slice:sunken-courtyard",
                "display_name": "Sunken Courtyard",
                "encounter_id": "encounter:sunken-courtyard",
                "status": "active",
                "round_number": 1,
                "turn_index": 0,
                "current_actor_id": "actor:ember",
                "initiative": [
                    {"actor_id": "actor:ember", "total": 18},
                    {"actor_id": "actor:shale", "total": 12},
                ],
                "actors": [
                    _actor("actor:ember", "Ember Scout", "ember", {"x": 1, "y": 2}),
                    _actor("actor:shale", "Shale Warden", "shale", {"x": 6, "y": 3}),
                ],
                "space": {
                    "space_id": "space:sunken-courtyard",
                    "width": 8,
                    "height": 6,
                    "cell_size_feet": 5,
                    "camera_bounds": {"min_x": 0, "min_y": 0, "max_x": 7, "max_y": 5},
                    "terrain": [],
                },
                "recent_events": [],
                "spellcasting": {
                    "sequence": sequence,
                    "casters": [
                        {
                            "actor_id": "actor:ember",
                            "ability": "intelligence",
                            "spell_attack_bonus": 4,
                            "spell_save_dc": 12,
                            "known_spell_ids": ["spell:arc-lance", "spell:echo-burst"],
                            "prepared_spell_ids": ["spell:echo-burst"],
                            "slots": [{"level": 1, "current": 3, "maximum": 3}],
                            "concentration": null,
                        },
                    ],
                    "active_effects": [],
                },
            },
        },
        "rng": {"algorithm": "pcg32-v1", "state": 1, "increment": 3},
    }


func _actor(
    actor_id: String,
    actor_name: String,
    team: String,
    position: Dictionary,
) -> Dictionary:
    return {
        "actor_id": actor_id,
        "name": actor_name,
        "kind": "npc",
        "size": "medium",
        "team": team,
        "position": position,
        "elevation_feet": 0,
        "hit_points": {"current": 18, "maximum": 18, "temporary": 0},
        "armor_class": 14,
        "life_state": "conscious",
        "conditions": [],
        "movement_modes": [{"mode": "walk", "speed_feet": 30}],
        "economy": {
            "action_available": true,
            "bonus_action_available": true,
            "reaction_available": true,
            "movement_remaining": 30,
        },
    }


func _last_message(transport, kind: String) -> Dictionary:
    for index in range(transport.sent_messages.size() - 1, -1, -1):
        var candidate: Dictionary = transport.sent_messages[index]
        if str(candidate.get("kind", "")) == kind:
            return candidate
    return {}


func _last_query(transport, query_type: String) -> Dictionary:
    for index in range(transport.sent_messages.size() - 1, -1, -1):
        var candidate: Dictionary = transport.sent_messages[index]
        if str(candidate.get("kind", "")) != "query.request":
            continue
        if str(candidate["payload"].get("query_type", "")) == query_type:
            return candidate
    return {}


func _last_preview(transport, preview_type: String) -> Dictionary:
    for index in range(transport.sent_messages.size() - 1, -1, -1):
        var candidate: Dictionary = transport.sent_messages[index]
        if str(candidate.get("kind", "")) != "preview.request":
            continue
        if str(candidate["payload"].get("preview_type", "")) == preview_type:
            return candidate
    return {}


func _check(condition: bool, message: String) -> void:
    if condition:
        return
    _failures += 1
    push_error("FAIL: %s" % message)
