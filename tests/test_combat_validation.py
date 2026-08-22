from __future__ import annotations

from dataclasses import replace

import pytest

from godot_dnd_engine.actors import (
    ActorKind,
    ActorState,
    DefenseState,
    HitPoints,
    MovementMode,
    MovementSpeed,
)
from godot_dnd_engine.combat import (
    ActionEconomy,
    ActionResource,
    AttackDefinition,
    CombatConditionRule,
    CombatEvent,
    CombatRuntime,
    CombatantState,
    DamagePacket,
    DeathSaveTrack,
    DefenseProfile,
    EncounterState,
    EncounterStatus,
    InitiativeEntry,
    LifeState,
    ReactionWindow,
    TemporaryHitPointChoice,
    ZeroHitPointRule,
    apply_combat_event,
    deserialize_event,
    deserialize_log,
    serialize_event,
    serialize_log,
)
from godot_dnd_engine.dice import DiceExpression
from godot_dnd_engine.errors import ValidationError
from godot_dnd_engine.rng import DeterministicRNG
from godot_dnd_engine.rules import Ability, AbilityScore, ProficiencyRank


def actor(
    actor_id: str = "actor:a", *, hp: int = 10, kind: ActorKind = ActorKind.HERO
) -> ActorState:
    return ActorState(
        actor_id=actor_id,
        name=actor_id,
        kind=kind,
        proficiency_bonus=2,
        abilities=tuple(AbilityScore(ability, 12) for ability in Ability),
        hit_points=HitPoints(hp, hp),
        defense=DefenseState(12),
        movement=(MovementSpeed(MovementMode.WALK, 30),),
    )


def active(runtime: CombatRuntime) -> EncounterState:
    base = runtime.create_encounter("encounter:test", (actor("actor:a"), actor("actor:b")))
    return runtime.start_encounter(base).state


def test_model_validation_boundaries() -> None:
    with pytest.raises(ValidationError):
        DeathSaveTrack(successes=4)
    with pytest.raises(ValidationError):
        DeathSaveTrack(failures=True)  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        DefenseProfile(resistances=frozenset({""}))
    with pytest.raises(ValidationError):
        ActionEconomy(movement_remaining=-1)
    with pytest.raises(ValidationError):
        ActionEconomy(movement_remaining=True)  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        CombatConditionRule("")
    with pytest.raises(ValidationError):
        CombatantState(replace(actor(), hit_points=HitPoints(0, 10)))
    with pytest.raises(ValidationError):
        CombatantState(actor(), life_state=LifeState.UNCONSCIOUS)
    with pytest.raises(ValidationError):
        CombatantState(actor()).with_actor(actor("actor:other"))
    with pytest.raises(ValidationError):
        InitiativeEntry("", 1, 1, 1)
    with pytest.raises(ValidationError):
        InitiativeEntry("actor:a", "bad", 1, 1)  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        InitiativeEntry("actor:a", 1, 1, 0)
    with pytest.raises(ValidationError):
        ReactionWindow("", "trigger", "actor:a", ())
    with pytest.raises(ValidationError):
        ReactionWindow("window", "", "actor:a", ())
    with pytest.raises(ValidationError):
        ReactionWindow("window", "trigger", "", ())
    with pytest.raises(ValidationError):
        ReactionWindow("window", "trigger", "actor:a", ("actor:b", "actor:b"))
    with pytest.raises(ValidationError):
        ReactionWindow("window", "trigger", "actor:a", ("",))
    with pytest.raises(ValidationError):
        CombatEvent(0, "event")
    with pytest.raises(ValidationError):
        CombatEvent(1, "")
    with pytest.raises(ValidationError):
        CombatEvent(1, "event", payload=(("a", 1), ("a", 2)))
    with pytest.raises(ValidationError):
        CombatEvent(1, "event", schema_version=2)
    with pytest.raises(ValidationError):
        CombatEvent(1, "event").value("missing")


