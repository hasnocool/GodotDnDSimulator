from __future__ import annotations

import json
from pathlib import Path

from godot_dnd_engine.rng import DeterministicRNG
from godot_dnd_engine.rules import (
    Ability,
    AbilityScore,
    D20TestKind,
    DifficultyClass,
    ProficiencyRank,
    ResolutionContext,
    RollMode,
    RulesRuntime,
    RulesetCapabilities,
)

ROOT = Path(__file__).resolve().parents[1]


def test_representative_imported_rule_conformance_cases() -> None:
    data = json.loads((ROOT / "tests/fixtures/rules_runtime/conformance.json").read_text())
    for case in data["cases"]:
        ability = Ability(case["ability"])
        kind = D20TestKind(case["test_kind"])
        context = ResolutionContext(
            f"resolution:{case['name'].replace(' ', '-')}",
            kind,
            actor_id="actor:fixture",
            ability=ability,
            proficiency_rank=ProficiencyRank(case["proficiency_rank"]),
            difficulty_class=DifficultyClass(case["difficulty_class"]),
            reason=case["name"],
        )
        runtime = RulesRuntime(
            DeterministicRNG.from_seed(case["seed"]),
            RulesetCapabilities.srd_5_2_1_core(),
        )
        outcome = runtime.resolve_d20(
            context,
            ability_score=AbilityScore(ability, case["ability_score"]),
            proficiency_bonus=case["proficiency_bonus"],
            advantage_sources=case["advantage_sources"],
            disadvantage_sources=case["disadvantage_sources"],
        )
        expected_mode = RollMode.from_sources(
            case["advantage_sources"], case["disadvantage_sources"]
        )
        assert outcome.roll_mode is expected_mode
        assert outcome.total == (
            outcome.selected_roll + outcome.ability_modifier + outcome.proficiency_modifier
        )
        assert outcome.success is (outcome.total >= case["difficulty_class"])
        assert outcome.context.test_kind is kind
