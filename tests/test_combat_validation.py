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
    SizeCategory,
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
    rng_from_events,
    serialize_event,
    serialize_log,
)
from godot_dnd_engine.dice import DiceExpression
from godot_dnd_engine.errors import ValidationError
from godot_dnd_engine.models import RNGCheckpoint
from godot_dnd_engine.rng import DeterministicRNG
from godot_dnd_engine.rules import Ability, AbilityScore, ProficiencyRank


def actor(
    actor_id: str = "actor:a",
    *,
    hp: int = 10,
    kind: ActorKind = ActorKind.HERO,
) -> ActorState:
    return ActorState(
        actor_id=actor_id,
        name=actor_id,
        kind=kind,
        size=SizeCategory.MEDIUM,
        proficiency_bonus=2,
        abilities=tuple(AbilityScore(ability, 12) for ability in Ability),
        hit_points=HitPoints(hp, hp),
        defense=DefenseState(12),
        movement=(MovementSpeed(MovementMode.WALK, 30),),
    )


def active(runtime: CombatRuntime) -> EncounterState:
    base = runtime.create_encounter(
        "encounter:test",
        (actor("actor:a"), actor("actor:b")),
    )
    return runtime.start_encounter(base).state


def test_model_validation_boundaries() -> None:
    invalid_builders = (
        lambda: DeathSaveTrack(successes=4),
        lambda: DeathSaveTrack(failures=True),
        lambda: DefenseProfile(resistances=frozenset({""})),
        lambda: ActionEconomy(movement_remaining=-1),
        lambda: ActionEconomy(movement_remaining=True),
        lambda: CombatConditionRule(""),
        lambda: InitiativeEntry("", 1, 1, 1),
        lambda: InitiativeEntry("actor:a", "bad", 1, 1),
        lambda: InitiativeEntry("actor:a", 1, 1, 0),
        lambda: ReactionWindow("", "trigger", "actor:a", ()),
        lambda: ReactionWindow("window", "", "actor:a", ()),
        lambda: ReactionWindow("window", "trigger", "", ()),
        lambda: ReactionWindow("window", "trigger", "actor:a", ("actor:b", "actor:b")),
        lambda: ReactionWindow("window", "trigger", "actor:a", ("",)),
        lambda: CombatEvent(0, "event"),
        lambda: CombatEvent(1, ""),
        lambda: CombatEvent(1, "event", payload=(("a", 1), ("a", 2))),
        lambda: CombatEvent(1, "event", schema_version=2),
        lambda: CombatEvent(1, "event", rng_after="bad"),
    )
    for builder in invalid_builders:
        with pytest.raises(ValidationError):
            builder()  # type: ignore[misc]

    with pytest.raises(ValidationError):
        CombatEvent(1, "event").value("missing")
    with pytest.raises(ValidationError):
        CombatantState(replace(actor(), hit_points=HitPoints(0, 10)))
    with pytest.raises(ValidationError):
        CombatantState(actor(), life_state=LifeState.UNCONSCIOUS)
    with pytest.raises(ValidationError):
        CombatantState(actor()).with_actor(actor("actor:other"))


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
    invalid_states = (
        dict(round_number=-1),
        dict(turn_index=2),
        dict(event_sequence=-1),
        dict(
            reaction_windows=(
                ReactionWindow("window", "trigger", "actor:a", ()),
                ReactionWindow("window", "trigger", "actor:a", ()),
            )
        ),
        dict(condition_rules=(CombatConditionRule("c"), CombatConditionRule("c"))),
    )
    for kwargs in invalid_states:
        with pytest.raises(ValidationError):
            EncounterState(
                "enc",
                EncounterStatus.ACTIVE,
                (combatant_a, combatant_b),
                initiative=initiative,
                **kwargs,
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
            damage_bonus=True,
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
    base = runtime.create_encounter(
        "encounter:test",
        (actor("actor:a"), actor("actor:b")),
    )
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
        runtime.apply_damage(
            dead_state,
            target_id="actor:b",
            packet=DamagePacket(1, "energy"),
        )


def test_damage_at_zero_tracks_failures_and_threshold() -> None:
    runtime = CombatRuntime(DeterministicRNG.from_seed(0))
    state = active(runtime)
    target = state.combatant("actor:b")
    zero_actor = replace(
        target.actor,
        hit_points=HitPoints(0, target.actor.hit_points.maximum),
    )
    state = state.replace_combatant(
        replace(
            target,
            actor=zero_actor,
            life_state=LifeState.UNCONSCIOUS,
            zero_hp_rule=ZeroHitPointRule.CHARACTER,
        )
    )
    state = runtime.apply_damage(
        state,
        target_id="actor:b",
        packet=DamagePacket(1, "energy"),
    )[0].state
    assert state.combatant("actor:b").death_saves.failures == 1
    maximum = state.combatant("actor:b").actor.hit_points.maximum
    state = runtime.apply_damage(
        state,
        target_id="actor:b",
        packet=DamagePacket(maximum, "energy"),
    )[0].state
    assert state.combatant("actor:b").life_state is LifeState.DEAD


def test_event_serialization_preserves_rng_checkpoint() -> None:
    checkpoint = RNGCheckpoint(DeterministicRNG.ALGORITHM, 123, 109)
    event = CombatEvent(
        1,
        "reaction.window.opened",
        actor_id="actor:a",
        payload=(
            ("window_id", "window"),
            ("trigger", "trigger"),
            ("eligible_actor_ids", ("actor:b", "actor:c")),
        ),
        rng_after=checkpoint,
    )
    encoded = serialize_event(event)
    assert deserialize_event(encoded) == event
    assert serialize_event(deserialize_event(encoded)) == encoded


def test_combat_log_restores_exact_future_rng_position() -> None:
    runtime = CombatRuntime(DeterministicRNG.from_seed(7))
    base = runtime.create_encounter(
        "encounter:rng",
        (actor("actor:a"), actor("actor:b")),
    )
    started = runtime.start_encounter(base)
    encoded = serialize_log(started.events)
    events = deserialize_log(encoded)
    restored = rng_from_events(events)
    assert restored.roll_die(20) == runtime.rng.roll_die(20)


def test_rng_restore_rejects_missing_or_unknown_checkpoint() -> None:
    with pytest.raises(ValidationError):
        rng_from_events((CombatEvent(1, "encounter.ended"),))
    event = CombatEvent(
        1,
        "initiative.rolled",
        rng_after=RNGCheckpoint("other-rng", 1, 3),
    )
    with pytest.raises(ValidationError):
        rng_from_events((event,))


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


def test_deserializer_rejects_malformed_shapes() -> None:
    with pytest.raises(ValidationError):
        deserialize_event("[]")
    with pytest.raises(ValidationError):
        deserialize_event('{"payload": []}')
    with pytest.raises(ValidationError):
        deserialize_event(
            '{"sequence":1,"event_type":"x","actor_id":null,"target_id":null,'
            '"payload":{"bad":[1]},"schema_version":1,"rng_after":null}'
        )
    with pytest.raises(ValidationError):
        deserialize_event(
            '{"sequence":1,"event_type":"x","actor_id":null,"target_id":null,'
            '"payload":{},"schema_version":1,"rng_after":{}}'
        )


def test_reducer_rejects_wrong_payload_types_and_unknown_event() -> None:
    runtime = CombatRuntime(DeterministicRNG.from_seed(0))
    state = active(runtime)
    sequence = state.next_sequence()
    with pytest.raises(ValidationError):
        apply_combat_event(
            state,
            CombatEvent(
                sequence,
                "movement.spent",
                actor_id="actor:a",
                payload=(("feet", "x"),),
            ),
        )
    with pytest.raises(ValidationError):
        apply_combat_event(
            state,
            CombatEvent(
                sequence,
                "action.spent",
                actor_id="actor:a",
                payload=(("resource", 1),),
            ),
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
