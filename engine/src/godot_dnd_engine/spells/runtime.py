# engine/src/godot_dnd_engine/spells/runtime.py
"""Deterministic generic spell resolver composed from existing engine authorities."""

from __future__ import annotations

from dataclasses import dataclass, replace

from ..combat import ActionResource, CombatRuntime, DamagePacket, EncounterState, LifeState
from ..dice import DiceExpression, roll_expression
from ..errors import ValidationError
from ..models import RNGCheckpoint
from ..rng import DeterministicRNG
from ..rules.capabilities import RulesetCapabilities
from ..rules.modifiers import RuleModifier
from ..rules.primitives import Ability, D20TestKind, DifficultyClass
from ..rules.runtime import ResolutionContext, RulesRuntime
from ..rules.state import RuleWorldState
from ..spatial import GridCell, SpatialQueryService, SpatialState
from .events import SpellEvent, SpellEventValue
from .model import (
    ConcentrationState,
    SaveEffect,
    SpellDefinition,
    SpellEffectKind,
    SpellEffectSpec,
    SpellResolution,
    SpellScaling,
    SpellTargetKind,
    SpellcastingState,
)
from .state import ActiveSpellEffect, SpellRuntimeState


@dataclass(frozen=True, slots=True)
class SpellTargetOutcome:
    target_id: str
    roll: int | None = None
    attack_total: int | None = None
    save_total: int | None = None
    success: bool | None = None
    amounts: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class SpellTransition:
    spell_state: SpellRuntimeState
    encounter: EncounterState
    events: tuple[SpellEvent, ...]
    outcomes: tuple[SpellTargetOutcome, ...]


@dataclass(frozen=True, slots=True)
class ConcentrationCheck:
    spell_state: SpellRuntimeState
    encounter: EncounterState
    maintained: bool
    total: int
    event: SpellEvent | None = None


