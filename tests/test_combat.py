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
    ActionResource,
    AttackDefinition,
    AttackModifiers,
    CombatConditionRule,
    CombatRuntime,
    DamagePacket,
    DefenseProfile,
    EncounterStatus,
    LifeState,
    TemporaryHitPointChoice,
    adjust_damage,
    replay_combat,
)
from godot_dnd_engine.dice import DiceExpression
from godot_dnd_engine.errors import ValidationError
from godot_dnd_engine.rng import DeterministicRNG
from godot_dnd_engine.rules import Ability, AbilityScore, ProficiencyRank


def actor(
    actor_id: str,
    *,
    kind: ActorKind = ActorKind.HERO,
    dexterity: int = 14,
    hp: int = 12,
    ac: int = 13,
    speed: int = 30,
) -> ActorState:
    abilities = tuple(
        AbilityScore(ability, dexterity if ability is Ability.DEXTERITY else 12)
        for ability in Ability
    )
    return ActorState(
        actor_id=actor_id,
        name=actor_id,
        kind=kind,
        size=SizeCategory.MEDIUM,
        proficiency_bonus=2,
        abilities=abilities,
        hit_points=HitPoints(hp, hp),
        defense=DefenseState(ac),
        movement=(MovementSpeed(MovementMode.WALK, speed),),
    )


def start(runtime: CombatRuntime, *actors: ActorState):
    base = runtime.create_encounter("encounter:test", tuple(actors))
    return base, runtime.start_encounter(base)


def test_start_encounter_rolls_deterministic_initiative_and_starts_turn() -> None:
    runtime = CombatRuntime(DeterministicRNG.from_seed(0))
    base, transition = start(
        runtime, actor("actor:b", dexterity=12), actor("actor:a", dexterity=14)
    )
    assert base.status is EncounterStatus.PREPARING
    assert transition.state.status is EncounterStatus.ACTIVE
    assert tuple(row.actor_id for row in transition.state.initiative) == ("actor:a", "actor:b")
    assert transition.state.current_actor_id == "actor:a"
    current = transition.state.combatant("actor:a")
    assert current.economy.action_available
    assert current.economy.bonus_action_available
    assert current.economy.reaction_available
    assert current.economy.movement_remaining == 30
    assert [event.event_type for event in transition.events] == [
        "initiative.rolled",
        "initiative.rolled",
        "encounter.started",
        "turn.started",
    ]


def test_initiative_ties_use_dex_then_actor_id_for_determinism() -> None:
    runtime = CombatRuntime(DeterministicRNG.from_seed(17))
    base = runtime.create_encounter(
        "encounter:tie",
        (
            actor("actor:z", dexterity=14),
            actor("actor:b", dexterity=12),
            actor("actor:a", dexterity=14),
        ),
    )
    result = runtime.start_encounter(base)
    assert tuple(row.actor_id for row in result.state.initiative) == (
        "actor:a",
        "actor:z",
        "actor:b",
    )


def test_action_bonus_and_movement_are_accounted_without_spatial_legality() -> None:
    runtime = CombatRuntime(DeterministicRNG.from_seed(0))
    _, started = start(runtime, actor("actor:a"), actor("actor:b"))
    state = started.state
    moved = runtime.spend_movement(state, "actor:a", 15)
    assert moved.state.combatant("actor:a").economy.movement_remaining == 15
    action = runtime.spend_action(moved.state, "actor:a", ActionResource.ACTION)
    assert not action.state.combatant("actor:a").economy.action_available
    bonus = runtime.spend_action(action.state, "actor:a", ActionResource.BONUS_ACTION)
    assert not bonus.state.combatant("actor:a").economy.bonus_action_available
    with pytest.raises(ValidationError):
        runtime.spend_movement(bonus.state, "actor:a", 16)
    with pytest.raises(ValidationError):
        runtime.spend_action(bonus.state, "actor:a", ActionResource.ACTION)


def test_condition_rules_can_block_actions_reactions_and_movement() -> None:
    condition = "condition:locked"
    runtime = CombatRuntime(DeterministicRNG.from_seed(0))
    base = runtime.create_encounter(
        "encounter:conditions",
        (actor("actor:a"), actor("actor:b")),
        condition_rules=(
            CombatConditionRule(
                condition,
                blocks_action=True,
                blocks_bonus_action=True,
                blocks_reaction=True,
                blocks_movement=True,
            ),
        ),
    )
    state = runtime.start_encounter(base).state
    state = runtime.apply_condition(state, target_id="actor:a", condition_id=condition).state
    with pytest.raises(ValidationError):
        runtime.spend_action(state, "actor:a", ActionResource.ACTION)
    with pytest.raises(ValidationError):
        runtime.spend_movement(state, "actor:a", 1)
    state = runtime.open_reaction_window(
        state,
        window_id="window:test",
        trigger="test",
        source_actor_id="actor:b",
        eligible_actor_ids=("actor:a",),
    ).state
    with pytest.raises(ValidationError):
        runtime.spend_reaction(state, window_id="window:test", actor_id="actor:a")


