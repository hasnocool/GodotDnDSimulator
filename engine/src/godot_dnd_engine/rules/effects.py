"""Generic deterministic effect pipeline for resources and conditions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ..errors import ValidationError
from .state import ConditionInstance, ConditionStacking, Duration, RuleSubjectState, RuleWorldState
from .targets import TargetSelector, select_targets


class EffectKind(StrEnum):
    RESOURCE_DELTA = "resource_delta"
    APPLY_CONDITION = "apply_condition"
    REMOVE_CONDITION = "remove_condition"


@dataclass(frozen=True, slots=True)
class RuleEffect:
    effect_id: str
    kind: EffectKind
    target_selector: TargetSelector
    resource_id: str | None = None
    amount: int = 0
    condition_id: str | None = None
    duration: Duration | None = None
    condition_stacking: ConditionStacking = ConditionStacking.UNIQUE
    stacks: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.effect_id, str) or not self.effect_id.strip():
            raise ValidationError("effect_id must be a non-empty string")
        if isinstance(self.amount, bool) or not isinstance(self.amount, int):
            raise ValidationError("effect amount must be an integer")
        if isinstance(self.stacks, bool) or not isinstance(self.stacks, int) or self.stacks < 1:
            raise ValidationError("effect stacks must be an integer >= 1")
        if self.kind is EffectKind.RESOURCE_DELTA:
            if not isinstance(self.resource_id, str) or not self.resource_id.strip():
                raise ValidationError("resource_delta effects require resource_id")
            if self.condition_id is not None:
                raise ValidationError("resource_delta effects cannot define condition_id")
        else:
            if not isinstance(self.condition_id, str) or not self.condition_id.strip():
                raise ValidationError("condition effects require condition_id")
            if self.resource_id is not None:
                raise ValidationError("condition effects cannot define resource_id")


@dataclass(frozen=True, slots=True)
class EffectApplication:
    effect_id: str
    target_id: str
    kind: EffectKind
    before: int | str | None
    after: int | str | None


@dataclass(frozen=True, slots=True)
class EffectBatchResult:
    world: RuleWorldState
    applications: tuple[EffectApplication, ...]


def _apply_condition(
    subject: RuleSubjectState,
    effect: RuleEffect,
    source_id: str,
) -> tuple[RuleSubjectState, EffectApplication]:
    assert effect.condition_id is not None
    matching = tuple(
        item for item in subject.conditions if item.condition_id == effect.condition_id
    )
    new_instance = ConditionInstance(
        condition_id=effect.condition_id,
        source_id=source_id,
        duration=effect.duration,
        stacks=effect.stacks,
    )
    before = str(sum(item.stacks for item in matching)) if matching else None

    if effect.condition_stacking is ConditionStacking.UNIQUE and matching:
        return subject, EffectApplication(
            effect.effect_id,
            subject.subject_id,
            effect.kind,
            before,
            before,
        )
    if effect.condition_stacking is ConditionStacking.REFRESH and matching:
        conditions = tuple(
            item for item in subject.conditions if item.condition_id != effect.condition_id
        ) + (new_instance,)
    elif effect.condition_stacking is ConditionStacking.STACK and matching:
        conditions = subject.conditions + (new_instance,)
    else:
        conditions = subject.conditions + (new_instance,)

    updated = subject.with_conditions(conditions)
    after = str(
        sum(item.stacks for item in updated.conditions if item.condition_id == effect.condition_id)
    )
    return updated, EffectApplication(
        effect.effect_id,
        subject.subject_id,
        effect.kind,
        before,
        after,
    )


def _remove_condition(
    subject: RuleSubjectState,
    effect: RuleEffect,
) -> tuple[RuleSubjectState, EffectApplication]:
    assert effect.condition_id is not None
    matching = tuple(
        item for item in subject.conditions if item.condition_id == effect.condition_id
    )
    conditions = tuple(
        item for item in subject.conditions if item.condition_id != effect.condition_id
    )
    updated = subject.with_conditions(conditions)
    before = str(sum(item.stacks for item in matching)) if matching else None
    return updated, EffectApplication(
        effect.effect_id,
        subject.subject_id,
        effect.kind,
        before,
        None,
    )


def _apply_one(
    subject: RuleSubjectState,
    effect: RuleEffect,
    source_id: str,
) -> tuple[RuleSubjectState, EffectApplication]:
    if effect.kind is EffectKind.RESOURCE_DELTA:
        assert effect.resource_id is not None
        resource = subject.resource(effect.resource_id)
        if resource is None:
            raise ValidationError(
                f"target {subject.subject_id!r} lacks resource {effect.resource_id!r}"
            )
        updated_resource = resource.with_delta(effect.amount)
        return subject.with_resource(updated_resource), EffectApplication(
            effect.effect_id,
            subject.subject_id,
            effect.kind,
            resource.current,
            updated_resource.current,
        )
    if effect.kind is EffectKind.APPLY_CONDITION:
        return _apply_condition(subject, effect, source_id)
    return _remove_condition(subject, effect)


def apply_effects(
    world: RuleWorldState,
    *,
    source_id: str,
    effects: tuple[RuleEffect, ...],
) -> EffectBatchResult:
    """Apply an ordered effect batch as a pure/atomic transform.

    The input world is never mutated. If any effect is invalid, the function raises and the caller
    retains the original world, so a multi-effect rule cannot partially commit state.
    """

    effect_ids = [effect.effect_id for effect in effects]
    if len(effect_ids) != len(set(effect_ids)):
        raise ValidationError("effect batches require unique effect IDs")

    updated_world = world
    applications: list[EffectApplication] = []
    for effect in effects:
        targets = select_targets(effect.target_selector, updated_world, source_id=source_id)
        for target in targets:
            current = updated_world.subject(target.subject_id)
            updated, application = _apply_one(current, effect, source_id)
            updated_world = updated_world.replace_subject(updated)
            applications.append(application)
    return EffectBatchResult(updated_world, tuple(applications))
