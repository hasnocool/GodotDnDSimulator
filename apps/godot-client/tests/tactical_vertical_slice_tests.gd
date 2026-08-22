extends SceneTree

const Protocol = preload("res://bridge/bridge_protocol.gd")
const FakeTransportScript = preload("res://bridge/fake_engine_transport.gd")

var _failures := 0
var _settings: Node


func _initialize() -> void:
    call_deferred("_run")


func _run() -> void:
    _settings = root.get_node("ClientSettings")
    _settings.reset_defaults(false)
    _settings.set_value("reduced_motion", true, false)
    await _test_shell_and_authoritative_tactical_flow()
    _settings.reset_defaults(false)
    if _failures == 0:
        print("Godot tactical vertical slice tests: PASS")
        quit(0)
    else:
        push_error("Godot tactical vertical slice tests: %d failure(s)" % _failures)
        quit(1)


func _test_shell_and_authoritative_tactical_flow() -> void:
    var shell_scene := load("res://scenes/shell/app_shell.tscn") as PackedScene
    _check(shell_scene != null, "app shell scene loads")
    if shell_scene == null:
        return
    var shell = shell_scene.instantiate()
    var transport = FakeTransportScript.new()
    shell.transport_override = transport
    root.add_child(shell)
    await process_frame

    var hello := _last_message(transport, "bridge.hello")
    _check(not hello.is_empty(), "shell sends hello")
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
                ],
            },
        )
    )
    await process_frame

    var snapshot_request := _last_query(transport, "tactical.snapshot")
    _check(not snapshot_request.is_empty(), "tactical capability selects tactical.snapshot")
    transport.queue_message(
        Protocol.make_response(
            "query.result",
            str(snapshot_request["request_id"]),
            str(snapshot_request["correlation_id"]),
            int(snapshot_request["generation"]),
            true,
            {"snapshot": _snapshot(0, {"x": 1, "y": 2}, 30)},
        )
    )
    for _index in range(60):
        await process_frame
        if shell.tactical_content() != null:
            break
    _check(shell.tactical_content() != null, "shell loads v0.7 tactical scene")
    if shell.tactical_content() == null:
        shell.shutdown()
        return
    var scene = shell.tactical_content()
    _check(scene.has_method("request_move_mode"), "v0.7 scene exposes tactical intent API")
    _check(scene.actor_view("actor:ember") != null, "actor registry renders engine actor IDs")
    _check(
        shell.client_state().interaction.selected_actor_id() == "actor:ember",
        "current authoritative actor becomes initial selection",
    )

    scene.request_move_mode()
    await process_frame
    var reachable := _last_preview(transport, "spatial.reachable")
    _check(not reachable.is_empty(), "Move requests authoritative reachable-space preview")
    transport.queue_message(
        Protocol.make_response(
            "preview.result",
            str(reachable["request_id"]),
            str(reachable["correlation_id"]),
            int(reachable["generation"]),
            true,
            {
                "cells": [
                    {"cell": {"x": 1, "y": 2}, "cost_feet": 0},
                    {"cell": {"x": 2, "y": 2}, "cost_feet": 10},
                ],
            },
        )
    )
    await process_frame

    scene.call("_request_path", {"x": 2, "y": 2})
    var path := _last_preview(transport, "spatial.path")
    _check(not path.is_empty(), "hovered destination requests authoritative path preview")
    transport.queue_message(
        Protocol.make_response(
            "preview.result",
            str(path["request_id"]),
            str(path["correlation_id"]),
            int(path["generation"]),
            true,
            {
                "legal": true,
                "path": [{"x": 1, "y": 2}, {"x": 2, "y": 2}],
                "cost_feet": 10,
                "reason": "",
            },
        )
    )
    await process_frame

    var command_request_id: String = shell.interaction_controller().confirm_current_intent()
    _check(not command_request_id.is_empty(), "legal path arms a confirmable command intent")
    var move_command := _last_message(transport, "command.submit")
    _check(
        str(move_command["payload"]["command"].get("command_type", "")) == "tactical.move",
        "confirmation submits one typed tactical.move command",
    )
    _check(
        int(move_command["payload"]["command"].get("expected_sequence", -1)) == 0,
        "move command carries authoritative expected sequence",
    )

    var presentation_count := [0]
    shell.client_state().presentation_events_received.connect(
        func(events: Array) -> void:
            presentation_count[0] += events.size()
    )
    transport.queue_message(
        Protocol.make_response(
            "command.accepted",
            str(move_command["request_id"]),
            str(move_command["correlation_id"]),
            int(move_command["generation"]),
            true,
            {
                "snapshot": _snapshot(1, {"x": 2, "y": 2}, 20),
                "presentation_events": [
                    {
                        "sequence": 1,
                        "type": "tactical.actor_moved",
                        "actor_id": "actor:ember",
                        "payload": {
                            "from": {"x": 1, "y": 2},
                            "to": {"x": 2, "y": 2},
                            "cost_feet": 10,
                        },
                    },
                ],
                "result": {"cost_feet": 10},
            },
        )
    )
    await process_frame
    _check(
        shell.client_state().authoritative.sequence() == 1,
        "accepted command replaces mirror with fresh authoritative snapshot",
    )
    _check(presentation_count[0] == 1, "resolved presentation events are forwarded separately")
    var ember = scene.actor_view("actor:ember")
    _check(
        ember != null and is_equal_approx(ember.global_position.x, 2.0),
        "actor presentation reconciles to authoritative logical position",
    )

    scene.request_strike_mode()
    scene.call("_request_attack_preview", "actor:shale")
    var attack_preview := _last_preview(transport, "tactical.attack")
    _check(not attack_preview.is_empty(), "Strike requests engine attack preview")
    transport.queue_message(
        Protocol.make_response(
            "preview.result",
            str(attack_preview["request_id"]),
            str(attack_preview["correlation_id"]),
            int(attack_preview["generation"]),
            true,
            {
                "legal": true,
                "reason": "",
                "attacker_id": "actor:ember",
                "target_id": "actor:shale",
                "distance_feet": 5,
                "reach_feet": 5,
                "visible": true,
                "cover": "half",
                "cover_sources": ["terrain:demo"],
            },
        )
    )
    await process_frame
    var strike_request_id: String = shell.interaction_controller().confirm_current_intent()
    _check(not strike_request_id.is_empty(), "engine-approved target arms strike command")
    var strike_command := _last_message(transport, "command.submit")
    _check(
        str(strike_command["payload"]["command"].get("command_type", "")) == "tactical.attack",
        "client trusts authoritative attack preview and submits typed intent",
    )

    scene.call("_on_area_debug_requested")
    var area := _last_preview(transport, "spatial.area")
    _check(not area.is_empty(), "AoE debug overlay asks engine for area membership")

    shell.shutdown()
    root.remove_child(shell)
    shell.queue_free()
    await process_frame


