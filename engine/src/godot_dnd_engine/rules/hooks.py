"""Trigger and reaction-hook matching for deterministic event-driven rules."""

from __future__ import annotations

from dataclasses import dataclass

from ..errors import ValidationError
from .capabilities import RulesetCapabilities
from .effects import RuleEffect
from .requirements import Requirement, evaluate_requirements
from .state import RuleWorldState


@dataclass(frozen=True, slots=True)
class RuleEventView:
    event_type: str
    actor_id: str | None = None
    target_id: str | None = None
    tags: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if not isinstance(self.event_type, str) or not self.event_type.strip():
            raise ValidationError("event_type must be a non-empty string")


@dataclass(frozen=True, slots=True)
class Trigger:
    event_type: str
    required_tags: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if not isinstance(self.event_type, str) or not self.event_type.strip():
            raise ValidationError("trigger event_type must be a non-empty string")

    def matches(self, event: RuleEventView) -> bool:
        return self.event_type == event.event_type and self.required_tags.issubset(event.tags)


@dataclass(frozen=True, slots=True)
class ReactionHook:
    hook_id: str
    owner_id: str
    trigger: Trigger
    requirements: tuple[Requirement, ...] = ()
    effects: tuple[RuleEffect, ...] = ()
    priority: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.hook_id, str) or not self.hook_id.strip():
            raise ValidationError("hook_id must be a non-empty string")
        if not isinstance(self.owner_id, str) or not self.owner_id.strip():
            raise ValidationError("hook owner_id must be a non-empty string")
        if isinstance(self.priority, bool) or not isinstance(self.priority, int):
            raise ValidationError("hook priority must be an integer")


@dataclass(frozen=True, slots=True)
class ReactionMatch:
    hook: ReactionHook
    event: RuleEventView


def collect_reactions(
    event: RuleEventView,
    hooks: tuple[ReactionHook, ...],
    world: RuleWorldState,
    capabilities: RulesetCapabilities,
) -> tuple[ReactionMatch, ...]:
    matches: list[ReactionMatch] = []
    for hook in hooks:
        if not hook.trigger.matches(event):
            continue
        owner = world.subject(hook.owner_id)
        if evaluate_requirements(hook.requirements, owner, capabilities).passed:
            matches.append(ReactionMatch(hook, event))
    return tuple(sorted(matches, key=lambda item: (item.hook.priority, item.hook.hook_id)))
