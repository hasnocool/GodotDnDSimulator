extends SceneTree

const Protocol = preload("res://bridge/bridge_protocol.gd")
const FakeTransportScript = preload("res://bridge/fake_engine_transport.gd")

var _failures := 0


func _initialize() -> void:
    call_deferred("_run")


func _run() -> void:
    await _test_rules_driven_creator_flow()
    if _failures == 0:
        print("Godot character creator tests: PASS")
        quit(0)
    else:
        push_error("Godot character creator tests: %d failure(s)" % _failures)
        quit(1)


func _test_rules_driven_creator_flow() -> void:
    var shell_scene := load("res://scenes/shell/app_shell.tscn") as PackedScene
    _check(shell_scene != null, "app shell loads for creator test")
    if shell_scene == null:
        return
    var shell = shell_scene.instantiate()
    var transport = FakeTransportScript.new()
    shell.transport_override = transport
    root.add_child(shell)
    await process_frame

    var hello := _last_message(transport, "bridge.hello")
    _check(not hello.is_empty(), "creator shell sends bridge hello")
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
                    "characters.creator.v1",
                    "characters.creator.commands.v1",
                    "characters.levelup.v1",
                ],
            },
        )
    )
    await process_frame

    var snapshot_request := _last_query(transport, "bridge.snapshot")
    _check(not snapshot_request.is_empty(), "creator-capable core session requests snapshot")
    transport.queue_message(
        Protocol.make_response(
            "query.result",
            str(snapshot_request["request_id"]),
            str(snapshot_request["correlation_id"]),
            int(snapshot_request["generation"]),
            true,
            {"snapshot": _snapshot()},
        )
    )
    for _index in range(60):
        await process_frame
        if shell.shell_state() == shell.ShellState.READY:
            break
    _check(shell.shell_state() == shell.ShellState.READY, "shell becomes ready")

    var launcher: Button = shell.get_node("ShellUI/CreatorButton")
    _check(launcher.visible, "creator launcher appears only with negotiated capability")
    launcher.pressed.emit()
    await process_frame
    var creator = shell.get_node("CharacterCreator")
    _check(creator.visible, "launcher opens creator overlay")

    var schema_request := _last_query(transport, "characters.creator.schema")
    _check(not schema_request.is_empty(), "creator requests engine schema")
    transport.queue_message(
        Protocol.make_response(
            "query.result",
            str(schema_request["request_id"]),
            str(schema_request["correlation_id"]),
            int(schema_request["generation"]),
            true,
            _creator_schema(),
        )
    )
    await process_frame
    _check(
        creator.call("creator_schema").get("catalog_id", "") == "catalog:test",
        "creator renders negotiated engine catalog rather than a hardcoded catalog",
    )

    for choice_id in [
        "species:test",
        "background:test",
        "class:test",
        "skill:a",
        "skill:b",
        "equipment:test",
        "feature:test",
    ]:
        creator.call("_set_choice_selected", choice_id, true)
    var draft: Dictionary = creator.call("build_draft")
    _check(
        draft.get("selected_choice_ids", []).has("class:test"),
        "draft selections come from engine-provided choice IDs",
    )
    _check(
        draft.get("ability_scores", {}).size() == 6,
        "creator builds all six ability assignments from engine policy",
    )

    creator.set("_step_index", 10)
    creator.call("_render_step")
    var preview_request := _last_query(transport, "characters.creator.preview")
    _check(not preview_request.is_empty(), "review step requests authoritative validation")
    transport.queue_message(
        Protocol.make_response(
            "query.result",
            str(preview_request["request_id"]),
            str(preview_request["correlation_id"]),
            int(preview_request["generation"]),
            true,
            {
                "legal": true,
                "errors": [],
                "warnings": [],
                "summary": {
                    "name": "New Hero",
                    "species_id": "species:test",
                    "background_id": "background:test",
                    "class_id": "class:test",
                },
            },
        )
    )
    await process_frame
    var create_button: Button = creator.get_node("Panel/Margin/VBox/Footer/Create")
    _check(not create_button.disabled, "create is enabled only after legal engine preview")
    create_button.pressed.emit()
    await process_frame
    var command := _last_message(transport, "command.submit")
    _check(not command.is_empty(), "creator submits typed command after legal preview")
    _check(
        str(command["payload"]["command"].get("command_type", "")) == "characters.create",
        "creator submits characters.create rather than mutating actor state locally",
    )

    shell.shutdown()
    root.remove_child(shell)
    shell.queue_free()
    await process_frame


func _creator_schema() -> Dictionary:
    return {
        "catalog_id": "catalog:test",
        "steps": [
            "identity", "species", "background", "class", "abilities", "skills",
            "equipment", "spells_features", "appearance", "biography", "review",
        ],
        "groups": [
            {"group_id": "species", "step": "species", "minimum": 1, "maximum": 1, "choice_ids": ["species:test"]},
            {"group_id": "background", "step": "background", "minimum": 1, "maximum": 1, "choice_ids": ["background:test"]},
            {"group_id": "class", "step": "class", "minimum": 1, "maximum": 1, "choice_ids": ["class:test"]},
            {"group_id": "skills", "step": "skills", "minimum": 2, "maximum": 2, "choice_ids": ["skill:a", "skill:b"]},
            {"group_id": "equipment", "step": "equipment", "minimum": 1, "maximum": 1, "choice_ids": ["equipment:test"]},
            {"group_id": "feature", "step": "spells_features", "minimum": 1, "maximum": 1, "choice_ids": ["feature:test"]},
        ],
        "choices": [
            {"choice_id": "species:test", "step": "species", "name": "Test Species", "description": "", "unlock_level": 1},
            {"choice_id": "background:test", "step": "background", "name": "Test Background", "description": "", "unlock_level": 1},
            {"choice_id": "class:test", "step": "class", "name": "Test Class", "description": "", "unlock_level": 1},
            {"choice_id": "skill:a", "step": "skills", "name": "Skill A", "description": "", "unlock_level": 1},
            {"choice_id": "skill:b", "step": "skills", "name": "Skill B", "description": "", "unlock_level": 1},
            {"choice_id": "equipment:test", "step": "equipment", "name": "Equipment", "description": "", "unlock_level": 1},
            {"choice_id": "feature:test", "step": "spells_features", "name": "Feature", "description": "", "unlock_level": 1},
        ],
        "ability_policies": [
            {"method_id": "standard-array", "values": [15, 14, 13, 12, 10, 8]},
        ],
        "appearance_fields": ["hair", "eyes", "portrait"],
        "profile_fields": ["biography", "personality"],
    }


func _snapshot() -> Dictionary:
    return {
        "schema_version": 1,
        "state": {
            "campaign_id": "campaign:test",
            "session_id": "session:test",
            "sequence": 0,
            "tick": 0,
        },
        "rng": {"algorithm": "pcg32-v1", "state": 1, "increment": 3},
    }


func _last_message(transport, kind: String) -> Dictionary:
    for index in range(transport.sent_messages.size() - 1, -1, -1):
        var message: Dictionary = transport.sent_messages[index]
        if str(message.get("kind", "")) == kind:
            return message
    return {}


func _last_query(transport, query_type: String) -> Dictionary:
    for index in range(transport.sent_messages.size() - 1, -1, -1):
        var message: Dictionary = transport.sent_messages[index]
        if str(message.get("kind", "")) != "query.request":
            continue
        var payload: Dictionary = message.get("payload", {})
        if str(payload.get("query_type", "")) == query_type:
            return message
    return {}


func _check(condition: bool, message: String) -> void:
    if condition:
        return
    _failures += 1
    push_error(message)
