from __future__ import annotations

from godot_dnd_engine.character_creator import (
    CharacterCreatorRuntime,
    CharacterCreatorService,
    demo_character_catalog,
)
from godot_dnd_engine.world.tactical_templates import (
    WORLD_PARTY_TEAM,
    create_world_tactical_session,
)
from godot_dnd_engine.world_bridge import _seed_premade_characters


ENCOUNTERS = {
    "encounter:road-ambush": ("Roadside Scavengers", "space:old-road-ambush"),
    "encounter:quarry-watchers": ("Quarry Watchers", "space:quarry-mouth-watch"),
    "encounter:underworks-swarm": (
        "Underworks Swarm",
        "space:flooded-underworks-swarm",
    ),
    "encounter:vault-warden": (
        "The Hollow Warden",
        "space:lantern-vault-warden",
    ),
}


def _party() -> tuple[object, ...]:
    creator = CharacterCreatorService(CharacterCreatorRuntime(demo_character_catalog()))
    _seed_premade_characters(creator)
    return tuple(
        creator.records[actor_id].actor
        for actor_id in (
            "actor:premade-mira",
            "actor:premade-aster",
            "actor:premade-tovan",
            "actor:premade-sable",
        )
    )


def test_all_world_encounter_gates_have_distinct_party_aware_tactical_templates() -> None:
    party = _party()
    seen_spaces: set[str] = set()
    seen_enemy_sets: set[tuple[str, ...]] = set()

    for index, (encounter_id, expected) in enumerate(ENCOUNTERS.items()):
        session = create_world_tactical_session(
            encounter_id=encounter_id,
            party_actors=party,  # type: ignore[arg-type]
            campaign_id="campaign:template-test",
            session_id="session:template-test",
            seed=100 + index,
        )
        snapshot = session.snapshot()
        state = snapshot["state"]
        assert isinstance(state, dict)
        tactical = state["tactical"]
        assert isinstance(tactical, dict)
        assert tactical["encounter_id"] == encounter_id
        assert tactical["display_name"] == expected[0]

        space = tactical["space"]
        assert isinstance(space, dict)
        assert space["space_id"] == expected[1]
        assert space["space_id"] not in seen_spaces
        seen_spaces.add(str(space["space_id"]))

        actors = tactical["actors"]
        assert isinstance(actors, list)
        rows = [row for row in actors if isinstance(row, dict)]
        party_rows = [row for row in rows if row.get("team") == WORLD_PARTY_TEAM]
        enemy_rows = [row for row in rows if row.get("team") != WORLD_PARTY_TEAM]
        assert [row["actor_id"] for row in party_rows] == [
            "actor:premade-mira",
            "actor:premade-aster",
            "actor:premade-tovan",
            "actor:premade-sable",
        ]
        enemy_ids = tuple(sorted(str(row["actor_id"]) for row in enemy_rows))
        assert enemy_ids
        assert enemy_ids not in seen_enemy_sets
        seen_enemy_sets.add(enemy_ids)


def test_world_tactical_template_is_deterministic_for_same_seed() -> None:
    party = _party()
    first = create_world_tactical_session(
        encounter_id="encounter:vault-warden",
        party_actors=party,  # type: ignore[arg-type]
        campaign_id="campaign:template-test",
        session_id="session:template-test",
        seed=707,
    )
    second = create_world_tactical_session(
        encounter_id="encounter:vault-warden",
        party_actors=party,  # type: ignore[arg-type]
        campaign_id="campaign:template-test",
        session_id="session:template-test",
        seed=707,
    )
    assert first.snapshot() == second.snapshot()