def test_action_economy_validation_and_reaction_spend() -> None:
    economy = ActionEconomy(True, True, True, 10)
    assert not economy.spend(ActionResource.REACTION).reaction_available
    with pytest.raises(ValidationError):
        replace(economy, reaction_available=False).spend(ActionResource.REACTION)
    with pytest.raises(ValidationError):
        economy.spend_movement(-1)


def test_encounter_validation_boundaries() -> None:
    combatant_a = CombatantState(actor("actor:a"))
    combatant_b = CombatantState(actor("actor:b"))
    with pytest.raises(ValidationError):
        EncounterState("", EncounterStatus.PREPARING, (combatant_a,))
    with pytest.raises(ValidationError):
        EncounterState("enc", EncounterStatus.PREPARING, ())
    with pytest.raises(ValidationError):
        EncounterState("enc", EncounterStatus.PREPARING, (combatant_a, combatant_a))
    with pytest.raises(ValidationError):
        EncounterState(
            "enc",
            EncounterStatus.PREPARING,
            (combatant_a,),
            initiative=(InitiativeEntry("actor:x", 1, 0, 1),),
        )
    with pytest.raises(ValidationError):
        EncounterState("enc", EncounterStatus.ACTIVE, (combatant_a, combatant_b))
    initiative = (
        InitiativeEntry("actor:a", 10, 1, 9),
        InitiativeEntry("actor:b", 9, 1, 8),
    )
    with pytest.raises(ValidationError):
        EncounterState(
            "enc",
            EncounterStatus.ACTIVE,
            (combatant_a, combatant_b),
            initiative=initiative,
            round_number=-1,
        )
    with pytest.raises(ValidationError):
        EncounterState(
            "enc",
            EncounterStatus.ACTIVE,
            (combatant_a, combatant_b),
            initiative=initiative,
            turn_index=2,
        )
    with pytest.raises(ValidationError):
        EncounterState(
            "enc",
            EncounterStatus.ACTIVE,
            (combatant_a, combatant_b),
            initiative=initiative,
            event_sequence=-1,
        )
    with pytest.raises(ValidationError):
        EncounterState(
            "enc",
            EncounterStatus.ACTIVE,
            (combatant_a, combatant_b),
            initiative=initiative,
            reaction_windows=(
                ReactionWindow("window", "trigger", "actor:a", ()),
                ReactionWindow("window", "trigger", "actor:a", ()),
            ),
        )
    with pytest.raises(ValidationError):
        EncounterState(
            "enc",
            EncounterStatus.ACTIVE,
            (combatant_a, combatant_b),
            initiative=initiative,
            condition_rules=(CombatConditionRule("c"), CombatConditionRule("c")),
        )
    state = EncounterState(
        "enc",
        EncounterStatus.ACTIVE,
        (combatant_b, combatant_a),
        initiative=initiative,
        condition_rules=(CombatConditionRule("condition:test"),),
    )
    assert tuple(item.actor_id for item in state.combatants) == ("actor:a", "actor:b")
    assert state.current_actor_id == "actor:a"
    assert state.condition_rule("condition:test") is not None
    assert state.condition_rule("condition:missing") is None
    with pytest.raises(ValidationError):
        state.combatant("actor:missing")
    with pytest.raises(ValidationError):
        state.replace_combatant(CombatantState(actor("actor:missing")))


