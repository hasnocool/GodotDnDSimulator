"""Typed deterministic D20 and generic rules runtime orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from ..dice import DiceExpression, roll_expression
from ..errors import ValidationError
from ..rng import DeterministicRNG
from .capabilities import RulesetCapabilities
from .effects import EffectBatchResult, RuleEffect, apply_effects
from .hooks import ReactionHook, ReactionMatch, RuleEventView, collect_reactions
from .modifiers import ModifierResolution, RuleModifier, resolve_modifiers
from .primitives import (
    Ability,
    AbilityScore,
    D20TestKind,
    DifficultyClass,
    ProficiencyRank,
    ResourceCost,
    RollMode,
)
from .requirements import Requirement, RequirementResult, evaluate_requirements
from .resources import ResourceSpendResult, spend_costs
from .state import RuleSubjectState, RuleWorldState
from .targets import TargetSelector, select_targets


@dataclass(frozen=True, slots=True)
class ResolutionContext:
    context_id: str
    test_kind: D20TestKind
    actor_id: str
    ability: Ability
    proficiency_rank: ProficiencyRank = ProficiencyRank.NONE
    difficulty_class: DifficultyClass | None = None
    target_id: str | None = None
    reason: str = "D20 Test"
    tags: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if not isinstance(self.context_id, str) or not self.context_id.strip():
            raise ValidationError("context_id must be a non-empty string")
        if not isinstance(self.actor_id, str) or not self.actor_id.strip():
            raise ValidationError("resolution actor_id must be a non-empty string")
        if self.target_id is not None and (
            not isinstance(self.target_id, str) or not self.target_id.strip()
        ):
            raise ValidationError("resolution target_id must be None or a non-empty string")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValidationError("resolution reason must be a non-empty string")


@dataclass(frozen=True, slots=True)
class D20Outcome:
    context: ResolutionContext
    roll_mode: RollMode
    raw_rolls: tuple[int, ...]
    selected_roll: int
    ability_modifier: int
    proficiency_modifier: int
    modifier_resolution: ModifierResolution
    total: int
    success: bool | None
    rng_algorithm: str


class RulesRuntime:
    """Small deterministic facade over reusable v0.3 rules primitives."""

    def __init__(self, rng: DeterministicRNG, capabilities: RulesetCapabilities) -> None:
        self._rng = rng
        self.capabilities = capabilities

    @property
    def rng(self) -> DeterministicRNG:
        return self._rng

    def resolve_d20(
        self,
        context: ResolutionContext,
        *,
        ability_score: AbilityScore,
        proficiency_bonus: int,
        modifiers: tuple[RuleModifier, ...] = (),
        advantage_sources: int = 0,
        disadvantage_sources: int = 0,
    ) -> D20Outcome:
        self.capabilities.require("d20_tests", "modifier_pipeline")
        if ability_score.ability is not context.ability:
            raise ValidationError("ability score does not match resolution context ability")
        mode = RollMode.from_sources(advantage_sources, disadvantage_sources)
        if mode is not RollMode.NORMAL:
            self.capabilities.require("advantage_disadvantage")

        roll_count = 1 if mode is RollMode.NORMAL else 2
        rolls = tuple(
            roll_expression(
                DiceExpression(1, 20),
                self._rng,
                reason=context.reason,
                actor_id=context.actor_id,
                target_id=context.target_id,
            ).raw_rolls[0]
            for _ in range(roll_count)
        )
        if mode is RollMode.ADVANTAGE:
            selected = max(rolls)
        elif mode is RollMode.DISADVANTAGE:
            selected = min(rolls)
        else:
            selected = rolls[0]

        proficiency_modifier = context.proficiency_rank.apply(proficiency_bonus)
        base_total = selected + ability_score.modifier + proficiency_modifier
        resolved = resolve_modifiers(base_total, modifiers)
        dc = context.difficulty_class
        success = None if dc is None else resolved.final_value >= dc.value
        return D20Outcome(
            context=context,
            roll_mode=mode,
            raw_rolls=rolls,
            selected_roll=selected,
            ability_modifier=ability_score.modifier,
            proficiency_modifier=proficiency_modifier,
            modifier_resolution=resolved,
            total=resolved.final_value,
            success=success,
            rng_algorithm=self._rng.ALGORITHM,
        )

    def resolve_save(
        self,
        context: ResolutionContext,
        *,
        ability_score: AbilityScore,
        proficiency_bonus: int,
        modifiers: tuple[RuleModifier, ...] = (),
        advantage_sources: int = 0,
        disadvantage_sources: int = 0,
    ) -> D20Outcome:
        if context.test_kind is not D20TestKind.SAVING_THROW:
            raise ValidationError("resolve_save requires a saving-throw context")
        if context.difficulty_class is None:
            raise ValidationError("saving throws require a difficulty class")
        return self.resolve_d20(
            context,
            ability_score=ability_score,
            proficiency_bonus=proficiency_bonus,
            modifiers=modifiers,
            advantage_sources=advantage_sources,
            disadvantage_sources=disadvantage_sources,
        )

    def spend_resources(
        self,
        subject: RuleSubjectState,
        costs: tuple[ResourceCost, ...],
    ) -> ResourceSpendResult:
        self.capabilities.require("resources")
        return spend_costs(subject, costs)

    def check_requirements(
        self,
        subject: RuleSubjectState,
        requirements: tuple[Requirement, ...],
    ) -> RequirementResult:
        self.capabilities.require("requirements")
        return evaluate_requirements(requirements, subject, self.capabilities)

    def targets(
        self,
        world: RuleWorldState,
        source_id: str,
        selector: TargetSelector,
    ) -> tuple[RuleSubjectState, ...]:
        self.capabilities.require("target_selectors")
        return select_targets(selector, world, source_id=source_id)

    def apply_effects(
        self,
        world: RuleWorldState,
        *,
        source_id: str,
        effects: tuple[RuleEffect, ...],
    ) -> EffectBatchResult:
        self.capabilities.require("effects", "conditions")
        return apply_effects(world, source_id=source_id, effects=effects)

    def reactions(
        self,
        event: RuleEventView,
        hooks: tuple[ReactionHook, ...],
        world: RuleWorldState,
    ) -> tuple[ReactionMatch, ...]:
        self.capabilities.require("reactions")
        return collect_reactions(event, hooks, world, self.capabilities)
