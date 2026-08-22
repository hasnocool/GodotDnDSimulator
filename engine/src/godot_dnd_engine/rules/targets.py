"""Deterministic target selector primitives independent of Godot scene state."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ..errors import ValidationError
from .state import RuleSubjectState, RuleWorldState


class TargetMode(StrEnum):
    SELF = "self"
    SINGLE = "single"
    ALL = "all"


@dataclass(frozen=True, slots=True)
class TargetSelector:
    mode: TargetMode
    required_tags: frozenset[str] = frozenset()
    excluded_tags: frozenset[str] = frozenset()
    max_targets: int | None = None

    def __post_init__(self) -> None:
        if self.required_tags & self.excluded_tags:
            raise ValidationError("target selector cannot require and exclude the same tag")
        if self.max_targets is not None and (
            isinstance(self.max_targets, bool)
            or not isinstance(self.max_targets, int)
            or self.max_targets < 1
        ):
            raise ValidationError("max_targets must be None or an integer >= 1")
        if self.mode is TargetMode.SELF and self.max_targets not in (None, 1):
            raise ValidationError("self target selectors can select at most one target")
        if self.mode is TargetMode.SINGLE and self.max_targets not in (None, 1):
            raise ValidationError("single target selectors can select at most one target")


def _matches(selector: TargetSelector, subject: RuleSubjectState) -> bool:
    if not selector.required_tags.issubset(subject.tags):
        return False
    return not bool(selector.excluded_tags & subject.tags)


def select_targets(
    selector: TargetSelector,
    world: RuleWorldState,
    *,
    source_id: str,
) -> tuple[RuleSubjectState, ...]:
    if selector.mode is TargetMode.SELF:
        source = world.subject(source_id)
        return (source,) if _matches(selector, source) else ()

    candidates = tuple(
        subject
        for subject in world.subjects
        if subject.subject_id != source_id and _matches(selector, subject)
    )
    limit = 1 if selector.mode is TargetMode.SINGLE else selector.max_targets
    return candidates if limit is None else candidates[:limit]
