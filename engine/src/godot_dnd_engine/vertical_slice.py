# engine/src/godot_dnd_engine/vertical_slice.py
"""Authoritative composite session for the v0.7 Godot tactical vertical slice."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .actors import (
    ActorKind,
    ActorState,
    DefenseState,
    HitPoints,
    MovementMode,
    MovementSpeed,
    SizeCategory,
)
from .combat import (
    ActionResource,
    AttackDefinition,
    CombatRuntime,
    EncounterState,
    EncounterStatus,
    LifeState,
    ZeroHitPointRule,
)
from .dice import DiceExpression
from .errors import SequenceError, UnsupportedCommandError, ValidationError
from .models import CommandEnvelope
from .rng import DeterministicRNG
from .rules import Ability, AbilityScore, ProficiencyRank
from .spatial import (
    CoverLevel,
    GridCell,
    MovementPolicy,
    SpatialPlacement,
    SpatialQueryService,
    SpatialRuntime,
    SpatialState,
    SquareGridSpace,
    TerrainCell,
    cover_between_entities,
    line_of_sight_between_entities,
    placement_in_reach,
)
from .spatial.integration import move_in_encounter

VERTICAL_SLICE_CAPABILITIES = (
    "tactical.vertical-slice.v1",
    "tactical.commands.v1",
    "tactical.queries.v1",
    "spatial.queries.v1",
    "spatial.previews.v1",
)


@dataclass(frozen=True, slots=True)
class TacticalCommandResult:
    snapshot: dict[str, object]
    presentation_events: tuple[dict[str, object], ...]
    result: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class TacticalVerticalSliceSession:
    campaign_id: str
    session_id: str
    rng: DeterministicRNG
    combat_runtime: CombatRuntime
    spatial_runtime: SpatialRuntime
    encounter: EncounterState
    spatial: SpatialState
    actors: tuple[ActorState, ...]
    sequence: int = 0
    recent_events: list[dict[str, object]] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        *,
        campaign_id: str,
        session_id: str,
        seed: int = 7,
    ) -> TacticalVerticalSliceSession:
        rng = DeterministicRNG.from_seed(seed)
        combat_runtime = CombatRuntime(rng)
        spatial_runtime = SpatialRuntime()
        actors = _demo_actors()
        encounter = combat_runtime.create_encounter(
            "encounter:sunken-courtyard",
            actors,
            zero_hp_rules={
                actor.actor_id: ZeroHitPointRule.MONSTER for actor in actors
            },
        )
        encounter = combat_runtime.start_encounter(encounter).state
        spatial = SpatialState(
            _demo_space(),
            (
                SpatialPlacement(
                    "actor:ember",
                    GridCell(1, 2),
                    tags=frozenset({"team:ember"}),
                ),
                SpatialPlacement(
                    "actor:shale",
                    GridCell(6, 3),
                    tags=frozenset({"team:shale"}),
                ),
            ),
        )
        return cls(
            campaign_id=campaign_id,
            session_id=session_id,
            rng=rng,
            combat_runtime=combat_runtime,
            spatial_runtime=spatial_runtime,
            encounter=encounter,
            spatial=spatial,
            actors=actors,
        )

    def snapshot(self) -> dict[str, object]:
        rng_state, rng_increment = self.rng.snapshot()
        return {
            "schema_version": 1,
            "state": {
                "campaign_id": self.campaign_id,
                "session_id": self.session_id,
                "sequence": self.sequence,
                "tick": self.sequence,
                "mode": "tactical_vertical_slice",
                "tactical": self._tactical_state(),
            },
            "rng": {
                "algorithm": self.rng.ALGORITHM,
                "state": rng_state,
                "increment": rng_increment,
            },
        }

    def query(self, query_type: str, payload: Mapping[str, Any]) -> dict[str, object]:
        query = dict(payload)
        if query_type == "tactical.snapshot":
            return {"snapshot": self.snapshot()}
        if query_type == "tactical.actions":
            return self._available_actions(query)
        if query_type == "tactical.attack_preview":
            return self._attack_preview(query)
        if query_type.startswith("spatial."):
            return self._spatial_query(query_type, query)
        raise UnsupportedCommandError(f"unsupported tactical query: {query_type!r}")

    def preview(
        self,
        preview_type: str,
        payload: Mapping[str, Any],
    ) -> dict[str, object]:
        preview = dict(payload)
        if preview_type == "tactical.attack":
            return self._attack_preview(preview)
        if preview_type.startswith("spatial."):
            return self._spatial_query(preview_type, preview)
        raise UnsupportedCommandError(
            f"unsupported tactical preview: {preview_type!r}"
        )

    def handle_command(self, command: CommandEnvelope) -> TacticalCommandResult:
        self._validate_command_envelope(command)
        if command.command_type == "tactical.move":
            return self._move(command)
        if command.command_type == "tactical.attack":
            return self._attack(command)
        if command.command_type == "tactical.end_turn":
            return self._end_turn(command)
        raise UnsupportedCommandError(
            f"unsupported vertical-slice command: {command.command_type!r}"
        )

    def _validate_command_envelope(self, command: CommandEnvelope) -> None:
        if command.campaign_id != self.campaign_id:
            raise ValidationError("tactical command campaign does not match active slice")
        if command.session_id != self.session_id:
            raise ValidationError("tactical command session does not match active slice")
        if command.expected_sequence is not None:
            if command.expected_sequence != self.sequence:
                raise SequenceError(
                    "expected tactical sequence "
                    f"{command.expected_sequence}, current {self.sequence}"
                )
        if command.actor_id is None:
            raise ValidationError("tactical commands require actor_id")
        if command.actor_id != self.encounter.current_actor_id:
            raise ValidationError("tactical command actor is not the current turn actor")

    def _move(self, command: CommandEnvelope) -> TacticalCommandResult:
        actor_id = command.actor_id
        assert actor_id is not None
        destination = _payload_cell(command.payload, "destination")
        mode = _payload_mode(
            command.payload.get("movement_mode", MovementMode.WALK.value)
        )
        before = self.spatial.placement(actor_id).anchor
        combined = move_in_encounter(
            spatial_runtime=self.spatial_runtime,
            combat_runtime=self.combat_runtime,
            spatial_state=self.spatial,
            encounter_state=self.encounter,
            actor_id=actor_id,
            destination=destination,
            movement_mode=mode,
        )
        self.spatial = combined.spatial.state
        self.encounter = combined.combat.state
        movement_remaining = self.encounter.combatant(
            actor_id
        ).economy.movement_remaining
        event = {
            "type": "tactical.actor_moved",
            "actor_id": actor_id,
            "payload": {
                "from": _cell_dict(before),
                "to": _cell_dict(destination),
                "path": [
                    _cell_dict(cell) for cell in combined.spatial.path.path
                ],
                "cost_feet": combined.spatial.path.cost_feet,
                "movement_mode": mode.value,
                "movement_remaining": movement_remaining,
            },
        }
        return self._accepted(
            (event,),
            {"cost_feet": combined.spatial.path.cost_feet},
        )

    def _attack(self, command: CommandEnvelope) -> TacticalCommandResult:
        attacker_id = command.actor_id
        assert attacker_id is not None
        target_id = _payload_string(command.payload, "target_id")
        preview = self._attack_preview(
            {"attacker_id": attacker_id, "target_id": target_id}
        )
        if not bool(preview["legal"]):
            raise ValidationError(str(preview["reason"]))
        transition, result = self.combat_runtime.perform_attack(
            self.encounter,
            attacker_id=attacker_id,
            target_id=target_id,
            attack=_training_strike(),
        )
        self.encounter = transition.state
        target = self.encounter.combatant(target_id)
        adjusted_damage = (
            0
            if result.damage_adjustment is None
            else result.damage_adjustment.adjusted_amount
        )
        events: list[dict[str, object]] = [
            {
                "type": "tactical.attack_resolved",
                "actor_id": attacker_id,
                "target_id": target_id,
                "payload": {
                    "attack_id": result.attack_id,
                    "natural_roll": result.d20.selected_roll,
                    "total": result.d20.total,
                    "hit": result.hit,
                    "critical": result.critical,
                    "damage": adjusted_damage,
                    "hp_after": target.actor.hit_points.current,
                    "life_state": target.life_state.value,
                },
            }
        ]
        winner = self._winning_team()
        if winner is not None and self.encounter.status is EncounterStatus.ACTIVE:
            self.encounter = self.combat_runtime.end_encounter(
                self.encounter
            ).state
            events.append(
                {
                    "type": "tactical.encounter_ended",
                    "payload": {"winner_team": winner},
                }
            )
        return self._accepted(
            tuple(events),
            {
                "hit": result.hit,
                "critical": result.critical,
                "damage": adjusted_damage,
            },
        )

    def _end_turn(self, command: CommandEnvelope) -> TacticalCommandResult:
        actor_id = command.actor_id
        assert actor_id is not None
        self.encounter = self.combat_runtime.end_turn(
            self.encounter,
            actor_id,
        ).state
        event = {
            "type": "tactical.turn_started",
            "actor_id": self.encounter.current_actor_id,
            "payload": {
                "round_number": self.encounter.round_number,
                "turn_index": self.encounter.turn_index,
            },
        }
        return self._accepted((event,))

    def _accepted(
        self,
        events: tuple[dict[str, object], ...],
        result: dict[str, object] | None = None,
    ) -> TacticalCommandResult:
        self.sequence += 1
        stamped: list[dict[str, object]] = []
        for raw_event in events:
            event = dict(raw_event)
            event["sequence"] = self.sequence
            stamped.append(event)
            self.recent_events.append(event)
        if len(self.recent_events) > 40:
            del self.recent_events[:-40]
        return TacticalCommandResult(
            snapshot=self.snapshot(),
            presentation_events=tuple(stamped),
            result={} if result is None else dict(result),
        )

    def _available_actions(self, payload: Mapping[str, Any]) -> dict[str, object]:
        actor_id = payload.get("actor_id", self.encounter.current_actor_id)
        if not isinstance(actor_id, str) or not actor_id:
            raise ValidationError("actor_id must be a non-empty string")
        combatant = self.encounter.combatant(actor_id)
        current = actor_id == self.encounter.current_actor_id
        conscious = combatant.life_state is LifeState.CONSCIOUS
        economy = combatant.economy
        move_enabled = current and conscious and economy.movement_remaining > 0
        attack_enabled = current and conscious and economy.action_available
        end_enabled = (
            current
            and conscious
            and self.encounter.status is EncounterStatus.ACTIVE
        )
        return {
            "actor_id": actor_id,
            "current_actor_id": self.encounter.current_actor_id,
            "actions": [
                {
                    "action_id": "move",
                    "label": "Move",
                    "enabled": move_enabled,
                    "reason": "" if move_enabled else "No movement available",
                },
                {
                    "action_id": "training_strike",
                    "label": "Strike",
                    "enabled": attack_enabled,
                    "reason": (
                        "" if attack_enabled else "Action is not available"
                    ),
                },
                {
                    "action_id": "end_turn",
                    "label": "End Turn",
                    "enabled": end_enabled,
                    "reason": (
                        ""
                        if end_enabled
                        else "Only the current conscious actor can end the turn"
                    ),
                },
            ],
        }

    def _attack_preview(self, payload: Mapping[str, Any]) -> dict[str, object]:
        attacker_id = _payload_string(payload, "attacker_id")
        target_id = _payload_string(payload, "target_id")
        attacker = self.encounter.combatant(attacker_id)
        target = self.encounter.combatant(target_id)
        distance = self._query_service().execute(
            "spatial.distance",
            {
                "source_entity_id": attacker_id,
                "target_entity_id": target_id,
            },
        )
        los = line_of_sight_between_entities(
            self.spatial,
            attacker_id,
            target_id,
        )
        cover = cover_between_entities(
            self.spatial,
            attacker_id,
            target_id,
        )
        in_reach = placement_in_reach(
            self.spatial,
            attacker_id,
            target_id,
            5,
        )
        reason = ""
        legal = True
        if self.encounter.status is not EncounterStatus.ACTIVE:
            legal = False
            reason = "Encounter is not active"
        elif attacker_id != self.encounter.current_actor_id:
            legal = False
            reason = "Attacker is not the current turn actor"
        elif attacker.life_state is not LifeState.CONSCIOUS:
            legal = False
            reason = "Attacker cannot act"
        elif target.life_state is LifeState.DEAD:
            legal = False
            reason = "Target is no longer active"
        elif not attacker.economy.action_available:
            legal = False
            reason = "Action is not available"
        elif not in_reach:
            legal = False
            reason = "Target is outside strike reach"
        elif not los.visible:
            legal = False
            reason = "Target is not visible"
        return {
            "legal": legal,
            "reason": reason,
            "attacker_id": attacker_id,
            "target_id": target_id,
            "distance_feet": distance["distance_feet"],
            "reach_feet": 5,
            "visible": los.visible,
            "cover": cover.level.value,
            "cover_sources": list(cover.sources),
        }

    def _spatial_query(
        self,
        query_type: str,
        payload: Mapping[str, Any],
    ) -> dict[str, object]:
        query = dict(payload)
        actor_id = query.get("entity_id")
        if query_type in {"spatial.path", "spatial.reachable"}:
            if "budget_feet" not in query and isinstance(actor_id, str):
                query["budget_feet"] = self.encounter.combatant(
                    actor_id
                ).economy.movement_remaining
        return self._query_service().execute(query_type, query)

    def _query_service(self) -> SpatialQueryService:
        actors = tuple(
            combatant.actor for combatant in self.encounter.combatants
        )
        return SpatialQueryService(
            self.spatial,
            actors,
            MovementPolicy(
                allow_diagonal=True,
                prevent_corner_cutting=True,
            ),
        )

    def _tactical_state(self) -> dict[str, object]:
        combatants: list[dict[str, object]] = []
        for combatant in self.encounter.combatants:
            actor = combatant.actor
            placement = self.spatial.placement(actor.actor_id)
            combatants.append(
                {
                    "actor_id": actor.actor_id,
                    "name": actor.name,
                    "kind": actor.kind.value,
                    "size": actor.size.value,
                    "team": _team(actor),
                    "position": _cell_dict(placement.anchor),
                    "elevation_feet": self.spatial.space.cell(
                        placement.anchor
                    ).elevation_feet,
                    "hit_points": {
                        "current": actor.hit_points.current,
                        "maximum": actor.hit_points.maximum,
                        "temporary": actor.hit_points.temporary,
                    },
                    "armor_class": actor.defense.armor_class,
                    "life_state": combatant.life_state.value,
                    "conditions": [
                        item.condition_id for item in actor.conditions
                    ],
                    "movement_modes": [
                        {
                            "mode": movement.mode.value,
                            "speed_feet": movement.feet,
                        }
                        for movement in actor.movement
                    ],
                    "economy": {
                        "action_available": combatant.economy.action_available,
                        "bonus_action_available": (
                            combatant.economy.bonus_action_available
                        ),
                        "reaction_available": combatant.economy.reaction_available,
                        "movement_remaining": (
                            combatant.economy.movement_remaining
                        ),
                    },
                }
            )
        return {
            "slice_id": "vertical-slice:sunken-courtyard",
            "display_name": "Sunken Courtyard",
            "encounter_id": self.encounter.encounter_id,
            "status": self.encounter.status.value,
            "round_number": self.encounter.round_number,
            "turn_index": self.encounter.turn_index,
            "current_actor_id": self.encounter.current_actor_id,
            "initiative": [
                {"actor_id": row.actor_id, "total": row.total}
                for row in self.encounter.initiative
            ],
            "actors": combatants,
            "space": {
                "space_id": self.spatial.space.space_id,
                "width": self.spatial.space.width,
                "height": self.spatial.space.height,
                "cell_size_feet": self.spatial.space.cell_size_feet,
                "camera_bounds": {
                    "min_x": 0,
                    "min_y": 0,
                    "max_x": 7,
                    "max_y": 5,
                },
                "terrain": [
                    {
                        "x": item.cell.x,
                        "y": item.cell.y,
                        "terrain_id": item.terrain_id,
                        "elevation_feet": item.elevation_feet,
                        "difficult": item.difficult,
                        "blocks_movement": item.blocks_movement,
                        "blocks_los": item.blocks_los,
                        "cover": item.cover.value,
                    }
                    for item in self.spatial.space.terrain
                ],
            },
            "recent_events": [
                dict(item) for item in self.recent_events[-12:]
            ],
        }

    def _winning_team(self) -> str | None:
        living_teams = {
            _team(combatant.actor)
            for combatant in self.encounter.combatants
            if combatant.life_state is not LifeState.DEAD
        }
        if len(living_teams) == 1:
            return next(iter(living_teams))
        return None


def _demo_actors() -> tuple[ActorState, ...]:
    return (
        _actor(
            "actor:ember",
            "Ember Scout",
            "team:ember",
            dexterity=16,
            armor_class=14,
        ),
        _actor(
            "actor:shale",
            "Shale Warden",
            "team:shale",
            dexterity=12,
            armor_class=13,
        ),
    )


def _actor(
    actor_id: str,
    name: str,
    team_tag: str,
    *,
    dexterity: int,
    armor_class: int,
) -> ActorState:
    abilities = tuple(
        AbilityScore(
            ability,
            dexterity
            if ability is Ability.DEXTERITY
            else (14 if ability is Ability.STRENGTH else 12),
        )
        for ability in Ability
    )
    return ActorState(
        actor_id=actor_id,
        name=name,
        kind=ActorKind.NPC,
        size=SizeCategory.MEDIUM,
        proficiency_bonus=2,
        abilities=abilities,
        hit_points=HitPoints(18, 18),
        defense=DefenseState(armor_class),
        movement=(MovementSpeed(MovementMode.WALK, 30),),
        tags=frozenset({team_tag, "vertical-slice"}),
    )


def _demo_space() -> SquareGridSpace:
    terrain = (
        TerrainCell(
            GridCell(2, 2),
            terrain_id="terrain:shallow-water",
            difficult=True,
        ),
        TerrainCell(
            GridCell(2, 3),
            terrain_id="terrain:shallow-water",
            difficult=True,
        ),
        TerrainCell(
            GridCell(5, 2),
            terrain_id="terrain:raised-stone",
            elevation_feet=5,
        ),
        TerrainCell(
            GridCell(5, 3),
            terrain_id="terrain:raised-stone",
            elevation_feet=5,
        ),
        TerrainCell(
            GridCell(3, 1),
            terrain_id="terrain:broken-pillar",
            blocks_movement=True,
            cover=CoverLevel.THREE_QUARTERS,
        ),
        TerrainCell(
            GridCell(4, 4),
            terrain_id="terrain:broken-pillar",
            blocks_movement=True,
            cover=CoverLevel.THREE_QUARTERS,
        ),
        TerrainCell(
            GridCell(3, 4),
            terrain_id="terrain:screen-wall",
            blocks_movement=True,
            blocks_los=True,
            obstacle_height_feet=10,
            cover=CoverLevel.TOTAL,
        ),
    )
    return SquareGridSpace(
        "space:sunken-courtyard",
        width=8,
        height=6,
        cell_size_feet=5,
        terrain=terrain,
    )


def _training_strike() -> AttackDefinition:
    return AttackDefinition(
        attack_id="attack:training-strike",
        ability=Ability.STRENGTH,
        proficiency_rank=ProficiencyRank.FULL,
        damage_dice=DiceExpression(1, 6),
        damage_type="damage:training-impact",
        action_resource=ActionResource.ACTION,
    )


def _team(actor: ActorState) -> str:
    for tag in sorted(actor.tags):
        if tag.startswith("team:"):
            return tag.removeprefix("team:")
    return "neutral"


def _payload_string(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{key} must be a non-empty string")
    return value


def _payload_cell(payload: Mapping[str, Any], key: str) -> GridCell:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise ValidationError(f"{key} must be a cell object")
    x = value.get("x")
    y = value.get("y")
    if (
        isinstance(x, bool)
        or not isinstance(x, int)
        or isinstance(y, bool)
        or not isinstance(y, int)
    ):
        raise ValidationError(f"{key}.x/y must be integers")
    return GridCell(x, y)


def _payload_mode(value: Any) -> MovementMode:
    if not isinstance(value, str):
        raise ValidationError("movement_mode must be a string")
    try:
        return MovementMode(value)
    except ValueError as exc:
        raise ValidationError("movement_mode is unsupported") from exc


def _cell_dict(cell: GridCell) -> dict[str, int]:
    return {"x": cell.x, "y": cell.y}
