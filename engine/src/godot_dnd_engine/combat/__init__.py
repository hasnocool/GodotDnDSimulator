# engine/src/godot_dnd_engine/combat/__init__.py
"""Deterministic v0.5 tactical-combat runtime."""

from .attacks import AttackDefinition, AttackModifiers, AttackResult
from .damage import DamageAdjustment, DamagePacket, adjust_damage
from .model import (
    COMBAT_EVENT_SCHEMA_VERSION,
    ActionEconomy,
    ActionResource,
    CombatantState,
    CombatConditionRule,
    CombatEvent,
    DeathSaveTrack,
    DefenseProfile,
    EncounterState,
    EncounterStatus,
    InitiativeEntry,
    LifeState,
    ReactionWindow,
    TemporaryHitPointChoice,
    ZeroHitPointRule,
)
from .reducer import apply_combat_event, replay_combat
from .runtime import CombatRuntime, CombatTransition
from .serialization import (
    deserialize_event,
    deserialize_log,
    event_to_dict,
    rng_from_events,
    serialize_event,
    serialize_log,
)

__all__ = [
    "COMBAT_EVENT_SCHEMA_VERSION",
    "ActionEconomy",
    "ActionResource",
    "AttackDefinition",
    "AttackModifiers",
    "AttackResult",
    "CombatConditionRule",
    "CombatEvent",
    "CombatRuntime",
    "CombatTransition",
    "CombatantState",
    "DamageAdjustment",
    "DamagePacket",
    "DeathSaveTrack",
    "DefenseProfile",
    "EncounterState",
    "EncounterStatus",
    "InitiativeEntry",
    "LifeState",
    "ReactionWindow",
    "TemporaryHitPointChoice",
    "ZeroHitPointRule",
    "adjust_damage",
    "apply_combat_event",
    "deserialize_event",
    "deserialize_log",
    "event_to_dict",
    "replay_combat",
    "rng_from_events",
    "serialize_event",
    "serialize_log",
]
