# engine/src/godot_dnd_engine/character_creator/catalog.py
"""Original data-only catalog used to exercise the v0.9 character creator."""

from __future__ import annotations

from ..actors import SizeCategory, Skill
from ..rules import Ability
from .model import (
    AbilityScorePolicy,
    CharacterCreatorCatalog,
    CreationChoice,
    CreationGroup,
    CreationStep,
    InventoryGrant,
)


def demo_character_catalog() -> CharacterCreatorCatalog:
    """Return original content that exercises all v0.9 creation/advancement families."""

    choices = (
        CreationChoice(
            "species:riverborn",
            CreationStep.SPECIES,
            "Riverborn",
            "Adaptable travelers from floodplain settlements.",
            ability_bonuses=((Ability.DEXTERITY, 1), (Ability.WISDOM, 1)),
            grants_tags=frozenset({"species:riverborn"}),
            size=SizeCategory.MEDIUM,
            walk_speed_feet=30,
        ),
        CreationChoice(
            "species:stonekin",
            CreationStep.SPECIES,
            "Stonekin",
            "Sturdy highland folk with a patient tradition.",
            ability_bonuses=((Ability.CONSTITUTION, 2),),
            grants_tags=frozenset({"species:stonekin"}),
            size=SizeCategory.MEDIUM,
            walk_speed_feet=25,
        ),
        CreationChoice(
            "background:wayfarer",
            CreationStep.BACKGROUND,
            "Wayfarer",
            "A life spent crossing roads and frontiers.",
            skill_proficiencies=(Skill.SURVIVAL,),
            training_proficiencies=("training:navigation",),
            feature_ids=("feature:trailwise",),
            grants_tags=frozenset({"background:wayfarer"}),
        ),
        CreationChoice(
            "background:archivist",
            CreationStep.BACKGROUND,
            "Archivist",
            "A researcher trained to preserve and compare records.",
            skill_proficiencies=(Skill.HISTORY,),
            training_proficiencies=("training:research",),
            feature_ids=("feature:reference-memory",),
            grants_tags=frozenset({"background:archivist"}),
        ),
        CreationChoice(
            "class:guardian",
            CreationStep.CLASS,
            "Guardian",
            "A durable front-line protector.",
            save_proficiencies=(Ability.STRENGTH, Ability.CONSTITUTION),
            training_proficiencies=("training:armor", "training:martial"),
            base_hit_points=12,
            hit_points_per_level=7,
            armor_class=15,
            feature_ids=("feature:guard-stance",),
            grants_tags=frozenset({"class:guardian"}),
        ),
        CreationChoice(
            "class:scholar",
            CreationStep.CLASS,
            "Scholar",
            "A flexible practitioner of studied arcane techniques.",
            save_proficiencies=(Ability.INTELLIGENCE, Ability.WISDOM),
            training_proficiencies=("training:light-armor", "training:arcane"),
            base_hit_points=8,
            hit_points_per_level=5,
            armor_class=12,
            spell_ids=("spell:arc-lance",),
            feature_ids=("feature:prepared-study",),
            grants_tags=frozenset({"class:scholar"}),
        ),
        CreationChoice("skill:athletics", CreationStep.SKILLS, "Athletics", skill_proficiencies=(Skill.ATHLETICS,)),
        CreationChoice("skill:arcana", CreationStep.SKILLS, "Arcana", skill_proficiencies=(Skill.ARCANA,)),
        CreationChoice("skill:insight", CreationStep.SKILLS, "Insight", skill_proficiencies=(Skill.INSIGHT,)),
        CreationChoice("skill:perception", CreationStep.SKILLS, "Perception", skill_proficiencies=(Skill.PERCEPTION,)),
        CreationChoice(
            "equipment:explorer-kit",
            CreationStep.EQUIPMENT,
            "Explorer Kit",
            inventory=(
                InventoryGrant("item:travel-pack"),
                InventoryGrant("item:field-tool", equip_slot="hand:primary"),
            ),
        ),
        CreationChoice(
            "equipment:defender-kit",
            CreationStep.EQUIPMENT,
            "Defender Kit",
            inventory=(
                InventoryGrant("item:training-shield", equip_slot="hand:off"),
                InventoryGrant("item:field-tool", equip_slot="hand:primary"),
            ),
        ),
        CreationChoice(
            "spellchoice:echo-burst",
            CreationStep.SPELLS_FEATURES,
            "Echo Burst",
            requires=frozenset({"class:scholar"}),
            spell_ids=("spell:echo-burst",),
        ),
        CreationChoice(
            "featurechoice:interpose",
            CreationStep.SPELLS_FEATURES,
            "Interpose",
            requires=frozenset({"class:guardian"}),
            feature_ids=("feature:interpose",),
        ),
        CreationChoice(
            "advance:guardian-brace",
            CreationStep.SPELLS_FEATURES,
            "Brace Training",
            requires=frozenset({"class:guardian"}),
            feature_ids=("feature:brace-training",),
            unlock_level=2,
        ),
        CreationChoice(
            "advance:scholar-binding-haze",
            CreationStep.SPELLS_FEATURES,
            "Binding Haze Study",
            requires=frozenset({"class:scholar"}),
            spell_ids=("spell:binding-haze",),
            unlock_level=2,
        ),
    )
    groups = (
        CreationGroup("group:species", CreationStep.SPECIES, ("species:riverborn", "species:stonekin")),
        CreationGroup("group:background", CreationStep.BACKGROUND, ("background:wayfarer", "background:archivist")),
        CreationGroup("group:class", CreationStep.CLASS, ("class:guardian", "class:scholar")),
        CreationGroup(
            "group:skills",
            CreationStep.SKILLS,
            ("skill:athletics", "skill:arcana", "skill:insight", "skill:perception"),
            minimum=2,
            maximum=2,
        ),
        CreationGroup(
            "group:equipment",
            CreationStep.EQUIPMENT,
            ("equipment:explorer-kit", "equipment:defender-kit"),
        ),
        CreationGroup(
            "group:spells-features",
            CreationStep.SPELLS_FEATURES,
            ("spellchoice:echo-burst", "featurechoice:interpose"),
            minimum=0,
            maximum=1,
        ),
    )
    return CharacterCreatorCatalog(
        catalog_id="catalog:original-v0.9-demo",
        choices=choices,
        groups=groups,
        ability_policies=(
            AbilityScorePolicy("standard-array", (15, 14, 13, 12, 10, 8)),
        ),
    )
