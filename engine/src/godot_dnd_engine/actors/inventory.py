"""Immutable inventory and equipment containers for shared actor state."""

from __future__ import annotations

from dataclasses import dataclass

from ..errors import ValidationError


@dataclass(frozen=True, slots=True)
class InventoryEntry:
    entry_id: str
    item_id: str
    quantity: int = 1
    tags: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if not isinstance(self.entry_id, str) or not self.entry_id.strip():
            raise ValidationError("inventory entry_id must be a non-empty string")
        if not isinstance(self.item_id, str) or not self.item_id.strip():
            raise ValidationError("inventory item_id must be a non-empty string")
        if (
            isinstance(self.quantity, bool)
            or not isinstance(self.quantity, int)
            or self.quantity < 1
        ):
            raise ValidationError("inventory quantity must be an integer >= 1")
        if any(not isinstance(tag, str) or not tag.strip() for tag in self.tags):
            raise ValidationError("inventory tags must be non-empty strings")


@dataclass(frozen=True, slots=True)
class EquipmentAssignment:
    slot_id: str
    entry_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.slot_id, str) or not self.slot_id.strip():
            raise ValidationError("equipment slot_id must be a non-empty string")
        if not isinstance(self.entry_id, str) or not self.entry_id.strip():
            raise ValidationError("equipment entry_id must be a non-empty string")


def validate_inventory_equipment(
    inventory: tuple[InventoryEntry, ...],
    equipment: tuple[EquipmentAssignment, ...],
) -> None:
    entry_ids = [entry.entry_id for entry in inventory]
    if len(entry_ids) != len(set(entry_ids)):
        raise ValidationError("inventory entries must have unique entry IDs")
    slot_ids = [assignment.slot_id for assignment in equipment]
    if len(slot_ids) != len(set(slot_ids)):
        raise ValidationError("equipment assignments must have unique slot IDs")
    known = set(entry_ids)
    for assignment in equipment:
        if assignment.entry_id not in known:
            raise ValidationError(
                f"equipment slot {assignment.slot_id!r} references unknown inventory entry"
            )
