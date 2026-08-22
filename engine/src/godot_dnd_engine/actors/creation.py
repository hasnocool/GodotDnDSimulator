"""Initial headless character-creation API built on the shared actor model."""

from __future__ import annotations

from dataclasses import dataclass

from ..errors import ValidationError
from ..rules.primitives import AbilityScore, ResourcePool, proficiency_bonus_for_level
from ..rules.state import ConditionInstance
from .choices import CharacterOption, ChoiceGroup, validate_choices
from .inventory import EquipmentAssignment, InventoryEntry
from .model import (
    ActorKind,
    ActorState,
    DefenseState,
    HitPoints,
    MovementSpeed,
    SaveProficiency,
    Sense,
    SizeCategory,
    SkillProficiency,
    TrainingProficiency,
)


@dataclass(frozen=True, slots=True)
class CharacterCreationSpec:
    spec_id: str
    kind: ActorKind
    level: int
    size: SizeCategory
    abilities: tuple[AbilityScore, ...]
    maximum_hit_points: int
    armor_class: int
    skills: tuple[SkillProficiency, ...] = ()
    saves: tuple[SaveProficiency, ...] = ()
    proficiencies: tuple[TrainingProficiency, ...] = ()
    movement: tuple[MovementSpeed, ...] = ()
    senses: tuple[Sense, ...] = ()
    inventory: tuple[InventoryEntry, ...] = ()
    equipment: tuple[EquipmentAssignment, ...] = ()
    resources: tuple[ResourcePool, ...] = ()
    conditions: tuple[ConditionInstance, ...] = ()
    options: tuple[CharacterOption, ...] = ()
    choice_groups: tuple[ChoiceGroup, ...] = ()
    base_tags: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if not isinstance(self.spec_id, str) or not self.spec_id.strip():
            raise ValidationError("character creation spec_id must be a non-empty string")
        proficiency_bonus = proficiency_bonus_for_level(self.level)
        ActorState(
            actor_id="actor:creation-spec-validation",
            name="Creation Spec",
            kind=self.kind,
            size=self.size,
            level=self.level,
            proficiency_bonus=proficiency_bonus,
            abilities=self.abilities,
            hit_points=HitPoints(self.maximum_hit_points, self.maximum_hit_points),
            defense=DefenseState(self.armor_class),
            skills=self.skills,
            saves=self.saves,
            proficiencies=self.proficiencies,
            movement=self.movement,
            senses=self.senses,
            inventory=self.inventory,
            equipment=self.equipment,
            resources=self.resources,
            conditions=self.conditions,
            tags=self.base_tags,
        )
        self._validate_option_references()

    def _validate_option_references(self) -> None:
        option_ids = [option.option_id for option in self.options]
        if len(option_ids) != len(set(option_ids)):
            raise ValidationError("character creation options must have unique option IDs")
        known = set(option_ids)
        group_ids = [group.group_id for group in self.choice_groups]
        if len(group_ids) != len(set(group_ids)):
            raise ValidationError("character creation groups must have unique group IDs")
        for option in self.options:
            missing = (option.requires | option.conflicts) - known
            if missing:
                raise ValidationError(
                    f"option {option.option_id!r} references unknown options: {sorted(missing)}"
                )
        for group in self.choice_groups:
            missing = set(group.option_ids) - known
            if missing:
                raise ValidationError(
                    f"choice group {group.group_id!r} references unknown options: {sorted(missing)}"
                )


@dataclass(frozen=True, slots=True)
class CharacterCreationRequest:
    actor_id: str
    name: str
    selected_option_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.actor_id, str) or not self.actor_id.strip():
            raise ValidationError("character creation actor_id must be a non-empty string")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValidationError("character creation name must be a non-empty string")


@dataclass(frozen=True, slots=True)
class CharacterCreationResult:
    actor: ActorState
    selected_option_ids: tuple[str, ...]


def create_character(
    spec: CharacterCreationSpec,
    request: CharacterCreationRequest,
) -> CharacterCreationResult:
    choice_result = validate_choices(spec.options, spec.choice_groups, request.selected_option_ids)
    actor = ActorState(
        actor_id=request.actor_id,
        name=request.name.strip(),
        kind=spec.kind,
        size=spec.size,
        level=spec.level,
        proficiency_bonus=proficiency_bonus_for_level(spec.level),
        abilities=spec.abilities,
        hit_points=HitPoints(spec.maximum_hit_points, spec.maximum_hit_points),
        defense=DefenseState(spec.armor_class),
        skills=spec.skills,
        saves=spec.saves,
        proficiencies=spec.proficiencies,
        movement=spec.movement,
        senses=spec.senses,
        inventory=spec.inventory,
        equipment=spec.equipment,
        resources=spec.resources,
        conditions=spec.conditions,
        selected_options=choice_result.selected_option_ids,
        tags=spec.base_tags | choice_result.granted_tags,
    )
    return CharacterCreationResult(actor, choice_result.selected_option_ids)
