# engine/src/godot_dnd_engine/world/tactical_templates.py
"""Authored tactical encounters for the original Lanterns Below campaign.

The world layer owns which encounter gate is active. This module translates that gate plus the
actual authoritative party actors into one tactical session without moving combat or spatial
legality into the client.
"""

from __future__ import annotations

from dataclasses import replace

from ..actors import (
    ActorKind,
    ActorState,
    DefenseState,
    HitPoints,
    MovementMode,
    MovementSpeed,
    SizeCategory,
)
from ..combat import CombatRuntime, ZeroHitPointRule
from ..errors import ValidationError
from ..rng import DeterministicRNG
from ..rules import Ability, AbilityScore
from ..spatial import (
    CoverLevel,
    GridCell,
    SpatialPlacement,
    SpatialRuntime,
    SpatialState,
    SquareGridSpace,
    TerrainCell,
)
from ..spell_slice import SpellEnabledTacticalSession, demo_spell_definitions
from ..spells import (
    SpellRuntime,
    SpellRuntimeState,
    SpellSlotPool,
    SpellcastingState,
)
from ..vertical_slice import TacticalVerticalSliceSession

WORLD_PARTY_TEAM = "party"
_WORLD_PARTY_TAG = f"team:{WORLD_PARTY_TEAM}"


