# engine/src/godot_dnd_engine/combat/serialization.py
"""Canonical combat event serialization and deterministic RNG continuation."""

from __future__ import annotations

import json
from typing import Any

from ..errors import ValidationError
from ..models import RNGCheckpoint
from ..rng import DeterministicRNG
from .model import CombatEvent, EventValue


def _checkpoint_to_dict(checkpoint: RNGCheckpoint | None) -> dict[str, object] | None:
    if checkpoint is None:
        return None
    return {
        "algorithm": checkpoint.algorithm,
        "state": checkpoint.state,
        "increment": checkpoint.increment,
    }


def event_to_dict(event: CombatEvent) -> dict[str, object]:
    payload: dict[str, object] = {}
    for key, value in event.payload:
        payload[key] = list(value) if isinstance(value, tuple) else value
    return {
        "sequence": event.sequence,
        "event_type": event.event_type,
        "actor_id": event.actor_id,
        "target_id": event.target_id,
        "payload": payload,
        "schema_version": event.schema_version,
        "rng_after": _checkpoint_to_dict(event.rng_after),
    }


def serialize_event(event: CombatEvent) -> str:
    return json.dumps(event_to_dict(event), sort_keys=True, separators=(",", ":"))


def _event_value(value: Any) -> EventValue:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return tuple(value)
    raise ValidationError("combat event payload contains an unsupported value")


def _checkpoint_from_raw(value: Any) -> RNGCheckpoint | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValidationError("combat event rng_after must be an object or null")
    try:
        return RNGCheckpoint(
            algorithm=value["algorithm"],
            state=value["state"],
            increment=value["increment"],
        )
    except KeyError as exc:
        raise ValidationError("combat event rng_after is missing a required field") from exc


def deserialize_event(value: str) -> CombatEvent:
    raw: Any = json.loads(value)
    if not isinstance(raw, dict):
        raise ValidationError("serialized combat event must be a JSON object")
    payload_raw = raw.get("payload")
    if not isinstance(payload_raw, dict):
        raise ValidationError("serialized combat event payload must be an object")
    payload = tuple(
        (str(key), _event_value(item))
        for key, item in payload_raw.items()
    )
    sequence = raw.get("sequence")
    event_type = raw.get("event_type")
    schema_version = raw.get("schema_version")
    if not isinstance(sequence, int):
        raise ValidationError("sequence must be an integer")
    if not isinstance(event_type, str):
        raise ValidationError("event_type must be a string")
    if not isinstance(schema_version, int):
        raise ValidationError("schema_version must be an integer")
    return CombatEvent(
        sequence=sequence,
        event_type=event_type,
        actor_id=raw.get("actor_id"),
        target_id=raw.get("target_id"),
        payload=payload,
        schema_version=schema_version,
        rng_after=_checkpoint_from_raw(raw.get("rng_after")),
    )


def serialize_log(events: tuple[CombatEvent, ...]) -> str:
    return "\n".join(serialize_event(event) for event in events)


def deserialize_log(value: str) -> tuple[CombatEvent, ...]:
    if not value.strip():
        return ()
    return tuple(deserialize_event(line) for line in value.splitlines() if line.strip())


def rng_from_events(events: tuple[CombatEvent, ...]) -> DeterministicRNG:
    """Restore the exact future combat RNG position from the latest checkpointed event."""

    for event in reversed(events):
        checkpoint = event.rng_after
        if checkpoint is None:
            continue
        if checkpoint.algorithm != DeterministicRNG.ALGORITHM:
            raise ValidationError(
                f"unsupported combat RNG algorithm: {checkpoint.algorithm!r}"
            )
        return DeterministicRNG.restore((checkpoint.state, checkpoint.increment))
    raise ValidationError("combat event log contains no RNG checkpoint")
