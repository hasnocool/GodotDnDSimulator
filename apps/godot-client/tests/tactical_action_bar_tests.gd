extends SceneTree

const Protocol = preload("res://bridge/bridge_protocol.gd")
const FakeTransportScript = preload("res://bridge/fake_engine_transport.gd")

var _failures := 0


func _initialize() -> void:
    call_deferred("_run")


func _run() -> void:
    var packed := load("res://scenes/shell/app_shell.tscn") as PackedScene
    _check(packed != null, "app shell loads")
    if packed == null:
        quit(1)
        return

    var shell = packed.instantiate()
    var transport = FakeTransportScript.new()
    shell.transport_override = transport
    root.add_child(shell)
    await process_frame

    var hello := _last_message(transport, "bridge.hello")
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

    var snapshot_query := _last_query(transport, "tactical.snapshot")
    transport.queue_message(
        Protocol.make_response(
            "query.result",
            str(snapshot_query["request_id"]),
            str(snapshot_query["correlation_id"]),
            int(snapshot_query["generation"]),
            true,
            {"snapshot": _snapshot()},
        )
    )
    for _index in range(60):
        await process_frame
        if shell.tactical_content() != null:
            break

    var scene = shell.tactical_content()
    _check(scene != null, "tactical scene loads")
    if scene == null:
        shell.shutdown()
        quit(1)
        return

    shell.client_state().interaction.set_selected_actor("actor:shale")
    await process_frame
    var action_query := _last_query(transport, "tactical.actions")
    _check(
        str(action_query["payload"]["query"].get("actor_id", "")) == "actor:ember",
        "action bar queries authoritative current-turn actor, not inspected actor",
    )
    transport.queue_message(
        Protocol.make_response(
            "query.result",
            str(action_query["request_id"]),
            str(action_query["correlation_id"]),
            int(action_query["generation"]),
            true,
            {
                "actor_id": "actor:ember",
                "current_actor_id": "actor:ember",
                "actions": [
                    {"action_id": "move", "enabled": true, "reason": ""},
                    {"action_id": "training_strike", "enabled": true, "reason": ""},
                    {"action_id": "end_turn", "enabled": true, "reason": ""},
                ],
            },
        )
    )
    await process_frame

    var hud = scene.tactical_hud()
    var move_button: Button = hud.get_node("ActionPanel/ActionMargin/Actions/MoveButton")
    var strike_button: Button = hud.get_node("ActionPanel/ActionMargin/Actions/StrikeButton")
    var end_button: Button = hud.get_node("ActionPanel/ActionMargin/Actions/EndTurnButton")
    _check(not move_button.disabled, "Move remains enabled while another actor is inspected")
    _check(not strike_button.disabled, "Strike remains enabled while another actor is inspected")
    _check(not end_button.disabled, "End Turn remains enabled while another actor is inspected")

    move_button.pressed.emit()
    await process_frame
    _check(
        shell.client_state().interaction.selected_actor_id() == "actor:ember",
        "Move switches action focus to current actor",
    )
    var reachable := _last_preview(transport, "spatial.reachable")
    _check(
        str(reachable["payload"]["preview"].get("entity_id", "")) == "actor:ember",
        "Move preview is requested for current actor",
    )

    strike_button.pressed.emit()
    await process_frame
    _check(
        shell.client_state().interaction.selected_actor_id() == "actor:ember",
        "Strike keeps action focus on current actor",
    )

    end_button.pressed.emit()
    await process_frame
    var command := _last_message(transport, "command.submit")
    _check(
        str(command["payload"]["command"].get("command_type", "")) == "tactical.end_turn",
        "End Turn button submits tactical.end_turn",
    )
    _check(
        str(command["payload"]["command"].get("actor_id", "")) == "actor:ember",
        "End Turn command uses authoritative current actor",
    )

    shell.shutdown()
    root.remove_child(shell)
    shell.queue_free()
    await process_frame
    if _failures == 0:
        print("Godot tactical action bar tests: PASS")
        quit(0)
    push_error("Godot tactical action bar tests: %d failure(s)" % _failures)
    quit(1)


func _snapshot() -> Dictionary:
    return {
        "schema_version": 1,
        "state": {
            "campaign_id": "campaign:action-bar-test",
            "session_id": "session:action-bar-test",
            "sequence": 0,
            "tick": 0,
            "mode": "tactical_vertical_slice",
            "tactical": {
                "slice_id": "vertical-slice:action-bar-test",
                "display_name": "Action Bar Test",
                "encounter_id": "encounter:action-bar-test",
                "status": "active",
                "round_number": 1,
                "turn_index": 0,
                "current_actor_id": "actor:ember",
                "initiative": [
                    {"actor_id": "actor:ember", "total": 18},
                    {"actor_id": "actor:shale", "total": 12},
                ],
                "actors": [
                    _actor("actor:ember", "Ember", "party", {"x": 1, "y": 2}, 30, true),
                    _actor("actor:shale", "Shale", "enemy", {"x": 4, "y": 2}, 30, false),
                ],
                "space": {
                    "space_id": "space:action-bar-test",
                    "width": 6,
                    "height": 5,
                    "cell_size_feet": 5,
                    "camera_bounds": {"min_x": 0, "min_y": 0, "max_x": 5, "max_y": 4},
                    "terrain": [],
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
        "kind": "hero" if team == "party" else "npc",
        "size": "medium",
        "team": team,
        "position": position,
        "elevation_feet": 0,
        "hit_points": {"current": 18, "maximum": 18, "temporary": 0},
        "armor_class": 13,
        "life_state": "conscious",
        "conditions": [],
        "movement_modes": [{"mode": "walk", "speed_feet": 30}],
        "economy": {
            "action_available": action_available,
            "bonus_action_available": true,
            "reaction_available": true,
            "movement_remaining": movement,
        },
    }


func _last_message(transport, kind: String) -> Dictionary:
    var sent: Array = transport.sent_messages()
    for index in range(sent.size() - 1, -1, -1):
        if str(sent[index].get("kind", "")) == kind:
            return sent[index]
    return {}


func _last_query(transport, query_type: String) -> Dictionary:
    var sent: Array = transport.sent_messages()
    for index in range(sent.size() - 1, -1, -1):
        var row: Dictionary = sent[index]
        if str(row.get("kind", "")) != "query.request":
            continue
        if str(row["payload"].get("query_type", "")) == query_type:
            return row
    return {}


func _last_preview(transport, preview_type: String) -> Dictionary:
    var sent: Array = transport.sent_messages()
    for index in range(sent.size() - 1, -1, -1):
        var row: Dictionary = sent[index]
        if str(row.get("kind", "")) != "preview.request":
            continue
        if str(row["payload"].get("preview_type", "")) == preview_type:
            return row
    return {}


func _check(condition: bool, message: String) -> void:
    if condition:
        return
    _failures += 1
    push_error("FAIL: %s" % message)
