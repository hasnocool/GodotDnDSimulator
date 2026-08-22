# engine/src/godot_dnd_engine/world/model.py
"""Authoritative v1.0 campaign/world domain contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Mapping

from ..errors import ValidationError


class QuestStatus(StrEnum):
    LOCKED = "locked"
    AVAILABLE = "available"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class AreaDefinition:
    area_id: str
    name: str
    exits: tuple[str, ...] = ()
    tags: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        _require_id(self.area_id, "area_id")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValidationError("area name must be non-empty")
        _require_unique_ids(self.exits, "area exits")


@dataclass(frozen=True, slots=True)
class DialogueChoice:
    choice_id: str
    text: str
    next_node_id: str | None = None
    set_flags: tuple[str, ...] = ()
    clear_flags: tuple[str, ...] = ()
    required_flags: frozenset[str] = frozenset()
    forbidden_flags: frozenset[str] = frozenset()
    quest_id: str | None = None
    quest_status: QuestStatus | None = None

    def __post_init__(self) -> None:
        _require_id(self.choice_id, "dialogue choice_id")
        if not isinstance(self.text, str) or not self.text.strip():
            raise ValidationError("dialogue choice text must be non-empty")
        if self.next_node_id is not None:
            _require_id(self.next_node_id, "dialogue next_node_id")
        _require_unique_ids(self.set_flags, "dialogue set_flags")
        _require_unique_ids(self.clear_flags, "dialogue clear_flags")
        if set(self.set_flags).intersection(self.clear_flags):
            raise ValidationError("dialogue choice cannot set and clear the same flag")
        if self.quest_status is not None and self.quest_id is None:
            raise ValidationError("dialogue quest_status requires quest_id")


@dataclass(frozen=True, slots=True)
class DialogueNode:
    node_id: str
    speaker: str
    text: str
    choices: tuple[DialogueChoice, ...] = ()

    def __post_init__(self) -> None:
        _require_id(self.node_id, "dialogue node_id")
        if not isinstance(self.speaker, str) or not self.speaker.strip():
            raise ValidationError("dialogue speaker must be non-empty")
        if not isinstance(self.text, str) or not self.text.strip():
            raise ValidationError("dialogue text must be non-empty")
        _require_unique_ids(tuple(item.choice_id for item in self.choices), "dialogue choices")


@dataclass(frozen=True, slots=True)
class DialogueDefinition:
    dialogue_id: str
    start_node_id: str
    nodes: tuple[DialogueNode, ...]

    def __post_init__(self) -> None:
        _require_id(self.dialogue_id, "dialogue_id")
        _require_id(self.start_node_id, "start_node_id")
        node_ids = tuple(item.node_id for item in self.nodes)
        _require_unique_ids(node_ids, "dialogue nodes")
        if self.start_node_id not in node_ids:
            raise ValidationError("dialogue start node is not present")
        known = set(node_ids)
        for node in self.nodes:
            for choice in node.choices:
                if choice.next_node_id is not None and choice.next_node_id not in known:
                    raise ValidationError("dialogue choice references unknown next node")


@dataclass(frozen=True, slots=True)
class QuestDefinition:
    quest_id: str
    title: str
    description: str
    start_status: QuestStatus = QuestStatus.AVAILABLE

    def __post_init__(self) -> None:
        _require_id(self.quest_id, "quest_id")
        if not isinstance(self.title, str) or not self.title.strip():
            raise ValidationError("quest title must be non-empty")
        if not isinstance(self.description, str):
            raise ValidationError("quest description must be a string")


@dataclass(frozen=True, slots=True)
class ShopItem:
    item_id: str
    buy_price: int
    sell_price: int
    stock: int | None = None

    def __post_init__(self) -> None:
        _require_id(self.item_id, "shop item_id")
        for label, value in (("buy_price", self.buy_price), ("sell_price", self.sell_price)):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValidationError(f"shop {label} must be an integer >= 0")
        if self.stock is not None and (
            isinstance(self.stock, bool) or not isinstance(self.stock, int) or self.stock < 0
        ):
            raise ValidationError("shop stock must be None or an integer >= 0")


@dataclass(frozen=True, slots=True)
class ShopDefinition:
    shop_id: str
    area_id: str
    name: str
    items: tuple[ShopItem, ...]

    def __post_init__(self) -> None:
        _require_id(self.shop_id, "shop_id")
        _require_id(self.area_id, "shop area_id")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValidationError("shop name must be non-empty")
        _require_unique_ids(tuple(item.item_id for item in self.items), "shop items")


@dataclass(frozen=True, slots=True)
class InteractionDefinition:
    interaction_id: str
    area_id: str
    name: str
    dc: int
    ability: str
    success_flags: tuple[str, ...] = ()
    failure_flags: tuple[str, ...] = ()
    reward_item_id: str | None = None
    reward_currency: int = 0

    def __post_init__(self) -> None:
        _require_id(self.interaction_id, "interaction_id")
        _require_id(self.area_id, "interaction area_id")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValidationError("interaction name must be non-empty")
        if isinstance(self.dc, bool) or not isinstance(self.dc, int) or not 0 <= self.dc <= 40:
            raise ValidationError("interaction dc must be an integer from 0 through 40")
        if not isinstance(self.ability, str) or not self.ability.strip():
            raise ValidationError("interaction ability must be non-empty")
        if isinstance(self.reward_currency, bool) or not isinstance(self.reward_currency, int):
            raise ValidationError("interaction reward_currency must be an integer")
        if self.reward_item_id is not None:
            _require_id(self.reward_item_id, "interaction reward_item_id")


@dataclass(frozen=True, slots=True)
class EncounterGate:
    encounter_id: str
    area_id: str
    name: str
    required_flags: frozenset[str] = frozenset()
    completion_flags: tuple[str, ...] = ()
    boss: bool = False

    def __post_init__(self) -> None:
        _require_id(self.encounter_id, "encounter_id")
        _require_id(self.area_id, "encounter area_id")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValidationError("encounter name must be non-empty")
        _require_unique_ids(self.completion_flags, "encounter completion_flags")


@dataclass(frozen=True, slots=True)
class CampaignDefinition:
    campaign_id: str
    title: str
    start_area_id: str
    areas: tuple[AreaDefinition, ...]
    dialogues: tuple[DialogueDefinition, ...] = ()
    quests: tuple[QuestDefinition, ...] = ()
    shops: tuple[ShopDefinition, ...] = ()
    interactions: tuple[InteractionDefinition, ...] = ()
    encounters: tuple[EncounterGate, ...] = ()

    def __post_init__(self) -> None:
        _require_id(self.campaign_id, "campaign_id")
        if not isinstance(self.title, str) or not self.title.strip():
            raise ValidationError("campaign title must be non-empty")
        area_ids = tuple(item.area_id for item in self.areas)
        _require_unique_ids(area_ids, "campaign areas")
        if self.start_area_id not in area_ids:
            raise ValidationError("campaign start area is unknown")
        known_areas = set(area_ids)
        for area in self.areas:
            if set(area.exits) - known_areas:
                raise ValidationError(f"area {area.area_id!r} references unknown exit")
        for label, ids in (
            ("dialogues", tuple(item.dialogue_id for item in self.dialogues)),
            ("quests", tuple(item.quest_id for item in self.quests)),
            ("shops", tuple(item.shop_id for item in self.shops)),
            ("interactions", tuple(item.interaction_id for item in self.interactions)),
            ("encounters", tuple(item.encounter_id for item in self.encounters)),
        ):
            _require_unique_ids(ids, f"campaign {label}")
        for item in (*self.shops, *self.interactions, *self.encounters):
            if item.area_id not in known_areas:
                raise ValidationError("campaign content references unknown area")


@dataclass(frozen=True, slots=True)
class WorldState:
    sequence: int
    current_area_id: str
    party_ids: tuple[str, ...]
    flags: frozenset[str]
    quests: tuple[tuple[str, QuestStatus], ...]
    inventory: tuple[tuple[str, int], ...]
    equipped: tuple[tuple[str, str], ...]
    currency: int
    active_dialogue: tuple[str, str] | None
    completed_encounters: frozenset[str]
    journal: tuple[str, ...]
    rest_count: int

    def quest_map(self) -> Mapping[str, QuestStatus]:
        return MappingProxyType(dict(self.quests))

    def inventory_map(self) -> Mapping[str, int]:
        return MappingProxyType(dict(self.inventory))

    def equipped_map(self) -> Mapping[str, str]:
        return MappingProxyType(dict(self.equipped))


@dataclass(frozen=True, slots=True)
class WorldEvent:
    sequence: int
    event_type: str
    payload: tuple[tuple[str, object], ...]
    rng_after: tuple[int, int] | None = None

    def payload_map(self) -> Mapping[str, object]:
        return MappingProxyType(dict(self.payload))


def _require_id(value: object, label: str) -> None:
    if not isinstance(value, str) or not value.strip() or ":" not in value:
        raise ValidationError(f"{label} must be a non-empty namespaced ID")


def _require_unique_ids(values: tuple[str, ...], label: str) -> None:
    if len(values) != len(set(values)):
        raise ValidationError(f"{label} must be unique")
    for value in values:
        _require_id(value, label)
