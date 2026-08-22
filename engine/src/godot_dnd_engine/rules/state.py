# engine/src/godot_dnd_engine/rules/state.py
"""Immutable lightweight rule-state primitives used before the v0.4 actor model."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ..errors import ValidationError
from .primitives import ResourcePool


class DurationUnit(StrEnum):
    TICKS = "ticks"
    ROUNDS = "rounds"
    TURNS = "turns"
    PERMANENT = "permanent"


@dataclass(frozen=True, slots=True)
class Duration:
    unit: DurationUnit
    remaining: int | None

    def __post_init__(self) -> None:
        if self.unit is DurationUnit.PERMANENT:
            if self.remaining is not None:
                raise ValidationError("permanent durations must not have a remaining value")
            return
        if (
            isinstance(self.remaining, bool)
            or not isinstance(self.remaining, int)
            or self.remaining < 1
        ):
            raise ValidationError("finite durations must have remaining >= 1")

    def advance(self, amount: int = 1) -> Duration | None:
        if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
            raise ValidationError("duration advance amount must be an integer >= 0")
        if self.unit is DurationUnit.PERMANENT or amount == 0:
            return self
        assert self.remaining is not None
        updated = self.remaining - amount
        if updated <= 0:
            return None
        return Duration(self.unit, updated)


class ConditionStacking(StrEnum):
    UNIQUE = "unique"
    REFRESH = "refresh"
    STACK = "stack"


@dataclass(frozen=True, slots=True)
class ConditionInstance:
    condition_id: str
    source_id: str | None = None
    duration: Duration | None = None
    stacks: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.condition_id, str) or not self.condition_id.strip():
            raise ValidationError("condition_id must be a non-empty string")
        if self.source_id is not None and (
            not isinstance(self.source_id, str) or not self.source_id.strip()
        ):
            raise ValidationError("condition source_id must be None or a non-empty string")
        if isinstance(self.stacks, bool) or not isinstance(self.stacks, int) or self.stacks < 1:
            raise ValidationError("condition stacks must be an integer >= 1")


@dataclass(frozen=True, slots=True)
class RuleSubjectState:
    subject_id: str
    tags: frozenset[str] = frozenset()
    resources: tuple[ResourcePool, ...] = ()
    conditions: tuple[ConditionInstance, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.subject_id, str) or not self.subject_id.strip():
            raise ValidationError("subject_id must be a non-empty string")
        if any(not isinstance(tag, str) or not tag for tag in self.tags):
            raise ValidationError("subject tags must be non-empty strings")
        resource_ids = [resource.resource_id for resource in self.resources]
        if len(resource_ids) != len(set(resource_ids)):
            raise ValidationError("subject resources must have unique resource IDs")
        sorted_resources = tuple(sorted(self.resources, key=lambda item: item.resource_id))
        object.__setattr__(self, "resources", sorted_resources)
        object.__setattr__(
            self,
            "conditions",
            tuple(
                sorted(
                    self.conditions,
                    key=lambda item: (item.condition_id, item.source_id or "", item.stacks),
                )
            ),
        )

    def resource(self, resource_id: str) -> ResourcePool | None:
        return next((item for item in self.resources if item.resource_id == resource_id), None)

    def has_condition(self, condition_id: str) -> bool:
        return any(item.condition_id == condition_id for item in self.conditions)

    def with_resource(self, updated: ResourcePool) -> RuleSubjectState:
        resources = {item.resource_id: item for item in self.resources}
        if updated.resource_id not in resources:
            raise ValidationError(f"unknown resource: {updated.resource_id!r}")
        resources[updated.resource_id] = updated
        return RuleSubjectState(
            subject_id=self.subject_id,
            tags=self.tags,
            resources=tuple(resources.values()),
            conditions=self.conditions,
        )

    def with_conditions(self, conditions: tuple[ConditionInstance, ...]) -> RuleSubjectState:
        return RuleSubjectState(
            subject_id=self.subject_id,
            tags=self.tags,
            resources=self.resources,
            conditions=conditions,
        )


def advance_condition_durations(
    subject: RuleSubjectState,
    unit: DurationUnit,
    amount: int = 1,
) -> RuleSubjectState:
    """Advance matching finite condition durations and remove expired conditions."""

    if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
        raise ValidationError("condition duration advance amount must be an integer >= 0")
    updated_conditions: list[ConditionInstance] = []
    for condition in subject.conditions:
        duration = condition.duration
        if duration is None or duration.unit is not unit:
            updated_conditions.append(condition)
            continue
        advanced = duration.advance(amount)
        if advanced is None:
            continue
        updated_conditions.append(
            ConditionInstance(
                condition_id=condition.condition_id,
                source_id=condition.source_id,
                duration=advanced,
                stacks=condition.stacks,
            )
        )
    return subject.with_conditions(tuple(updated_conditions))


@dataclass(frozen=True, slots=True)
class RuleWorldState:
    subjects: tuple[RuleSubjectState, ...]

    def __post_init__(self) -> None:
        subject_ids = [subject.subject_id for subject in self.subjects]
        if len(subject_ids) != len(set(subject_ids)):
            raise ValidationError("world subjects must have unique subject IDs")
        sorted_subjects = tuple(sorted(self.subjects, key=lambda item: item.subject_id))
        object.__setattr__(self, "subjects", sorted_subjects)

    def subject(self, subject_id: str) -> RuleSubjectState:
        for subject in self.subjects:
            if subject.subject_id == subject_id:
                return subject
        raise ValidationError(f"unknown subject: {subject_id!r}")

    def replace_subject(self, updated: RuleSubjectState) -> RuleWorldState:
        if not any(subject.subject_id == updated.subject_id for subject in self.subjects):
            raise ValidationError(f"unknown subject: {updated.subject_id!r}")
        return RuleWorldState(
            tuple(
                updated if subject.subject_id == updated.subject_id else subject
                for subject in self.subjects
            )
        )
