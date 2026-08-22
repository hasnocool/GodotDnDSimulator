"""Serializable requirement predicates for actions, effects, and reactions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ..errors import ValidationError
from .capabilities import RulesetCapabilities
from .state import RuleSubjectState


class RequirementKind(StrEnum):
    TAG_PRESENT = "tag_present"
    TAG_ABSENT = "tag_absent"
    RESOURCE_AT_LEAST = "resource_at_least"
    CONDITION_PRESENT = "condition_present"
    CONDITION_ABSENT = "condition_absent"
    CAPABILITY = "capability"


@dataclass(frozen=True, slots=True)
class Requirement:
    requirement_id: str
    kind: RequirementKind
    key: str
    minimum: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.requirement_id, str) or not self.requirement_id.strip():
            raise ValidationError("requirement_id must be a non-empty string")
        if not isinstance(self.key, str) or not self.key.strip():
            raise ValidationError("requirement key must be a non-empty string")
        if isinstance(self.minimum, bool) or not isinstance(self.minimum, int) or self.minimum < 0:
            raise ValidationError("requirement minimum must be an integer >= 0")


@dataclass(frozen=True, slots=True)
class RequirementResult:
    passed: bool
    failed_requirement_ids: tuple[str, ...]


def requirement_passes(
    requirement: Requirement,
    subject: RuleSubjectState,
    capabilities: RulesetCapabilities,
) -> bool:
    if requirement.kind is RequirementKind.TAG_PRESENT:
        return requirement.key in subject.tags
    if requirement.kind is RequirementKind.TAG_ABSENT:
        return requirement.key not in subject.tags
    if requirement.kind is RequirementKind.CONDITION_PRESENT:
        return subject.has_condition(requirement.key)
    if requirement.kind is RequirementKind.CONDITION_ABSENT:
        return not subject.has_condition(requirement.key)
    if requirement.kind is RequirementKind.CAPABILITY:
        return capabilities.supports(requirement.key)
    resource = subject.resource(requirement.key)
    return resource is not None and resource.current >= requirement.minimum


def evaluate_requirements(
    requirements: tuple[Requirement, ...],
    subject: RuleSubjectState,
    capabilities: RulesetCapabilities,
) -> RequirementResult:
    failed = tuple(
        requirement.requirement_id
        for requirement in requirements
        if not requirement_passes(requirement, subject, capabilities)
    )
    return RequirementResult(passed=not failed, failed_requirement_ids=failed)
