# engine/src/godot_dnd_engine/actors/serialization.py
"""Versioned actor serialization and explicit migrations."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from ..errors import ValidationError
from ..rules.primitives import Ability, AbilityScore, ProficiencyRank, ResourcePool
from ..rules.state import ConditionInstance, Duration, DurationUnit
from .inventory import EquipmentAssignment, InventoryEntry
from .model import (
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

ACTOR_SCHEMA_VERSION = 1


def actor_to_dict(actor: ActorState) -> dict[str, Any]:
    return {
        "schema_version": ACTOR_SCHEMA_VERSION,
        "actor_id": actor.actor_id,
        "name": actor.name,
        "kind": actor.kind.value,
        "size": actor.size.value,
        "level": actor.level,
        "proficiency_bonus": actor.proficiency_bonus,
        "abilities": {item.ability.value: item.score for item in actor.abilities},
        "hit_points": asdict(actor.hit_points),
        "defense": asdict(actor.defense),
        "skills": [
            {"skill": item.skill.value, "rank": item.rank.value} for item in actor.skills
        ],
        "saves": [
            {"ability": item.ability.value, "rank": item.rank.value} for item in actor.saves
        ],
        "proficiencies": [
            {"proficiency_id": item.proficiency_id, "rank": item.rank.value}
            for item in actor.proficiencies
        ],
        "movement": [
            {"mode": item.mode.value, "feet": item.feet} for item in actor.movement
        ],
        "senses": [asdict(item) for item in actor.senses],
        "inventory": [
            {
                "entry_id": item.entry_id,
                "item_id": item.item_id,
                "quantity": item.quantity,
                "tags": sorted(item.tags),
            }
            for item in actor.inventory
        ],
        "equipment": [asdict(item) for item in actor.equipment],
        "resources": [asdict(item) for item in actor.resources],
        "conditions": [_condition_to_dict(item) for item in actor.conditions],
        "selected_options": list(actor.selected_options),
        "tags": sorted(actor.tags),
    }


def _condition_to_dict(condition: ConditionInstance) -> dict[str, Any]:
    duration = condition.duration
    return {
        "condition_id": condition.condition_id,
        "source_id": condition.source_id,
        "duration": None
        if duration is None
        else {"unit": duration.unit.value, "remaining": duration.remaining},
        "stacks": condition.stacks,
    }


def serialize_actor(actor: ActorState) -> str:
    return json.dumps(actor_to_dict(actor), sort_keys=True, separators=(",", ":"))


def migrate_actor_payload(payload: dict[str, Any]) -> dict[str, Any]:
    version = payload.get("schema_version")
    if version == ACTOR_SCHEMA_VERSION:
        return dict(payload)
    if version != 0:
        raise ValidationError(f"unsupported actor schema version: {version!r}")
    abilities = payload.get("abilities")
    hp = payload.get("hp")
    if not isinstance(abilities, dict) or not isinstance(hp, dict):
        raise ValidationError("legacy actor payload requires abilities and hp objects")
    speed = payload.get("speed", 0)
    return {
        "schema_version": ACTOR_SCHEMA_VERSION,
        "actor_id": payload.get("id"),
        "name": payload.get("name"),
        "kind": payload.get("type"),
        "size": payload.get("size", SizeCategory.MEDIUM.value),
        "level": payload.get("level"),
        "proficiency_bonus": payload.get("proficiency_bonus", 0),
        "abilities": abilities,
        "hit_points": {
            "current": hp.get("current"),
            "maximum": hp.get("max"),
            "temporary": hp.get("temp", 0),
        },
        "defense": {"armor_class": payload.get("ac")},
        "skills": [],
        "saves": [],
        "proficiencies": [],
        "movement": [{"mode": MovementMode.WALK.value, "feet": speed}],
        "senses": [],
        "inventory": [],
        "equipment": [],
        "resources": [],
        "conditions": [],
        "selected_options": [],
        "tags": [],
    }


def actor_from_dict(payload: dict[str, Any]) -> ActorState:
    data = migrate_actor_payload(payload)
    try:
        abilities_data = _dict(data["abilities"], "abilities")
        abilities = tuple(
            AbilityScore(Ability(ability.value), _int(abilities_data[ability.value], ability.value))
            for ability in Ability
        )
        hp = _dict(data["hit_points"], "hit_points")
        defense = _dict(data["defense"], "defense")
        skills = tuple(
            SkillProficiency(
                Skill(_str(item["skill"], "skill")),
                ProficiencyRank(_str(item["rank"], "rank")),
            )
            for item in _dict_list(data.get("skills", []), "skills")
        )
        saves = tuple(
            SaveProficiency(
                Ability(_str(item["ability"], "ability")),
                ProficiencyRank(_str(item["rank"], "rank")),
            )
            for item in _dict_list(data.get("saves", []), "saves")
        )
        proficiencies = tuple(
            TrainingProficiency(
                _str(item["proficiency_id"], "proficiency_id"),
                ProficiencyRank(_str(item["rank"], "rank")),
            )
            for item in _dict_list(data.get("proficiencies", []), "proficiencies")
        )
        movement = tuple(
            MovementSpeed(
                MovementMode(_str(item["mode"], "mode")),
                _int(item["feet"], "feet"),
            )
            for item in _dict_list(data.get("movement", []), "movement")
        )
        senses = tuple(
            Sense(
                _str(item["sense_id"], "sense_id"),
                _optional_int(item.get("range_feet"), "range_feet"),
            )
            for item in _dict_list(data.get("senses", []), "senses")
        )
        inventory = tuple(
            InventoryEntry(
                _str(item["entry_id"], "entry_id"),
                _str(item["item_id"], "item_id"),
                _int(item.get("quantity", 1), "quantity"),
                frozenset(_string_list(item.get("tags", []), "inventory tags")),
            )
            for item in _dict_list(data.get("inventory", []), "inventory")
        )
        equipment = tuple(
            EquipmentAssignment(
                _str(item["slot_id"], "slot_id"),
                _str(item["entry_id"], "entry_id"),
            )
            for item in _dict_list(data.get("equipment", []), "equipment")
        )
        resources = tuple(
            ResourcePool(
                _str(item["resource_id"], "resource_id"),
                _int(item["current"], "current"),
                _int(item["maximum"], "maximum"),
                _int(item.get("minimum", 0), "minimum"),
            )
            for item in _dict_list(data.get("resources", []), "resources")
        )
        conditions = tuple(
            _condition_from_dict(item)
            for item in _dict_list(data.get("conditions", []), "conditions")
        )
        return ActorState(
            actor_id=_str(data["actor_id"], "actor_id"),
            name=_str(data["name"], "name"),
            kind=ActorKind(_str(data["kind"], "kind")),
            size=SizeCategory(_str(data["size"], "size")),
            level=_optional_int(data.get("level"), "level"),
            proficiency_bonus=_int(data["proficiency_bonus"], "proficiency_bonus"),
            abilities=abilities,
            hit_points=HitPoints(
                _int(hp["current"], "hp current"),
                _int(hp["maximum"], "hp maximum"),
                _int(hp.get("temporary", 0), "hp temporary"),
            ),
            defense=DefenseState(_int(defense["armor_class"], "armor_class")),
            skills=skills,
            saves=saves,
            proficiencies=proficiencies,
            movement=movement,
            senses=senses,
            inventory=inventory,
            equipment=equipment,
            resources=resources,
            conditions=conditions,
            selected_options=tuple(
                _string_list(data.get("selected_options", []), "selected_options")
            ),
            tags=frozenset(_string_list(data.get("tags", []), "tags")),
        )
    except (KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, ValidationError):
            raise
        raise ValidationError(f"invalid actor payload: {exc}") from exc


def deserialize_actor(value: str) -> ActorState:
    if not isinstance(value, str):
        raise ValidationError("serialized actor must be a string")
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValidationError("serialized actor is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValidationError("serialized actor must contain a JSON object")
    return actor_from_dict(payload)


def _condition_from_dict(item: dict[str, Any]) -> ConditionInstance:
    duration_data = item.get("duration")
    duration: Duration | None = None
    if duration_data is not None:
        raw_duration = _dict(duration_data, "duration")
        duration = Duration(
            DurationUnit(_str(raw_duration["unit"], "duration unit")),
            _optional_int(raw_duration.get("remaining"), "duration remaining"),
        )
    return ConditionInstance(
        condition_id=_str(item["condition_id"], "condition_id"),
        source_id=_optional_str(item.get("source_id"), "source_id"),
        duration=duration,
        stacks=_int(item.get("stacks", 1), "stacks"),
    )


def _dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError(f"{label} must be an object")
    return value


def _dict_list(value: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise ValidationError(f"{label} must be an array of objects")
    return value


def _string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValidationError(f"{label} must be an array of strings")
    return value


def _str(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{label} must be a string")
    return value


def _optional_str(value: Any, label: str) -> str | None:
    if value is None:
        return None
    return _str(value, label)


def _int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"{label} must be an integer")
    return value


def _optional_int(value: Any, label: str) -> int | None:
    if value is None:
        return None
    return _int(value, label)
