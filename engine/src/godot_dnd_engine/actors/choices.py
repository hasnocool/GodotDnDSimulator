"""Data-driven character option and choice-constraint primitives."""

from __future__ import annotations

from dataclasses import dataclass

from ..errors import ValidationError


@dataclass(frozen=True, slots=True)
class CharacterOption:
    option_id: str
    category: str
    grants_tags: frozenset[str] = frozenset()
    requires: frozenset[str] = frozenset()
    conflicts: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if not isinstance(self.option_id, str) or not self.option_id.strip():
            raise ValidationError("character option_id must be a non-empty string")
        if not isinstance(self.category, str) or not self.category.strip():
            raise ValidationError("character option category must be a non-empty string")
        for label, values in (
            ("grants_tags", self.grants_tags),
            ("requires", self.requires),
            ("conflicts", self.conflicts),
        ):
            if any(not isinstance(value, str) or not value.strip() for value in values):
                raise ValidationError(f"character option {label} must contain non-empty strings")
        if self.option_id in self.conflicts:
            raise ValidationError("character option cannot conflict with itself")


@dataclass(frozen=True, slots=True)
class ChoiceGroup:
    group_id: str
    option_ids: tuple[str, ...]
    minimum: int = 1
    maximum: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.group_id, str) or not self.group_id.strip():
            raise ValidationError("choice group_id must be a non-empty string")
        if not self.option_ids:
            raise ValidationError("choice group must contain at least one option")
        if len(self.option_ids) != len(set(self.option_ids)):
            raise ValidationError("choice group option IDs must be unique")
        if any(not isinstance(value, str) or not value.strip() for value in self.option_ids):
            raise ValidationError("choice group option IDs must be non-empty strings")
        for label, value in (("minimum", self.minimum), ("maximum", self.maximum)):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValidationError(f"choice group {label} must be an integer >= 0")
        if self.minimum > self.maximum:
            raise ValidationError("choice group minimum cannot exceed maximum")
        if self.maximum > len(self.option_ids):
            raise ValidationError("choice group maximum cannot exceed its option count")


@dataclass(frozen=True, slots=True)
class ChoiceValidationResult:
    selected_option_ids: tuple[str, ...]
    granted_tags: frozenset[str]


def validate_choices(
    options: tuple[CharacterOption, ...],
    groups: tuple[ChoiceGroup, ...],
    selected_option_ids: tuple[str, ...],
) -> ChoiceValidationResult:
    option_map = {option.option_id: option for option in options}
    if len(option_map) != len(options):
        raise ValidationError("character options must have unique option IDs")
    group_ids = [group.group_id for group in groups]
    if len(group_ids) != len(set(group_ids)):
        raise ValidationError("choice groups must have unique group IDs")
    for group in groups:
        missing = set(group.option_ids) - option_map.keys()
        if missing:
            raise ValidationError(
                f"choice group {group.group_id!r} references unknown options: {sorted(missing)}"
            )
    if len(selected_option_ids) != len(set(selected_option_ids)):
        raise ValidationError("selected character option IDs must be unique")
    selected = set(selected_option_ids)
    unknown = selected - option_map.keys()
    if unknown:
        raise ValidationError(f"unknown selected character options: {sorted(unknown)}")
    for group in groups:
        count = len(selected.intersection(group.option_ids))
        if not group.minimum <= count <= group.maximum:
            raise ValidationError(
                f"choice group {group.group_id!r} requires {group.minimum}..{group.maximum} choices"
            )
    granted_tags: set[str] = set()
    for option_id in sorted(selected):
        option = option_map[option_id]
        missing_requirements = option.requires - selected
        if missing_requirements:
            raise ValidationError(
                f"option {option_id!r} requires selections: {sorted(missing_requirements)}"
            )
        conflicts = option.conflicts.intersection(selected)
        if conflicts:
            raise ValidationError(f"option {option_id!r} conflicts with: {sorted(conflicts)}")
        granted_tags.update(option.grants_tags)
    return ChoiceValidationResult(tuple(sorted(selected)), frozenset(granted_tags))
