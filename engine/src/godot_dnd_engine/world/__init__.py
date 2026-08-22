# engine/src/godot_dnd_engine/world/__init__.py
"""Authoritative v1.0 campaign/world runtime API."""

from .content import demo_campaign
from .model import (
    AreaDefinition,
    CampaignDefinition,
    DialogueChoice,
    DialogueDefinition,
    DialogueNode,
    EncounterGate,
    InteractionDefinition,
    QuestDefinition,
    QuestStatus,
    ShopDefinition,
    ShopItem,
    WorldEvent,
    WorldState,
)
from .runtime import WorldRuntime, apply_world_event, event_to_dict, replay_world_events
from .serialization import restore_world_runtime

__all__ = [
    "AreaDefinition",
    "CampaignDefinition",
    "DialogueChoice",
    "DialogueDefinition",
    "DialogueNode",
    "EncounterGate",
    "InteractionDefinition",
    "QuestDefinition",
    "QuestStatus",
    "ShopDefinition",
    "ShopItem",
    "WorldEvent",
    "WorldRuntime",
    "WorldState",
    "apply_world_event",
    "demo_campaign",
    "event_to_dict",
    "replay_world_events",
    "restore_world_runtime",
]
