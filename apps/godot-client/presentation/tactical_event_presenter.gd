class_name TacticalEventPresenter
extends Node

signal event_presented(event: Dictionary)
signal combat_log_entry(text: String)
signal actor_emphasis_requested(actor_id: String)
signal audio_cue_requested(cue_id: String)

var _state: ClientStateCoordinator
var _queued := 0


func bind_state(state: ClientStateCoordinator) -> void:
    if _state == state:
        return
    unbind_state()
    _state = state
    if _state != null:
        _state.presentation_events_received.connect(_on_presentation_events)


func unbind_state() -> void:
    if _state != null and _state.presentation_events_received.is_connected(_on_presentation_events):
        _state.presentation_events_received.disconnect(_on_presentation_events)
    _state = null
    _queued = 0


func queued_count() -> int:
    return _queued


func _on_presentation_events(events: Array) -> void:
    _queued += events.size()
    for value in events:
        if typeof(value) != TYPE_DICTIONARY:
            _queued -= 1
            continue
        var event: Dictionary = (value as Dictionary).duplicate(true)
        _present(event)
        _queued -= 1


func _present(event: Dictionary) -> void:
    var event_type := str(event.get("type", ""))
    var actor_id := str(event.get("actor_id", ""))
    var target_id := str(event.get("target_id", ""))
    var payload_value: Variant = event.get("payload", {})
    var payload: Dictionary = (
        payload_value if typeof(payload_value) == TYPE_DICTIONARY else {}
    )
    match event_type:
        "tactical.actor_moved":
            combat_log_entry.emit(
                "%s moved %d ft" % [actor_id, int(payload.get("cost_feet", 0))]
            )
            actor_emphasis_requested.emit(actor_id)
            audio_cue_requested.emit("movement")
        "tactical.attack_resolved":
            var outcome := "hit" if bool(payload.get("hit", false)) else "miss"
            combat_log_entry.emit(
                "%s %s %s (%d damage)" % [
                    actor_id,
                    outcome,
                    target_id,
                    int(payload.get("damage", 0)),
                ]
            )
            actor_emphasis_requested.emit(target_id)
            audio_cue_requested.emit("attack_hit" if outcome == "hit" else "attack_miss")
        "tactical.spell_resolved":
            _present_spell(actor_id, payload)
        "tactical.spell_duration_expired":
            combat_log_entry.emit(
                "Spell effect ended · %s" % str(payload.get("spell_id", ""))
            )
            audio_cue_requested.emit("spell_expired")
        "tactical.turn_started":
            combat_log_entry.emit("Turn: %s" % actor_id)
            actor_emphasis_requested.emit(actor_id)
            audio_cue_requested.emit("turn_started")
        "tactical.encounter_ended":
            combat_log_entry.emit(
                "Encounter complete · %s" % str(payload.get("winner_team", ""))
            )
            audio_cue_requested.emit("encounter_complete")
        _:
            combat_log_entry.emit(event_type)
    event_presented.emit(event)


func _present_spell(actor_id: String, payload: Dictionary) -> void:
    var spell_id := str(payload.get("spell_id", "spell"))
    var target_summaries: Array[String] = []
    var targets_value: Variant = payload.get("targets", [])
    if typeof(targets_value) == TYPE_ARRAY:
        for target_value in targets_value:
            if typeof(target_value) != TYPE_DICTIONARY:
                continue
            var target: Dictionary = target_value
            var target_id := str(target.get("target_id", ""))
            var amounts_value: Variant = target.get("amounts", [])
            var amount_total := 0
            if typeof(amounts_value) == TYPE_ARRAY:
                for amount in amounts_value:
                    if typeof(amount) == TYPE_INT or typeof(amount) == TYPE_FLOAT:
                        amount_total += int(amount)
            var outcome := "resolved"
            if target.get("success") != null:
                outcome = "success" if bool(target.get("success")) else "failed"
            target_summaries.append("%s %s %d" % [target_id, outcome, amount_total])
            if not target_id.is_empty():
                actor_emphasis_requested.emit(target_id)
    var suffix := ""
    if not target_summaries.is_empty():
        suffix = " · %s" % ", ".join(target_summaries)
    combat_log_entry.emit("%s cast %s%s" % [actor_id, spell_id, suffix])
    actor_emphasis_requested.emit(actor_id)
    audio_cue_requested.emit("spell_resolved")