def test_reaction_window_spends_reaction_and_next_turn_refreshes_it() -> None:
    runtime = CombatRuntime(DeterministicRNG.from_seed(0))
    _, started = start(runtime, actor("actor:a"), actor("actor:b"))
    state = runtime.open_reaction_window(
        started.state,
        window_id="window:1",
        trigger="trigger:test",
        source_actor_id="actor:a",
        eligible_actor_ids=("actor:b",),
    ).state
    state = runtime.spend_reaction(state, window_id="window:1", actor_id="actor:b").state
    assert not state.combatant("actor:b").economy.reaction_available
    state = runtime.close_reaction_window(state, "window:1").state
    state = runtime.end_turn(state, "actor:a").state
    assert state.current_actor_id == "actor:b"
    assert state.combatant("actor:b").economy.reaction_available


def test_attack_natural_one_misses_and_twenty_hits_and_doubles_damage_dice() -> None:
    attack = AttackDefinition(
        "attack:test",
        Ability.STRENGTH,
        ProficiencyRank.FULL,
        DiceExpression(1, 6),
        "energy",
    )
    miss_runtime = CombatRuntime(DeterministicRNG.from_seed(28))
    _, started = start(miss_runtime, actor("actor:a"), actor("actor:b", ac=1))
    transition, result = miss_runtime.perform_attack(
        started.state,
        attacker_id="actor:a",
        target_id="actor:b",
        attack=attack,
    )
    assert not result.hit
    assert not result.critical
    assert transition.state.combatant("actor:b").actor.hit_points.current == 12

    crit_runtime = CombatRuntime(DeterministicRNG.from_seed(1))
    _, started = start(crit_runtime, actor("actor:a"), actor("actor:b", ac=99))
    transition, result = crit_runtime.perform_attack(
        started.state,
        attacker_id="actor:a",
        target_id="actor:b",
        attack=attack,
    )
    assert result.hit and result.critical
    assert result.damage_raw_rolls == (3, 5)
    assert result.damage_before_defenses == 9
    assert transition.state.combatant("actor:b").actor.hit_points.current == 3


def test_attack_uses_advantage_and_armor_class() -> None:
    attack = AttackDefinition(
        "attack:adv",
        Ability.DEXTERITY,
        ProficiencyRank.FULL,
        DiceExpression(1, 4),
        "energy",
        add_ability_to_damage=False,
    )
    runtime = CombatRuntime(DeterministicRNG.from_seed(16))
    _, started = start(runtime, actor("actor:a"), actor("actor:b", ac=20))
    transition, result = runtime.perform_attack(
        started.state,
        attacker_id="actor:a",
        target_id="actor:b",
        attack=attack,
        modifiers=AttackModifiers(advantage_sources=1),
    )
    assert result.d20.raw_rolls == (17, 5)
    assert result.hit
    assert transition.state.combatant("actor:b").actor.hit_points.current == 11


def test_damage_defenses_order_immunity_resistance_then_vulnerability() -> None:
    profile = DefenseProfile(
        resistances=frozenset({"energy"}),
        vulnerabilities=frozenset({"energy"}),
    )
    adjustment = adjust_damage(DamagePacket(23, "energy"), profile)
    assert adjustment.adjusted_amount == 22
    immune = adjust_damage(
        DamagePacket(23, "energy"),
        replace(profile, immunities=frozenset({"energy"})),
    )
    assert immune.adjusted_amount == 0


def test_temporary_hp_absorbs_damage_before_current_hp_and_does_not_stack() -> None:
    runtime = CombatRuntime(DeterministicRNG.from_seed(0))
    _, started = start(runtime, actor("actor:a"), actor("actor:b"))
    state = runtime.grant_temporary_hp(
        started.state,
        target_id="actor:b",
        amount=5,
        choice=TemporaryHitPointChoice.TAKE_NEW,
    ).state
    state = runtime.grant_temporary_hp(
        state,
        target_id="actor:b",
        amount=3,
        choice=TemporaryHitPointChoice.KEEP_CURRENT,
    ).state
    assert state.combatant("actor:b").actor.hit_points.temporary == 5
    transition, _ = runtime.apply_damage(
        state,
        target_id="actor:b",
        packet=DamagePacket(7, "energy"),
    )
    hp = transition.state.combatant("actor:b").actor.hit_points
    assert hp.temporary == 0
    assert hp.current == 10


