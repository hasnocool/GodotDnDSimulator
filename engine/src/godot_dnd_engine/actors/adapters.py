"""Adapters between rich actor state and the generic v0.3 rules world."""

from __future__ import annotations

from dataclasses import dataclass

from ..errors import ValidationError
from ..rules.effects import EffectApplication, RuleEffect, apply_effects
from ..rules.state import RuleWorldState
from .model import ActorState


@dataclass(frozen=True, slots=True)
class ActorEffectResult:
    actors: tuple[ActorState, ...]
    applications: tuple[EffectApplication, ...]


def actors_to_rule_world(actors: tuple[ActorState, ...]) -> RuleWorldState:
    actor_ids = [actor.actor_id for actor in actors]
    if len(actor_ids) != len(set(actor_ids)):
        raise ValidationError("actor collections must have unique actor IDs")
    return RuleWorldState(tuple(actor.to_rule_subject() for actor in actors))


def merge_rule_world(
    actors: tuple[ActorState, ...],
    world: RuleWorldState,
) -> tuple[ActorState, ...]:
    actor_map = {actor.actor_id: actor for actor in actors}
    world_ids = {subject.subject_id for subject in world.subjects}
    if set(actor_map) != world_ids:
        raise ValidationError("rules world subject IDs must exactly match actor IDs")
    return tuple(
        sorted(
            (
                actor_map[subject.subject_id].with_rule_subject(subject)
                for subject in world.subjects
            ),
            key=lambda actor: actor.actor_id,
        )
    )


def apply_actor_effects(
    actors: tuple[ActorState, ...],
    *,
    source_id: str,
    effects: tuple[RuleEffect, ...],
) -> ActorEffectResult:
    world = actors_to_rule_world(actors)
    result = apply_effects(world, source_id=source_id, effects=effects)
    return ActorEffectResult(merge_rule_world(actors, result.world), result.applications)
