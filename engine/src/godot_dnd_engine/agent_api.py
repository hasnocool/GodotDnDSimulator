# engine/src/godot_dnd_engine/agent_api.py
"""Structured observation/legal-action API for AI players and test agents."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol

from .character_creator import CharacterCreatorService
from .client_bridge import PROTOCOL_VERSION
from .diagnostics import JsonlDiagnosticWriter
from .engine import SimulationEngine
from .errors import UnsupportedCommandError, ValidationError
from .ids import require_id
from .spell_slice import SpellEnabledTacticalSession
from .world import WorldRuntime

AGENT_CAPABILITIES = (
    "agent.observations.v1",
    "agent.legal-actions.v1",
    "agent.control.v1",
    "agent.execute.v1",
)


class AgentControlMode(str, Enum):
    HUMAN = "human"
    AGENT = "agent"


@dataclass(frozen=True, slots=True)
class AgentController:
    actor_id: str
    mode: AgentControlMode
    policy_id: str = "external"

    def to_dict(self) -> dict[str, object]:
        return {
            "actor_id": self.actor_id,
            "mode": self.mode.value,
            "policy_id": self.policy_id,
        }


@dataclass(frozen=True, slots=True)
class AgentAction:
    action_id: str
    label: str
    command_type: str
    actor_id: str | None
    payload: dict[str, object]
    expected_sequence: int
    context: str
    metadata: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "action_id": self.action_id,
            "label": self.label,
            "command_type": self.command_type,
            "actor_id": self.actor_id,
            "payload": dict(self.payload),
            "expected_sequence": self.expected_sequence,
            "context": self.context,
            "metadata": dict(self.metadata),
        }


class AgentHost(Protocol):
    engine: SimulationEngine
    world: WorldRuntime
    creator: CharacterCreatorService
    spell_tactical: SpellEnabledTacticalSession | None
    active_world_encounter_id: str | None

    def world_actions_for_client(self) -> dict[str, object]: ...

    def handle_message(self, message: dict[str, Any]) -> dict[str, object] | None: ...


class AgentControlRegistry:
    """Non-authoritative ownership metadata for human/AI control assignment."""

    def __init__(self) -> None:
        self._controllers: dict[str, AgentController] = {}

    def set_control(
        self,
        actor_id: str,
        mode: AgentControlMode,
        *,
        policy_id: str = "external",
    ) -> AgentController:
        actor_id = require_id(actor_id, "actor")
        if not isinstance(policy_id, str) or not policy_id.strip() or len(policy_id) > 128:
            raise ValidationError("policy_id must be a non-empty string <= 128 characters")
        controller = AgentController(actor_id, mode, policy_id.strip())
        self._controllers[actor_id] = controller
        return controller

    def controller_for(
        self,
        actor_id: str,
        *,
        party_ids: tuple[str, ...],
    ) -> AgentController:
        configured = self._controllers.get(actor_id)
        if configured is not None:
            return configured
        default_mode = (
            AgentControlMode.HUMAN
            if actor_id in party_ids
            else AgentControlMode.AGENT
        )
        default_policy = "human" if default_mode is AgentControlMode.HUMAN else "external"
        return AgentController(actor_id, default_mode, default_policy)


class AgentService:
    """AI/test facade that exposes only recomputed legal typed actions."""

    def __init__(
        self,
        host: AgentHost,
        *,
        diagnostics: JsonlDiagnosticWriter | None = None,
    ) -> None:
        self.host = host
        self.controllers = AgentControlRegistry()
        self.diagnostics = diagnostics
        self._execute_counter = 0

    def query(
        self,
        query_type: str,
        payload: dict[str, Any],
    ) -> dict[str, object]:
        if query_type == "agent.observe":
            return self.observe()
        if query_type == "agent.actions":
            return {"actions": [item.to_dict() for item in self.legal_actions()]}
        if query_type == "agent.controllers":
            return {"controllers": self._controller_rows()}
        raise UnsupportedCommandError(f"unsupported agent query: {query_type}")

    def command(
        self,
        command_type: str,
        payload: dict[str, Any],
    ) -> dict[str, object]:
        if command_type == "agent.set_control":
            actor_id = _string(payload.get("actor_id"), "actor_id")
            if actor_id not in self._known_actor_ids():
                raise ValidationError("agent control actor is not present in this session")
            mode_value = _string(payload.get("mode"), "mode")
            try:
                mode = AgentControlMode(mode_value)
            except ValueError as exc:
                raise ValidationError("agent control mode must be human or agent") from exc
            policy_id = payload.get("policy_id", "external")
            if not isinstance(policy_id, str):
                raise ValidationError("policy_id must be a string")
            controller = self.controllers.set_control(
                actor_id,
                mode,
                policy_id=policy_id,
            )
            self._log(
                "control.changed",
                actor_id=actor_id,
                mode=mode.value,
                policy_id=controller.policy_id,
            )
            return {"controller": controller.to_dict()}
        if command_type == "agent.execute":
            return self.execute(_string(payload.get("action_id"), "action_id"))
        raise UnsupportedCommandError(f"unsupported agent command: {command_type}")

    def observe(self) -> dict[str, object]:
        tactical = self._tactical_state()
        raw_current_actor_id = (
            tactical.get("current_actor_id") if tactical is not None else None
        )
        current_actor_id = (
            raw_current_actor_id.strip()
            if isinstance(raw_current_actor_id, str)
            else ""
        )
        current_controller: dict[str, object] | None = None
        if current_actor_id:
            current_controller = self.controllers.controller_for(
                current_actor_id,
                party_ids=self.host.world.state.party_ids,
            ).to_dict()
        actions = self.legal_actions()
        return {
            "schema_version": 1,
            "context": "tactical" if tactical is not None else "world",
            "campaign_id": self.host.engine.state.campaign_id,
            "session_id": self.host.engine.state.session_id,
            "world": self.host.world.state_to_dict(),
            "active_world_encounter_id": self.host.active_world_encounter_id,
            "tactical": tactical,
            "current_actor_id": current_actor_id or None,
            "current_controller": current_controller,
            "controllers": self._controller_rows(),
            "legal_actions": [item.to_dict() for item in actions],
        }

    def legal_actions(self) -> tuple[AgentAction, ...]:
        if self.host.active_world_encounter_id is not None and self.host.spell_tactical is not None:
            return self._tactical_actions()
        return self._world_actions()

    def execute(self, action_id: str) -> dict[str, object]:
        action = next(
            (item for item in self.legal_actions() if item.action_id == action_id),
            None,
        )
        if action is None:
            raise ValidationError("agent action token is stale, unknown, or no longer legal")
        if action.actor_id is not None:
            controller = self.controllers.controller_for(
                action.actor_id,
                party_ids=self.host.world.state.party_ids,
            )
            if controller.mode is not AgentControlMode.AGENT:
                raise ValidationError(
                    "actor is human-controlled; set agent control before executing its action"
                )
        self._execute_counter += 1
        command_id = f"command:agent-exec-{self._execute_counter}"
        request_id = f"agent-exec-{self._execute_counter}"
        inner = {
            "bridge_version": PROTOCOL_VERSION,
            "kind": "command.submit",
            "request_id": request_id,
            "correlation_id": action.action_id,
            "generation": 0,
            "payload": {
                "command": {
                    "command_id": command_id,
                    "campaign_id": self.host.engine.state.campaign_id,
                    "session_id": self.host.engine.state.session_id,
                    "command_type": action.command_type,
                    "payload": dict(action.payload),
                    "version": 1,
                    "actor_id": action.actor_id,
                    "expected_sequence": action.expected_sequence,
                }
            },
        }
        self._log(
            "action.execute",
            action_id=action.action_id,
            command_type=action.command_type,
            actor_id=action.actor_id,
            expected_sequence=action.expected_sequence,
        )
        response = self.host.handle_message(inner)
        if response is None:
            raise ValidationError("agent action produced no bridge response")
        if not bool(response.get("ok", False)):
            error_value = response.get("error", {})
            if isinstance(error_value, dict):
                detail = str(error_value.get("debug_detail", "agent action rejected"))
            else:
                detail = "agent action rejected"
            self._log("action.rejected", action_id=action.action_id, detail=detail)
            raise ValidationError(detail)
        self._log("action.accepted", action_id=action.action_id)
        payload_value = response.get("payload", {})
        result_payload = dict(payload_value) if isinstance(payload_value, dict) else {}
        return {
            "executed_action": action.to_dict(),
            "result": result_payload,
            "observation": self.observe(),
        }

    def _world_actions(self) -> tuple[AgentAction, ...]:
        sequence = self.host.world.state.sequence
        if not self.host.world.state.party_ids:
            party_ids = tuple(sorted(self.host.creator.records)[:4])
            if not party_ids:
                return ()
            return (
                self._action(
                    "Start campaign with premade party",
                    "world.start",
                    None,
                    {"party_ids": list(party_ids)},
                    sequence,
                    "world",
                    {"kind": "campaign_start"},
                ),
            )

        if self.host.world.state.active_dialogue is not None:
            dialogue = self.host.world.query("dialogue.current", {})
            choices_value = dialogue.get("choices", [])
            actions: list[AgentAction] = []
            if isinstance(choices_value, list):
                for row in choices_value:
                    if not isinstance(row, dict):
                        continue
                    choice_id = str(row.get("choice_id", ""))
                    if not choice_id:
                        continue
                    actions.append(
                        self._action(
                            f"Dialogue: {row.get('text', choice_id)}",
                            "dialogue.choose",
                            None,
                            {"choice_id": choice_id},
                            sequence,
                            "world",
                            {"kind": "dialogue_choice"},
                        )
                    )
            return tuple(actions)

        rows = self.host.world_actions_for_client()
        actions = []
        for row in _dict_rows(rows.get("dialogues")):
            dialogue_id = str(row.get("dialogue_id", ""))
            if dialogue_id:
                actions.append(
                    self._action(
                        f"Talk to {row.get('name', dialogue_id)}",
                        "dialogue.start",
                        None,
                        {"dialogue_id": dialogue_id},
                        sequence,
                        "world",
                        {"kind": "dialogue_start"},
                    )
                )
        for row in _dict_rows(rows.get("travel")):
            if not bool(row.get("available", True)):
                continue
            area_id = str(row.get("area_id", ""))
            if area_id:
                actions.append(
                    self._action(
                        f"Travel to {row.get('name', area_id)}",
                        "world.travel",
                        None,
                        {"area_id": area_id},
                        sequence,
                        "world",
                        {"kind": "travel"},
                    )
                )
        for row in _dict_rows(rows.get("interactions")):
            if not bool(row.get("available", not row.get("completed", False))):
                continue
            interaction_id = str(row.get("interaction_id", ""))
            if not interaction_id:
                continue
            for actor_id in self.host.world.state.party_ids:
                actions.append(
                    self._action(
                        f"{row.get('name', interaction_id)} as {actor_id}",
                        "world.resolve_interaction",
                        actor_id,
                        {"interaction_id": interaction_id, "actor_id": actor_id},
                        sequence,
                        "world",
                        {
                            "kind": "interaction",
                            "ability": str(row.get("ability", "")),
                            "dc": int(row.get("dc", 0)),
                        },
                    )
                )
        for row in _dict_rows(rows.get("encounters")):
            if not bool(row.get("available", False)):
                continue
            encounter_id = str(row.get("encounter_id", ""))
            if encounter_id:
                actions.append(
                    self._action(
                        f"Begin encounter: {row.get('name', encounter_id)}",
                        "world.begin_encounter",
                        None,
                        {"encounter_id": encounter_id},
                        sequence,
                        "world",
                        {"kind": "encounter", "boss": bool(row.get("boss", False))},
                    )
                )
        for shop in _dict_rows(rows.get("shops")):
            shop_id = str(shop.get("shop_id", ""))
            for item in _dict_rows(shop.get("items")):
                item_id = str(item.get("item_id", ""))
                if not shop_id or not item_id:
                    continue
                if bool(item.get("buy_available", False)):
                    actions.append(
                        self._action(
                            f"Buy {item_id}",
                            "shop.buy",
                            None,
                            {"shop_id": shop_id, "item_id": item_id, "quantity": 1},
                            sequence,
                            "world",
                            {"kind": "shop_buy", "price": int(item.get("buy_price", 0))},
                        )
                    )
                if bool(item.get("sell_available", False)):
                    actions.append(
                        self._action(
                            f"Sell {item_id}",
                            "shop.sell",
                            None,
                            {"shop_id": shop_id, "item_id": item_id, "quantity": 1},
                            sequence,
                            "world",
                            {"kind": "shop_sell", "price": int(item.get("sell_price", 0))},
                        )
                    )
        actions.extend(self._equipment_actions(sequence))
        if bool(rows.get("can_rest", False)):
            actions.append(
                self._action(
                    "Rest",
                    "world.rest",
                    None,
                    {},
                    sequence,
                    "world",
                    {"kind": "rest"},
                )
            )
        return tuple(actions)

    def _equipment_actions(self, sequence: int) -> list[AgentAction]:
        inventory = self.host.world.state.inventory_map()
        actions: list[AgentAction] = []
        for compatibility in self.host.world.definition.equipment_compatibility:
            if inventory.get(compatibility.item_id, 0) < 1:
                continue
            for actor_id in self.host.world.state.party_ids:
                for slot in compatibility.slots:
                    actions.append(
                        self._action(
                            f"Equip {compatibility.item_id} on {actor_id} ({slot})",
                            "inventory.equip",
                            actor_id,
                            {
                                "actor_id": actor_id,
                                "item_id": compatibility.item_id,
                                "slot": slot,
                            },
                            sequence,
                            "world",
                            {"kind": "equip"},
                        )
                    )
        return actions

    def _tactical_actions(self) -> tuple[AgentAction, ...]:
        tactical_session = self.host.spell_tactical
        if tactical_session is None:
            return ()
        sequence = tactical_session.sequence
        tactical = self._tactical_state()
        if tactical is None:
            return ()
        if str(tactical.get("status", "")) == "ended":
            encounter_id = self.host.active_world_encounter_id
            winner = self._winner_team(tactical_session)
            if encounter_id is not None and winner == "party":
                return (
                    self._action(
                        f"Record victory for {encounter_id}",
                        "world.complete_encounter",
                        None,
                        {"encounter_id": encounter_id},
                        self.host.world.state.sequence,
                        "world",
                        {"kind": "encounter_complete"},
                    ),
                )
            return ()

        actor_id = str(tactical.get("current_actor_id", ""))
        if not actor_id:
            return ()
        actors = _dict_rows(tactical.get("actors"))
        current = next((row for row in actors if row.get("actor_id") == actor_id), None)
        if current is None:
            return ()
        actions_info = tactical_session.query("tactical.actions", {"actor_id": actor_id})
        action_rows = _dict_rows(actions_info.get("actions"))
        enabled = {str(row.get("action_id", "")): bool(row.get("enabled", False)) for row in action_rows}
        actions: list[AgentAction] = []
        current_team = str(current.get("team", "neutral"))

        if enabled.get("training_strike", False):
            for target in actors:
                target_id = str(target.get("actor_id", ""))
                if (
                    not target_id
                    or target_id == actor_id
                    or str(target.get("team", "neutral")) == current_team
                    or str(target.get("life_state", "")) == "dead"
                ):
                    continue
                preview = tactical_session.preview(
                    "tactical.attack",
                    {"attacker_id": actor_id, "target_id": target_id},
                )
                if bool(preview.get("legal", False)):
                    actions.append(
                        self._action(
                            f"Strike {target_id}",
                            "tactical.attack",
                            actor_id,
                            {"target_id": target_id},
                            sequence,
                            "tactical",
                            {
                                "kind": "attack",
                                "target_id": target_id,
                                "distance_feet": preview.get("distance_feet"),
                                "cover": preview.get("cover"),
                            },
                        )
                    )
            actions.extend(self._spell_actions(actor_id, actors, current_team, sequence))

        if enabled.get("move", False):
            reachable = tactical_session.query(
                "spatial.reachable",
                {"entity_id": actor_id, "movement_mode": "walk"},
            )
            current_position = current.get("position")
            for row in _dict_rows(reachable.get("cells")):
                cell = row.get("cell")
                if not isinstance(cell, dict) or cell == current_position:
                    continue
                actions.append(
                    self._action(
                        f"Move to {cell.get('x')},{cell.get('y')}",
                        "tactical.move",
                        actor_id,
                        {"destination": dict(cell), "movement_mode": "walk"},
                        sequence,
                        "tactical",
                        {"kind": "move", "cost_feet": int(row.get("cost_feet", 0))},
                    )
                )
        if enabled.get("end_turn", False):
            actions.append(
                self._action(
                    "End turn",
                    "tactical.end_turn",
                    actor_id,
                    {},
                    sequence,
                    "tactical",
                    {"kind": "end_turn"},
                )
            )
        return tuple(actions)

    def _spell_actions(
        self,
        actor_id: str,
        actors: list[dict[str, object]],
        current_team: str,
        sequence: int,
    ) -> list[AgentAction]:
        tactical_session = self.host.spell_tactical
        if tactical_session is None:
            return []
        available = tactical_session.query("spells.available", {"actor_id": actor_id})
        results: list[AgentAction] = []
        for spell in _dict_rows(available.get("spells")):
            if not bool(spell.get("castable", False)):
                continue
            spell_id = str(spell.get("spell_id", ""))
            target_kind = str(spell.get("target_kind", ""))
            slot_levels = spell.get("slot_levels", [])
            if not spell_id or not isinstance(slot_levels, list):
                continue
            for raw_slot in slot_levels:
                if isinstance(raw_slot, bool) or not isinstance(raw_slot, int):
                    continue
                candidates: list[tuple[list[str], dict[str, int] | None]] = []
                if target_kind == "self":
                    candidates.append(([], None))
                elif target_kind == "creature":
                    for target in actors:
                        target_id = str(target.get("actor_id", ""))
                        if not target_id or str(target.get("life_state", "")) == "dead":
                            continue
                        candidates.append(([target_id], None))
                elif target_kind == "area":
                    for target in actors:
                        if str(target.get("team", "neutral")) == current_team:
                            continue
                        position = target.get("position")
                        if isinstance(position, dict):
                            candidates.append(([], {"x": int(position.get("x", 0)), "y": int(position.get("y", 0))}))
                for target_ids, point in candidates:
                    preview_payload: dict[str, object] = {
                        "caster_id": actor_id,
                        "spell_id": spell_id,
                        "slot_level": raw_slot,
                        "target_ids": target_ids,
                    }
                    if point is not None:
                        preview_payload["point"] = point
                    preview = tactical_session.preview("spells.preview", preview_payload)
                    if not bool(preview.get("legal", False)):
                        continue
                    command_payload = dict(preview_payload)
                    command_payload.pop("caster_id", None)
                    target_label = target_ids[0] if target_ids else (
                        f"{point['x']},{point['y']}" if point is not None else "self"
                    )
                    results.append(
                        self._action(
                            f"Cast {spell_id} (slot {raw_slot}) at {target_label}",
                            "tactical.cast_spell",
                            actor_id,
                            command_payload,
                            sequence,
                            "tactical",
                            {
                                "kind": "spell",
                                "spell_id": spell_id,
                                "slot_level": raw_slot,
                                "target_kind": target_kind,
                                "resolved_target_ids": preview.get("target_ids", []),
                            },
                        )
                    )
        return results

    def _action(
        self,
        label: str,
        command_type: str,
        actor_id: str | None,
        payload: dict[str, object],
        expected_sequence: int,
        context: str,
        metadata: dict[str, object],
    ) -> AgentAction:
        canonical = json.dumps(
            {
                "command_type": command_type,
                "actor_id": actor_id,
                "payload": payload,
                "sequence": expected_sequence,
                "context": context,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
        return AgentAction(
            action_id=f"agent-action:{expected_sequence}:{digest}",
            label=label,
            command_type=command_type,
            actor_id=actor_id,
            payload=payload,
            expected_sequence=expected_sequence,
            context=context,
            metadata=metadata,
        )

    def _tactical_state(self) -> dict[str, object] | None:
        if self.host.active_world_encounter_id is None or self.host.spell_tactical is None:
            return None
        snapshot = self.host.spell_tactical.snapshot()
        state = snapshot.get("state")
        if not isinstance(state, dict):
            return None
        tactical = state.get("tactical")
        return dict(tactical) if isinstance(tactical, dict) else None

    def _winner_team(self, tactical_session: SpellEnabledTacticalSession) -> str | None:
        for event in reversed(tactical_session.tactical.recent_events):
            if event.get("type") != "tactical.encounter_ended":
                continue
            payload = event.get("payload")
            if not isinstance(payload, dict):
                return None
            winner = payload.get("winner_team")
            return winner if isinstance(winner, str) else None
        return None

    def _known_actor_ids(self) -> tuple[str, ...]:
        actor_ids = set(self.host.creator.records)
        if self.host.spell_tactical is not None:
            actor_ids.update(
                combatant.actor.actor_id
                for combatant in self.host.spell_tactical.tactical.encounter.combatants
            )
        return tuple(sorted(actor_ids))

    def _controller_rows(self) -> list[dict[str, object]]:
        party_ids = self.host.world.state.party_ids
        return [
            self.controllers.controller_for(actor_id, party_ids=party_ids).to_dict()
            for actor_id in self._known_actor_ids()
        ]

    def _log(self, message: str, **fields: Any) -> None:
        if self.diagnostics is not None:
            self.diagnostics.write("agent", message, **fields)


def _dict_rows(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{label} must be a non-empty string")
    return value.strip()
