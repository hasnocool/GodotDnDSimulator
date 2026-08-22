# engine/src/godot_dnd_engine/character_creator/data.py
"""Deserialize creator catalogs from validated canonical/content-pack data."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from ..actors import SizeCategory, Skill
from ..errors import ValidationError
from ..rules import Ability
from .model import (
    AbilityScorePolicy,
    CharacterCreatorCatalog,
    CreationChoice,
    CreationGroup,
    CreationStep,
    InventoryGrant,
)

EnumT = TypeVar("EnumT")


def catalog_from_data(payload: dict[str, Any]) -> CharacterCreatorCatalog:
    """Build a runtime catalog without embedding content choices in Godot or rules code."""

    if not isinstance(payload, dict):
        raise ValidationError("creator catalog payload must be an object")
    choices_raw = _dict_list(payload.get("choices", []), "choices")
    groups_raw = _dict_list(payload.get("groups", []), "groups")
    policies_raw = _dict_list(payload.get("ability_policies", []), "ability_policies")
    return CharacterCreatorCatalog(
        catalog_id=_string(payload.get("catalog_id"), "catalog_id"),
        choices=tuple(_choice(item) for item in choices_raw),
        groups=tuple(_group(item) for item in groups_raw),
        ability_policies=tuple(_policy(item) for item in policies_raw),
    )


def catalog_to_data(catalog: CharacterCreatorCatalog) -> dict[str, object]:
    return {
        "catalog_id": catalog.catalog_id,
        "choices": [_choice_to_data(item) for item in catalog.choices],
        "groups": [
            {
                "group_id": item.group_id,
                "step": item.step.value,
                "choice_ids": list(item.choice_ids),
                "minimum": item.minimum,
                "maximum": item.maximum,
            }
            for item in catalog.groups
        ],
        "ability_policies": [
            {"method_id": item.method_id, "values": list(item.values)}
            for item in catalog.ability_policies
        ],
    }


def _choice(value: dict[str, Any]) -> CreationChoice:
    bonuses: list[tuple[Ability, int]] = []
    bonuses_raw = value.get("ability_bonuses", {})
    if not isinstance(bonuses_raw, dict):
        raise ValidationError("creator ability_bonuses must be an object")
    for ability_id, bonus in bonuses_raw.items():
        ability = _enum(Ability, ability_id, "ability bonus key")
        bonuses.append((ability, _integer(bonus, "ability bonus")))
    inventory = tuple(
        InventoryGrant(
            item_id=_string(item.get("item_id"), "item_id"),
            quantity=_integer(item.get("quantity", 1), "quantity"),
            equip_slot=_optional_string(item.get("equip_slot"), "equip_slot"),
        )
        for item in _dict_list(value.get("inventory", []), "inventory")
    )
    size_value = value.get("size")
    return CreationChoice(
        choice_id=_string(value.get("choice_id"), "choice_id"),
        step=_enum(CreationStep, value.get("step"), "step"),
        name=_string(value.get("name"), "name"),
        description=_optional_string(
            value.get("description", ""), "description"
        )
        or "",
        requires=frozenset(_string_list(value.get("requires", []), "requires")),
        conflicts=frozenset(
            _string_list(value.get("conflicts", []), "conflicts")
        ),
        grants_tags=frozenset(
            _string_list(value.get("grants_tags", []), "grants_tags")
        ),
        ability_bonuses=tuple(bonuses),
        skill_proficiencies=tuple(
            _enum(Skill, item, "skill proficiency")
            for item in _string_list(
                value.get("skill_proficiencies", []),
                "skill_proficiencies",
            )
        ),
        save_proficiencies=tuple(
            _enum(Ability, item, "save proficiency")
            for item in _string_list(
                value.get("save_proficiencies", []),
                "save_proficiencies",
            )
        ),
        training_proficiencies=_string_tuple(
            value.get("training_proficiencies", []),
            "training_proficiencies",
        ),
        inventory=inventory,
        spell_ids=_string_tuple(value.get("spell_ids", []), "spell_ids"),
        feature_ids=_string_tuple(value.get("feature_ids", []), "feature_ids"),
        size=(
            None
            if size_value is None
            else _enum(SizeCategory, size_value, "size")
        ),
        walk_speed_feet=_optional_int(
            value.get("walk_speed_feet"), "walk_speed_feet"
        ),
        base_hit_points=_optional_int(
            value.get("base_hit_points"), "base_hit_points"
        ),
        hit_points_per_level=_optional_int(
            value.get("hit_points_per_level"),
            "hit_points_per_level",
        ),
        armor_class=_optional_int(value.get("armor_class"), "armor_class"),
        unlock_level=_integer(value.get("unlock_level", 1), "unlock_level"),
    )


def _choice_to_data(choice: CreationChoice) -> dict[str, object]:
    return {
        "choice_id": choice.choice_id,
        "step": choice.step.value,
        "name": choice.name,
        "description": choice.description,
        "requires": sorted(choice.requires),
        "conflicts": sorted(choice.conflicts),
        "grants_tags": sorted(choice.grants_tags),
        "ability_bonuses": {
            ability.value: bonus for ability, bonus in choice.ability_bonuses
        },
        "skill_proficiencies": [
            item.value for item in choice.skill_proficiencies
        ],
        "save_proficiencies": [
            item.value for item in choice.save_proficiencies
        ],
        "training_proficiencies": list(choice.training_proficiencies),
        "inventory": [
            {
                "item_id": item.item_id,
                "quantity": item.quantity,
                "equip_slot": item.equip_slot,
            }
            for item in choice.inventory
        ],
        "spell_ids": list(choice.spell_ids),
        "feature_ids": list(choice.feature_ids),
        "size": None if choice.size is None else choice.size.value,
        "walk_speed_feet": choice.walk_speed_feet,
        "base_hit_points": choice.base_hit_points,
        "hit_points_per_level": choice.hit_points_per_level,
        "armor_class": choice.armor_class,
        "unlock_level": choice.unlock_level,
    }


def _group(value: dict[str, Any]) -> CreationGroup:
    return CreationGroup(
        group_id=_string(value.get("group_id"), "group_id"),
        step=_enum(CreationStep, value.get("step"), "step"),
        choice_ids=_string_tuple(value.get("choice_ids", []), "choice_ids"),
        minimum=_integer(value.get("minimum", 1), "minimum"),
        maximum=_integer(value.get("maximum", 1), "maximum"),
    )


def _policy(value: dict[str, Any]) -> AbilityScorePolicy:
    values_raw = value.get("values", [])
    if not isinstance(values_raw, list):
        raise ValidationError("ability policy values must be an array")
    return AbilityScorePolicy(
        method_id=_string(value.get("method_id"), "method_id"),
        values=tuple(
            _integer(item, "ability policy value") for item in values_raw
        ),
    )


def _dict_list(value: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValidationError(f"{label} must be an array of objects")
    result: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            raise ValidationError(f"{label} must be an array of objects")
        result.append(dict(item))
    return result


def _enum(
    constructor: Callable[[str], EnumT],
    value: Any,
    label: str,
) -> EnumT:
    raw = _string(value, label)
    try:
        return constructor(raw)
    except ValueError as exc:
        raise ValidationError(f"unsupported {label}: {raw!r}") from exc


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{label} must be a non-empty string")
    return value.strip()


def _optional_string(value: Any, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValidationError(f"{label} must be null or a string")
    return value


def _string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list):
        raise ValidationError(
            f"{label} must be an array of non-empty strings"
        )
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValidationError(
                f"{label} must be an array of non-empty strings"
            )
        result.append(item)
    return result


def _string_tuple(value: Any, label: str) -> tuple[str, ...]:
    return tuple(_string_list(value, label))


def _integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"{label} must be an integer")
    return value


def _optional_int(value: Any, label: str) -> int | None:
    if value is None:
        return None
    return _integer(value, label)