def test_attack_and_damage_input_validation() -> None:
    with pytest.raises(ValidationError):
        DamagePacket(-1, "energy")
    with pytest.raises(ValidationError):
        DamagePacket(1, "")
    with pytest.raises(ValidationError):
        AttackDefinition(
            "",
            Ability.STRENGTH,
            ProficiencyRank.FULL,
            DiceExpression(1, 4),
            "energy",
        )
    with pytest.raises(ValidationError):
        AttackDefinition(
            "attack:test",
            Ability.STRENGTH,
            ProficiencyRank.FULL,
            DiceExpression(1, 4, 1),
            "energy",
        )
    with pytest.raises(ValidationError):
        AttackDefinition(
            "attack:test",
            Ability.STRENGTH,
            ProficiencyRank.FULL,
            DiceExpression(1, 4),
            "",
        )
    with pytest.raises(ValidationError):
        AttackDefinition(
            "attack:test",
            Ability.STRENGTH,
            ProficiencyRank.FULL,
            DiceExpression(1, 4),
            "energy",
            damage_bonus=True,  # type: ignore[arg-type]
        )
    with pytest.raises(ValidationError):
        AttackDefinition(
            "attack:test",
            Ability.STRENGTH,
            ProficiencyRank.FULL,
            DiceExpression(1, 4),
            "energy",
            action_resource=ActionResource.REACTION,
        )


def test_runtime_command_validation_boundaries() -> None:
    runtime = CombatRuntime(DeterministicRNG.from_seed(0))
    base = runtime.create_encounter("encounter:test", (actor("actor:a"), actor("actor:b")))
    with pytest.raises(ValidationError):
        runtime.spend_movement(base, "actor:a", 1)
    started = runtime.start_encounter(base).state
    with pytest.raises(ValidationError):
        runtime.start_encounter(started)
    with pytest.raises(ValidationError):
        runtime.spend_movement(started, "actor:b", 1)
    with pytest.raises(ValidationError):
        runtime.spend_action(started, "actor:a", ActionResource.REACTION)
    with pytest.raises(ValidationError):
        runtime.open_reaction_window(
            started,
            window_id="window",
            trigger="trigger",
            source_actor_id="actor:a",
            eligible_actor_ids=("actor:missing",),
        )
    opened = runtime.open_reaction_window(
        started,
        window_id="window",
        trigger="trigger",
        source_actor_id="actor:a",
        eligible_actor_ids=("actor:b",),
    ).state
    with pytest.raises(ValidationError):
        runtime.open_reaction_window(
            opened,
            window_id="window",
            trigger="trigger",
            source_actor_id="actor:a",
            eligible_actor_ids=("actor:b",),
        )
    with pytest.raises(ValidationError):
        runtime.spend_reaction(opened, window_id="missing", actor_id="actor:b")
    with pytest.raises(ValidationError):
        runtime.spend_reaction(opened, window_id="window", actor_id="actor:a")
    with pytest.raises(ValidationError):
        runtime.close_reaction_window(opened, "missing")


def test_runtime_healing_temp_hp_and_damage_validation() -> None:
    runtime = CombatRuntime(DeterministicRNG.from_seed(0))
    state = active(runtime)
    with pytest.raises(ValidationError):
        runtime.heal(state, target_id="actor:b", amount=-1)
    with pytest.raises(ValidationError):
        runtime.grant_temporary_hp(
            state,
            target_id="actor:b",
            amount=-1,
            choice=TemporaryHitPointChoice.TAKE_NEW,
        )
    dead = replace(state.combatant("actor:b"), life_state=LifeState.DEAD)
    dead_state = state.replace_combatant(dead)
    with pytest.raises(ValidationError):
        runtime.heal(dead_state, target_id="actor:b", amount=1)
    with pytest.raises(ValidationError):
        runtime.apply_damage(dead_state, target_id="actor:b", packet=DamagePacket(1, "energy"))


def test_damage_at_zero_single_failure_and_instant_threshold() -> None:
    runtime = CombatRuntime(DeterministicRNG.from_seed(0))
    state = active(runtime)
    b = state.combatant("actor:b")
    zero_actor = replace(b.actor, hit_points=HitPoints(0, b.actor.hit_points.maximum))
    zero = replace(
        b,
        actor=zero_actor,
        life_state=LifeState.UNCONSCIOUS,
        zero_hp_rule=ZeroHitPointRule.CHARACTER,
    )
    state = state.replace_combatant(zero)
    state = runtime.apply_damage(
        state, target_id="actor:b", packet=DamagePacket(1, "energy")
    )[0].state
    assert state.combatant("actor:b").death_saves.failures == 1
    maximum = state.combatant("actor:b").actor.hit_points.maximum
    state = runtime.apply_damage(
        state, target_id="actor:b", packet=DamagePacket(maximum, "energy")
    )[0].state
    assert state.combatant("actor:b").life_state is LifeState.DEAD


