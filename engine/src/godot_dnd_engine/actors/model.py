# engine/src/godot_dnd_engine/actors/model.py
"""Shared immutable actor model for heroes, NPCs, and creatures."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from ..errors import ValidationError
from ..rules.primitives import Ability, AbilityScore, ProficiencyRank, ResourcePool
from ..rules.state import ConditionInstance, RuleSubjectState
from .inventory import EquipmentAssignment, InventoryEntry, validate_inventory_equipment


class ActorKind(StrEnum):
    HERO = "hero"
    NPC = "npc"
    CREATURE = "creature"


class SizeCategory(StrEnum):
    TINY = "tiny"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    HUGE = "huge"
    GARGANTUAN = "gargantuan"


class MovementMode(StrEnum):
    WALK = "walk"
    CLIMB = "climb"
    SWIM = "swim"
    FLY = "fly"
    BURROW = "burrow"


class Skill(StrEnum):
    ACROBATICS = "acrobatics"
    ANIMAL_HANDLING = "animal_handling"
    ARCANA = "arcana"
    ATHLETICS = "athletics"
    DECEPTION = "deception"
    HISTORY = "history"
    INSIGHT = "insight"
    INTIMIDATION = "intimidation"
    INVESTIGATION = "investigation"
    MEDICINE = "medicine"
    NATURE = "nature"
    PERCEPTION = "perception"
    PERFORMANCE = "performance"
    PERSUASION = "persuasion"
    RELIGION = "religion"
    SLEIGHT_OF_HAND = "sleight_of_hand"
    STEALTH = "stealth"
    SURVIVAL = "survival"


SKILL_ABILITIES: dict[Skill, Ability] = {
    Skill.ACROBATICS: Ability.DEXTERITY,
    Skill.ANIMAL_HANDLING: Ability.WISDOM,
    Skill.ARCANA: Ability.INTELLIGENCE,
    Skill.ATHLETICS: Ability.STRENGTH,
    Skill.DECEPTION: Ability.CHARISMA,
    Skill.HISTORY: Ability.INTELLIGENCE,
    Skill.INSIGHT: Ability.WISDOM,
    Skill.INTIMIDATION: Ability.CHARISMA,
    Skill.INVESTIGATION: Ability.INTELLIGENCE,
    Skill.MEDICINE: Ability.WISDOM,
    Skill.NATURE: Ability.INTELLIGENCE,
    Skill.PERCEPTION: Ability.WISDOM,
    Skill.PERFORMANCE: Ability.CHARISMA,
    Skill.PERSUASION: Ability.CHARISMA,
    Skill.RELIGION: Ability.INTELLIGENCE,
    Skill.SLEIGHT_OF_HAND: Ability.DEXTERITY,
    Skill.STEALTH: Ability.DEXTERITY,
    Skill.SURVIVAL: Ability.WISDOM,
}


@dataclass(frozen=True, slots=True)
class HitPoints:
    current: int
    maximum: int
    temporary: int = 0

    def __post_init__(self) -> None:
        for label, value in (
            ("current", self.current),
            ("maximum", self.maximum),
            ("temporary", self.temporary),
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValidationError(f"hit point {label} must be an integer")
        if self.maximum < 1:
            raise ValidationError("maximum hit points must be >= 1")
        if not 0 <= self.current <= self.maximum:
            raise ValidationError("current hit points must be between 0 and maximum")
        if self.temporary < 0:
            raise ValidationError("temporary hit points must be >= 0")

    def with_current(self, current: int) -> HitPoints:
        return HitPoints(current=current, maximum=self.maximum, temporary=self.temporary)

    def with_temporary(self, temporary: int) -> HitPoints:
        return HitPoints(current=self.current, maximum=self.maximum, temporary=temporary)


@dataclass(frozen=True, slots=True)
class DefenseState:
    armor_class: int

    def __post_init__(self) -> None:
        if (
            isinstance(self.armor_class, bool)
            or not isinstance(self.armor_class, int)
            or not 0 <= self.armor_class <= 1_000
        ):
            raise ValidationError("armor_class must be an integer between 0 and 1000")


@dataclass(frozen=True, slots=True)
class MovementSpeed:
    mode: MovementMode
    feet: int

    def __post_init__(self) -> None:
        if isinstance(self.feet, bool) or not isinstance(self.feet, int) or self.feet < 0:
            raise ValidationError("movement speed must be an integer >= 0")


@dataclass(frozen=True, slots=True)
class Sense:
    sense_id: str
    range_feet: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.sense_id, str) or not self.sense_id.strip():
            raise ValidationError("sense_id must be a non-empty string")
        if self.range_feet is not None and (
            isinstance(self.range_feet, bool)
            or not isinstance(self.range_feet, int)
            or self.range_feet < 0
        ):
            raise ValidationError("sense range must be None or an integer >= 0")


@dataclass(frozen=True, slots=True)
class SkillProficiency:
    skill: Skill
    rank: ProficiencyRank = ProficiencyRank.FULL


@dataclass(frozen=True, slots=True)
class SaveProficiency:
    ability: Ability
    rank: ProficiencyRank = ProficiencyRank.FULL


@dataclass(frozen=True, slots=True)
class TrainingProficiency:
    proficiency_id: str
    rank: ProficiencyRank = ProficiencyRank.FULL

    def __post_init__(self) -> None:
        if not isinstance(self.proficiency_id, str) or not self.proficiency_id.strip():
            raise ValidationError("proficiency_id must be a non-empty string")


@dataclass(frozen=True, slots=True)
class ActorState:
    actor_id: str
    name: str
    kind: ActorKind
    size: SizeCategory
    proficiency_bonus: int
    abilities: tuple[AbilityScore, ...]
    hit_points: HitPoints
    defense: DefenseState
    level: int | None = None
    skills: tuple[SkillProficiency, ...] = ()
    saves: tuple[SaveProficiency, ...] = ()
    proficiencies: tuple[TrainingProficiency, ...] = ()
    movement: tuple[MovementSpeed, ...] = ()
    senses: tuple[Sense, ...] = ()
    inventory: tuple[InventoryEntry, ...] = ()
    equipment: tuple[EquipmentAssignment, ...] = ()
    resources: tuple[ResourcePool, ...] = ()
    conditions: tuple[ConditionInstance, ...] = ()
    selected_options: tuple[str, ...] = ()
    tags: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if not isinstance(self.actor_id, str) or not self.actor_id.strip():
            raise ValidationError("actor_id must be a non-empty string")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValidationError("actor name must be a non-empty string")
        if isinstance(self.proficiency_bonus, bool) or not isinstance(self.proficiency_bonus, int):
            raise ValidationError("proficiency_bonus must be an integer")
        if not 0 <= self.proficiency_bonus <= 20:
            raise ValidationError("proficiency_bonus is outside supported range")
        if self.level is not None and (
            isinstance(self.level, bool)
            or not isinstance(self.level, int)
            or not 1 <= self.level <= 20
        ):
            raise ValidationError("actor level must be None or between 1 and 20")
        self._validate_collections()
        object.__setattr__(
            self, "abilities", tuple(sorted(self.abilities, key=lambda item: item.ability))
        )
        object.__setattr__(self, "skills", tuple(sorted(self.skills, key=lambda item: item.skill)))
        object.__setattr__(self, "saves", tuple(sorted(self.saves, key=lambda item: item.ability)))
        object.__setattr__(
            self,
            "proficiencies",
            tuple(sorted(self.proficiencies, key=lambda item: item.proficiency_id)),
        )
        object.__setattr__(
            self, "movement", tuple(sorted(self.movement, key=lambda item: item.mode))
        )
        object.__setattr__(
            self, "senses", tuple(sorted(self.senses, key=lambda item: item.sense_id))
        )
        object.__setattr__(
            self, "inventory", tuple(sorted(self.inventory, key=lambda item: item.entry_id))
        )
        object.__setattr__(
            self, "equipment", tuple(sorted(self.equipment, key=lambda item: item.slot_id))
        )
        object.__setattr__(
            self, "resources", tuple(sorted(self.resources, key=lambda item: item.resource_id))
        )
        object.__setattr__(
            self,
            "conditions",
            tuple(
                sorted(
                    self.conditions,
                    key=lambda item: (
                        item.condition_id,
                        item.source_id or "",
                        item.stacks,
                        "" if item.duration is None else item.duration.unit.value,
                        -1
                        if item.duration is None or item.duration.remaining is None
                        else item.duration.remaining,
                    ),
                )
            ),
        )
        object.__setattr__(self, "selected_options", tuple(sorted(self.selected_options)))

    def _validate_collections(self) -> None:
        ability_ids = [score.ability for score in self.abilities]
        if len(ability_ids) != len(set(ability_ids)) or set(ability_ids) != set(Ability):
            raise ValidationError("actors must define each of the six abilities exactly once")
        skill_ids = [item.skill for item in self.skills]
        if len(skill_ids) != len(set(skill_ids)):
            raise ValidationError("actor skill proficiencies must be unique by skill")
        save_ids = [item.ability for item in self.saves]
        if len(save_ids) != len(set(save_ids)):
            raise ValidationError("actor save proficiencies must be unique by ability")
        proficiency_ids = [item.proficiency_id for item in self.proficiencies]
        if len(proficiency_ids) != len(set(proficiency_ids)):
            raise ValidationError("actor proficiencies must be unique by ID")
        movement_ids = [item.mode for item in self.movement]
        if len(movement_ids) != len(set(movement_ids)):
            raise ValidationError("actor movement modes must be unique")
        sense_ids = [item.sense_id for item in self.senses]
        if len(sense_ids) != len(set(sense_ids)):
            raise ValidationError("actor senses must have unique sense IDs")
        resource_ids = [item.resource_id for item in self.resources]
        if len(resource_ids) != len(set(resource_ids)):
            raise ValidationError("actor resources must have unique resource IDs")
        if len(self.selected_options) != len(set(self.selected_options)):
            raise ValidationError("selected character options must be unique")
        if any(not isinstance(item, str) or not item.strip() for item in self.selected_options):
            raise ValidationError("selected option IDs must be non-empty strings")
        if any(not isinstance(tag, str) or not tag.strip() for tag in self.tags):
            raise ValidationError("actor tags must be non-empty strings")
        validate_inventory_equipment(self.inventory, self.equipment)

    def ability_score(self, ability: Ability) -> AbilityScore:
        return next(item for item in self.abilities if item.ability is ability)

    def skill_rank(self, skill: Skill) -> ProficiencyRank:
        match = next((item for item in self.skills if item.skill is skill), None)
        return ProficiencyRank.NONE if match is None else match.rank

    def save_rank(self, ability: Ability) -> ProficiencyRank:
        match = next((item for item in self.saves if item.ability is ability), None)
        return ProficiencyRank.NONE if match is None else match.rank

    def skill_modifier(self, skill: Skill) -> int:
        ability = SKILL_ABILITIES[skill]
        return self.ability_score(ability).modifier + self.skill_rank(skill).apply(
            self.proficiency_bonus
        )

    def save_modifier(self, ability: Ability) -> int:
        return self.ability_score(ability).modifier + self.save_rank(ability).apply(
            self.proficiency_bonus
        )

    def proficiency_rank(self, proficiency_id: str) -> ProficiencyRank:
        match = next(
            (item for item in self.proficiencies if item.proficiency_id == proficiency_id),
            None,
        )
        return ProficiencyRank.NONE if match is None else match.rank

    def movement_speed(self, mode: MovementMode) -> int | None:
        match = next((item for item in self.movement if item.mode is mode), None)
        return None if match is None else match.feet

    def to_rule_subject(self) -> RuleSubjectState:
        return RuleSubjectState(
            subject_id=self.actor_id,
            tags=self.tags | frozenset({f"actor-kind:{self.kind.value}"}),
            resources=self.resources,
            conditions=self.conditions,
        )

    def with_rule_subject(self, subject: RuleSubjectState) -> ActorState:
        if subject.subject_id != self.actor_id:
            raise ValidationError("rule subject ID does not match actor ID")
        return replace(self, resources=subject.resources, conditions=subject.conditions)
