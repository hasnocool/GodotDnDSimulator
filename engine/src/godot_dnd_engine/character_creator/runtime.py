# engine/src/godot_dnd_engine/character_creator/runtime.py
"""Authoritative v0.9 character creation, validation, and level-up runtime."""

from __future__ import annotations

from dataclasses import replace

from ..actors import (
    ActorKind,
    ActorState,
    DefenseState,
    EquipmentAssignment,
    HitPoints,
    InventoryEntry,
    MovementMode,
    MovementSpeed,
    SaveProficiency,
    SizeCategory,
    Skill,
    SkillProficiency,
    TrainingProficiency,
)
from ..errors import ValidationError
from ..rules import Ability, AbilityScore, proficiency_bonus_for_level
from .model import (
    CharacterCreatorCatalog,
    CharacterDraft,
    CharacterRecord,
    CreationChoice,
    CreationStep,
)


class CharacterCreatorRuntime:
    """Build and advance actors only from engine-supplied catalog choices."""

    def __init__(self, catalog: CharacterCreatorCatalog) -> None:
        self.catalog = catalog
        self._choices = {item.choice_id: item for item in catalog.choices}
        self._policies = {item.method_id: item for item in catalog.ability_policies}

    def schema(self) -> dict[str, object]:
        return {
            "catalog_id": self.catalog.catalog_id,
            "steps": [step.value for step in CreationStep],
            "groups": [
                {
                    "group_id": group.group_id,
                    "step": group.step.value,
                    "minimum": group.minimum,
                    "maximum": group.maximum,
                    "choice_ids": list(group.choice_ids),
                }
                for group in self.catalog.groups
                if all(
                    self._choices[item].unlock_level <= 1
                    for item in group.choice_ids
                )
            ],
            "choices": [
                self._choice_row(choice)
                for choice in self.catalog.choices
                if choice.unlock_level <= 1
            ],
            "ability_policies": [
                {"method_id": policy.method_id, "values": list(policy.values)}
                for policy in self.catalog.ability_policies
            ],
        }

    def preview(self, draft: CharacterDraft) -> dict[str, object]:
        try:
            selected = self._validate_creation_choices(draft.selected_choice_ids)
            abilities = self._resolved_abilities(draft, selected)
            return {
                "legal": True,
                "errors": [],
                "warnings": [],
                "summary": self._summary(draft, selected, abilities),
            }
        except ValidationError as exc:
            return {
                "legal": False,
                "errors": [str(exc)],
                "warnings": [],
                "summary": {},
            }

    def create(self, draft: CharacterDraft) -> CharacterRecord:
        selected = self._validate_creation_choices(draft.selected_choice_ids)
        abilities = self._resolved_abilities(draft, selected)
        species = self._one(selected, CreationStep.SPECIES)
        background = self._one(selected, CreationStep.BACKGROUND)
        class_choice = self._one(selected, CreationStep.CLASS)
        size = species.size or SizeCategory.MEDIUM
        speed = species.walk_speed_feet if species.walk_speed_feet is not None else 30
        maximum_hp = class_choice.base_hit_points or 1
        armor_class = (
            class_choice.armor_class if class_choice.armor_class is not None else 10
        )
        inventory: list[InventoryEntry] = []
        equipment: list[EquipmentAssignment] = []
        skills: set[Skill] = set()
        saves: set[Ability] = set()
        training: set[str] = set()
        tags: set[str] = {"created:v0.9"}
        spell_ids: set[str] = set()
        feature_ids: set[str] = set()
        for choice in selected:
            skills.update(choice.skill_proficiencies)
            saves.update(choice.save_proficiencies)
            training.update(choice.training_proficiencies)
            tags.update(choice.grants_tags)
            spell_ids.update(choice.spell_ids)
            feature_ids.update(choice.feature_ids)
            for index, grant in enumerate(choice.inventory):
                entry_id = f"inventory:{choice.choice_id}:{index + 1}"
                inventory.append(
                    InventoryEntry(
                        entry_id=entry_id,
                        item_id=grant.item_id,
                        quantity=grant.quantity,
                        tags=frozenset({f"source:{choice.choice_id}"}),
                    )
                )
                if grant.equip_slot is not None:
                    equipment.append(
                        EquipmentAssignment(grant.equip_slot, entry_id)
                    )
        actor = ActorState(
            actor_id=draft.actor_id,
            name=draft.name.strip(),
            kind=ActorKind.HERO,
            size=size,
            level=1,
            proficiency_bonus=proficiency_bonus_for_level(1),
            abilities=abilities,
            hit_points=HitPoints(maximum_hp, maximum_hp),
            defense=DefenseState(armor_class),
            skills=tuple(SkillProficiency(item) for item in sorted(skills)),
            saves=tuple(SaveProficiency(item) for item in sorted(saves)),
            proficiencies=tuple(
                TrainingProficiency(item) for item in sorted(training)
            ),
            movement=(MovementSpeed(MovementMode.WALK, speed),),
            inventory=tuple(inventory),
            equipment=tuple(equipment),
            selected_options=tuple(sorted(draft.selected_choice_ids)),
            tags=frozenset(tags),
        )
        return CharacterRecord(
            actor=actor,
            catalog_id=self.catalog.catalog_id,
            species_id=species.choice_id,
            background_id=background.choice_id,
            class_id=class_choice.choice_id,
            ability_method_id=draft.ability_method_id,
            appearance=draft.appearance,
            biography=draft.biography.strip(),
            personality=draft.personality.strip(),
            spell_ids=tuple(sorted(spell_ids)),
            feature_ids=tuple(sorted(feature_ids)),
        )

    def level_up_choices(self, record: CharacterRecord) -> dict[str, object]:
        current_level = record.actor.level
        if current_level is None or current_level >= 20:
            raise ValidationError("character cannot gain another supported level")
        target_level = current_level + 1
        selected = set(record.actor.selected_options)
        choices = [
            choice
            for choice in self.catalog.choices
            if choice.unlock_level == target_level
            and (not choice.requires or choice.requires.issubset(selected))
        ]
        return {
            "actor_id": record.actor.actor_id,
            "current_level": current_level,
            "target_level": target_level,
            "choices": [self._choice_row(choice) for choice in choices],
        }

    def level_up(
        self,
        record: CharacterRecord,
        selected_choice_ids: tuple[str, ...],
    ) -> CharacterRecord:
        actor = record.actor
        if actor.level is None or actor.level >= 20:
            raise ValidationError("character cannot gain another supported level")
        target_level = actor.level + 1
        choices = tuple(self._choice(choice_id) for choice_id in selected_choice_ids)
        if len(selected_choice_ids) != len(set(selected_choice_ids)):
            raise ValidationError("level-up choices must be unique")
        if any(choice.unlock_level != target_level for choice in choices):
            raise ValidationError(
                "level-up choice is not unlocked at the target level"
            )
        existing = set(actor.selected_options)
        chosen = set(selected_choice_ids)
        for choice in choices:
            if not choice.requires.issubset(existing | chosen):
                raise ValidationError(
                    f"level-up choice {choice.choice_id!r} has unmet requirements"
                )
            if choice.conflicts.intersection(existing | chosen):
                raise ValidationError(
                    f"level-up choice {choice.choice_id!r} conflicts with existing choices"
                )
        class_choice = self._choice(record.class_id)
        hp_gain = class_choice.hit_points_per_level or 1
        maximum = actor.hit_points.maximum + hp_gain
        tags = set(actor.tags)
        spells = set(record.spell_ids)
        features = set(record.feature_ids)
        for choice in choices:
            tags.update(choice.grants_tags)
            spells.update(choice.spell_ids)
            features.update(choice.feature_ids)
        updated_actor = replace(
            actor,
            level=target_level,
            proficiency_bonus=proficiency_bonus_for_level(target_level),
            hit_points=HitPoints(
                min(actor.hit_points.current + hp_gain, maximum),
                maximum,
                actor.hit_points.temporary,
            ),
            selected_options=tuple(sorted(existing | chosen)),
            tags=frozenset(tags),
        )
        return replace(
            record,
            actor=updated_actor,
            spell_ids=tuple(sorted(spells)),
            feature_ids=tuple(sorted(features)),
        )

    def _validate_creation_choices(
        self,
        selected_ids: tuple[str, ...],
    ) -> tuple[CreationChoice, ...]:
        if len(selected_ids) != len(set(selected_ids)):
            raise ValidationError("creator selected choices must be unique")
        selected = tuple(self._choice(item) for item in selected_ids)
        selected_set = set(selected_ids)
        if any(choice.unlock_level != 1 for choice in selected):
            raise ValidationError(
                "level-up-only choice cannot be selected at creation"
            )
        for group in self.catalog.groups:
            creation_ids = tuple(
                item
                for item in group.choice_ids
                if self._choices[item].unlock_level == 1
            )
            if not creation_ids:
                continue
            count = len(selected_set.intersection(creation_ids))
            if not group.minimum <= count <= group.maximum:
                raise ValidationError(
                    f"creator group {group.group_id!r} requires "
                    f"{group.minimum}..{group.maximum} selections"
                )
        for choice in selected:
            if not choice.requires.issubset(selected_set):
                raise ValidationError(
                    f"creator choice {choice.choice_id!r} has unmet requirements"
                )
            if choice.conflicts.intersection(selected_set):
                raise ValidationError(
                    f"creator choice {choice.choice_id!r} conflicts with another selection"
                )
        return selected

    def _resolved_abilities(
        self,
        draft: CharacterDraft,
        selected: tuple[CreationChoice, ...],
    ) -> tuple[AbilityScore, ...]:
        policy = self._policies.get(draft.ability_method_id)
        if policy is None:
            raise ValidationError("unknown ability score method")
        values = [score for _, score in draft.base_ability_scores]
        if sorted(values) != sorted(policy.values):
            raise ValidationError(
                "ability assignments do not match the selected engine policy"
            )
        scores = {ability: score for ability, score in draft.base_ability_scores}
        for choice in selected:
            for ability, bonus in choice.ability_bonuses:
                scores[ability] += bonus
        return tuple(AbilityScore(ability, scores[ability]) for ability in Ability)

    def _summary(
        self,
        draft: CharacterDraft,
        selected: tuple[CreationChoice, ...],
        abilities: tuple[AbilityScore, ...],
    ) -> dict[str, object]:
        return {
            "actor_id": draft.actor_id,
            "name": draft.name.strip(),
            "species_id": self._one(selected, CreationStep.SPECIES).choice_id,
            "background_id": self._one(selected, CreationStep.BACKGROUND).choice_id,
            "class_id": self._one(selected, CreationStep.CLASS).choice_id,
            "abilities": {item.ability.value: item.score for item in abilities},
            "selected_choice_ids": sorted(draft.selected_choice_ids),
            "appearance": dict(draft.appearance),
            "biography": draft.biography.strip(),
            "personality": draft.personality.strip(),
        }

    def _choice(self, choice_id: str) -> CreationChoice:
        choice = self._choices.get(choice_id)
        if choice is None:
            raise ValidationError(f"unknown creator choice: {choice_id}")
        return choice

    @staticmethod
    def _one(
        selected: tuple[CreationChoice, ...],
        step: CreationStep,
    ) -> CreationChoice:
        matches = tuple(item for item in selected if item.step is step)
        if len(matches) != 1:
            raise ValidationError(
                f"creator step {step.value!r} requires exactly one primary choice"
            )
        return matches[0]

    @staticmethod
    def _choice_row(choice: CreationChoice) -> dict[str, object]:
        return {
            "choice_id": choice.choice_id,
            "step": choice.step.value,
            "name": choice.name,
            "description": choice.description,
            "requires": sorted(choice.requires),
            "conflicts": sorted(choice.conflicts),
            "grants_tags": sorted(choice.grants_tags),
            "spell_ids": list(choice.spell_ids),
            "feature_ids": list(choice.feature_ids),
            "unlock_level": choice.unlock_level,
        }
