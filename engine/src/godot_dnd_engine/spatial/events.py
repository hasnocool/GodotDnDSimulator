# engine/src/godot_dnd_engine/spatial/events.py
"""Versioned spatial facts used for deterministic movement replay."""

from __future__ import annotations

from dataclasses import dataclass

from ..errors import ValidationError

SPATIAL_EVENT_SCHEMA_VERSION = 1

type CellValue = tuple[int, int]
type PathValue = tuple[CellValue, ...]
type SpatialEventValue = str | int | bool | CellValue | PathValue | tuple[str, ...] | None


@dataclass(frozen=True, slots=True)
class SpatialEvent:
    sequence: int
    event_type: str
    entity_id: str
    payload: tuple[tuple[str, SpatialEventValue], ...] = ()
    schema_version: int = SPATIAL_EVENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if (
            isinstance(self.sequence, bool)
            or not isinstance(self.sequence, int)
            or self.sequence < 1
        ):
            raise ValidationError("spatial event sequence must be an integer >= 1")
        if not isinstance(self.event_type, str) or not self.event_type.strip():
            raise ValidationError("spatial event_type must be a non-empty string")
        if not isinstance(self.entity_id, str) or not self.entity_id.strip():
            raise ValidationError("spatial event entity_id must be a non-empty string")
        if self.schema_version != SPATIAL_EVENT_SCHEMA_VERSION:
            raise ValidationError("unsupported spatial event schema version")
        keys = [key for key, _ in self.payload]
        if len(keys) != len(set(keys)):
            raise ValidationError("spatial event payload keys must be unique")
        if any(not isinstance(key, str) or not key.strip() for key in keys):
            raise ValidationError("spatial event payload keys must be non-empty strings")
        object.__setattr__(self, "payload", tuple(sorted(self.payload, key=lambda item: item[0])))

    def value(self, key: str) -> SpatialEventValue:
        match = next((value for name, value in self.payload if name == key), None)
        if match is None and key not in {name for name, _ in self.payload}:
            raise ValidationError(f"spatial event missing payload field: {key}")
        return match
