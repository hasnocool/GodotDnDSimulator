# engine/src/godot_dnd_engine/character_creator/model.py
"""Data-driven v0.9 character-creation and advancement contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ..actors import ActorState, SizeCategory, Skill
from ..errors import ValidationError
from ..rules import Ability


class CreationStep(StrEnum):
    IDENTITY = "identity"
    SPECIES = "species"
    BACKGROUND = "background"
    CLASS = "class"
    ABILITIES = "abilities"
    SKILLS = "skills"
    EQUIPMENT = "equipment"
    SPELLS_FEATURES = "spells_features"
    APPEARANCE = "appearance"
    BIOGRAPHY = "biography"
    REVIEW = "review"


@dataclass(frozen=True, slots=True)
class InventoryGrant:
    item_id: str
    quantity: int = 1
    equip_slot: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.item_id, str) or not self.item_id.strip():
            raise ValidationError("creator inventory grant item_id must be non-empty")
        if (
            isinstance(self.quantity, bool)
            or not isinstance(self.quantity, int)
            or self.quantity < 1
        ):
            raise ValidationError(
                "creator inventory grant quantity must be an integer >= 1"
            )
        if self.equip_slot is not None and (
            not isinstance(self.equip_slot, str) or not self.equip_slot.strip()
        ):
            raise ValidationError(
                "creator inventory equip_slot must be None or non-empty"
            )


@dataclass(frozen=True, slots=True)
class CreationChoice:
    choice_id: str
    step: CreationStep
    name: str
    description: str = ""
    requires: frozenset[str] = frozenset()
    conflicts: frozenset[str] = frozenset()
    grants_tags: frozenset[str] = frozenset()
    ability_bonuses: tuple[tuple[Ability, int], ...] = ()
    skill_proficiencies: tuple[Skill, ...] = ()
    save_proficiencies: tuple[Ability, ...] = ()
    training_proficiencies: tuple[str, ...] = ()
    inventory: tuple[InventoryGrant, ...] = ()
    spell_ids: tuple[str, ...] = ()
    feature_ids: tuple[str, ...] = ()
    size: SizeCategory | None = None
    walk_speed_feet: int | None = None
    base_hit_points: int | None = None
    hit_points_per_level: int | None = None
    armor_class: int | None = None
    unlock_level: int = 1

    def __post_init__(self) -> None:
        if (
            not isinstance(self.choice_id, str)
            or not self.choice_id.strip()
            or not isinstance(self.name, str)
            or not self.name.strip()
        ):
            raise ValidationError("creator choice ID/name must be non-empty")
        if not isinstance(self.description, str):
            raise ValidationError("creator choice description must be a string")
        if self.choice_id in self.conflicts:
            raise ValidationError("creator choice cannot conflict with itself")
        for label, values in (
            ("requires", self.requires),
            ("conflicts", self.conflicts),
            ("grants_tags", self.grants_tags),
            ("training_proficiencies", self.training_proficiencies),
            ("spell_ids", self.spell_ids),
            ("feature_ids", self.feature_ids),
        ):
            if any(not isinstance(value, str) or not value.strip() for value in values):
                raise ValidationError(
                    f"creator choice {label} must contain non-empty strings"
                )
        if len(self.skill_proficiencies) != len(set(self.skill_proficiencies)):
            raise ValidationError(
                "creator choice skill proficiencies must be unique"
            )
        if len(self.save_proficiencies) != len(set(self.save_proficiencies)):
            raise ValidationError(
                "creator choice save proficiencies must be unique"
            )
        if len(self.training_proficiencies) != len(
            set(self.training_proficiencies)
        ):
            raise ValidationError(
                "creator choice training proficiencies must be unique"
            )
        if len(self.spell_ids) != len(set(self.spell_ids)) or len(
            self.feature_ids
        ) != len(set(self.feature_ids)):
            raise ValidationError("creator choice spell/feature IDs must be unique")
        bonus_abilities = [ability for ability, _ in self.ability_bonuses]
        if len(bonus_abilities) != len(set(bonus_abilities)):
            raise ValidationError(
                "creator choice ability bonuses must be unique by ability"
            )
        for _, bonus in self.ability_bonuses:
            if isinstance(bonus, bool) or not isinstance(bonus, int):
                raise ValidationError("creator ability bonuses must be integers")
        for label, value in (
            ("walk_speed_feet", self.walk_speed_feet),
            ("base_hit_points", self.base_hit_points),
            ("hit_points_per_level", self.hit_points_per_level),
            ("armor_class", self.armor_class),
        ):
            if value is not None and (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ValidationError(
                    f"creator {label} must be None or an integer >= 0"
                )
        if (
            isinstance(self.unlock_level, bool)
            or not isinstance(self.unlock_level, int)
            or not 1 <= self.unlock_level <= 20
        ):
            raise ValidationError(
                "creator unlock_level must be an integer from 1 through 20"
            )


@dataclass(frozen=True, slots=True)
class CreationGroup:
    group_id: str
    step: CreationStep
    choice_ids: tuple[str, ...]
    minimum: int = 1
    maximum: int = 1

    def __post_init__(self) -> None:
        if (
            not isinstance(self.group_id, str)
            or not self.group_id.strip()
            or not self.choice_ids
        ):
            raise ValidationError(
                "creator groups require a non-empty ID and choices"
            )
        if len(self.choice_ids) != len(set(self.choice_ids)):
            raise ValidationError("creator group choice IDs must be unique")
        if any(
            not isinstance(item, str) or not item.strip()
            for item in self.choice_ids
        ):
            raise ValidationError("creator group choice IDs must be non-empty")
        if (
            isinstance(self.minimum, bool)
            or not isinstance(self.minimum, int)
            or isinstance(self.maximum, bool)
            or not isinstance(self.maximum, int)
            or self.minimum < 0
            or self.maximum < self.minimum
            or self.maximum > len(self.choice_ids)
        ):
            raise ValidationError("creator group cardinality is invalid")


@dataclass(frozen=True, slots=True)
class AbilityScorePolicy:
    method_id: str
    values: tuple[int, ...]

    def __post_init__(self) -> None:
        if (
            not isinstance(self.method_id, str)
            or not self.method_id.strip()
            or len(self.values) != len(Ability)
        ):
            raise ValidationError(
                "ability policy requires an ID and exactly six values"
            )
        if any(
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 1 <= value <= 30
            for value in self.values
        ):
            raise ValidationError(
                "ability policy values must be integer scores from 1 through 30"
            )


@dataclass(frozen=True, slots=True)
class CharacterCreatorCatalog:
    catalog_id: str
    choices: tuple[CreationChoice, ...]
    groups: tuple[CreationGroup, ...]
    ability_policies: tuple[AbilityScorePolicy, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.catalog_id, str) or not self.catalog_id.strip():
            raise ValidationError("creator catalog_id must be non-empty")
        choice_ids = [item.choice_id for item in self.choices]
        if len(choice_ids) != len(set(choice_ids)):
            raise ValidationError("creator catalog choices must have unique IDs")
        known = set(choice_ids)
        group_ids = [item.group_id for item in self.groups]
        if len(group_ids) != len(set(group_ids)):
            raise ValidationError("creator catalog groups must have unique IDs")
        for group in self.groups:
            missing = set(group.choice_ids) - known
            if missing:
                raise ValidationError(
                    f"creator group {group.group_id!r} references unknown choices"
                )
        for choice in self.choices:
            if (choice.requires | choice.conflicts) - known:
                raise ValidationError(
                    f"creator choice {choice.choice_id!r} references unknown choices"
                )
        policy_ids = [item.method_id for item in self.ability_policies]
        if len(policy_ids) != len(set(policy_ids)) or not policy_ids:
            raise ValidationError(
                "creator catalog requires unique ability policies"
            )


@dataclass(frozen=True, slots=True)
class CharacterDraft:
    actor_id: str
    name: str
    selected_choice_ids: tuple[str, ...]
    ability_method_id: str
    base_ability_scores: tuple[tuple[Ability, int], ...]
    appearance: tuple[tuple[str, str], ...] = ()
    biography: str = ""
    personality: str = ""

    def __post_init__(self) -> None:
        if (
            not isinstance(self.actor_id, str)
            or not self.actor_id.strip()
            or not isinstance(self.name, str)
            or not self.name.strip()
            or not isinstance(self.ability_method_id, str)
            or not self.ability_method_id.strip()
        ):
            raise ValidationError(
                "character draft actor/name/ability method must be non-empty"
            )
        if not isinstance(self.biography, str) or not isinstance(
            self.personality, str
        ):
            raise ValidationError(
                "character biography/personality metadata must be strings"
            )
        if len(self.selected_choice_ids) != len(set(self.selected_choice_ids)):
            raise ValidationError("character draft selected choices must be unique")
        if any(
            not isinstance(item, str) or not item.strip()
            for item in self.selected_choice_ids
        ):
            raise ValidationError(
                "character draft selected choices must be non-empty strings"
            )
        ability_ids = [ability for ability, _ in self.base_ability_scores]
        if set(ability_ids) != set(Ability) or len(ability_ids) != len(
            set(ability_ids)
        ):
            raise ValidationError(
                "character draft must assign each ability exactly once"
            )
        for _, score in self.base_ability_scores:
            if (
                isinstance(score, bool)
                or not isinstance(score, int)
                or not 1 <= score <= 30
            ):
                raise ValidationError(
                    "character draft ability scores must be integer values "
                    "from 1 through 30"
                )
        appearance_keys = [key for key, _ in self.appearance]
        if len(appearance_keys) != len(set(appearance_keys)) or any(
            not isinstance(key, str) or not key.strip()
            for key in appearance_keys
        ):
            raise ValidationError(
                "character appearance keys must be unique non-empty strings"
            )
        if any(not isinstance(value, str) for _, value in self.appearance):
            raise ValidationError("character appearance values must be strings")


@dataclass(frozen=True, slots=True)
class CharacterRecord:
    actor: ActorState
    catalog_id: str
    species_id: str
    background_id: str
    class_id: str
    ability_method_id: str
    appearance: tuple[tuple[str, str], ...] = ()
    biography: str = ""
    personality: str = ""
    spell_ids: tuple[str, ...] = ()
    feature_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for value in (
            self.catalog_id,
            self.species_id,
            self.background_id,
            self.class_id,
            self.ability_method_id,
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValidationError(
                    "character record identity fields must be non-empty"
                )
        if not isinstance(self.biography, str) or not isinstance(
            self.personality, str
        ):
            raise ValidationError(
                "character record biography/personality must be strings"
            )
        if len(self.spell_ids) != len(set(self.spell_ids)) or len(
            self.feature_ids
        ) != len(set(self.feature_ids)):
            raise ValidationError(
                "character record spell/feature IDs must be unique"
            )
        if any(
            not isinstance(item, str) or not item.strip()
            for item in (*self.spell_ids, *self.feature_ids)
        ):
            raise ValidationError(
                "character record spell/feature IDs must be non-empty strings"
            )
