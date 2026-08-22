# engine/src/godot_dnd_engine/rules/__init__.py
"""Public v0.3 headless rules runtime API."""

from .capabilities import CORE_V03_CAPABILITIES, RulesetCapabilities
from .effects import EffectBatchResult, EffectKind, RuleEffect, apply_effects
from .hooks import ReactionHook, ReactionMatch, RuleEventView, Trigger, collect_reactions
from .modifiers import (
    ModifierOperation,
    ModifierResolution,
    RuleModifier,
    StackingRule,
    resolve_modifiers,
)
from .primitives import (
    Ability,
    AbilityScore,
    D20TestKind,
    DifficultyClass,
    ProficiencyRank,
    ResourceCost,
    ResourcePool,
    RollMode,
    proficiency_bonus_for_level,
)
from .requirements import (
    Requirement,
    RequirementKind,
    RequirementResult,
    evaluate_requirements,
)
from .resources import ResourceSpendResult, spend_costs
from .runtime import D20Outcome, ResolutionContext, RulesRuntime
from .state import (
    ConditionInstance,
    ConditionStacking,
    Duration,
    DurationUnit,
    RuleSubjectState,
    RuleWorldState,
    advance_condition_durations,
)
from .targets import TargetMode, TargetSelector, select_targets

__all__ = [
    "CORE_V03_CAPABILITIES",
    "Ability",
    "AbilityScore",
    "ConditionInstance",
    "ConditionStacking",
    "D20Outcome",
    "D20TestKind",
    "DifficultyClass",
    "Duration",
    "DurationUnit",
    "EffectBatchResult",
    "EffectKind",
    "ModifierOperation",
    "ModifierResolution",
    "ProficiencyRank",
    "ReactionHook",
    "ReactionMatch",
    "Requirement",
    "RequirementKind",
    "RequirementResult",
    "ResolutionContext",
    "ResourceCost",
    "ResourcePool",
    "ResourceSpendResult",
    "RollMode",
    "RuleEffect",
    "RuleEventView",
    "RuleModifier",
    "RuleSubjectState",
    "RuleWorldState",
    "RulesRuntime",
    "RulesetCapabilities",
    "StackingRule",
    "TargetMode",
    "TargetSelector",
    "Trigger",
    "advance_condition_durations",
    "apply_effects",
    "collect_reactions",
    "evaluate_requirements",
    "proficiency_bonus_for_level",
    "resolve_modifiers",
    "select_targets",
    "spend_costs",
]