func _snapshot(sequence: int, ember_position: Dictionary, movement: int) -> Dictionary:
    return {
        "schema_version": 1,
        "state": {
            "campaign_id": "campaign:v07-client",
            "session_id": "session:v07-client",
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
                    _actor("actor:ember", "Ember Scout", "ember", ember_position, movement, true),
                    _actor("actor:shale", "Shale Warden", "shale", {"x": 6, "y": 3}, 0, false),
                ],
                "space": {
                    "space_id": "space:sunken-courtyard",
                    "width": 8,
                    "height": 6,
                    "cell_size_feet": 5,
                    "camera_bounds": {"min_x": 0, "min_y": 0, "max_x": 7, "max_y": 5},
                    "terrain": [
                        {
                            "x": 2,
                            "y": 2,
                            "terrain_id": "terrain:shallow-water",
                            "elevation_feet": 0,
                            "difficult": true,
                            "blocks_movement": false,
                            "blocks_los": false,
                            "cover": "none",
                        },
                    ],
                },
                "recent_events": [],
            },
        },
        "rng": {"algorithm": "pcg32-v1", "state": 1, "increment": 3},
    }


func _actor(
    actor_id: String,
    actor_name: String,
    team: String,
    position: Dictionary,
    movement: int,
    action_available: bool,
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
            "action_available": action_available,
            "bonus_action_available": action_available,
            "reaction_available": true,
            "movement_remaining": movement,
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
