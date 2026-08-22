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
    RulesetCapabilities,
    RulesRuntime,
)

from tools.rules_importer.models import CanonicalEntity, Provenance

ROOT = Path(__file__).resolve().parents[1]


def _canonical_entity(data: dict[str, object]) -> CanonicalEntity:
    provenance_data = data["provenance"]
    assert isinstance(provenance_data, dict)
    mechanics = data["mechanics"]
    assert isinstance(mechanics, dict)
    return CanonicalEntity(
        entity_id=str(data["entity_id"]),
        kind=str(data["kind"]),
        name=str(data["name"]),
        schema_version=int(data["schema_version"]),
        status=str(data["status"]),  # type: ignore[arg-type]
        source_text=str(data["source_text"]),
        provenance=Provenance(**provenance_data),  # type: ignore[arg-type]
        mechanics=mechanics,
    )


def test_representative_imported_rule_conformance_cases() -> None:
    data = json.loads((ROOT / "tests/fixtures/rules_runtime/conformance.json").read_text())
    for case in data["cases"]:
        entity = _canonical_entity(case["entity"])
        assert entity.provenance.source_id == "wotc-srd-5.2.1-en"
        mechanics = entity.mechanics
        ability = Ability(mechanics["ability"])
        kind = D20TestKind(mechanics["test_kind"])
        context = ResolutionContext(
            f"resolution:{entity.entity_id}",
            kind,
            actor_id="actor:fixture",
            ability=ability,
            proficiency_rank=ProficiencyRank(mechanics["proficiency_rank"]),
            difficulty_class=DifficultyClass(mechanics["difficulty_class"]),
            reason=entity.name,
        )
        runtime = RulesRuntime(
            DeterministicRNG.from_seed(case["seed"]),
            RulesetCapabilities.srd_5_2_1_core(),
        )
        outcome = runtime.resolve_d20(
            context,
            ability_score=AbilityScore(ability, mechanics["ability_score"]),
            proficiency_bonus=mechanics["proficiency_bonus"],
            advantage_sources=mechanics["advantage_sources"],
            disadvantage_sources=mechanics["disadvantage_sources"],
        )
        expected_mode = RollMode.from_sources(
            mechanics["advantage_sources"], mechanics["disadvantage_sources"]
        )
        assert outcome.roll_mode is expected_mode
        assert outcome.total == (
            outcome.selected_roll + outcome.ability_modifier + outcome.proficiency_modifier
        )
        assert outcome.success is (outcome.total >= mechanics["difficulty_class"])
        assert outcome.context.test_kind is kind
