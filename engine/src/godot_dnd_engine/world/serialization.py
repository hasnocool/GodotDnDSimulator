# engine/src/godot_dnd_engine/world/serialization.py
"""Versioned v1.0 world snapshot and event restoration."""

from __future__ import annotations

from typing import Any

from ..errors import ValidationError
from ..rng import DeterministicRNG
from .model import CampaignDefinition, QuestStatus, WorldEvent, WorldState
from .runtime import WorldRuntime, replay_world_events


def restore_world_runtime(
    definition: CampaignDefinition,
    snapshot: dict[str, Any],
) -> WorldRuntime:
    if snapshot.get("schema_version") != 1:
        raise ValidationError(
            "unsupported world snapshot schema version"
        )
    state_value = _dict(snapshot.get("state"), "world snapshot state")
    if state_value.get("campaign_id") != definition.campaign_id:
        raise ValidationError(
            "world snapshot campaign does not match definition"
        )
    initial_rng = _rng_checkpoint(
        snapshot.get("rng_initial"),
        "world snapshot initial rng",
    )
    final_rng = _rng_checkpoint(
        snapshot.get("rng"),
        "world snapshot rng",
    )
    state = _state_from_dict(definition, state_value)

    events_value = snapshot.get("events", [])
    if not isinstance(events_value, list):
        raise ValidationError("world snapshot events must be an array")
    events = tuple(_event_from_dict(item) for item in events_value)
    if state.sequence == 0 and events:
        raise ValidationError(
            "zero-sequence world snapshot cannot contain events"
        )
    if state.sequence > 0 and not events:
        raise ValidationError(
            "nonzero world snapshot requires complete event history"
        )

    canonical_initial = WorldRuntime(definition, seed=0).state
    try:
        replayed_state = replay_world_events(canonical_initial, events)
    except (SequenceError, UnsupportedCommandError, ValueError) as exc:
        raise ValidationError(
            "world snapshot event history is not replayable"
        ) from exc
    if replayed_state != state:
        raise ValidationError(
            "world snapshot state does not match replayed event history"
        )
    _validate_rng_history(events, initial_rng, final_rng)

    runtime = WorldRuntime(definition, seed=0)
    runtime.initial_rng = initial_rng
    runtime.state = state
    runtime.rng = DeterministicRNG.restore(final_rng)
    runtime.events = list(events)
    return runtime


def _state_from_dict(
    definition: CampaignDefinition,
    value: dict[str, Any],
) -> WorldState:
    area_value = _dict(value.get("area"), "world area")
    area_id = _string(area_value.get("area_id"), "area_id")
    if area_id not in {item.area_id for item in definition.areas}:
        raise ValidationError(
            "world snapshot references unknown area"
        )
    quests_value = _dict(value.get("quests", {}), "world quests")
    quests: list[tuple[str, QuestStatus]] = []
    known_quests = {item.quest_id for item in definition.quests}
    for quest_id, status_value in quests_value.items():
        if quest_id not in known_quests:
            raise ValidationError(
                "world snapshot references unknown quest"
            )
        try:
            status = QuestStatus(
                _string(status_value, "quest status")
            )
        except ValueError as exc:
            raise ValidationError(
                "world snapshot contains invalid quest status"
            ) from exc
        quests.append((quest_id, status))

    active_value = value.get("active_dialogue")
    active: tuple[str, str] | None = None
    if active_value is not None:
        active_dict = _dict(active_value, "active_dialogue")
        active = (
            _string(active_dict.get("dialogue_id"), "dialogue_id"),
            _string(active_dict.get("node_id"), "node_id"),
        )

    inventory = _integer_map(
        value.get("inventory", {}),
        "inventory",
        minimum=1,
    )
    equipped = _string_map(
        value.get("equipped", {}),
        "equipped",
    )
    shop_stock = _integer_map(
        value.get("shop_stock", {}),
        "shop_stock",
        minimum=0,
    )
    completed_interactions = _string_tuple(
        value.get("completed_interactions", []),
        "completed_interactions",
    )
    completed_encounters = _string_tuple(
        value.get("completed_encounters", []),
        "completed_encounters",
    )
    journal = _string_tuple(
        value.get("journal", []),
        "journal",
        allow_empty=True,
    )
    return WorldState(
        sequence=_integer(
            value.get("sequence"),
            "sequence",
            minimum=0,
        ),
        current_area_id=area_id,
        party_ids=_string_tuple(
            value.get("party_ids", []),
            "party_ids",
        ),
        flags=frozenset(
            _string_tuple(value.get("flags", []), "flags")
        ),
        quests=tuple(sorted(quests)),
        inventory=tuple(sorted(inventory.items())),
        equipped=tuple(sorted(equipped.items())),
        shop_stock=tuple(sorted(shop_stock.items())),
        currency=_integer(
            value.get("currency"),
            "currency",
            minimum=0,
        ),
        active_dialogue=active,
        completed_interactions=frozenset(completed_interactions),
        completed_encounters=frozenset(completed_encounters),
        journal=journal,
        rest_count=_integer(
            value.get("rest_count"),
            "rest_count",
            minimum=0,
        ),
    )


