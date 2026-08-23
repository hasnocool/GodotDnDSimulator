class_name TacticalEventPresenter
extends Node

signal event_presented(event: Dictionary)
signal event_deduplicated(event_key: String)
signal combat_log_entry(text: String)
signal actor_emphasis_requested(actor_id: String)
signal audio_cue_requested(cue_id: String)
signal vfx_cue_requested(cue_id: String, actor_id: String, payload: Dictionary)

const MAX_SEEN_EVENTS := 256

var _state: ClientStateCoordinator
var _queued := 0
var _seen_event_keys: Dictionary = {}
var _seen_order: Array[String] = []
# Standalone/headless presenter instances retain full diagnostics. Once bound to
# client state, the user-visible debug setting owns whether sequence/type/IDs appear.
var _debug_expanded := true


func bind_state(state: ClientStateCoordinator) -> void:
    if _state == state:
        return
    unbind_state()
    _state = state
    if _state != null:
        _state.presentation_events_received.connect(_on_presentation_events)
        _state.presentation.options_changed.connect(_on_presentation_options_changed)
        _debug_expanded = _state.presentation.debug_visible()


func unbind_state() -> void:
    if _state != null:
        if _state.presentation_events_received.is_connected(_on_presentation_events):
            _state.presentation_events_received.disconnect(_on_presentation_events)
        if _state.presentation.options_changed.is_connected(_on_presentation_options_changed):
            _state.presentation.options_changed.disconnect(_on_presentation_options_changed)
    _state = null
    _queued = 0


func set_debug_expanded(enabled: bool) -> void:
    _debug_expanded = enabled


func debug_expanded() -> bool:
    return _debug_expanded


func reset_deduplication() -> void:
    _seen_event_keys.clear()
    _seen_order.clear()


func queued_count() -> int:
    return _queued


func seen_event_count() -> int:
    return _seen_order.size()


func _on_presentation_options_changed() -> void:
    if _state != null:
        _debug_expanded = _state.presentation.debug_visible()


func _on_presentation_events(events: Array) -> void:
    _queued += events.size()
    for value in events:
        if typeof(value) != TYPE_DICTIONARY:
            _queued -= 1
            continue
        var event: Dictionary = (value as Dictionary).duplicate(true)
        var event_key := _event_key(event)
        if _seen_event_keys.has(event_key):
            event_deduplicated.emit(event_key)
            _queued -= 1
            continue
        _remember_event(event_key)
        _present(event)
        _queued -= 1


func _present(event: Dictionary) -> void:
    var event_type := str(event.get("type", ""))
    var actor_id := str(event.get("actor_id", ""))
    var target_id := str(event.get("target_id", ""))
    var sequence := int(event.get("sequence", -1))
    var payload_value: Variant = event.get("payload", {})
    var payload: Dictionary = (
        payload_value if typeof(payload_value) == TYPE_DICTIONARY else {}
    )
    var prefix := _prefix(sequence, event_type)
    match event_type:
        "tactical.actor_moved":
            combat_log_entry.emit(
                "%s%s moved %d ft" % [
                    prefix,
                    _identity(actor_id),
                    int(payload.get("cost_feet", 0)),
                ]
            )
            actor_emphasis_requested.emit(actor_id)
            audio_cue_requested.emit("movement")
            vfx_cue_requested.emit("movement", actor_id, payload)
        "tactical.attack_resolved":
            var outcome := "hit" if bool(payload.get("hit", false)) else "miss"
            combat_log_entry.emit(
                "%s%s %s %s (%d damage)" % [
                    prefix,
                    _identity(actor_id),
                    outcome,
                    _identity(target_id),
                    int(payload.get("damage", 0)),
                ]
            )
            actor_emphasis_requested.emit(target_id)
            audio_cue_requested.emit("attack_hit" if outcome == "hit" else "attack_miss")
            vfx_cue_requested.emit(
                "damage" if outcome == "hit" else "miss",
                target_id,
                payload,
            )
        "tactical.spell_resolved":
            _present_spell(prefix, actor_id, payload)
        "tactical.spell_duration_expired":
            combat_log_entry.emit(
                "%sSpell effect ended · %s" % [prefix, str(payload.get("spell_id", ""))]
            )
            audio_cue_requested.emit("spell_expired")
            vfx_cue_requested.emit("status_expired", actor_id, payload)
        "tactical.turn_started":
            combat_log_entry.emit("%sTurn: %s" % [prefix, _identity(actor_id)])
            actor_emphasis_requested.emit(actor_id)
            audio_cue_requested.emit("turn_started")
        "tactical.encounter_ended":
            combat_log_entry.emit(
                "%sEncounter complete · %s" % [
                    prefix,
                    str(payload.get("winner_team", "")),
                ]
            )
            audio_cue_requested.emit("encounter_complete")
        _:
            combat_log_entry.emit("%s%s" % [prefix, event_type])
    event_presented.emit(event)


func _present_spell(prefix: String, actor_id: String, payload: Dictionary) -> void:
    var spell_id := str(payload.get("spell_id", "spell"))
    var effect_kinds := _string_array(payload.get("effect_kinds", []))
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
            target_summaries.append(
                "%s %s %d" % [_identity(target_id), outcome, amount_total]
            )
            if not target_id.is_empty():
                actor_emphasis_requested.emit(target_id)
                vfx_cue_requested.emit(_spell_vfx_cue(effect_kinds), target_id, target)
    var suffix := ""
    if not target_summaries.is_empty():
        suffix = " · %s" % ", ".join(target_summaries)
    combat_log_entry.emit(
        "%s%s cast %s%s" % [prefix, _identity(actor_id), spell_id, suffix]
    )
    actor_emphasis_requested.emit(actor_id)
    audio_cue_requested.emit("spell_resolved")


func _prefix(sequence: int, event_type: String) -> String:
    if not _debug_expanded:
        return ""
    return "[%d] %s · " % [sequence, event_type]


func _identity(actor_id: String) -> String:
    if _debug_expanded:
        return actor_id
    if actor_id.is_empty():
        return "Actor"
    return actor_id.get_slice(":", actor_id.get_slice_count(":") - 1).replace("-", " ").capitalize()


func _spell_vfx_cue(effect_kinds: Array[String]) -> String:
    for kind in effect_kinds:
        if kind.contains("heal"):
            return "healing"
    for kind in effect_kinds:
        if kind.contains("damage"):
            return "damage"
    return "status"


func _string_array(value: Variant) -> Array[String]:
    var rows: Array[String] = []
    if typeof(value) != TYPE_ARRAY:
        return rows
    for raw in value:
        if typeof(raw) == TYPE_STRING:
            rows.append(str(raw))
    return rows


func _event_key(event: Dictionary) -> String:
    var payload_value: Variant = event.get("payload", {})
    var payload: Dictionary = (
        payload_value if typeof(payload_value) == TYPE_DICTIONARY else {}
    )
    return "%s|%s|%s|%s|%s" % [
        str(event.get("sequence", "?")),
        str(event.get("type", "")),
        str(event.get("actor_id", "")),
        str(event.get("target_id", "")),
        JSON.stringify(payload),
    ]


func _remember_event(event_key: String) -> void:
    _seen_event_keys[event_key] = true
    _seen_order.append(event_key)
    if _seen_order.size() <= MAX_SEEN_EVENTS:
        return
    var stale: String = str(_seen_order.pop_front())
    _seen_event_keys.erase(stale)