def test_monster_style_zero_hp_ends_in_dead_state() -> None:
    runtime = CombatRuntime(DeterministicRNG.from_seed(0))
    _, started = start(runtime, actor("actor:a"), actor("actor:b", kind=ActorKind.CREATURE, hp=5))
    transition, _ = runtime.apply_damage(
        started.state,
        target_id="actor:b",
        packet=DamagePacket(5, "energy"),
    )
    assert transition.state.combatant("actor:b").life_state is LifeState.DEAD


def test_character_style_zero_hp_is_unconscious_and_healing_recovers() -> None:
    runtime = CombatRuntime(DeterministicRNG.from_seed(0))
    _, started = start(runtime, actor("actor:a"), actor("actor:b", hp=5))
    transition, _ = runtime.apply_damage(
        started.state,
        target_id="actor:b",
        packet=DamagePacket(5, "energy"),
    )
    target = transition.state.combatant("actor:b")
    assert target.life_state is LifeState.UNCONSCIOUS
    assert target.has_condition("condition:unconscious")
    healed = runtime.heal(transition.state, target_id="actor:b", amount=2)
    target = healed.state.combatant("actor:b")
    assert target.life_state is LifeState.CONSCIOUS
    assert target.actor.hit_points.current == 2
    assert not target.has_condition("condition:unconscious")


def test_character_massive_damage_can_transition_directly_to_dead() -> None:
    runtime = CombatRuntime(DeterministicRNG.from_seed(0))
    _, started = start(runtime, actor("actor:a"), actor("actor:b", hp=5))
    transition, _ = runtime.apply_damage(
        started.state,
        target_id="actor:b",
        packet=DamagePacket(10, "energy"),
    )
    assert transition.state.combatant("actor:b").life_state is LifeState.DEAD


def test_damage_at_zero_records_failed_death_save_and_critical_records_two() -> None:
    runtime = CombatRuntime(DeterministicRNG.from_seed(0))
    _, started = start(runtime, actor("actor:a"), actor("actor:b", hp=5))
    state = runtime.apply_damage(
        started.state, target_id="actor:b", packet=DamagePacket(5, "energy")
    )[0].state
    state = runtime.apply_damage(
        state, target_id="actor:b", packet=DamagePacket(1, "energy"), critical=True
    )[0].state
    assert state.combatant("actor:b").death_saves.failures == 2


def test_end_turn_auto_resolves_character_death_save() -> None:
    runtime = CombatRuntime(DeterministicRNG.from_seed(0))
    _, started = start(runtime, actor("actor:a"), actor("actor:b", hp=5))
    state = runtime.apply_damage(
        started.state,
        target_id="actor:b",
        packet=DamagePacket(5, "energy"),
    )[0].state
    transition = runtime.end_turn(state, "actor:a")
    assert transition.state.current_actor_id == "actor:b"
    assert transition.state.combatant("actor:b").death_saves.successes == 1
    assert transition.events[-1].event_type == "death_save.resolved"


def test_three_death_save_successes_stabilize() -> None:
    runtime = CombatRuntime(DeterministicRNG.from_seed(20))
    _, started = start(runtime, actor("actor:a"), actor("actor:b", hp=5))
    state = runtime.apply_damage(
        started.state, target_id="actor:b", packet=DamagePacket(5, "energy")
    )[0].state
    state = runtime.end_turn(state, "actor:a").state
    state = runtime.end_turn(state, "actor:b").state
    state = runtime.end_turn(state, "actor:a").state
    state = runtime.end_turn(state, "actor:b").state
    state = runtime.end_turn(state, "actor:a").state
    assert state.combatant("actor:b").life_state is LifeState.STABLE


def test_replay_from_preparing_state_matches_live_transition() -> None:
    runtime = CombatRuntime(DeterministicRNG.from_seed(0))
    base, started = start(runtime, actor("actor:a"), actor("actor:b"))
    moved = runtime.spend_movement(started.state, "actor:a", 5)
    acted = runtime.spend_action(moved.state, "actor:a", ActionResource.ACTION)
    events = (*started.events, *moved.events, *acted.events)
    replayed = replay_combat(base, events)
    assert replayed == acted.state


def test_invalid_replay_sequence_is_rejected() -> None:
    runtime = CombatRuntime(DeterministicRNG.from_seed(0))
    base, started = start(runtime, actor("actor:a"), actor("actor:b"))
    with pytest.raises(ValidationError):
        replay_combat(base, started.events[1:])


def test_encounter_can_end_and_reject_further_active_commands() -> None:
    runtime = CombatRuntime(DeterministicRNG.from_seed(0))
    _, started = start(runtime, actor("actor:a"), actor("actor:b"))
    ended = runtime.end_encounter(started.state)
    assert ended.state.status is EncounterStatus.ENDED
    with pytest.raises(ValidationError):
        runtime.spend_movement(ended.state, "actor:a", 1)
