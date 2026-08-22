"""Canonical combat event serialization used by deterministic replay fixtures."""

from __future__ import annotations

import json

from .model import CombatEvent, EventValue


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
    }


def serialize_event(event: CombatEvent) -> str:
    return json.dumps(event_to_dict(event), sort_keys=True, separators=(",", ":"))


def deserialize_event(value: str) -> CombatEvent:
    raw = json.loads(value)
    payload: list[tuple[str, EventValue]] = []
    for key, item in raw["payload"].items():
        normalized: EventValue = tuple(item) if isinstance(item, list) else item
        payload.append((key, normalized))
    return CombatEvent(
        sequence=raw["sequence"],
        event_type=raw["event_type"],
        actor_id=raw["actor_id"],
        target_id=raw["target_id"],
        payload=tuple(payload),
        schema_version=raw["schema_version"],
    )


def serialize_log(events: tuple[CombatEvent, ...]) -> str:
    return "\n".join(serialize_event(event) for event in events)


def deserialize_log(value: str) -> tuple[CombatEvent, ...]:
    if not value.strip():
        return ()
    return tuple(deserialize_event(line) for line in value.splitlines() if line.strip())