class SpellRuntime:
    """Resolve data-defined spells without spell-name conditionals."""

    def __init__(
        self,
        rng: DeterministicRNG,
        definitions: tuple[SpellDefinition, ...],
        capabilities: RulesetCapabilities | None = None,
    ) -> None:
        ids = [item.spell_id for item in definitions]
        if len(ids) != len(set(ids)):
            raise ValidationError("spell definitions must have unique IDs")
        self.rng = rng
        self.rules = RulesRuntime(
            rng,
            capabilities or RulesetCapabilities.srd_5_2_1_core(),
        )
        self.combat = CombatRuntime(rng, self.rules.capabilities)
        self.definitions: dict[str, SpellDefinition] = {
            item.spell_id: item for item in definitions
        }

    def definition(self, spell_id: str) -> SpellDefinition:
        definition = self.definitions.get(spell_id)
        if definition is None:
            raise ValidationError(f"unknown spell definition: {spell_id}")
        return definition

    def available_spells(
        self,
        state: SpellRuntimeState,
        actor_id: str,
    ) -> tuple[dict[str, object], ...]:
        caster = state.caster(actor_id)
        rows: list[dict[str, object]] = []
        for spell_id in caster.known_spell_ids:
            definition = self.definitions.get(spell_id)
            if definition is None:
                continue
            known_and_prepared = caster.can_cast(
                spell_id,
                requires_preparation=definition.requires_preparation,
            )
            if definition.level == 0:
                slot_levels = [0]
            else:
                slot_levels = [
                    pool.level
                    for pool in caster.slots
                    if pool.level >= definition.level and pool.current > 0
                ]
            rows.append(
                {
                    "spell_id": definition.spell_id,
                    "name": definition.name,
                    "level": definition.level,
                    "castable": known_and_prepared and bool(slot_levels),
                    "prepared": definition.spell_id in caster.prepared_spell_ids,
                    "slot_levels": slot_levels,
                    "resolution": definition.resolution.value,
                    "target_kind": definition.target_kind.value,
                    "range_feet": definition.range_feet,
                    "max_targets": definition.max_targets,
                    "concentration": definition.concentration,
                    "duration_rounds": definition.duration_rounds,
                    "area_shape": definition.area_shape,
                    "area_size_feet": definition.area_size_feet,
                    "tags": sorted(definition.tags),
                }
            )
        return tuple(rows)

    def preview_cast(
        self,
        state: SpellRuntimeState,
        encounter: EncounterState,
        spatial: SpatialState,
        *,
        caster_id: str,
        spell_id: str,
        slot_level: int | None = None,
        target_ids: tuple[str, ...] = (),
        point: GridCell | None = None,
        direction: tuple[float, float] = (1.0, 0.0),
    ) -> dict[str, object]:
        definition = self.definition(spell_id)
        caster_state = state.caster(caster_id)
        cast_level = definition.cast_level(slot_level)
        reason = self._castability_reason(caster_state, definition, cast_level)
        if reason:
            return {"legal": False, "reason": reason, "spell_id": spell_id}
        if encounter.current_actor_id != caster_id:
            return {
                "legal": False,
                "reason": "Caster is not the current turn actor",
                "spell_id": spell_id,
            }
        combatant = encounter.combatant(caster_id)
        if combatant.life_state is not LifeState.CONSCIOUS:
            return {"legal": False, "reason": "Caster cannot act", "spell_id": spell_id}
        if not combatant.economy.action_available:
            return {
                "legal": False,
                "reason": "Action is not available",
                "spell_id": spell_id,
            }
        try:
            resolved_targets = self._resolve_targets(
                encounter,
                spatial,
                definition,
                caster_id,
                cast_level,
                target_ids,
                point,
                direction,
            )
        except ValidationError as exc:
            return {"legal": False, "reason": str(exc), "spell_id": spell_id}
        return {
            "legal": True,
            "reason": "",
            "spell_id": spell_id,
            "slot_level": cast_level,
            "target_ids": list(resolved_targets),
            "point": None if point is None else {"x": point.x, "y": point.y},
            "area": self._area_preview(spatial, definition, caster_id, point, direction),
            "concentration_will_replace": (
                definition.concentration and caster_state.concentration is not None
            ),
        }

    def cast(
        self,
        state: SpellRuntimeState,
        encounter: EncounterState,
        spatial: SpatialState,
        *,
        caster_id: str,
        spell_id: str,
        slot_level: int | None = None,
        target_ids: tuple[str, ...] = (),
        point: GridCell | None = None,
        direction: tuple[float, float] = (1.0, 0.0),
    ) -> SpellTransition:
        preview = self.preview_cast(
            state,
            encounter,
            spatial,
            caster_id=caster_id,
            spell_id=spell_id,
            slot_level=slot_level,
            target_ids=target_ids,
            point=point,
            direction=direction,
        )
        if not bool(preview.get("legal", False)):
            raise ValidationError(str(preview.get("reason", "spell cast is not legal")))

        definition = self.definition(spell_id)
        cast_level = definition.cast_level(slot_level)
        target_values = preview.get("target_ids", [])
        if not isinstance(target_values, list):
            raise ValidationError("spell preview target_ids are malformed")
        targets = tuple(str(item) for item in target_values)
        current_state, current_encounter, events = self._prepare_cast(
            state,
            encounter,
            caster_id,
            definition,
            cast_level,
        )
        outcomes: list[SpellTargetOutcome] = []
        for target_id in targets:
            current_encounter, outcome = self._resolve_target(
                current_encounter,
                caster_id,
                current_state.caster(caster_id),
                definition,
                cast_level,
                target_id,
            )
            outcomes.append(outcome)
            events.append(
                self._target_event(
                    state.sequence + len(events) + 1,
                    caster_id,
                    definition.spell_id,
                    outcome,
                )
            )

        duration_effects = self._duration_effects(definition)
        duration_targets = self._duration_target_ids(definition, tuple(outcomes))
        if (
            definition.duration_rounds is not None
            and duration_effects
            and duration_targets
        ):
            active = ActiveSpellEffect(
                effect_id=(
                    f"spell-effect:{state.sequence + len(events) + 1}:"
                    f"{definition.spell_id}"
                ),
                spell_id=definition.spell_id,
                caster_id=caster_id,
                target_ids=duration_targets,
                effects=duration_effects,
                remaining_rounds=definition.duration_rounds,
                cast_level=cast_level,
                concentration=definition.concentration,
            )
            current_state = replace(
                current_state,
                active_effects=(*current_state.active_effects, active),
            )

        cast_event = self._event(
            state.sequence + len(events) + 1,
            "spell.cast",
            caster_id,
            definition.spell_id,
            targets,
            (
                ("slot_level", cast_level),
                ("concentration", definition.concentration),
            ),
            rng_after=self._checkpoint(),
        )
        events.append(cast_event)
        current_state = replace(current_state, sequence=cast_event.sequence)
        return SpellTransition(
            spell_state=current_state,
            encounter=current_encounter,
            events=tuple(events),
            outcomes=tuple(outcomes),
        )

    def advance_round(
        self,
        state: SpellRuntimeState,
        encounter: EncounterState,
    ) -> SpellTransition:
        current = encounter
        next_effects: list[ActiveSpellEffect] = []
        events: list[SpellEvent] = []
        expired_concentration: set[tuple[str, str]] = set()
        for active in state.active_effects:
            definition = self.definition(active.spell_id)
            total_amount = 0
            applied_ongoing = False
            for target_id in active.target_ids:
                if not self._is_combatant(current, target_id):
                    continue
                if current.combatant(target_id).life_state is LifeState.DEAD:
                    continue
                for effect in active.effects:
                    if not effect.ongoing:
                        continue
                    applied_ongoing = True
                    current, amount = self._apply_effect(
                        current,
                        active.caster_id,
                        target_id,
                        effect,
                        cast_level=active.cast_level,
                        base_level=definition.level,
                        save_succeeded=False,
                        scaling=definition.scaling,
                    )
                    total_amount += amount
            if applied_ongoing:
                events.append(
                    self._event(
                        state.sequence + len(events) + 1,
                        "spell.ongoing.resolved",
                        active.caster_id,
                        active.spell_id,
                        active.target_ids,
                        (("total_amount", total_amount),),
                        rng_after=self._checkpoint(),
                    )
                )
            ticked = active.tick()
            if ticked is None:
                current = self._remove_duration_conditions(current, active)
                if active.concentration:
                    expired_concentration.add((active.caster_id, active.spell_id))
                events.append(
                    self._event(
                        state.sequence + len(events) + 1,
                        "spell.duration.expired",
                        active.caster_id,
                        active.spell_id,
                        active.target_ids,
                    )
                )
            else:
                next_effects.append(ticked)
        next_state = replace(
            state,
            active_effects=tuple(next_effects),
            sequence=state.sequence + len(events),
        )
        next_state = self._sync_concentration_durations(
            next_state,
            tuple(next_effects),
            expired_concentration,
        )
        return SpellTransition(next_state, current, tuple(events), ())

    def check_concentration(
        self,
        state: SpellRuntimeState,
        encounter: EncounterState,
        *,
        caster_id: str,
        dc: int,
    ) -> ConcentrationCheck:
        caster_state = state.caster(caster_id)
        if caster_state.concentration is None:
            return ConcentrationCheck(state, encounter, True, 0, None)
        actor = encounter.combatant(caster_id).actor
        outcome = self.rules.resolve_save(
            ResolutionContext(
                context_id=f"concentration:{state.sequence + 1}:{caster_id}",
                test_kind=D20TestKind.SAVING_THROW,
                actor_id=caster_id,
                ability=Ability.CONSTITUTION,
                proficiency_rank=actor.save_rank(Ability.CONSTITUTION),
                difficulty_class=DifficultyClass(dc),
                reason="Concentration",
            ),
            ability_score=actor.ability_score(Ability.CONSTITUTION),
            proficiency_bonus=actor.proficiency_bonus,
        )
        maintained = bool(outcome.success)
        next_state = state
        next_encounter = encounter
        spell_id = caster_state.concentration.spell_id
        if not maintained:
            next_state, next_encounter = self._break_concentration(
                state,
                encounter,
                caster_id,
            )
        event = self._event(
            state.sequence + 1,
            "spell.concentration.checked",
            caster_id,
            spell_id,
            (),
            (
                ("dc", dc),
                ("roll", outcome.selected_roll),
                ("total", outcome.total),
                ("maintained", maintained),
            ),
            rng_after=self._checkpoint(),
        )
        next_state = replace(next_state, sequence=event.sequence)
        return ConcentrationCheck(
            next_state,
            next_encounter,
            maintained,
            outcome.total,
            event,
        )

    def end_concentration(
        self,
        state: SpellRuntimeState,
        encounter: EncounterState,
        caster_id: str,
    ) -> SpellTransition:
        caster = state.caster(caster_id)
        if caster.concentration is None:
            return SpellTransition(state, encounter, (), ())
        spell_id = caster.concentration.spell_id
        next_state, next_encounter = self._break_concentration(
            state,
            encounter,
            caster_id,
        )
        event = self._event(
            state.sequence + 1,
            "spell.concentration.ended",
            caster_id,
            spell_id,
        )
        return SpellTransition(
            replace(next_state, sequence=event.sequence),
            next_encounter,
            (event,),
            (),
        )

    def _prepare_cast(
        self,
        state: SpellRuntimeState,
        encounter: EncounterState,
        caster_id: str,
        definition: SpellDefinition,
        cast_level: int,
    ) -> tuple[SpellRuntimeState, EncounterState, list[SpellEvent]]:
        current_state = state
        current_encounter = encounter
        events: list[SpellEvent] = []
        existing = state.caster(caster_id).concentration
        if definition.concentration and existing is not None:
            current_state, current_encounter = self._break_concentration(
                current_state,
                current_encounter,
                caster_id,
            )
            events.append(
                self._event(
                    state.sequence + 1,
                    "spell.concentration.ended",
                    caster_id,
                    existing.spell_id,
                )
            )
        caster = current_state.caster(caster_id).spend_slot(cast_level)
        current_state = current_state.replace_caster(caster)
        current_encounter = self.combat.spend_action(
            current_encounter,
            caster_id,
            ActionResource.ACTION,
        ).state
        if definition.concentration:
            concentration = ConcentrationState(
                spell_id=definition.spell_id,
                caster_id=caster_id,
                remaining_rounds=definition.duration_rounds,
            )
            current_state = current_state.start_concentration(caster_id, concentration)
            events.append(
                self._event(
                    state.sequence + len(events) + 1,
                    "spell.concentration.started",
                    caster_id,
                    definition.spell_id,
                )
            )
        return current_state, current_encounter, events

    def _resolve_target(
        self,
        encounter: EncounterState,
        caster_id: str,
        caster_state: SpellcastingState,
        definition: SpellDefinition,
        cast_level: int,
        target_id: str,
    ) -> tuple[EncounterState, SpellTargetOutcome]:
        current = encounter
        roll: int | None = None
        attack_total: int | None = None
        save_total: int | None = None
        success: bool | None = None
        if definition.resolution is SpellResolution.ATTACK:
            caster = current.combatant(caster_id).actor
            base = caster.ability_score(caster_state.ability)
            modifier = RuleModifier(
                modifier_id=f"spell-attack:{definition.spell_id}",
                value=caster_state.spell_attack_bonus - base.modifier,
            )
            result = self.rules.resolve_d20(
                ResolutionContext(
                    context_id=f"spell-attack:{definition.spell_id}:{target_id}",
                    test_kind=D20TestKind.ATTACK_ROLL,
                    actor_id=caster_id,
                    target_id=target_id,
                    ability=caster_state.ability,
                    reason=definition.spell_id,
                ),
                ability_score=base,
                proficiency_bonus=caster.proficiency_bonus,
                modifiers=(modifier,),
            )
            roll = result.selected_roll
            attack_total = result.total
            armor_class = current.combatant(target_id).actor.defense.armor_class
            success = result.selected_roll == 20 or (
                result.selected_roll != 1 and result.total >= armor_class
            )
        elif definition.resolution is SpellResolution.SAVE:
            target = current.combatant(target_id).actor
            assert definition.save_ability is not None
            result = self.rules.resolve_save(
                ResolutionContext(
                    context_id=f"spell-save:{definition.spell_id}:{target_id}",
                    test_kind=D20TestKind.SAVING_THROW,
                    actor_id=target_id,
                    target_id=caster_id,
                    ability=definition.save_ability,
                    proficiency_rank=target.save_rank(definition.save_ability),
                    difficulty_class=DifficultyClass(caster_state.spell_save_dc),
                    reason=definition.spell_id,
                ),
                ability_score=target.ability_score(definition.save_ability),
                proficiency_bonus=target.proficiency_bonus,
            )
            roll = result.selected_roll
            save_total = result.total
            success = bool(result.success)
        else:
            success = True

        amounts: list[int] = []
        if definition.resolution is not SpellResolution.ATTACK or success:
            for effect in definition.effects:
                current, amount = self._apply_effect(
                    current,
                    caster_id,
                    target_id,
                    effect,
                    cast_level=cast_level,
                    base_level=definition.level,
                    save_succeeded=(
                        definition.resolution is SpellResolution.SAVE and bool(success)
                    ),
                    scaling=definition.scaling,
                )
                amounts.append(amount)
        return current, SpellTargetOutcome(
            target_id=target_id,
            roll=roll,
            attack_total=attack_total,
            save_total=save_total,
            success=success,
            amounts=tuple(amounts),
        )

    def _apply_effect(
        self,
        encounter: EncounterState,
        caster_id: str,
        target_id: str,
        effect: SpellEffectSpec,
        *,
        cast_level: int,
        base_level: int,
        save_succeeded: bool,
        scaling: SpellScaling | None,
    ) -> tuple[EncounterState, int]:
        if save_succeeded and effect.save_effect is SaveEffect.NEGATES:
            return encounter, 0
        amount = self._effect_amount(
            effect,
            caster_id,
            target_id,
            cast_level,
            base_level,
            scaling,
        )
        if save_succeeded and effect.save_effect is SaveEffect.HALF:
            amount //= 2
        if effect.kind is SpellEffectKind.DAMAGE:
            transition, _ = self.combat.apply_damage(
                encounter,
                target_id=target_id,
                packet=DamagePacket(amount, effect.damage_type or "damage:untyped"),
                source_actor_id=caster_id,
            )
            return transition.state, amount
        if effect.kind is SpellEffectKind.HEALING:
            return (
                self.combat.heal(
                    encounter,
                    target_id=target_id,
                    amount=amount,
                    source_actor_id=caster_id,
                ).state,
                amount,
            )
        if effect.kind is SpellEffectKind.CONDITION:
            assert effect.condition_id is not None
            return (
                self.combat.apply_condition(
                    encounter,
                    target_id=target_id,
                    condition_id=effect.condition_id,
                    source_actor_id=caster_id,
                ).state,
                0,
            )
        assert effect.condition_id is not None
        return (
            self.combat.remove_condition(
                encounter,
                target_id=target_id,
                condition_id=effect.condition_id,
            ).state,
            0,
        )

    def _effect_amount(
        self,
        effect: SpellEffectSpec,
        caster_id: str,
        target_id: str,
        cast_level: int,
        base_level: int,
        scaling: SpellScaling | None,
    ) -> int:
        value = effect.flat_amount
        if effect.dice is None:
            return max(0, value)
        extra = 0
        if scaling is not None and cast_level > base_level:
            per_level = (
                scaling.extra_damage_dice_per_slot
                if effect.kind is SpellEffectKind.DAMAGE
                else scaling.extra_healing_dice_per_slot
            )
            extra = (cast_level - base_level) * per_level
        dice = DiceExpression(effect.dice.count + extra, effect.dice.sides)
        rolled = roll_expression(
            dice,
            self.rng,
            reason=f"{caster_id}:{effect.kind.value}",
            actor_id=caster_id,
            target_id=target_id,
        )
        return max(0, rolled.total + value)

    def _castability_reason(
        self,
        caster: SpellcastingState,
        definition: SpellDefinition,
        cast_level: int,
    ) -> str:
        if not caster.can_cast(
            definition.spell_id,
            requires_preparation=definition.requires_preparation,
        ):
            return "Spell is not known/prepared"
        if cast_level == 0:
            return ""
        pool = caster.slot(cast_level)
        if pool is None or pool.current < 1:
            return f"No level {cast_level} spell slot is available"
        return ""

    def _resolve_targets(
        self,
        encounter: EncounterState,
        spatial: SpatialState,
        definition: SpellDefinition,
        caster_id: str,
        cast_level: int,
        requested: tuple[str, ...],
        point: GridCell | None,
        direction: tuple[float, float],
    ) -> tuple[str, ...]:
        eligible = self._eligible_target_ids(encounter, definition, caster_id)
        if definition.target_kind is SpellTargetKind.SELF:
            if caster_id not in eligible:
                raise ValidationError("caster does not satisfy the spell target selector")
            if requested and requested != (caster_id,):
                raise ValidationError("self-target spells may only target the caster")
            return (caster_id,)
        if definition.target_kind is SpellTargetKind.AREA:
            area = self._area_preview(spatial, definition, caster_id, point, direction)
            raw_ids = area.get("entity_ids", [])
            if not isinstance(raw_ids, list):
                raise ValidationError("spatial area entity_ids are malformed")
            return tuple(str(item) for item in raw_ids if str(item) in eligible)
        if definition.target_kind is SpellTargetKind.POINT:
            if point is None:
                raise ValidationError("point-target spells require a point")
            self._validate_point_range(spatial, caster_id, point, definition.range_feet)
            return ()
        max_targets = definition.max_targets + max(
            0,
            cast_level - definition.level,
        ) * definition.scaling.extra_targets_per_slot
        if (
            not requested
            or len(requested) > max_targets
            or len(requested) != len(set(requested))
        ):
            raise ValidationError("spell target count is outside the allowed range")
        service = SpatialQueryService(
            spatial,
            tuple(combatant.actor for combatant in encounter.combatants),
        )
        for target_id in requested:
            if target_id not in eligible:
                raise ValidationError("spell target does not satisfy the target selector")
            encounter.combatant(target_id)
            distance = service.execute(
                "spatial.distance",
                {"source_entity_id": caster_id, "target_entity_id": target_id},
            )
            if self._integer_result(distance, "distance_feet") > definition.range_feet:
                raise ValidationError("spell target is outside range")
            los = service.execute(
                "spatial.los",
                {"source_entity_id": caster_id, "target_entity_id": target_id},
            )
            if not bool(los.get("visible", False)):
                raise ValidationError("spell target is not visible")
        return requested

    def _eligible_target_ids(
        self,
        encounter: EncounterState,
        definition: SpellDefinition,
        caster_id: str,
    ) -> frozenset[str]:
        if definition.selector is None:
            return frozenset(item.actor.actor_id for item in encounter.combatants)
        world = RuleWorldState(
            tuple(item.actor.to_rule_subject() for item in encounter.combatants)
        )
        selected = self.rules.targets(world, caster_id, definition.selector)
        return frozenset(item.subject_id for item in selected)

    def _area_preview(
        self,
        spatial: SpatialState,
        definition: SpellDefinition,
        caster_id: str,
        point: GridCell | None,
        direction: tuple[float, float],
    ) -> dict[str, object]:
        if definition.target_kind is not SpellTargetKind.AREA:
            return {}
        origin = spatial.placement(caster_id).anchor
        size = definition.area_size_feet or 0
        if definition.area_shape in {"sphere", "cube", "cylinder"}:
            if point is None:
                raise ValidationError("area spell requires a target point")
            self._validate_point_range(spatial, caster_id, point, definition.range_feet)
        shape: dict[str, object]
        if definition.area_shape == "sphere":
            shape = {
                "kind": "sphere",
                "center": self._cell(point),
                "radius_feet": size,
            }
        elif definition.area_shape == "cube":
            shape = {
                "kind": "cube",
                "center": self._cell(point),
                "size_feet": size,
            }
        elif definition.area_shape == "cylinder":
            shape = {
                "kind": "cylinder",
                "center": self._cell(point),
                "radius_feet": size,
                "height_feet": size,
            }
        elif definition.area_shape == "cone":
            shape = {
                "kind": "cone",
                "origin": self._cell(origin),
                "direction": {"x": direction[0], "y": direction[1]},
                "length_feet": size,
            }
        else:
            shape = {
                "kind": "line",
                "origin": self._cell(origin),
                "direction": {"x": direction[0], "y": direction[1]},
                "length_feet": size,
                "width_feet": 5,
            }
        return SpatialQueryService(spatial).execute("spatial.area", {"shape": shape})

    def _validate_point_range(
        self,
        spatial: SpatialState,
        caster_id: str,
        point: GridCell,
        range_feet: int,
    ) -> None:
        if not spatial.space.contains(point):
            raise ValidationError("spell point is outside spatial bounds")
        origin = spatial.placement(caster_id).anchor
        distance = (
            max(abs(point.x - origin.x), abs(point.y - origin.y))
            * spatial.space.cell_size_feet
        )
        if distance > range_feet:
            raise ValidationError("spell point is outside range")

    def _break_concentration(
        self,
        state: SpellRuntimeState,
        encounter: EncounterState,
        caster_id: str,
    ) -> tuple[SpellRuntimeState, EncounterState]:
        current = encounter
        for active in state.active_effects:
            if active.caster_id != caster_id or not active.concentration:
                continue
            current = self._remove_duration_conditions(current, active)
        return state.end_concentration(caster_id), current

    def _remove_duration_conditions(
        self,
        encounter: EncounterState,
        active: ActiveSpellEffect,
    ) -> EncounterState:
        current = encounter
        for target_id in active.target_ids:
            if not self._is_combatant(current, target_id):
                continue
            for effect in active.effects:
                if effect.kind is not SpellEffectKind.CONDITION or not effect.condition_id:
                    continue
                subject = current.combatant(target_id).actor.to_rule_subject()
                if subject.has_condition(effect.condition_id):
                    current = self.combat.remove_condition(
                        current,
                        target_id=target_id,
                        condition_id=effect.condition_id,
                    ).state
        return current

    def _duration_effects(
        self,
        definition: SpellDefinition,
    ) -> tuple[SpellEffectSpec, ...]:
        return tuple(
            effect
            for effect in definition.effects
            if effect.ongoing or effect.kind is SpellEffectKind.CONDITION
        )

    def _duration_target_ids(
        self,
        definition: SpellDefinition,
        outcomes: tuple[SpellTargetOutcome, ...],
    ) -> tuple[str, ...]:
        duration_effects = self._duration_effects(definition)
        result: list[str] = []
        for outcome in outcomes:
            if definition.resolution is SpellResolution.ATTACK and not outcome.success:
                continue
            if definition.resolution is SpellResolution.SAVE and outcome.success:
                if all(
                    effect.save_effect is SaveEffect.NEGATES
                    for effect in duration_effects
                ):
                    continue
            result.append(outcome.target_id)
        return tuple(result)

    def _sync_concentration_durations(
        self,
        state: SpellRuntimeState,
        active_effects: tuple[ActiveSpellEffect, ...],
        expired: set[tuple[str, str]],
    ) -> SpellRuntimeState:
        current = state
        for caster in state.casters:
            concentration = caster.concentration
            if concentration is None:
                continue
            matching = next(
                (
                    effect
                    for effect in active_effects
                    if effect.concentration
                    and effect.caster_id == caster.actor_id
                    and effect.spell_id == concentration.spell_id
                ),
                None,
            )
            if matching is not None:
                current = current.replace_caster(
                    replace(
                        current.caster(caster.actor_id),
                        concentration=replace(
                            concentration,
                            remaining_rounds=matching.remaining_rounds,
                        ),
                    )
                )
            elif (caster.actor_id, concentration.spell_id) in expired:
                current = current.replace_caster(
                    replace(current.caster(caster.actor_id), concentration=None)
                )
        return current

    def _target_event(
        self,
        sequence: int,
        caster_id: str,
        spell_id: str,
        outcome: SpellTargetOutcome,
    ) -> SpellEvent:
        return self._event(
            sequence,
            "spell.target.resolved",
            caster_id,
            spell_id,
            (outcome.target_id,),
            (
                ("roll", outcome.roll),
                ("attack_total", outcome.attack_total),
                ("save_total", outcome.save_total),
                ("success", outcome.success),
                ("amounts", outcome.amounts),
            ),
            rng_after=self._checkpoint(),
        )

    def _checkpoint(self) -> RNGCheckpoint:
        state, increment = self.rng.snapshot()
        return RNGCheckpoint(
            algorithm=self.rng.ALGORITHM,
            state=state,
            increment=increment,
        )

    @staticmethod
    def _integer_result(result: dict[str, object], key: str) -> int:
        value = result.get(key)
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValidationError(f"spatial query {key} must be an integer")
        return value

    @staticmethod
    def _cell(cell: GridCell | None) -> dict[str, int]:
        if cell is None:
            raise ValidationError("spell shape requires a cell")
        return {"x": cell.x, "y": cell.y}

    @staticmethod
    def _is_combatant(encounter: EncounterState, actor_id: str) -> bool:
        return any(item.actor.actor_id == actor_id for item in encounter.combatants)

    @staticmethod
    def _event(
        sequence: int,
        event_type: str,
        caster_id: str,
        spell_id: str,
        target_ids: tuple[str, ...] = (),
        payload: tuple[tuple[str, SpellEventValue], ...] = (),
        *,
        rng_after: RNGCheckpoint | None = None,
    ) -> SpellEvent:
        return SpellEvent(
            sequence=sequence,
            event_type=event_type,
            caster_id=caster_id,
            spell_id=spell_id,
            target_ids=target_ids,
            payload=payload,
            rng_after=rng_after,
        )
