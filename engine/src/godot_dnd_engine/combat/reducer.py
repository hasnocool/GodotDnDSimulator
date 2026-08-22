# engine/src/godot_dnd_engine/combat/reducer.py
"""Pure combat event reducer for replayable tactical state."""

from __future__ import annotations

from dataclasses import replace

from ..errors import ValidationError
from ..rules.state import ConditionInstance
from .model import (
    ActionEconomy,
    ActionResource,
    CombatEvent,
    DeathSaveTrack,
    EncounterState,
    EncounterStatus,
    InitiativeEntry,
    LifeState,
    ReactionWindow,
    actor_with_conditions,
    actor_with_hit_points,
)

_UNCONSCIOUS_CONDITION = "condition:unconscious"


def _int(event: CombatEvent, key: str) -> int:
    value = event.value(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"combat event {key!r} must be an integer")
    return value


def _str(event: CombatEvent, key: str) -> str:
    value = event.value(key)
    if not isinstance(value, str):
        raise ValidationError(f"combat event {key!r} must be a string")
    return value


def _strings(event: CombatEvent, key: str) -> tuple[str, ...]:
    value = event.value(key)
    if not isinstance(value, tuple) or any(not isinstance(item, str) for item in value):
        raise ValidationError(f"combat event {key!r} must be a string tuple")
    return value


def _sync_unconscious_condition(state: EncounterState, actor_id: str) -> EncounterState:
    combatant = state.combatant(actor_id)
    conditions = tuple(
        item for item in combatant.actor.conditions if item.condition_id != _UNCONSCIOUS_CONDITION
    )
    if combatant.life_state in (LifeState.UNCONSCIOUS, LifeState.STABLE):
        conditions = (
            *conditions,
            ConditionInstance(_UNCONSCIOUS_CONDITION, source_id="combat:v0.5"),
        )
    actor = actor_with_conditions(combatant.actor, conditions)
    return state.replace_combatant(combatant.with_actor(actor))


def apply_combat_event(state: EncounterState, event: CombatEvent) -> EncounterState:
    if event.sequence != state.event_sequence + 1:
        raise ValidationError("combat event sequence is not contiguous")
    updated = replace(state, event_sequence=event.sequence)

    if event.event_type == "initiative.rolled":
        assert event.actor_id is not None
        entry = InitiativeEntry(
            actor_id=event.actor_id,
            total=_int(event, "total"),
            dexterity_modifier=_int(event, "dexterity_modifier"),
            raw_roll=_int(event, "raw_roll"),
        )
        initiative = tuple(item for item in updated.initiative if item.actor_id != entry.actor_id)
        return replace(updated, initiative=(*initiative, entry))

    if event.event_type == "encounter.started":
        order = _strings(event, "order")
        by_id = {item.actor_id: item for item in updated.initiative}
        initiative = tuple(by_id[actor_id] for actor_id in order)
        return replace(
            updated,
            status=EncounterStatus.ACTIVE,
            round_number=1,
            turn_index=0,
            initiative=initiative,
        )

    if event.event_type == "encounter.ended":
        return replace(updated, status=EncounterStatus.ENDED, reaction_windows=())

    if event.event_type == "turn.started":
        assert event.actor_id is not None
        actor_id = event.actor_id
        turn_index = _int(event, "turn_index")
        round_number = _int(event, "round_number")
        combatant = updated.combatant(actor_id)
        economy = ActionEconomy(
            action_available=True,
            bonus_action_available=True,
            reaction_available=True,
            movement_remaining=combatant.walking_speed(),
        )
        combatant = replace(combatant, economy=economy)
        updated = updated.replace_combatant(combatant)
        return replace(updated, round_number=round_number, turn_index=turn_index)

    if event.event_type == "action.spent":
        assert event.actor_id is not None
        resource = ActionResource(_str(event, "resource"))
        combatant = updated.combatant(event.actor_id)
        return updated.replace_combatant(
            replace(combatant, economy=combatant.economy.spend(resource))
        )

    if event.event_type == "movement.spent":
        assert event.actor_id is not None
        combatant = updated.combatant(event.actor_id)
        return updated.replace_combatant(
            replace(combatant, economy=combatant.economy.spend_movement(_int(event, "feet")))
        )

    if event.event_type in {"damage.applied", "healing.applied", "death_save.resolved"}:
        assert event.target_id is not None
        combatant = updated.combatant(event.target_id)
        actor = actor_with_hit_points(
            combatant.actor,
            current=_int(event, "hp_after"),
            temporary=_int(event, "temporary_after"),
        )
        combatant = replace(
            combatant,
            actor=actor,
            life_state=LifeState(_str(event, "life_state")),
            death_saves=DeathSaveTrack(
                successes=_int(event, "death_successes"),
                failures=_int(event, "death_failures"),
            ),
        )
        synced = updated.replace_combatant(combatant)
        return _sync_unconscious_condition(synced, event.target_id)

    if event.event_type == "temporary_hp.changed":
        assert event.target_id is not None
        combatant = updated.combatant(event.target_id)
        actor = actor_with_hit_points(
            combatant.actor,
            current=combatant.actor.hit_points.current,
            temporary=_int(event, "temporary_after"),
        )
        return updated.replace_combatant(combatant.with_actor(actor))

    if event.event_type == "reaction.window.opened":
        assert event.actor_id is not None
        window = ReactionWindow(
            window_id=_str(event, "window_id"),
            trigger=_str(event, "trigger"),
            source_actor_id=event.actor_id,
            eligible_actor_ids=_strings(event, "eligible_actor_ids"),
        )
        return replace(updated, reaction_windows=(*updated.reaction_windows, window))

    if event.event_type == "reaction.window.closed":
        window_id = _str(event, "window_id")
        return replace(
            updated,
            reaction_windows=tuple(
                window for window in updated.reaction_windows if window.window_id != window_id
            ),
        )

    if event.event_type == "condition.applied":
        assert event.target_id is not None
        combatant = updated.combatant(event.target_id)
        condition_id = _str(event, "condition_id")
        source_id = event.value("source_id")
        source = source_id if isinstance(source_id, str) else None
        existing = tuple(
            item for item in combatant.actor.conditions if item.condition_id != condition_id
        )
        actor = actor_with_conditions(
            combatant.actor,
            (*existing, ConditionInstance(condition_id, source_id=source)),
        )
        return updated.replace_combatant(combatant.with_actor(actor))

    if event.event_type == "condition.removed":
        assert event.target_id is not None
        combatant = updated.combatant(event.target_id)
        condition_id = _str(event, "condition_id")
        actor = actor_with_conditions(
            combatant.actor,
            tuple(item for item in combatant.actor.conditions if item.condition_id != condition_id),
        )
        return updated.replace_combatant(combatant.with_actor(actor))

    if event.event_type == "attack.resolved":
        return updated

    raise ValidationError(f"unsupported combat event type: {event.event_type!r}")


def replay_combat(initial: EncounterState, events: tuple[CombatEvent, ...]) -> EncounterState:
    state = initial
    for event in events:
        state = apply_combat_event(state, event)
    return state
