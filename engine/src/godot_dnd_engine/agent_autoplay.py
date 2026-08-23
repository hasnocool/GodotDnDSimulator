# engine/src/godot_dnd_engine/agent_autoplay.py
"""Deterministic baseline agent that completes the Lanterns Below test campaign."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from .agent_api import AgentAction, AgentControlMode
from .agent_world_bridge import AgentWorldClientBridgeSession
from .character_creator import (
    CharacterCreatorRuntime,
    CharacterCreatorService,
    demo_character_catalog,
)
from .diagnostics import JsonlDiagnosticWriter
from .engine import SimulationEngine
from .spell_slice import SpellEnabledTacticalSession
from .world import WorldRuntime, demo_campaign
from .world_bridge import _seed_premade_characters

_PREMADE_PARTY = (
    "actor:premade-mira",
    "actor:premade-aster",
    "actor:premade-tovan",
    "actor:premade-sable",
)


@dataclass(frozen=True, slots=True)
class AutoplayStep:
    index: int
    context: str
    action_id: str
    command_type: str
    actor_id: str | None
    label: str
    world_sequence: int
    tactical_sequence: int | None

    def to_dict(self) -> dict[str, object]:
        return {
            "index": self.index,
            "context": self.context,
            "action_id": self.action_id,
            "command_type": self.command_type,
            "actor_id": self.actor_id,
            "label": self.label,
            "world_sequence": self.world_sequence,
            "tactical_sequence": self.tactical_sequence,
        }


@dataclass(frozen=True, slots=True)
class AutoplayResult:
    completed: bool
    reason: str
    steps: tuple[AutoplayStep, ...]
    final_observation: dict[str, object]

    def summary(self) -> dict[str, object]:
        world = self.final_observation.get("world", {})
        world_dict = world if isinstance(world, dict) else {}
        return {
            "completed": self.completed,
            "reason": self.reason,
            "step_count": len(self.steps),
            "world_sequence": world_dict.get("sequence"),
            "area": world_dict.get("area"),
            "flags": world_dict.get("flags", []),
            "completed_encounters": world_dict.get("completed_encounters", []),
        }


@dataclass(slots=True)
class LanternsBelowAutoplayPolicy:
    """Simple deterministic policy intended for regression testing, not optimal play."""

    market_bought: bool = False
    market_equipped: bool = False
    market_rested: bool = False
    market_sold: bool = False

    def choose(self, observation: dict[str, object]) -> AgentAction | None:
        action_rows = _action_rows(observation.get("legal_actions"))
        if not action_rows:
            return None
        if observation.get("context") == "tactical":
            return self._choose_tactical(observation, action_rows)
        return self._choose_world(observation, action_rows)

    def after_action(self, action: AgentAction) -> None:
        if action.command_type == "shop.buy" and action.payload.get("item_id") == "item:rope-coil":
            self.market_bought = True
        elif (
            action.command_type == "inventory.equip"
            and action.payload.get("item_id") == "item:rope-coil"
        ):
            self.market_equipped = True
        elif action.command_type == "world.rest":
            self.market_rested = True
        elif action.command_type == "shop.sell" and action.payload.get("item_id") == "item:rope-coil":
            self.market_sold = True

    def _choose_tactical(
        self,
        observation: dict[str, object],
        actions: list[AgentAction],
    ) -> AgentAction:
        tactical_value = observation.get("tactical", {})
        tactical = tactical_value if isinstance(tactical_value, dict) else {}
        current_actor_id = str(tactical.get("current_actor_id", ""))
        actors = _dict_rows(tactical.get("actors"))
        current = next(
            (row for row in actors if row.get("actor_id") == current_actor_id),
            {},
        )
        current_team = str(current.get("team", "neutral"))
        if current_team != "party":
            return _prefer(actions, command_type="tactical.end_turn") or actions[0]

        arc_lance = next(
            (
                action
                for action in actions
                if action.command_type == "tactical.cast_spell"
                and action.metadata.get("spell_id") == "spell:arc-lance"
            ),
            None,
        )
        if arc_lance is not None:
            return arc_lance
        strike = _prefer(actions, command_type="tactical.attack")
        if strike is not None:
            return strike
        movement = [item for item in actions if item.command_type == "tactical.move"]
        if movement:
            return min(
                movement,
                key=lambda item: self._movement_score(item, actors, current_team),
            )
        return _prefer(actions, command_type="tactical.end_turn") or actions[0]

    def _movement_score(
        self,
        action: AgentAction,
        actors: list[dict[str, object]],
        current_team: str,
    ) -> tuple[int, int, str]:
        destination = action.payload.get("destination", {})
        if not isinstance(destination, dict):
            return (1_000_000, 1_000_000, action.action_id)
        x = int(destination.get("x", 0))
        y = int(destination.get("y", 0))
        distances = []
        for actor in actors:
            if (
                str(actor.get("team", "neutral")) == current_team
                or str(actor.get("life_state", "")) == "dead"
            ):
                continue
            position = actor.get("position", {})
            if not isinstance(position, dict):
                continue
            distances.append(
                max(
                    abs(x - int(position.get("x", 0))),
                    abs(y - int(position.get("y", 0))),
                )
            )
        distance = min(distances) if distances else 1_000_000
        return (
            distance,
            int(action.metadata.get("cost_feet", 0)),
            action.action_id,
        )

    def _choose_world(
        self,
        observation: dict[str, object],
        actions: list[AgentAction],
    ) -> AgentAction:
        world_value = observation.get("world", {})
        world = world_value if isinstance(world_value, dict) else {}
        party_ids = world.get("party_ids", [])
        if not isinstance(party_ids, list) or not party_ids:
            return _prefer(actions, command_type="world.start") or actions[0]

        active_dialogue = world.get("active_dialogue")
        if isinstance(active_dialogue, dict):
            dialogue_id = str(active_dialogue.get("dialogue_id", ""))
            node_id = str(active_dialogue.get("node_id", ""))
            if dialogue_id == "dialogue:warden-ilar":
                choice = (
                    "choice:accept-quarry"
                    if node_id == "node:warden-intro"
                    else "choice:leave-warden"
                )
                return _prefer_payload(actions, "dialogue.choose", "choice_id", choice) or actions[0]
            if dialogue_id == "dialogue:surveyor-echo":
                return (
                    _prefer_payload(
                        actions,
                        "dialogue.choose",
                        "choice_id",
                        "choice:keep-lantern",
                    )
                    or actions[0]
                )
            return actions[0]

        flags = _string_set(world.get("flags"))
        completed_interactions = _string_set(world.get("completed_interactions"))
        completed_encounters = _string_set(world.get("completed_encounters"))
        area_value = world.get("area", {})
        area = area_value if isinstance(area_value, dict) else {}
        area_id = str(area.get("area_id", ""))

        if area_id == "area:reedhollow-square":
            if "flag:quarry-mission" not in flags:
                return (
                    _prefer_payload(
                        actions,
                        "dialogue.start",
                        "dialogue_id",
                        "dialogue:warden-ilar",
                    )
                    or actions[0]
                )
            if not self.market_sold:
                return _prefer_payload(actions, "world.travel", "area_id", "area:market-row") or actions[0]
            return _prefer_payload(actions, "world.travel", "area_id", "area:old-road") or actions[0]

        if area_id == "area:market-row":
            if not self.market_bought:
                return (
                    _prefer_payload(actions, "shop.buy", "item_id", "item:rope-coil")
                    or actions[0]
                )
            if not self.market_equipped:
                return (
                    _prefer_payload(
                        actions,
                        "inventory.equip",
                        "item_id",
                        "item:rope-coil",
                    )
                    or actions[0]
                )
            if not self.market_rested:
                return _prefer(actions, command_type="world.rest") or actions[0]
            if not self.market_sold:
                return (
                    _prefer_payload(actions, "shop.sell", "item_id", "item:rope-coil")
                    or actions[0]
                )
            return (
                _prefer_payload(
                    actions,
                    "world.travel",
                    "area_id",
                    "area:reedhollow-square",
                )
                or actions[0]
            )

        if area_id == "area:old-road":
            if "interaction:collapsed-marker" not in completed_interactions:
                return (
                    _prefer_payload(
                        actions,
                        "world.resolve_interaction",
                        "interaction_id",
                        "interaction:collapsed-marker",
                    )
                    or actions[0]
                )
            if "encounter:road-ambush" not in completed_encounters:
                return (
                    _prefer_payload(
                        actions,
                        "world.begin_encounter",
                        "encounter_id",
                        "encounter:road-ambush",
                    )
                    or actions[0]
                )
            return _prefer_payload(actions, "world.travel", "area_id", "area:quarry-mouth") or actions[0]

        if area_id == "area:quarry-mouth":
            if "interaction:flooded-gate" not in completed_interactions:
                return (
                    _prefer_payload(
                        actions,
                        "world.resolve_interaction",
                        "interaction_id",
                        "interaction:flooded-gate",
                    )
                    or actions[0]
                )
            if "encounter:quarry-watchers" not in completed_encounters:
                return (
                    _prefer_payload(
                        actions,
                        "world.begin_encounter",
                        "encounter_id",
                        "encounter:quarry-watchers",
                    )
                    or actions[0]
                )
            return _prefer_payload(actions, "world.travel", "area_id", "area:underworks") or actions[0]

        if area_id == "area:underworks":
            if "interaction:survey-lantern" not in completed_interactions:
                return (
                    _prefer_payload(
                        actions,
                        "world.resolve_interaction",
                        "interaction_id",
                        "interaction:survey-lantern",
                    )
                    or actions[0]
                )
            if "interaction:stonefall-trigger" not in completed_interactions:
                return (
                    _prefer_payload(
                        actions,
                        "world.resolve_interaction",
                        "interaction_id",
                        "interaction:stonefall-trigger",
                    )
                    or actions[0]
                )
            if "flag:lantern-kept" not in flags and "flag:echo-freed" not in flags:
                return (
                    _prefer_payload(
                        actions,
                        "dialogue.start",
                        "dialogue_id",
                        "dialogue:surveyor-echo",
                    )
                    or actions[0]
                )
            if "encounter:underworks-swarm" not in completed_encounters:
                return (
                    _prefer_payload(
                        actions,
                        "world.begin_encounter",
                        "encounter_id",
                        "encounter:underworks-swarm",
                    )
                    or actions[0]
                )
            return _prefer_payload(actions, "world.travel", "area_id", "area:lantern-vault") or actions[0]

        if area_id == "area:lantern-vault":
            if "encounter:vault-warden" not in completed_encounters:
                return (
                    _prefer_payload(
                        actions,
                        "world.begin_encounter",
                        "encounter_id",
                        "encounter:vault-warden",
                    )
                    or actions[0]
                )
        return actions[0]


def create_autoplay_session(
    *,
    seed: int = 7,
    diagnostics: JsonlDiagnosticWriter | None = None,
) -> AgentWorldClientBridgeSession:
    campaign_id = "campaign:lanterns-below"
    session_id = "session:agent-autoplay"
    engine = SimulationEngine.create(
        campaign_id=campaign_id,
        session_id=session_id,
        seed=seed,
    )
    tactical = SpellEnabledTacticalSession.create(
        campaign_id=campaign_id,
        session_id=session_id,
        seed=seed,
    )
    creator = CharacterCreatorService(
        CharacterCreatorRuntime(demo_character_catalog())
    )
    _seed_premade_characters(creator)
    world = WorldRuntime(replace(demo_campaign(), campaign_id=campaign_id), seed=seed)
    return AgentWorldClientBridgeSession(
        engine,
        tactical,
        creator,
        world,
        diagnostics=diagnostics,
    )


def run_lanterns_below_autoplay(
    *,
    seed: int = 7,
    max_steps: int = 2_000,
    diagnostics: JsonlDiagnosticWriter | None = None,
) -> AutoplayResult:
    if max_steps < 1:
        raise ValueError("max_steps must be >= 1")
    session = create_autoplay_session(seed=seed, diagnostics=diagnostics)
    for actor_id in _PREMADE_PARTY:
        session.agent.controllers.set_control(
            actor_id,
            AgentControlMode.AGENT,
            policy_id="baseline-party",
        )
    policy = LanternsBelowAutoplayPolicy()
    steps: list[AutoplayStep] = []

    for index in range(1, max_steps + 1):
        observation = session.agent.observe()
        world_value = observation.get("world", {})
        world = world_value if isinstance(world_value, dict) else {}
        if "flag:campaign-complete" in _string_set(world.get("flags")):
            return AutoplayResult(True, "campaign complete", tuple(steps), observation)

        if observation.get("context") == "tactical":
            current_actor = observation.get("current_actor_id")
            if isinstance(current_actor, str) and current_actor:
                tactical_value = observation.get("tactical", {})
                tactical = tactical_value if isinstance(tactical_value, dict) else {}
                actors = _dict_rows(tactical.get("actors"))
                row = next(
                    (item for item in actors if item.get("actor_id") == current_actor),
                    {},
                )
                team = str(row.get("team", "neutral"))
                session.agent.controllers.set_control(
                    current_actor,
                    AgentControlMode.AGENT,
                    policy_id=(
                        "baseline-party"
                        if team == "party"
                        else "baseline-passive-npc"
                    ),
                )

        action = policy.choose(observation)
        if action is None:
            return AutoplayResult(
                False,
                "no legal action available before campaign completion",
                tuple(steps),
                observation,
            )
        session.agent.execute(action.action_id)
        policy.after_action(action)
        tactical_sequence = (
            session.spell_tactical.sequence
            if session.active_world_encounter_id is not None
            and session.spell_tactical is not None
            else None
        )
        step = AutoplayStep(
            index=index,
            context=action.context,
            action_id=action.action_id,
            command_type=action.command_type,
            actor_id=action.actor_id,
            label=action.label,
            world_sequence=session.world.state.sequence,
            tactical_sequence=tactical_sequence,
        )
        steps.append(step)
        if diagnostics is not None:
            diagnostics.write("autoplay", "step", **step.to_dict())

    final_observation = session.agent.observe()
    return AutoplayResult(
        False,
        f"step limit reached ({max_steps})",
        tuple(steps),
        final_observation,
    )


def _action_rows(value: object) -> list[AgentAction]:
    if not isinstance(value, list):
        return []
    rows: list[AgentAction] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        payload = item.get("payload", {})
        metadata = item.get("metadata", {})
        if not isinstance(payload, dict) or not isinstance(metadata, dict):
            continue
        rows.append(
            AgentAction(
                action_id=str(item.get("action_id", "")),
                label=str(item.get("label", "")),
                command_type=str(item.get("command_type", "")),
                actor_id=(
                    str(item["actor_id"])
                    if isinstance(item.get("actor_id"), str)
                    else None
                ),
                payload=dict(payload),
                expected_sequence=int(item.get("expected_sequence", 0)),
                context=str(item.get("context", "")),
                metadata=dict(metadata),
            )
        )
    return rows


def _dict_rows(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _string_set(value: object) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {str(item) for item in value}


def _prefer(
    actions: list[AgentAction],
    *,
    command_type: str,
) -> AgentAction | None:
    return next((item for item in actions if item.command_type == command_type), None)


def _prefer_payload(
    actions: list[AgentAction],
    command_type: str,
    key: str,
    value: object,
) -> AgentAction | None:
    return next(
        (
            item
            for item in actions
            if item.command_type == command_type and item.payload.get(key) == value
        ),
        None,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run deterministic AI playthrough of the Lanterns Below test campaign"
    )
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--max-steps", type=int, default=2_000)
    parser.add_argument("--log-dir", default=".logs/godot-dnd")
    parser.add_argument(
        "--no-disk-log",
        action="store_true",
        help="Disable structured autoplay JSONL diagnostics",
    )
    parser.add_argument(
        "--trace-json",
        default="",
        help="Optional output path for the complete deterministic action trace",
    )
    args = parser.parse_args()
    diagnostics = (
        None
        if args.no_disk_log
        else JsonlDiagnosticWriter.for_directory(args.log_dir, prefix="autoplay")
    )
    try:
        result = run_lanterns_below_autoplay(
            seed=args.seed,
            max_steps=args.max_steps,
            diagnostics=diagnostics,
        )
    finally:
        if diagnostics is not None:
            diagnostics.close()
    if args.trace_json:
        path = Path(args.trace_json)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "summary": result.summary(),
                    "steps": [item.to_dict() for item in result.steps],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    print(json.dumps(result.summary(), sort_keys=True))
    raise SystemExit(0 if result.completed else 1)


if __name__ == "__main__":
    main()
