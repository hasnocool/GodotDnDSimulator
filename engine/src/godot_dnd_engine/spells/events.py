# engine/src/godot_dnd_engine/spells/events.py
"""Versioned spell events and canonical serialization."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from ..errors import ValidationError

SPELL_EVENT_SCHEMA_VERSION = 1
SpellEventValue = str | int | bool | None | tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SpellEvent:
    sequence: int
    event_type: str
    caster_id: str
    spell_id: str
    target_ids: tuple[str, ...] = ()
    payload: tuple[tuple[str, SpellEventValue], ...] = ()
    version: int = SPELL_EVENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if isinstance(self.sequence, bool) or not isinstance(self.sequence, int) or self.sequence < 1:
            raise ValidationError("spell event sequence must be an integer >= 1")
        if not self.event_type.strip() or not self.caster_id.strip() or not self.spell_id.strip():
            raise ValidationError("spell event type/caster/spell IDs must be non-empty")
        if self.version != SPELL_EVENT_SCHEMA_VERSION:
            raise ValidationError("unsupported spell event version")
        if len(self.target_ids) != len(set(self.target_ids)):
            raise ValidationError("spell event target IDs must be unique")
        keys = [key for key, _ in self.payload]
        if len(keys) != len(set(keys)) or any(not key.strip() for key in keys):
            raise ValidationError("spell event payload keys must be unique non-empty strings")
        object.__setattr__(self, "target_ids", tuple(self.target_ids))
        object.__setattr__(self, "payload", tuple(sorted(self.payload)))

    def value(self, key: str, default: SpellEventValue = None) -> SpellEventValue:
        return dict(self.payload).get(key, default)


def spell_event_to_dict(event: SpellEvent) -> dict[str, Any]:
    return {
        "version": event.version,
        "sequence": event.sequence,
        "event_type": event.event_type,
        "caster_id": event.caster_id,
        "spell_id": event.spell_id,
        "target_ids": list(event.target_ids),
        "payload": dict(event.payload),
    }


def spell_event_from_dict(value: dict[str, Any]) -> SpellEvent:
    if not isinstance(value, dict):
        raise ValidationError("spell event must be an object")
    payload = value.get("payload", {})
    target_ids = value.get("target_ids", [])
    if not isinstance(payload, dict) or not isinstance(target_ids, list):
        raise ValidationError("spell event payload/target_ids are malformed")
    try:
        return SpellEvent(
            version=value.get("version", SPELL_EVENT_SCHEMA_VERSION),
            sequence=value["sequence"],
            event_type=value["event_type"],
            caster_id=value["caster_id"],
            spell_id=value["spell_id"],
            target_ids=tuple(target_ids),
            payload=tuple(payload.items()),
        )
    except (KeyError, TypeError) as exc:
        raise ValidationError("spell event fields are malformed") from exc


def spell_events_jsonl(events: tuple[SpellEvent, ...]) -> str:
    previous = 0
    rows: list[str] = []
    for event in events:
        if event.sequence != previous + 1:
            raise ValidationError("spell event logs require contiguous sequence numbers")
        previous = event.sequence
        rows.append(json.dumps(spell_event_to_dict(event), sort_keys=True, separators=(",", ":")))
    return "\n".join(rows) + ("\n" if rows else "")
