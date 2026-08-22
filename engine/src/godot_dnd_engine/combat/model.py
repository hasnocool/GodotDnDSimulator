# engine/src/godot_dnd_engine/combat/model.py
"""Immutable tactical-combat state for the v0.5 headless runtime."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import StrEnum

from ..actors import ActorKind, ActorState, HitPoints, MovementMode
from ..errors import ValidationError
from ..models import RNGCheckpoint
from ..rules.state import ConditionInstance


class EncounterStatus(StrEnum):
    PREPARING = "preparing"
    ACTIVE = "active"
    ENDED = "ended"


class ActionResource(StrEnum):
    ACTION = "action"
    BONUS_ACTION = "bonus_action"
    REACTION = "reaction"


class LifeState(StrEnum):
    CONSCIOUS = "conscious"
    UNCONSCIOUS = "unconscious"
    STABLE = "stable"
    DEAD = "dead"


class ZeroHitPointRule(StrEnum):
    CHARACTER = "character"
    MONSTER = "monster"


class TemporaryHitPointChoice(StrEnum):
    KEEP_CURRENT = "keep_current"
    TAKE_NEW = "take_new"


COMBAT_EVENT_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class DeathSaveTrack:
    successes: int = 0
    failures: int = 0

    def __post_init__(self) -> None:
        for label, value in (("successes", self.successes), ("failures", self.failures)):
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 3:
                raise ValidationError(f"death-save {label} must be an integer from 0 to 3")


@dataclass(frozen=True, slots=True)
class DefenseProfile:
    resistances: frozenset[str] = frozenset()
    immunities: frozenset[str] = frozenset()
    vulnerabilities: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        for name, values in (
            ("resistances", self.resistances),
            ("immunities", self.immunities),
            ("vulnerabilities", self.vulnerabilities),
        ):
            if any(not isinstance(value, str) or not value.strip() for value in values):
                raise ValidationError(f"{name} must contain non-empty damage-type IDs")


@dataclass(frozen=True, slots=True)
class ActionEconomy:
    action_available: bool = False
    bonus_action_available: bool = False
    reaction_available: bool = True
    movement_remaining: int = 0

    def __post_init__(self) -> None:
        if (
            isinstance(self.movement_remaining, bool)
            or not isinstance(self.movement_remaining, int)
            or self.movement_remaining < 0
        ):
            raise ValidationError("movement_remaining must be an integer >= 0")

    def spend(self, resource: ActionResource) -> ActionEconomy:
        if resource is ActionResource.ACTION:
            if not self.action_available:
                raise ValidationError("action is not available")
            return replace(self, action_available=False)
        if resource is ActionResource.BONUS_ACTION:
            if not self.bonus_action_available:
                raise ValidationError("bonus action is not available")
            return replace(self, bonus_action_available=False)
        if not self.reaction_available:
            raise ValidationError("reaction is not available")
        return replace(self, reaction_available=False)

    def spend_movement(self, feet: int) -> ActionEconomy:
        if isinstance(feet, bool) or not isinstance(feet, int) or feet < 0:
            raise ValidationError("movement cost must be an integer >= 0")
        if feet > self.movement_remaining:
            raise ValidationError("movement cost exceeds remaining movement")
        return replace(self, movement_remaining=self.movement_remaining - feet)


@dataclass(frozen=True, slots=True)
class CombatConditionRule:
    condition_id: str
    blocks_action: bool = False
    blocks_bonus_action: bool = False
    blocks_reaction: bool = False
    blocks_movement: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.condition_id, str) or not self.condition_id.strip():
            raise ValidationError("condition rule ID must be a non-empty string")


@dataclass(frozen=True, slots=True)
class CombatantState:
    actor: ActorState
    defenses: DefenseProfile = field(default_factory=DefenseProfile)
    life_state: LifeState = LifeState.CONSCIOUS
    death_saves: DeathSaveTrack = field(default_factory=DeathSaveTrack)
    economy: ActionEconomy = field(default_factory=ActionEconomy)
    zero_hp_rule: ZeroHitPointRule | None = None

    def __post_init__(self) -> None:
        rule = self.zero_hp_rule
        if rule is None:
            rule = (
                ZeroHitPointRule.MONSTER
                if self.actor.kind is ActorKind.CREATURE
                else ZeroHitPointRule.CHARACTER
            )
            object.__setattr__(self, "zero_hp_rule", rule)
        if self.life_state is LifeState.CONSCIOUS and self.actor.hit_points.current == 0:
            raise ValidationError("a conscious combatant must have at least 1 hit point")
        if self.life_state in (LifeState.UNCONSCIOUS, LifeState.STABLE) and (
            self.actor.hit_points.current != 0
        ):
            raise ValidationError("unconscious/stable combatants must have 0 hit points")

    @property
    def actor_id(self) -> str:
        return self.actor.actor_id

    def walking_speed(self) -> int:
        return self.actor.movement_speed(MovementMode.WALK) or 0

    def has_condition(self, condition_id: str) -> bool:
        return any(item.condition_id == condition_id for item in self.actor.conditions)

    def with_actor(self, actor: ActorState) -> CombatantState:
        if actor.actor_id != self.actor_id:
            raise ValidationError("combatant actor ID cannot change")
        return replace(self, actor=actor)


@dataclass(frozen=True, slots=True)
class InitiativeEntry:
    actor_id: str
    total: int
    dexterity_modifier: int
    raw_roll: int

    def __post_init__(self) -> None:
        if not isinstance(self.actor_id, str) or not self.actor_id.strip():
            raise ValidationError("initiative actor_id must be a non-empty string")
        for label, value in (
            ("total", self.total),
            ("dexterity_modifier", self.dexterity_modifier),
            ("raw_roll", self.raw_roll),
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValidationError(f"initiative {label} must be an integer")
        if not 1 <= self.raw_roll <= 20:
            raise ValidationError("initiative raw_roll must be between 1 and 20")


@dataclass(frozen=True, slots=True)
class ReactionWindow:
    window_id: str
    trigger: str
    source_actor_id: str
    eligible_actor_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        for label, value in (("window_id", self.window_id), ("trigger", self.trigger)):
            if not isinstance(value, str) or not value.strip():
                raise ValidationError(f"reaction {label} must be a non-empty string")
        if not isinstance(self.source_actor_id, str) or not self.source_actor_id.strip():
            raise ValidationError("reaction source_actor_id must be a non-empty string")
        if len(self.eligible_actor_ids) != len(set(self.eligible_actor_ids)):
            raise ValidationError("reaction eligible actor IDs must be unique")
        if any(not isinstance(item, str) or not item.strip() for item in self.eligible_actor_ids):
            raise ValidationError("reaction eligible actor IDs must be non-empty strings")
        object.__setattr__(self, "eligible_actor_ids", tuple(sorted(self.eligible_actor_ids)))


type EventValue = str | int | bool | tuple[str, ...] | None


@dataclass(frozen=True, slots=True)
class CombatEvent:
    sequence: int
    event_type: str
    actor_id: str | None = None
    target_id: str | None = None
    payload: tuple[tuple[str, EventValue], ...] = ()
    schema_version: int = COMBAT_EVENT_SCHEMA_VERSION
    rng_after: RNGCheckpoint | None = None

    def __post_init__(self) -> None:
        if (
            isinstance(self.sequence, bool)
            or not isinstance(self.sequence, int)
            or self.sequence < 1
        ):
            raise ValidationError("combat event sequence must be an integer >= 1")
        if self.schema_version != COMBAT_EVENT_SCHEMA_VERSION:
            raise ValidationError(
                f"unsupported combat event schema version: {self.schema_version!r}"
            )
        if not isinstance(self.event_type, str) or not self.event_type.strip():
            raise ValidationError("combat event_type must be a non-empty string")
        if self.rng_after is not None and not isinstance(self.rng_after, RNGCheckpoint):
            raise ValidationError("combat event rng_after must be an RNGCheckpoint or None")
        keys = [key for key, _ in self.payload]
        if len(keys) != len(set(keys)):
            raise ValidationError("combat event payload keys must be unique")
        object.__setattr__(self, "payload", tuple(sorted(self.payload, key=lambda item: item[0])))

    def value(self, key: str) -> EventValue:
        for candidate, value in self.payload:
            if candidate == key:
                return value
        raise ValidationError(f"combat event payload is missing {key!r}")


@dataclass(frozen=True, slots=True)
class EncounterState:
    encounter_id: str
    status: EncounterStatus
    combatants: tuple[CombatantState, ...]
    initiative: tuple[InitiativeEntry, ...] = ()
    round_number: int = 0
    turn_index: int = 0
    reaction_windows: tuple[ReactionWindow, ...] = ()
    condition_rules: tuple[CombatConditionRule, ...] = ()
    event_sequence: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.encounter_id, str) or not self.encounter_id.strip():
            raise ValidationError("encounter_id must be a non-empty string")
        actor_ids = [item.actor_id for item in self.combatants]
        if not actor_ids:
            raise ValidationError("encounters require at least one combatant")
        if len(actor_ids) != len(set(actor_ids)):
            raise ValidationError("encounter combatant IDs must be unique")
        initiative_ids = [item.actor_id for item in self.initiative]
        if len(initiative_ids) != len(set(initiative_ids)):
            raise ValidationError("initiative actor IDs must be unique")
        if self.status is not EncounterStatus.PREPARING and set(initiative_ids) != set(actor_ids):
            raise ValidationError("active/ended initiative must contain every encounter combatant")
        if (
            self.status is EncounterStatus.PREPARING
            and not set(initiative_ids).issubset(set(actor_ids))
        ):
            raise ValidationError("preparing initiative contains an unknown combatant")
        if (
            isinstance(self.round_number, bool)
            or not isinstance(self.round_number, int)
            or self.round_number < 0
        ):
            raise ValidationError("round_number must be an integer >= 0")
        if (
            isinstance(self.turn_index, bool)
            or not isinstance(self.turn_index, int)
            or self.turn_index < 0
        ):
            raise ValidationError("turn_index must be an integer >= 0")
        if (
            isinstance(self.event_sequence, bool)
            or not isinstance(self.event_sequence, int)
            or self.event_sequence < 0
        ):
            raise ValidationError("event_sequence must be an integer >= 0")
        if self.initiative and self.turn_index >= len(self.initiative):
            raise ValidationError("turn_index is outside initiative order")
        window_ids = [item.window_id for item in self.reaction_windows]
        if len(window_ids) != len(set(window_ids)):
            raise ValidationError("reaction window IDs must be unique")
        rule_ids = [item.condition_id for item in self.condition_rules]
        if len(rule_ids) != len(set(rule_ids)):
            raise ValidationError("combat condition rule IDs must be unique")
        object.__setattr__(
            self,
            "combatants",
            tuple(sorted(self.combatants, key=lambda item: item.actor_id)),
        )
        object.__setattr__(
            self,
            "reaction_windows",
            tuple(sorted(self.reaction_windows, key=lambda item: item.window_id)),
        )
        object.__setattr__(
            self,
            "condition_rules",
            tuple(sorted(self.condition_rules, key=lambda item: item.condition_id)),
        )

    @property
    def current_actor_id(self) -> str | None:
        if self.status is not EncounterStatus.ACTIVE or not self.initiative:
            return None
        return self.initiative[self.turn_index].actor_id

    def combatant(self, actor_id: str) -> CombatantState:
        for item in self.combatants:
            if item.actor_id == actor_id:
                return item
        raise ValidationError(f"unknown combatant: {actor_id!r}")

    def replace_combatant(self, updated: CombatantState) -> EncounterState:
        if not any(item.actor_id == updated.actor_id for item in self.combatants):
            raise ValidationError(f"unknown combatant: {updated.actor_id!r}")
        return replace(
            self,
            combatants=tuple(
                updated if item.actor_id == updated.actor_id else item for item in self.combatants
            ),
        )

    def condition_rule(self, condition_id: str) -> CombatConditionRule | None:
        return next(
            (item for item in self.condition_rules if item.condition_id == condition_id),
            None,
        )

    def next_sequence(self) -> int:
        return self.event_sequence + 1


def actor_with_hit_points(actor: ActorState, current: int, temporary: int) -> ActorState:
    return replace(
        actor,
        hit_points=HitPoints(
            current=current,
            maximum=actor.hit_points.maximum,
            temporary=temporary,
        ),
    )


def actor_with_conditions(
    actor: ActorState,
    conditions: tuple[ConditionInstance, ...],
) -> ActorState:
    return replace(actor, conditions=conditions)