class AuthoredWorldTacticalSession(TacticalVerticalSliceSession):
    """Vertical-slice mechanics with authored world encounter presentation metadata."""

    __slots__ = ("authored_slice_id", "authored_display_name", "authored_camera_bounds")

    def __init__(
        self,
        *,
        authored_slice_id: str,
        authored_display_name: str,
        authored_camera_bounds: dict[str, int],
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self.authored_slice_id = authored_slice_id
        self.authored_display_name = authored_display_name
        self.authored_camera_bounds = dict(authored_camera_bounds)

    def _tactical_state(self) -> dict[str, object]:
        state = super()._tactical_state()
        state["slice_id"] = self.authored_slice_id
        state["display_name"] = self.authored_display_name
        space_value = state.get("space")
        if isinstance(space_value, dict):
            space = dict(space_value)
            space["camera_bounds"] = dict(self.authored_camera_bounds)
            state["space"] = space
        return state


def create_world_spell_tactical_session(
    *,
    encounter_id: str,
    party_actors: tuple[ActorState, ...],
    campaign_id: str,
    session_id: str,
    seed: int,
) -> SpellEnabledTacticalSession:
    """Create the authored tactical session bound to one world encounter gate."""

    tactical = create_world_tactical_session(
        encounter_id=encounter_id,
        party_actors=party_actors,
        campaign_id=campaign_id,
        session_id=session_id,
        seed=seed,
    )
    definitions = demo_spell_definitions()
    spell_runtime = SpellRuntime(tactical.rng, definitions)
    spell_ids = tuple(item.spell_id for item in definitions)
    prepared_ids = tuple(
        item.spell_id for item in definitions if item.requires_preparation
    )
    spell_state = SpellRuntimeState(
        casters=tuple(
            SpellcastingState(
                actor_id=combatant.actor.actor_id,
                ability=Ability.INTELLIGENCE,
                spell_attack_bonus=4,
                spell_save_dc=12,
                known_spell_ids=spell_ids,
                prepared_spell_ids=prepared_ids,
                slots=(
                    SpellSlotPool(1, 3, 3),
                    SpellSlotPool(2, 1, 1),
                ),
            )
            for combatant in tactical.encounter.combatants
        )
    )
    return SpellEnabledTacticalSession(
        tactical=tactical,
        spell_runtime=spell_runtime,
        spell_state=spell_state,
    )


def create_world_tactical_session(
    *,
    encounter_id: str,
    party_actors: tuple[ActorState, ...],
    campaign_id: str,
    session_id: str,
    seed: int,
) -> AuthoredWorldTacticalSession:
    """Build a deterministic, party-aware tactical encounter for one campaign gate."""

    if not party_actors:
        raise ValidationError("world tactical encounters require at least one party actor")
    if len(party_actors) > 4:
        raise ValidationError("world tactical encounters support at most four party actors")
    if len({actor.actor_id for actor in party_actors}) != len(party_actors):
        raise ValidationError("world tactical party actor IDs must be unique")

    spec = _encounter_spec(encounter_id)
    party = tuple(_as_party_actor(actor) for actor in party_actors)
    enemies = tuple(
        _enemy_actor(
            row["actor_id"],
            row["name"],
            team_tag=row["team_tag"],
            hit_points=row["hit_points"],
            dexterity=row["dexterity"],
            armor_class=row["armor_class"],
            strength=row["strength"],
        )
        for row in spec["enemies"]
    )
    actors = (*party, *enemies)

    rng = DeterministicRNG.from_seed(seed)
    combat_runtime = CombatRuntime(rng)
    spatial_runtime = SpatialRuntime()
    zero_hp_rules = {
        actor.actor_id: (
            ZeroHitPointRule.CHARACTER
            if actor.actor_id in {item.actor_id for item in party}
            else ZeroHitPointRule.MONSTER
        )
        for actor in actors
    }
    encounter = combat_runtime.create_encounter(
        encounter_id,
        actors,
        zero_hp_rules=zero_hp_rules,
    )
    encounter = combat_runtime.start_encounter(encounter).state

    space = SquareGridSpace(
        spec["space_id"],
        width=spec["width"],
        height=spec["height"],
        cell_size_feet=5,
        terrain=spec["terrain"],
    )
    placements: list[SpatialPlacement] = []
    for actor, cell in zip(party, spec["party_cells"], strict=True):
        placements.append(
            SpatialPlacement(
                actor.actor_id,
                cell,
                tags=frozenset({_WORLD_PARTY_TAG, "world-party"}),
            )
        )
    for actor, cell in zip(enemies, spec["enemy_cells"], strict=True):
        team_tag = next(
            tag for tag in actor.tags if tag.startswith("team:")
        )
        placements.append(
            SpatialPlacement(
                actor.actor_id,
                cell,
                tags=frozenset({team_tag, "world-enemy"}),
            )
        )
    spatial = SpatialState(space, tuple(placements))

    return AuthoredWorldTacticalSession(
        authored_slice_id=f"world-tactical:{encounter_id.removeprefix('encounter:')}",
        authored_display_name=spec["display_name"],
        authored_camera_bounds={
            "min_x": 0,
            "min_y": 0,
            "max_x": spec["width"] - 1,
            "max_y": spec["height"] - 1,
        },
        campaign_id=campaign_id,
        session_id=session_id,
        rng=rng,
        combat_runtime=combat_runtime,
        spatial_runtime=spatial_runtime,
        encounter=encounter,
        spatial=spatial,
        actors=actors,
    )


def _as_party_actor(actor: ActorState) -> ActorState:
    tags = {
        tag for tag in actor.tags if not tag.startswith("team:")
    }
    tags.update({_WORLD_PARTY_TAG, "world-party"})
    return replace(actor, kind=ActorKind.HERO, tags=frozenset(tags))


def _enemy_actor(
    actor_id: str,
    name: str,
    *,
    team_tag: str,
    hit_points: int,
    dexterity: int,
    armor_class: int,
    strength: int,
) -> ActorState:
    abilities = tuple(
        AbilityScore(
            ability,
            dexterity
            if ability is Ability.DEXTERITY
            else (strength if ability is Ability.STRENGTH else 11),
        )
        for ability in Ability
    )
    return ActorState(
        actor_id=actor_id,
        name=name,
        kind=ActorKind.CREATURE,
        size=SizeCategory.MEDIUM,
        proficiency_bonus=2,
        abilities=abilities,
        hit_points=HitPoints(hit_points, hit_points),
        defense=DefenseState(armor_class),
        movement=(MovementSpeed(MovementMode.WALK, 30),),
        tags=frozenset({team_tag, "world-enemy"}),
    )


def _encounter_spec(encounter_id: str) -> dict[str, object]:
    specs = {
        "encounter:road-ambush": {
            "display_name": "Roadside Scavengers",
            "space_id": "space:old-road-ambush",
            "width": 10,
            "height": 7,
            "party_cells": (
                GridCell(1, 1),
                GridCell(1, 3),
                GridCell(1, 5),
                GridCell(2, 6),
            ),
            "enemy_cells": (GridCell(8, 2), GridCell(8, 5)),
            "enemies": (
                {
                    "actor_id": "actor:road-scavenger-a",
                    "name": "Road Scavenger",
                    "team_tag": "team:road-scavengers",
                    "hit_points": 12,
                    "dexterity": 14,
                    "armor_class": 12,
                    "strength": 12,
                },
                {
                    "actor_id": "actor:road-scavenger-b",
                    "name": "Road Prowler",
                    "team_tag": "team:road-scavengers",
                    "hit_points": 14,
                    "dexterity": 13,
                    "armor_class": 12,
                    "strength": 13,
                },
            ),
            "terrain": (
                TerrainCell(
                    GridCell(4, 1),
                    terrain_id="terrain:road-rubble",
                    difficult=True,
                ),
                TerrainCell(
                    GridCell(4, 2),
                    terrain_id="terrain:road-rubble",
                    difficult=True,
                ),
                TerrainCell(
                    GridCell(5, 4),
                    terrain_id="terrain:fallen-cart",
                    blocks_movement=True,
                    cover=CoverLevel.THREE_QUARTERS,
                ),
            ),
        },
        "encounter:quarry-watchers": {
            "display_name": "Quarry Watchers",
            "space_id": "space:quarry-mouth-watch",
            "width": 10,
            "height": 8,
            "party_cells": (
                GridCell(1, 1),
                GridCell(1, 3),
                GridCell(1, 5),
                GridCell(1, 7),
            ),
            "enemy_cells": (GridCell(8, 2), GridCell(8, 6)),
            "enemies": (
                {
                    "actor_id": "actor:quarry-watcher-a",
                    "name": "Quarry Watcher",
                    "team_tag": "team:quarry-watchers",
                    "hit_points": 18,
                    "dexterity": 12,
                    "armor_class": 14,
                    "strength": 14,
                },
                {
                    "actor_id": "actor:quarry-watcher-b",
                    "name": "Quarry Sentinel",
                    "team_tag": "team:quarry-watchers",
                    "hit_points": 20,
                    "dexterity": 11,
                    "armor_class": 14,
                    "strength": 15,
                },
            ),
            "terrain": (
                TerrainCell(
                    GridCell(4, 2),
                    terrain_id="terrain:quarry-pool",
                    difficult=True,
                ),
                TerrainCell(
                    GridCell(4, 3),
                    terrain_id="terrain:quarry-pool",
                    difficult=True,
                ),
                TerrainCell(
                    GridCell(5, 5),
                    terrain_id="terrain:quarry-block",
                    elevation_feet=5,
                    cover=CoverLevel.HALF,
                ),
                TerrainCell(
                    GridCell(6, 3),
                    terrain_id="terrain:quarry-wall",
                    blocks_movement=True,
                    blocks_los=True,
                    obstacle_height_feet=10,
                    cover=CoverLevel.TOTAL,
                ),
            ),
        },
        "encounter:underworks-swarm": {
            "display_name": "Underworks Swarm",
            "space_id": "space:flooded-underworks-swarm",
            "width": 11,
            "height": 8,
            "party_cells": (
                GridCell(1, 1),
                GridCell(1, 3),
                GridCell(1, 5),
                GridCell(1, 7),
            ),
            "enemy_cells": (
                GridCell(9, 1),
                GridCell(9, 4),
                GridCell(9, 7),
            ),
            "enemies": (
                {
                    "actor_id": "actor:underworks-swarm-a",
                    "name": "Lantern Swarm",
                    "team_tag": "team:underworks-swarm",
                    "hit_points": 14,
                    "dexterity": 16,
                    "armor_class": 13,
                    "strength": 10,
                },
                {
                    "actor_id": "actor:underworks-swarm-b",
                    "name": "Flood Crawler",
                    "team_tag": "team:underworks-swarm",
                    "hit_points": 16,
                    "dexterity": 14,
                    "armor_class": 13,
                    "strength": 12,
                },
                {
                    "actor_id": "actor:underworks-swarm-c",
                    "name": "Stone Mite Cluster",
                    "team_tag": "team:underworks-swarm",
                    "hit_points": 16,
                    "dexterity": 13,
                    "armor_class": 14,
                    "strength": 13,
                },
            ),
            "terrain": (
                TerrainCell(
                    GridCell(4, 1),
                    terrain_id="terrain:underworks-water",
                    difficult=True,
                ),
                TerrainCell(
                    GridCell(4, 2),
                    terrain_id="terrain:underworks-water",
                    difficult=True,
                ),
                TerrainCell(
                    GridCell(4, 3),
                    terrain_id="terrain:underworks-water",
                    difficult=True,
                ),
                TerrainCell(
                    GridCell(6, 5),
                    terrain_id="terrain:stonefall-pile",
                    blocks_movement=True,
                    cover=CoverLevel.THREE_QUARTERS,
                ),
                TerrainCell(
                    GridCell(6, 2),
                    terrain_id="terrain:underworks-column",
                    blocks_movement=True,
                    blocks_los=True,
                    obstacle_height_feet=10,
                    cover=CoverLevel.TOTAL,
                ),
            ),
        },
        "encounter:vault-warden": {
            "display_name": "The Hollow Warden",
            "space_id": "space:lantern-vault-warden",
            "width": 12,
            "height": 9,
            "party_cells": (
                GridCell(1, 2),
                GridCell(1, 4),
                GridCell(1, 6),
                GridCell(2, 8),
            ),
            "enemy_cells": (
                GridCell(10, 4),
                GridCell(9, 1),
                GridCell(9, 7),
            ),
            "enemies": (
                {
                    "actor_id": "actor:hollow-warden",
                    "name": "The Hollow Warden",
                    "team_tag": "team:vault-warden",
                    "hit_points": 42,
                    "dexterity": 12,
                    "armor_class": 16,
                    "strength": 17,
                },
                {
                    "actor_id": "actor:lantern-shade-a",
                    "name": "Lantern Shade",
                    "team_tag": "team:vault-warden",
                    "hit_points": 12,
                    "dexterity": 15,
                    "armor_class": 13,
                    "strength": 10,
                },
                {
                    "actor_id": "actor:lantern-shade-b",
                    "name": "Lantern Shade",
                    "team_tag": "team:vault-warden",
                    "hit_points": 12,
                    "dexterity": 15,
                    "armor_class": 13,
                    "strength": 10,
                },
            ),
            "terrain": (
                TerrainCell(
                    GridCell(5, 2),
                    terrain_id="terrain:vault-dais",
                    elevation_feet=5,
                    cover=CoverLevel.HALF,
                ),
                TerrainCell(
                    GridCell(5, 6),
                    terrain_id="terrain:vault-dais",
                    elevation_feet=5,
                    cover=CoverLevel.HALF,
                ),
                TerrainCell(
                    GridCell(6, 4),
                    terrain_id="terrain:vault-seal",
                    blocks_movement=True,
                    cover=CoverLevel.THREE_QUARTERS,
                ),
                TerrainCell(
                    GridCell(7, 4),
                    terrain_id="terrain:vault-shadow-wall",
                    blocks_movement=True,
                    blocks_los=True,
                    obstacle_height_feet=15,
                    cover=CoverLevel.TOTAL,
                ),
            ),
        },
    }
    try:
        raw = specs[encounter_id]
    except KeyError as exc:
        raise ValidationError(
            f"no authored tactical template exists for {encounter_id!r}"
        ) from exc
    # A narrow cast-free normalization keeps the public builder simple and the
    # authored table immutable-by-convention.
    return dict(raw)
