"""Atomic resource-cost resolution helpers."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from ..errors import ValidationError
from .primitives import ResourceCost
from .state import RuleSubjectState


@dataclass(frozen=True, slots=True)
class ResourceSpendResult:
    subject: RuleSubjectState
    spent: tuple[ResourceCost, ...]


def spend_costs(
    subject: RuleSubjectState,
    costs: tuple[ResourceCost, ...],
) -> ResourceSpendResult:
    aggregated: dict[str, int] = defaultdict(int)
    for cost in costs:
        aggregated[cost.resource_id] += cost.amount

    replacements = {item.resource_id: item for item in subject.resources}
    for resource_id, amount in sorted(aggregated.items()):
        resource = replacements.get(resource_id)
        if resource is None:
            raise ValidationError(f"unknown resource cost: {resource_id!r}")
        replacements[resource_id] = resource.with_delta(-amount)

    updated = RuleSubjectState(
        subject_id=subject.subject_id,
        tags=subject.tags,
        resources=tuple(replacements.values()),
        conditions=subject.conditions,
    )
    spent = tuple(
        ResourceCost(resource_id, amount)
        for resource_id, amount in sorted(aggregated.items())
    )
    return ResourceSpendResult(updated, spent)