def _event_from_dict(value: object) -> WorldEvent:
    event = _dict(value, "world event")
    rng_value = event.get("rng_after")
    rng_after: tuple[int, int] | None = None
    if rng_value is not None:
        rng_after = _rng_checkpoint(
            rng_value,
            "world event rng_after",
            require_algorithm=False,
        )
    payload = _dict(event.get("payload"), "world event payload")
    return WorldEvent(
        sequence=_integer(
            event.get("sequence"),
            "event sequence",
            minimum=1,
        ),
        event_type=_string(event.get("type"), "event type"),
        payload=tuple(sorted(payload.items())),
        rng_after=rng_after,
    )


def _validate_rng_history(
    events: tuple[WorldEvent, ...],
    initial: tuple[int, int],
    final: tuple[int, int],
) -> None:
    rng = DeterministicRNG.restore(initial)
    for event in events:
        if event.event_type != "world.interaction_resolved":
            if event.rng_after is not None:
                raise ValidationError(
                    "non-random world event cannot carry rng_after"
                )
            continue
        payload = event.payload_map()
        expected_roll = rng.roll_die(20)
        if payload.get("roll") != expected_roll:
            raise ValidationError(
                "world interaction roll does not match RNG replay"
            )
        if event.rng_after != rng.snapshot():
            raise ValidationError(
                "world interaction rng_after does not match RNG replay"
            )
    if rng.snapshot() != final:
        raise ValidationError(
            "world snapshot final RNG does not match replayed history"
        )


def _rng_checkpoint(
    value: object,
    label: str,
    *,
    require_algorithm: bool = True,
) -> tuple[int, int]:
    raw = _dict(value, label)
    if require_algorithm and raw.get("algorithm") != DeterministicRNG.ALGORITHM:
        raise ValidationError(f"{label} uses unsupported RNG algorithm")
    checkpoint = (
        _integer(raw.get("state"), "rng state", minimum=0),
        _integer(raw.get("increment"), "rng increment", minimum=0),
    )
    DeterministicRNG.restore(checkpoint)
    return checkpoint


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
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < minimum
    ):
        raise ValidationError(
            f"{label} must be an integer >= {minimum}"
        )
    return value


def _integer_map(
    value: object,
    label: str,
    *,
    minimum: int,
) -> dict[str, int]:
    raw = _dict(value, label)
    return {
        _string(key, label): _integer(item, label, minimum=minimum)
        for key, item in raw.items()
    }


def _string_map(value: object, label: str) -> dict[str, str]:
    raw = _dict(value, label)
    return {
        _string(key, label): _string(item, label)
        for key, item in raw.items()
    }
