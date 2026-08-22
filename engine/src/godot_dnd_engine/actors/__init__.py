"""Shared v0.4 actor and character runtime."""

from .adapters import (
    ActorEffectResult,
    actors_to_rule_world,
    apply_actor_effects,
    merge_rule_world,
)
from .choices import CharacterOption, ChoiceGroup, ChoiceValidationResult, validate_choices
from .creation import (
    CharacterCreationRequest,
    CharacterCreationResult,
    CharacterCreationSpec,
    create_character,
)
from .inventory import EquipmentAssignment, InventoryEntry
from .model import (
    SKILL_ABILITIES,
    ActorKind,
    ActorState,
    DefenseState,
    HitPoints,
    MovementMode,
    MovementSpeed,
    SaveProficiency,
    Sense,
    SizeCategory,
    Skill,
    SkillProficiency,
    TrainingProficiency,
)
from .serialization import (
    ACTOR_SCHEMA_VERSION,
    actor_from_dict,
    actor_to_dict,
    deserialize_actor,
    migrate_actor_payload,
    serialize_actor,
)

__all__ = [
    "ACTOR_SCHEMA_VERSION",
    "SKILL_ABILITIES",
    "ActorEffectResult",
    "ActorKind",
    "ActorState",
    "CharacterCreationRequest",
    "CharacterCreationResult",
    "CharacterCreationSpec",
    "CharacterOption",
    "ChoiceGroup",
    "ChoiceValidationResult",
    "DefenseState",
    "EquipmentAssignment",
    "HitPoints",
    "InventoryEntry",
    "MovementMode",
    "MovementSpeed",
    "SaveProficiency",
    "Sense",
    "SizeCategory",
    "Skill",
    "SkillProficiency",
    "TrainingProficiency",
    "actor_from_dict",
    "actor_to_dict",
    "actors_to_rule_world",
    "apply_actor_effects",
    "create_character",
    "deserialize_actor",
    "merge_rule_world",
    "migrate_actor_payload",
    "serialize_actor",
    "validate_choices",
]
