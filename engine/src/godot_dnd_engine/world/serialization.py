# engine/src/godot_dnd_engine/world/serialization.py
"""Versioned v1.0 world snapshot and event restoration."""

from __future__ import annotations

from typing import Any

from ..errors import ValidationError
from ..rng import DeterministicRNG
from .model import CampaignDefinition, QuestStatus, WorldEvent, WorldState
from .runtime import WorldRuntime


def restore_world_runtime(
    definition: CampaignDefinition,
    snapshot: dict[str, Any],
) -> WorldRuntime:
    if snapshot.get("schema_version") != 1:
        raise ValidationError("unsupported world snapshot schema version")
    state_value = _dict(snapshot.get("state"), "world snapshot state")
    if state_value.get("campaign_id") != definition.campaign_id:
        raise ValidationError("world snapshot campaign does not match definition")
    rng_value = _dict(snapshot.get("rng"), "world snapshot rng")
    if rng_value.get("algorithm") != DeterministicRNG.ALGORITHM:
        raise ValidationError("unsupported world snapshot RNG algorithm")
    rng_state = _integer(rng_value.get("state"), "rng state", minimum=0)
    rng_increment = _integer(rng_value.get("increment"), "rng increment", minimum=0)

    runtime = WorldRuntime(definition, seed=0)
    runtime.state = _state_from_dict(definition, state_value)
    runtime.rng = DeterministicRNG.restore((rng_state, rng_increment))
    events_value = snapshot.get("events", [])
    if not isinstance(events_value, list):
        raise ValidationError("world snapshot events must be an array")
    runtime.events = [_event_from_dict(item) for item in events_value]
    if runtime.events and runtime.events[-1].sequence != runtime.state.sequence:
        raise ValidationError("world snapshot event tail does not match state sequence")
    return runtime


def _state_from_dict(
    definition: CampaignDefinition,
    value: dict[str, Any],
) -> WorldState:
    area_value = _dict(value.get("area"), "world area")
    area_id = _string(area_value.get("area_id"), "area_id")
    if area_id not in {item.area_id for item in definition.areas}:
        raise ValidationError("world snapshot references unknown area")
    quests_value = _dict(value.get("quests", {}), "world quests")
    quests: list[tuple[str, QuestStatus]] = []
    known_quests = {item.quest_id for item in definition.quests}
    for quest_id, status_value in quests_value.items():
        if quest_id not in known_quests:
            raise ValidationError("world snapshot references unknown quest")
        try:
            status = QuestStatus(_string(status_value, "quest status"))
        except ValueError as exc:
            raise ValidationError("world snapshot contains invalid quest status") from exc
        quests.append((quest_id, status))

    active_value = value.get("active_dialogue")
    active: tuple[str, str] | None = None
    if active_value is not None:
        active_dict = _dict(active_value, "active_dialogue")
        active = (
            _string(active_dict.get("dialogue_id"), "dialogue_id"),
            _string(active_dict.get("node_id"), "node_id"),
        )

    return WorldState(
        sequence=_integer(value.get("sequence"), "sequence", minimum=0),
        current_area_id=area_id,
        party_ids=_string_tuple(value.get("party_ids", []), "party_ids"),
        flags=frozenset(_string_tuple(value.get("flags", []), "flags")),
        quests=tuple(sorted(quests)),
        inventory=tuple(sorted(_integer_map(value.get("inventory", {}), "inventory").items())),
        equipped=tuple(sorted(_string_map(value.get("equipped", {}), "equipped").items())),
        currency=_integer(value.get("currency"), "currency", minimum=0),
        active_dialogue=active,
        completed_encounters=frozenset(
            _string_tuple(value.get("completed_encounters", []), "completed_encounters")
        ),
        journal=_string_tuple(value.get("journal", []), "journal", allow_empty=True),
        rest_count=_integer(value.get("rest_count"), "rest_count", minimum=0),
    )


def _event_from_dict(value: object) -> WorldEvent:
    event = _dict(value, "world event")
    rng_value = event.get("rng_after")
    rng_after: tuple[int, int] | None = None
    if rng_value is not None:
        rng_dict = _dict(rng_value, "world event rng_after")
        rng_after = (
            _integer(rng_dict.get("state"), "rng state", minimum=0),
            _integer(rng_dict.get("increment"), "rng increment", minimum=0),
        )
    payload = _dict(event.get("payload"), "world event payload")
    return WorldEvent(
        sequence=_integer(event.get("sequence"), "event sequence", minimum=1),
        event_type=_string(event.get("type"), "event type"),
        payload=tuple(sorted(payload.items())),
        rng_after=rng_after,
    )


def _dict(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError(f"{label} must be an object")
    if any(not isinstance(key, str) for key in value):
        raise ValidationError(f"{label} keys must be strings")
    return dict(value)


def _string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{label} must be a non-empty string")
    return value.strip()


def _string_tuple(
    value: object,
    label: str,
    *,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValidationError(f"{label} must be an array")
    result: list[str] = []
    for item in value:
        if allow_empty and isinstance(item, str):
            result.append(item)
        else:
            result.append(_string(item, label))
    return tuple(result)


def _integer(value: object, label: str, *, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValidationError(f"{label} must be an integer >= {minimum}")
    return value


def _integer_map(value: object, label: str) -> dict[str, int]:
    raw = _dict(value, label)
    return {
        _string(key, label): _integer(item, label, minimum=1)
        for key, item in raw.items()
    }


def _string_map(value: object, label: str) -> dict[str, str]:
    raw = _dict(value, label)
    return {_string(key, label): _string(item, label) for key, item in raw.items()}