def test_death_save_special_rolls_and_invalid_state() -> None:
    runtime = CombatRuntime(DeterministicRNG.from_seed(1))
    state = active(runtime)
    with pytest.raises(ValidationError):
        runtime._death_save_event(state, "actor:b")
    b = state.combatant("actor:b")
    zero_actor = replace(b.actor, hit_points=HitPoints(0, b.actor.hit_points.maximum))
    state = state.replace_combatant(
        replace(
            b,
            actor=zero_actor,
            life_state=LifeState.UNCONSCIOUS,
            zero_hp_rule=ZeroHitPointRule.CHARACTER,
        )
    )
    event = runtime._death_save_event(state, "actor:b")
    result = apply_combat_event(state, event)
    assert result.combatant("actor:b").life_state is LifeState.CONSCIOUS
    assert result.combatant("actor:b").actor.hit_points.current == 1

    monster_runtime = CombatRuntime(DeterministicRNG.from_seed(0))
    monster_state = active(monster_runtime)
    m = monster_state.combatant("actor:b")
    zero_actor = replace(m.actor, hit_points=HitPoints(0, m.actor.hit_points.maximum))
    monster_state = monster_state.replace_combatant(
        replace(
            m,
            actor=zero_actor,
            life_state=LifeState.UNCONSCIOUS,
            zero_hp_rule=ZeroHitPointRule.MONSTER,
        )
    )
    with pytest.raises(ValidationError):
        monster_runtime._death_save_event(monster_state, "actor:b")


def test_event_serialization_round_trip_with_tuple_payload() -> None:
    event = CombatEvent(
        1,
        "reaction.window.opened",
        actor_id="actor:a",
        payload=(
            ("window_id", "window"),
            ("trigger", "trigger"),
            ("eligible_actor_ids", ("actor:b", "actor:c")),
        ),
    )
    encoded = serialize_event(event)
    assert deserialize_event(encoded) == event
    assert encoded == serialize_event(deserialize_event(encoded))


def test_event_log_serialization_is_canonical_and_round_trips() -> None:
    events = (
        CombatEvent(1, "encounter.started", payload=(("round_number", 1),)),
        CombatEvent(2, "turn.started", actor_id="actor:a"),
    )
    encoded = serialize_log(events)
    assert encoded.splitlines() == [serialize_event(event) for event in events]
    assert deserialize_log(encoded) == events
    assert deserialize_log("  \n") == ()
    assert serialize_log(deserialize_log(encoded)) == encoded


def test_reducer_rejects_wrong_payload_types_and_unknown_event() -> None:
    runtime = CombatRuntime(DeterministicRNG.from_seed(0))
    state = active(runtime)
    sequence = state.next_sequence()
    with pytest.raises(ValidationError):
        apply_combat_event(
            state,
            CombatEvent(sequence, "movement.spent", actor_id="actor:a", payload=(("feet", "x"),)),
        )
    with pytest.raises(ValidationError):
        apply_combat_event(
            state,
            CombatEvent(sequence, "action.spent", actor_id="actor:a", payload=(("resource", 1),)),
        )
    with pytest.raises(ValidationError):
        apply_combat_event(
            state,
            CombatEvent(
                sequence,
                "reaction.window.opened",
                actor_id="actor:a",
                payload=(
                    ("window_id", "window"),
                    ("trigger", "trigger"),
                    ("eligible_actor_ids", "actor:b"),
                ),
            ),
        )
    with pytest.raises(ValidationError):
        apply_combat_event(state, CombatEvent(sequence, "unknown.event"))
