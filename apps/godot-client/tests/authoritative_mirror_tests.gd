extends SceneTree

const MirrorScript = preload("res://state/authoritative_mirror.gd")

var _failures := 0


func _initialize() -> void:
    _test_events_require_snapshot_baseline()
    _test_snapshot_resets_post_snapshot_event_history()
    if _failures == 0:
        print("Godot authoritative mirror tests: PASS")
        quit(0)
    else:
        push_error("Godot authoritative mirror tests: %d failure(s)" % _failures)
        quit(1)


func _test_events_require_snapshot_baseline() -> void:
    var mirror = MirrorScript.new()
    _check(
        not mirror.ingest_events([{"sequence": 1, "event_type": "test.before_snapshot"}]),
        "events are rejected before a snapshot baseline",
    )
    _check(mirror.sequence() == 0, "rejected pre-snapshot events do not advance sequence")
    _check(mirror.recent_events().is_empty(), "rejected pre-snapshot events are not retained")


func _test_snapshot_resets_post_snapshot_event_history() -> void:
    var mirror = MirrorScript.new()
    _check(mirror.ingest_snapshot(_snapshot(0)), "initial snapshot is accepted")
    _check(
        mirror.ingest_events([{"sequence": 1, "event_type": "test.first"}]),
        "post-snapshot event is accepted",
    )
    _check(mirror.recent_events().size() == 1, "post-snapshot event is retained")
    _check(mirror.ingest_snapshot(_snapshot(1)), "newer snapshot is accepted")
    _check(mirror.recent_events().is_empty(), "new snapshot supersedes retained event history")
    _check(mirror.sequence() == 1, "new snapshot sequence becomes reconstruction baseline")


func _snapshot(sequence: int) -> Dictionary:
    return {
        "schema_version": 1,
        "state": {
            "schema_version": 1,
            "campaign_id": "campaign:mirror-test",
            "session_id": "session:mirror-test",
            "sequence": sequence,
            "tick": sequence,
            "counters": {},
        },
        "rng": {
            "algorithm": "pcg32-v1",
            "state": 1,
            "increment": 3,
        },
    }


func _check(condition: bool, message: String) -> void:
    if condition:
        return
    _failures += 1
    push_error("FAIL: %s" % message)
