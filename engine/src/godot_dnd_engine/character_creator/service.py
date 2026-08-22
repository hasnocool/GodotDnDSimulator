# engine/src/godot_dnd_engine/character_creator/service.py
"""Transport-neutral v0.9 character creator session and JSON-shaped API."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..actors import actor_to_dict
from ..errors import UnsupportedCommandError, ValidationError
from ..rules import Ability
from .model import CharacterDraft, CharacterRecord
from .runtime import CharacterCreatorRuntime


@dataclass(slots=True)
class CharacterCreatorService:
    runtime: CharacterCreatorRuntime
    records: dict[str, CharacterRecord] = field(default_factory=dict)

    def query(
        self,
        query_type: str,
        payload: dict[str, Any],
    ) -> dict[str, object]:
        if query_type == "characters.creator.schema":
            schema = self.runtime.schema()
            schema["appearance_fields"] = [
                "body",
                "hair",
                "eyes",
                "voice",
                "portrait",
            ]
            schema["profile_fields"] = ["biography", "personality"]
            return schema
        if query_type == "characters.creator.preview":
            return self.runtime.preview(_draft(payload))
        if query_type == "characters.get":
            actor_id = _string(payload.get("actor_id"), "actor_id")
            return {"record": record_to_dict(self._record(actor_id))}
        if query_type == "characters.levelup.choices":
            actor_id = _string(payload.get("actor_id"), "actor_id")
            return self.runtime.level_up_choices(self._record(actor_id))
        raise UnsupportedCommandError(
            f"unsupported character creator query: {query_type}"
        )

    def command(
        self,
        command_type: str,
        payload: dict[str, Any],
    ) -> dict[str, object]:
        if command_type == "characters.create":
            draft = _draft(payload)
            if draft.actor_id in self.records:
                raise ValidationError(
                    "character actor_id already exists in creator session"
                )
            record = self.runtime.create(draft)
            self.records[record.actor.actor_id] = record
            return {"record": record_to_dict(record)}
        if command_type == "characters.level_up":
            actor_id = _string(payload.get("actor_id"), "actor_id")
            selected = _string_tuple(
                payload.get("selected_choice_ids", []),
                "selected_choice_ids",
            )
            record = self.runtime.level_up(self._record(actor_id), selected)
            self.records[actor_id] = record
            return {"record": record_to_dict(record)}
        raise UnsupportedCommandError(
            f"unsupported character creator command: {command_type}"
        )

    def _record(self, actor_id: str) -> CharacterRecord:
        record = self.records.get(actor_id)
        if record is None:
            raise ValidationError(f"unknown created character: {actor_id}")
        return record


def record_to_dict(record: CharacterRecord) -> dict[str, object]:
    return {
        "schema_version": 1,
        "catalog_id": record.catalog_id,
        "actor": actor_to_dict(record.actor),
        "species_id": record.species_id,
        "background_id": record.background_id,
        "class_id": record.class_id,
        "ability_method_id": record.ability_method_id,
        "appearance": dict(record.appearance),
        "biography": record.biography,
        "personality": record.personality,
        "spell_ids": list(record.spell_ids),
        "feature_ids": list(record.feature_ids),
    }


def _draft(payload: dict[str, Any]) -> CharacterDraft:
    draft_value = payload.get("draft", payload)
    if not isinstance(draft_value, dict):
        raise ValidationError("character draft must be an object")
    scores_value = draft_value.get("ability_scores")
    if not isinstance(scores_value, dict):
        raise ValidationError(
            "character draft ability_scores must be an object"
        )
    scores: list[tuple[Ability, int]] = []
    for ability in Ability:
        score = scores_value.get(ability.value)
        if isinstance(score, bool) or not isinstance(score, int):
            raise ValidationError(
                f"ability score {ability.value} must be an integer"
            )
        scores.append((ability, score))
    appearance_value = draft_value.get("appearance", {})
    if not isinstance(appearance_value, dict):
        raise ValidationError("character appearance must be an object")
    appearance: list[tuple[str, str]] = []
    for key, value in appearance_value.items():
        if (
            not isinstance(key, str)
            or not key.strip()
            or not isinstance(value, str)
        ):
            raise ValidationError(
                "character appearance entries must be string pairs"
            )
        appearance.append((key, value.strip()))
    return CharacterDraft(
        actor_id=_string(draft_value.get("actor_id"), "actor_id"),
        name=_string(draft_value.get("name"), "name"),
        selected_choice_ids=_string_tuple(
            draft_value.get("selected_choice_ids", []),
            "selected_choice_ids",
        ),
        ability_method_id=_string(
            draft_value.get("ability_method_id"),
            "ability_method_id",
        ),
        base_ability_scores=tuple(scores),
        appearance=tuple(sorted(appearance)),
        biography=_optional_string(
            draft_value.get("biography", ""),
            "biography",
        ),
        personality=_optional_string(
            draft_value.get("personality", ""),
            "personality",
        ),
    )


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{label} must be a non-empty string")
    return value.strip()


def _optional_string(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{label} must be a string")
    return value


def _string_tuple(value: Any, label: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValidationError(f"{label} must be an array")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValidationError(
                f"{label} must contain non-empty strings"
            )
        result.append(item)
    return tuple(result)
