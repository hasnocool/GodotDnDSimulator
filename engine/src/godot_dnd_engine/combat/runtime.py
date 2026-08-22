"""Deterministic tactical-combat command/resolution facade."""

from __future__ import annotations

from dataclasses import dataclass, replace

from ..actors import ActorState
from ..dice import DiceExpression, roll_expression
from ..errors import ValidationError
from ..models import RNGCheckpoint
from ..rng import DeterministicRNG
from ..rules.capabilities import RulesetCapabilities
from ..rules.primitives import Ability, D20TestKind
from ..rules.runtime import ResolutionContext, RulesRuntime
from .attacks import AttackDefinition, AttackModifiers, AttackResult
from .damage import DamageAdjustment, DamagePacket, adjust_damage
from .model import (
    ActionResource,
    CombatConditionRule,
    CombatEvent,
    CombatantState,
    DefenseProfile,
    EncounterState,
    EncounterStatus,
    EventValue,
    LifeState,
    TemporaryHitPointChoice,
    ZeroHitPointRule,
)
from .reducer import apply_combat_event


@dataclass(frozen=True, slots=True)
class CombatTransition:
    state: EncounterState
    events: tuple[CombatEvent, ...]


class CombatRuntime:
    """Resolve tactical commands into ordered events and immutable combat state."""

    def __init__(
        self,
        rng: DeterministicRNG,
        capabilities: RulesetCapabilities | None = None,
    ) -> None:
        self.rng = rng
        self.rules = RulesRuntime(rng, capabilities or RulesetCapabilities.srd_5_2_1_core())

    def create_encounter(
        self,
        encounter_id: str,
        actors: tuple[ActorState, ...],
        *,
        defenses: dict[str, DefenseProfile] | None = None,
        zero_hp_rules: dict[str, ZeroHitPointRule] | None = None,
        condition_rules: tuple[CombatConditionRule, ...] = (),
    ) -> EncounterState:
        defense_map = defenses or {}
        zero_hp_map = zero_hp_rules or {}
        combatants = tuple(
            CombatantState(
                actor=actor,
                defenses=defense_map.get(actor.actor_id, DefenseProfile()),
                zero_hp_rule=zero_hp_map.get(actor.actor_id),
            )
            for actor in actors
        )
        return EncounterState(
            encounter_id=encounter_id,
            status=EncounterStatus.PREPARING,
            combatants=combatants,
            condition_rules=condition_rules,
        )

    def _checkpoint(self) -> RNGCheckpoint:
        state, increment = self.rng.snapshot()
        return RNGCheckpoint(
            algorithm=self.rng.ALGORITHM,
            state=state,
            increment=increment,
        )

    def _event(
        self,
        state: EncounterState,
        event_type: str,
        *,
        actor_id: str | None = None,
        target_id: str | None = None,
        payload: tuple[tuple[str, EventValue], ...] = (),
        rng_after: RNGCheckpoint | None = None,
    ) -> CombatEvent:
        return CombatEvent(
            sequence=state.next_sequence(),
            event_type=event_type,
            actor_id=actor_id,
            target_id=target_id,
            payload=payload,
            rng_after=rng_after,
        )

    def _apply(self, state: EncounterState, event: CombatEvent) -> EncounterState:
        return apply_combat_event(state, event)

    def start_encounter(self, state: EncounterState) -> CombatTransition:
        if state.status is not EncounterStatus.PREPARING:
            raise ValidationError("only preparing encounters can start")
        current = state
        events: list[CombatEvent] = []
        initiative_rows: list[tuple[str, int, int, int]] = []
        for combatant in state.combatants:
            actor = combatant.actor
            dexterity = actor.ability_score(Ability.DEXTERITY)
            outcome = self.rules.resolve_d20(
                ResolutionContext(
                    context_id=f"initiative:{state.encounter_id}:{actor.actor_id}",
                    test_kind=D20TestKind.ABILITY_CHECK,
                    actor_id=actor.actor_id,
                    ability=Ability.DEXTERITY,
                    reason="Initiative",
                ),
                ability_score=dexterity,
                proficiency_bonus=actor.proficiency_bonus,
            )
            raw_roll = outcome.selected_roll
            initiative_rows.append(
                (actor.actor_id, outcome.total, dexterity.modifier, raw_roll)
            )
            event = self._event(
                current,
                "initiative.rolled",
                actor_id=actor.actor_id,
                payload=(
                    ("total", outcome.total),
                    ("dexterity_modifier", dexterity.modifier),
                    ("raw_roll", raw_roll),
                ),
                rng_after=self._checkpoint(),
            )
            current = self._apply(current, event)
            events.append(event)

        order = tuple(
            actor_id
            for actor_id, _, _, _ in sorted(
                initiative_rows,
                key=lambda item: (-item[1], -item[2], item[0]),
            )
        )
        started = self._event(current, "encounter.started", payload=(("order", order),))
        current = self._apply(current, started)
        events.append(started)
        turn = self._start_turn_event(current, turn_index=0, round_number=1)
        current = self._apply(current, turn)
        events.append(turn)
        return CombatTransition(current, tuple(events))

    def _start_turn_event(
        self,
        state: EncounterState,
        *,
        turn_index: int,
        round_number: int,
    ) -> CombatEvent:
        actor_id = state.initiative[turn_index].actor_id
        return self._event(
            state,
            "turn.started",
            actor_id=actor_id,
            payload=(("turn_index", turn_index), ("round_number", round_number)),
        )

    def _assert_active(self, state: EncounterState) -> None:
        if state.status is not EncounterStatus.ACTIVE:
            raise ValidationError("combat command requires an active encounter")

    def _assert_current_actor(self, state: EncounterState, actor_id: str) -> CombatantState:
        self._assert_active(state)
        if state.current_actor_id != actor_id:
            raise ValidationError("combat command actor is not the current turn actor")
        combatant = state.combatant(actor_id)
        if combatant.life_state is not LifeState.CONSCIOUS:
            raise ValidationError("combatant is not conscious")
        return combatant

    def _condition_blocks(
        self,
        state: EncounterState,
        combatant: CombatantState,
        resource: ActionResource | None,
        *,
        movement: bool = False,
    ) -> bool:
        for condition in combatant.actor.conditions:
            rule = state.condition_rule(condition.condition_id)
            if rule is None:
                continue
            if movement and rule.blocks_movement:
                return True
            if resource is ActionResource.ACTION and rule.blocks_action:
                return True
            if resource is ActionResource.BONUS_ACTION and rule.blocks_bonus_action:
                return True
            if resource is ActionResource.REACTION and rule.blocks_reaction:
                return True
        return False

    def spend_action(
        self,
        state: EncounterState,
        actor_id: str,
        resource: ActionResource,
    ) -> CombatTransition:
        combatant = self._assert_current_actor(state, actor_id)
        if resource is ActionResource.REACTION:
            raise ValidationError("reactions must be spent through an open reaction window")
        if self._condition_blocks(state, combatant, resource):
            raise ValidationError("combat conditions block that action resource")
        event = self._event(
            state,
            "action.spent",
            actor_id=actor_id,
            payload=(("resource", resource.value),),
        )
        return CombatTransition(self._apply(state, event), (event,))

    def spend_movement(self, state: EncounterState, actor_id: str, feet: int) -> CombatTransition:
        combatant = self._assert_current_actor(state, actor_id)
        if self._condition_blocks(state, combatant, None, movement=True):
            raise ValidationError("combat conditions block movement")
        event = self._event(
            state,
            "movement.spent",
            actor_id=actor_id,
            payload=(("feet", feet),),
        )
        return CombatTransition(self._apply(state, event), (event,))

    def end_turn(self, state: EncounterState, actor_id: str) -> CombatTransition:
        self._assert_active(state)
        if state.current_actor_id != actor_id:
            raise ValidationError("combat command actor is not the current turn actor")
        next_index, next_round = self._next_living_turn(state)
        turn = self._start_turn_event(
            state,
            turn_index=next_index,
            round_number=next_round,
        )
        next_state = self._apply(state, turn)
        events: list[CombatEvent] = [turn]
        next_actor_id = next_state.current_actor_id
        assert next_actor_id is not None
        next_actor = next_state.combatant(next_actor_id)
        if (
            next_actor.life_state is LifeState.UNCONSCIOUS
            and next_actor.actor.hit_points.current == 0
            and next_actor.zero_hp_rule is ZeroHitPointRule.CHARACTER
        ):
            death_save = self._death_save_event(next_state, next_actor.actor_id)
            next_state = self._apply(next_state, death_save)
            events.append(death_save)
        return CombatTransition(next_state, tuple(events))

    def _next_living_turn(self, state: EncounterState) -> tuple[int, int]:
        count = len(state.initiative)
        for offset in range(1, count + 1):
            candidate = (state.turn_index + offset) % count
            actor_id = state.initiative[candidate].actor_id
            if state.combatant(actor_id).life_state is not LifeState.DEAD:
                round_number = state.round_number + (1 if candidate <= state.turn_index else 0)
                return candidate, round_number
        raise ValidationError("encounter has no living combatants")

    def open_reaction_window(
        self,
        state: EncounterState,
        *,
        window_id: str,
        trigger: str,
        source_actor_id: str,
        eligible_actor_ids: tuple[str, ...],
    ) -> CombatTransition:
        self._assert_active(state)
        if any(window.window_id == window_id for window in state.reaction_windows):
            raise ValidationError("reaction window ID already exists")
        state.combatant(source_actor_id)
        for actor_id in eligible_actor_ids:
            state.combatant(actor_id)
        event = self._event(
            state,
            "reaction.window.opened",
            actor_id=source_actor_id,
            payload=(
                ("window_id", window_id),
                ("trigger", trigger),
                ("eligible_actor_ids", tuple(sorted(eligible_actor_ids))),
            ),
        )
        return CombatTransition(self._apply(state, event), (event,))

    def spend_reaction(
        self,
        state: EncounterState,
        *,
        window_id: str,
        actor_id: str,
    ) -> CombatTransition:
        self._assert_active(state)
        window = next(
            (item for item in state.reaction_windows if item.window_id == window_id),
            None,
        )
        if window is None:
            raise ValidationError("reaction window is not open")
        if actor_id not in window.eligible_actor_ids:
            raise ValidationError("actor is not eligible for this reaction window")
        combatant = state.combatant(actor_id)
        if combatant.life_state is not LifeState.CONSCIOUS:
            raise ValidationError("combatant is not conscious")
        if self._condition_blocks(state, combatant, ActionResource.REACTION):
            raise ValidationError("combat conditions block reactions")
        event = self._event(
            state,
            "action.spent",
            actor_id=actor_id,
            payload=(("resource", ActionResource.REACTION.value),),
        )
        return CombatTransition(self._apply(state, event), (event,))

    def close_reaction_window(self, state: EncounterState, window_id: str) -> CombatTransition:
        if not any(item.window_id == window_id for item in state.reaction_windows):
            raise ValidationError("reaction window is not open")
        event = self._event(
            state,
            "reaction.window.closed",
            payload=(("window_id", window_id),),
        )
        return CombatTransition(self._apply(state, event), (event,))

    def perform_attack(
        self,
        state: EncounterState,
        *,
        attacker_id: str,
        target_id: str,
        attack: AttackDefinition,
        modifiers: AttackModifiers | None = None,
    ) -> tuple[CombatTransition, AttackResult]:
        attacker = self._assert_current_actor(state, attacker_id)
        attack_modifiers = modifiers or AttackModifiers()
        target = state.combatant(target_id)
        if target.life_state is LifeState.DEAD:
            raise ValidationError("target is already dead")
        if self._condition_blocks(state, attacker, attack.action_resource):
            raise ValidationError("combat conditions block that attack action")

        spent = self.spend_action(state, attacker_id, attack.action_resource)
        current = spent.state
        events = list(spent.events)
        d20 = self.rules.resolve_d20(
            ResolutionContext(
                context_id=(
                    f"attack:{state.encounter_id}:{attack.attack_id}:{state.next_sequence()}"
                ),
                test_kind=D20TestKind.ATTACK_ROLL,
                actor_id=attacker_id,
                target_id=target_id,
                ability=attack.ability,
                proficiency_rank=attack.proficiency_rank,
                reason=attack.attack_id,
            ),
            ability_score=attacker.actor.ability_score(attack.ability),
            proficiency_bonus=attacker.actor.proficiency_bonus,
            modifiers=attack_modifiers.attack_roll,
            advantage_sources=attack_modifiers.advantage_sources,
            disadvantage_sources=attack_modifiers.disadvantage_sources,
        )
        natural_roll = d20.selected_roll
        critical = natural_roll == 20
        hit = critical or (
            natural_roll != 1 and d20.total >= target.actor.defense.armor_class
        )
        attack_event = self._event(
            current,
            "attack.resolved",
            actor_id=attacker_id,
            target_id=target_id,
            payload=(
                ("attack_id", attack.attack_id),
                ("natural_roll", natural_roll),
                ("total", d20.total),
                ("target_armor_class", target.actor.defense.armor_class),
                ("hit", hit),
                ("critical", critical),
            ),
            rng_after=self._checkpoint(),
        )
        current = self._apply(current, attack_event)
        events.append(attack_event)

        damage_raw: tuple[int, ...] = ()
        damage_before = 0
        adjustment: DamageAdjustment | None = None
        if hit:
            base_damage = DiceExpression(
                count=attack.damage_dice.count,
                sides=attack.damage_dice.sides,
                modifier=0,
            )
            damage_roll = roll_expression(
                base_damage,
                self.rng,
                reason=f"{attack.attack_id}:damage",
                actor_id=attacker_id,
                target_id=target_id,
            )
            damage_raw = damage_roll.raw_rolls
            if critical:
                critical_roll = roll_expression(
                    base_damage,
                    self.rng,
                    reason=f"{attack.attack_id}:critical-damage",
                    actor_id=attacker_id,
                    target_id=target_id,
                )
                damage_raw = (*damage_raw, *critical_roll.raw_rolls)
            ability_bonus = (
                attacker.actor.ability_score(attack.ability).modifier
                if attack.add_ability_to_damage
                else 0
            )
            damage_before = max(0, sum(damage_raw) + ability_bonus + attack.damage_bonus)
            damage_transition, adjustment = self.apply_damage(
                current,
                target_id=target_id,
                packet=DamagePacket(damage_before, attack.damage_type),
                source_actor_id=attacker_id,
                critical=critical,
                rng_after=self._checkpoint(),
            )
            current = damage_transition.state
            events.extend(damage_transition.events)

        result = AttackResult(
            attack_id=attack.attack_id,
            attacker_id=attacker_id,
            target_id=target_id,
            d20=d20,
            target_armor_class=target.actor.defense.armor_class,
            hit=hit,
            critical=critical,
            damage_raw_rolls=damage_raw,
            damage_before_defenses=damage_before,
            damage_adjustment=adjustment,
        )
        return CombatTransition(current, tuple(events)), result

    def apply_damage(
        self,
        state: EncounterState,
        *,
        target_id: str,
        packet: DamagePacket,
        source_actor_id: str | None = None,
        critical: bool = False,
        rng_after: RNGCheckpoint | None = None,
    ) -> tuple[CombatTransition, DamageAdjustment]:
        self._assert_active(state)
        target = state.combatant(target_id)
        if target.life_state is LifeState.DEAD:
            raise ValidationError("target is already dead")
        adjustment = adjust_damage(packet, target.defenses)
        hp = target.actor.hit_points
        temp_absorbed = min(hp.temporary, adjustment.adjusted_amount)
        remaining = adjustment.adjusted_amount - temp_absorbed
        hp_after = max(0, hp.current - remaining)
        leftover_after_zero = max(0, remaining - hp.current)
        life_state = target.life_state
        death_saves = target.death_saves

        if hp.current == 0 and adjustment.adjusted_amount > 0:
            if adjustment.adjusted_amount >= hp.maximum:
                life_state = LifeState.DEAD
            elif target.zero_hp_rule is ZeroHitPointRule.CHARACTER:
                failures = min(3, death_saves.failures + (2 if critical else 1))
                death_saves = replace(death_saves, failures=failures)
                life_state = (
                    LifeState.DEAD if failures >= 3 else LifeState.UNCONSCIOUS
                )
        elif hp.current > 0 and hp_after == 0:
            if target.zero_hp_rule is ZeroHitPointRule.MONSTER:
                life_state = LifeState.DEAD
            elif leftover_after_zero >= hp.maximum:
                life_state = LifeState.DEAD
            else:
                life_state = LifeState.UNCONSCIOUS
                death_saves = replace(death_saves, successes=0, failures=0)

        event = self._event(
            state,
            "damage.applied",
            actor_id=source_actor_id,
            target_id=target_id,
            payload=(
                ("damage_type", packet.damage_type),
                ("raw_amount", packet.amount),
                ("adjusted_amount", adjustment.adjusted_amount),
                ("temporary_after", hp.temporary - temp_absorbed),
                ("hp_after", hp_after),
                ("life_state", life_state.value),
                ("death_successes", death_saves.successes),
                ("death_failures", death_saves.failures),
                ("critical", critical),
            ),
            rng_after=rng_after,
        )
        return CombatTransition(self._apply(state, event), (event,)), adjustment

    def heal(
        self,
        state: EncounterState,
        *,
        target_id: str,
        amount: int,
        source_actor_id: str | None = None,
    ) -> CombatTransition:
        self._assert_active(state)
        if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
            raise ValidationError("healing amount must be an integer >= 0")
        target = state.combatant(target_id)
        if target.life_state is LifeState.DEAD:
            raise ValidationError("ordinary healing cannot restore a dead combatant")
        hp = target.actor.hit_points
        hp_after = min(hp.maximum, hp.current + amount)
        life_state = LifeState.CONSCIOUS if hp_after > 0 else target.life_state
        death_saves = (
            target.death_saves
            if hp_after == 0
            else replace(target.death_saves, successes=0, failures=0)
        )
        event = self._event(
            state,
            "healing.applied",
            actor_id=source_actor_id,
            target_id=target_id,
            payload=(
                ("amount", amount),
                ("temporary_after", hp.temporary),
                ("hp_after", hp_after),
                ("life_state", life_state.value),
                ("death_successes", death_saves.successes),
                ("death_failures", death_saves.failures),
            ),
        )
        return CombatTransition(self._apply(state, event), (event,))

    def grant_temporary_hp(
        self,
        state: EncounterState,
        *,
        target_id: str,
        amount: int,
        choice: TemporaryHitPointChoice,
    ) -> CombatTransition:
        self._assert_active(state)
        if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
            raise ValidationError("temporary hit points must be an integer >= 0")
        target = state.combatant(target_id)
        current = target.actor.hit_points.temporary
        temporary_after = (
            amount
            if current == 0 or choice is TemporaryHitPointChoice.TAKE_NEW
            else current
        )
        event = self._event(
            state,
            "temporary_hp.changed",
            target_id=target_id,
            payload=(("temporary_after", temporary_after),),
        )
        return CombatTransition(self._apply(state, event), (event,))

    def apply_condition(
        self,
        state: EncounterState,
        *,
        target_id: str,
        condition_id: str,
        source_actor_id: str | None = None,
    ) -> CombatTransition:
        self._assert_active(state)
        event = self._event(
            state,
            "condition.applied",
            actor_id=source_actor_id,
            target_id=target_id,
            payload=(("condition_id", condition_id), ("source_id", source_actor_id)),
        )
        return CombatTransition(self._apply(state, event), (event,))

    def remove_condition(
        self,
        state: EncounterState,
        *,
        target_id: str,
        condition_id: str,
    ) -> CombatTransition:
        self._assert_active(state)
        event = self._event(
            state,
            "condition.removed",
            target_id=target_id,
            payload=(("condition_id", condition_id),),
        )
        return CombatTransition(self._apply(state, event), (event,))

    def _death_save_event(self, state: EncounterState, actor_id: str) -> CombatEvent:
        target = state.combatant(actor_id)
        hp = target.actor.hit_points
        if target.zero_hp_rule is not ZeroHitPointRule.CHARACTER:
            raise ValidationError("only character-style combatants make death saves")
        if target.life_state is not LifeState.UNCONSCIOUS or hp.current != 0:
            raise ValidationError("death save requires an unconscious combatant at 0 hit points")
        roll = self.rng.roll_die(20)
        successes = target.death_saves.successes
        failures = target.death_saves.failures
        life_state = target.life_state
        hp_after = 0
        if roll == 20:
            hp_after = 1
            successes = 0
            failures = 0
            life_state = LifeState.CONSCIOUS
        elif roll == 1:
            failures = min(3, failures + 2)
        elif roll >= 10:
            successes = min(3, successes + 1)
        else:
            failures = min(3, failures + 1)
        if failures >= 3:
            life_state = LifeState.DEAD
        elif successes >= 3:
            life_state = LifeState.STABLE
            successes = 0
            failures = 0
        return self._event(
            state,
            "death_save.resolved",
            actor_id=actor_id,
            target_id=actor_id,
            payload=(
                ("roll", roll),
                ("hp_after", hp_after),
                ("temporary_after", hp.temporary),
                ("life_state", life_state.value),
                ("death_successes", successes),
                ("death_failures", failures),
            ),
            rng_after=self._checkpoint(),
        )

    def end_encounter(self, state: EncounterState) -> CombatTransition:
        self._assert_active(state)
        event = self._event(state, "encounter.ended")
        return CombatTransition(self._apply(state, event), (event,))
