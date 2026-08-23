# engine/src/godot_dnd_engine/world_bridge.py
"""v1.0 bridge host adding the authoritative playable campaign/world runtime."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from collections.abc import Mapping
from dataclasses import replace
from typing import Any

from .actors import ActorState
from .character_bridge import CharacterClientBridgeSession
from .character_creator import (
    CharacterCreatorRuntime,
    CharacterCreatorService,
    demo_character_catalog,
)
from .client_bridge import (
    MAX_MESSAGE_BYTES,
    PROTOCOL_VERSION,
    ClientBridgeServer,
    _command_from_dict,
    _require_mapping,
    _response,
)
from .engine import SimulationEngine
from .errors import SequenceError, ValidationError
from .rules import Ability
from .serialization import dumps_canonical
from .spell_slice import SpellEnabledTacticalSession
from .world import EncounterGate, WorldRuntime, demo_campaign, restore_world_runtime
from .world.tactical_templates import (
    WORLD_PARTY_TEAM,
    create_world_spell_tactical_session,
)

WORLD_CAPABILITIES = (
    "world.runtime.v1",
    "world.commands.v1",
    "world.queries.v1",
    "world.save-replay.v1",
    "inventory.equipment-options.v1",
    "dialogue.v1",
    "quests.v1",
    "shops.v1",
)
BLOCKED_DURING_TACTICAL = frozenset(
    {
        "world.travel",
        "world.resolve_interaction",
        "world.rest",
        "dialogue.start",
        "dialogue.choose",
        "shop.buy",
        "shop.sell",
        "inventory.equip",
    }
)


class WorldClientBridgeSession(CharacterClientBridgeSession):
    """Character/spell/tactical bridge plus one isolated authoritative campaign stream."""

    def __init__(
        self,
        engine: SimulationEngine,
        tactical: SpellEnabledTacticalSession | None,
        creator: CharacterCreatorService,
        world: WorldRuntime,
    ) -> None:
        super().__init__(engine, tactical, creator)
        self.world = world
        self.active_world_encounter_id: str | None = None

    def capabilities(self) -> tuple[str, ...]:
        return (*super().capabilities(), *WORLD_CAPABILITIES)

    def _command(self, request: dict[str, Any]) -> dict[str, object]:
        payload = _require_mapping(request["payload"], "command payload")
        command_data = _require_mapping(payload.get("command"), "command")
        command = _command_from_dict(command_data)
        if command.command_type.startswith(
            ("world.", "dialogue.", "shop.", "inventory.")
        ):
            if command.campaign_id != self.engine.state.campaign_id:
                raise ValidationError(
                    "world command campaign does not match bridge campaign"
                )
            if command.command_type == "world.load":
                return self._load_world(
                    request,
                    command.expected_sequence,
                    command.payload,
                )
            if command.command_type == "world.begin_encounter":
                return self._begin_encounter(
                    request,
                    command.expected_sequence,
                    command.payload,
                )
            if (
                self.active_world_encounter_id is not None
                and command.command_type in BLOCKED_DURING_TACTICAL
            ):
                raise ValidationError(
                    "finish the active tactical encounter before changing world state"
                )
            world_payload = dict(command.payload)
            if command.command_type == "world.resolve_interaction":
                world_payload["bonus"] = self._authoritative_interaction_bonus(
                    world_payload
                )
            if command.command_type == "inventory.equip":
                self._require_equipment_compatibility(world_payload)
            if command.command_type == "world.complete_encounter":
                encounter_id = _payload_id(
                    world_payload,
                    "encounter_id",
                )
                self._require_tactical_victory(encounter_id)
            result = self.world.handle_command(
                command.command_type,
                world_payload,
                expected_sequence=command.expected_sequence,
            )
            if command.command_type == "world.complete_encounter":
                self.active_world_encounter_id = None
            return _response(
                request,
                "command.accepted",
                payload={
                    "world_snapshot": result["snapshot"],
                    "world_events": result["events"],
                    "presentation_events": result["presentation_events"],
                    "result": {
                        "world_sequence": self.world.state.sequence,
                        "active_encounter_id": self.active_world_encounter_id,
                    },
                },
            )
        return super()._command(request)

    def _query(self, request: dict[str, Any]) -> dict[str, object]:
        payload = _require_mapping(request["payload"], "query payload")
        query_type = payload.get("query_type")
        query = _require_mapping(payload.get("query", {}), "query")
        if isinstance(query_type, str) and query_type.startswith(
            ("world.", "dialogue.", "shop.", "inventory.")
        ):
            if query_type == "world.snapshot":
                return _response(
                    request,
                    "query.result",
                    payload={"world_snapshot": self.world.snapshot()},
                )
            if query_type == "world.save":
                encoding = query.get("encoding", "structured")
                if encoding == "structured":
                    return _response(
                        request,
                        "query.result",
                        payload={"world_snapshot": self.world.snapshot()},
                    )
                if encoding == "lossless-json":
                    return _response(
                        request,
                        "query.result",
                        payload=_lossless_world_save_payload(self.world),
                    )
                raise ValidationError(
                    f"unsupported world.save encoding: {encoding!r}"
                )
            if query_type == "inventory.equipment_options":
                return _response(
                    request,
                    "query.result",
                    payload=self._equipment_options(),
                )
            result = self.world.query(query_type, query)
            if query_type == "world.actions":
                result = self._world_actions_with_bridge_state(result)
            return _response(request, "query.result", payload=result)
        return super()._query(request)

    def _world_actions_with_bridge_state(
        self,
        result: dict[str, object],
    ) -> dict[str, object]:
        rows = dict(result)
        current_area = self.world.state.current_area_id
        area = next(
            item
            for item in self.world.definition.areas
            if item.area_id == current_area
        )
        active_dialogue = self.world.state.active_dialogue is not None
        active_tactical = self.active_world_encounter_id is not None
        rows["area_name"] = area.name
        rows["area_tags"] = sorted(area.tags)
        if active_tactical:
            rows["exploration_prompt"] = (
                "Finish the active tactical encounter before continuing exploration."
            )
        elif active_dialogue:
            rows["exploration_prompt"] = (
                "Finish the current conversation before travelling or resting."
            )
        else:
            rows["exploration_prompt"] = (
                "Choose a destination, conversation, interaction, rest, shop action, or encounter."
            )

        travel_value = rows.get("travel", [])
        travel: list[dict[str, object]] = []
        if isinstance(travel_value, list):
            for value in travel_value:
                if not isinstance(value, dict):
                    continue
                row = dict(value)
                row["available"] = not active_dialogue and not active_tactical
                if active_tactical:
                    row["reason"] = "Finish the active tactical encounter first."
                elif active_dialogue:
                    row["reason"] = "Finish the active dialogue first."
                else:
                    row["reason"] = ""
                travel.append(row)
        rows["travel"] = travel

        rows["dialogues"] = (
            []
            if active_tactical
            else [
                {
                    "dialogue_id": dialogue.dialogue_id,
                    "name": dialogue.nodes[0].speaker,
                }
                for dialogue in self.world.definition.dialogues
                if dialogue.area_id == current_area
                and self._dialogue_available(dialogue.dialogue_id)
            ]
        )

        interaction_value = rows.get("interactions", [])
        interactions: list[dict[str, object]] = []
        if isinstance(interaction_value, list):
            for value in interaction_value:
                if not isinstance(value, dict):
                    continue
                row = dict(value)
                completed = bool(row.get("completed", False))
                row["available"] = not completed and not active_tactical
                if active_tactical:
                    row["reason"] = "Finish the active tactical encounter first."
                elif completed:
                    row["reason"] = "Already completed."
                else:
                    row["reason"] = ""
                interactions.append(row)
        rows["interactions"] = interactions

        encounters_value = rows.get("encounters", [])
        encounters: list[dict[str, object]] = []
        if isinstance(encounters_value, list):
            for value in encounters_value:
                if not isinstance(value, dict):
                    continue
                row = dict(value)
                active = row.get("encounter_id") == self.active_world_encounter_id
                row["active"] = active
                if active:
                    row["available"] = False
                    row["reason"] = "Tactical encounter is already active."
                elif active_tactical:
                    row["available"] = False
                    row["reason"] = "Finish the active tactical encounter first."
                elif not bool(row.get("available", False)):
                    row["reason"] = "Encounter prerequisites are not satisfied."
                else:
                    row["reason"] = ""
                encounters.append(row)
        rows["encounters"] = encounters

        shop_value = rows.get("shops", [])
        shops: list[dict[str, object]] = []
        inventory = self.world.state.inventory_map()
        if isinstance(shop_value, list):
            for shop_value_item in shop_value:
                if not isinstance(shop_value_item, dict):
                    continue
                shop = dict(shop_value_item)
                item_value = shop.get("items", [])
                items: list[dict[str, object]] = []
                if isinstance(item_value, list):
                    for item_value_item in item_value:
                        if not isinstance(item_value_item, dict):
                            continue
                        item = dict(item_value_item)
                        item_id = str(item.get("item_id", ""))
                        owned = int(inventory.get(item_id, 0))
                        stock_value = item.get("stock")
                        stock_available = (
                            stock_value is None or int(stock_value) > 0
                        )
                        price = int(item.get("buy_price", 0))
                        item["owned_quantity"] = owned
                        item["buy_available"] = (
                            not active_tactical
                            and stock_available
                            and price <= self.world.state.currency
                        )
                        if active_tactical:
                            item["buy_reason"] = (
                                "Finish the active tactical encounter first."
                            )
                        elif not stock_available:
                            item["buy_reason"] = "Out of stock."
                        elif price > self.world.state.currency:
                            item["buy_reason"] = "Not enough currency."
                        else:
                            item["buy_reason"] = ""
                        item["sell_available"] = owned > 0 and not active_tactical
                        if active_tactical:
                            item["sell_reason"] = (
                                "Finish the active tactical encounter first."
                            )
                        elif owned <= 0:
                            item["sell_reason"] = "Party does not own this item."
                        else:
                            item["sell_reason"] = ""
                        items.append(item)
                shop["items"] = items
                shops.append(shop)
        rows["shops"] = shops
        runtime_can_rest = bool(rows.get("can_rest", False))
        rows["can_rest"] = runtime_can_rest and not active_tactical
        if active_tactical:
            rows["rest_reason"] = "Finish the active tactical encounter first."
        elif active_dialogue:
            rows["rest_reason"] = "Finish the active dialogue first."
        else:
            rows["rest_reason"] = ""
        rows["premade_party_ids"] = sorted(self.creator.records)
        return rows

    def _equipment_options(self) -> dict[str, object]:
        inventory = self.world.state.inventory_map()
        compatibility = {
            item.item_id: item.slots
            for item in self.world.definition.equipment_compatibility
        }
        items: list[dict[str, object]] = []
        for item_id, quantity in sorted(inventory.items()):
            slots = compatibility.get(item_id, ())
            if quantity < 1 or not slots:
                continue
            items.append(
                {
                    "item_id": item_id,
                    "quantity": quantity,
                    "slots": [
                        {
                            "slot_id": slot_id,
                            "label": slot_id.split(":", 1)[-1].replace(
                                "_",
                                " ",
                            ).title(),
                        }
                        for slot_id in slots
                    ],
                }
            )
        return {
            "party_ids": list(self.world.state.party_ids),
            "items": items,
        }

    def _require_equipment_compatibility(
        self,
        payload: Mapping[str, Any],
    ) -> None:
        item_id = _payload_id(payload, "item_id")
        slot = _payload_id(payload, "slot")
        compatibility = next(
            (
                item
                for item in self.world.definition.equipment_compatibility
                if item.item_id == item_id
            ),
            None,
        )
        if compatibility is None or slot not in compatibility.slots:
            raise ValidationError(
                "item is not compatible with requested equipment slot"
            )

    def _dialogue_available(self, dialogue_id: str) -> bool:
        dialogue = next(
            item
            for item in self.world.definition.dialogues
            if item.dialogue_id == dialogue_id
        )
        start = next(
            item
            for item in dialogue.nodes
            if item.node_id == dialogue.start_node_id
        )
        if not start.choices:
            return True
        flags = self.world.state.flags
        return any(
            choice.required_flags.issubset(flags)
            and not choice.forbidden_flags.intersection(flags)
            for choice in start.choices
        )

    def _begin_encounter(
        self,
        request: dict[str, Any],
        expected_sequence: int | None,
        payload: Mapping[str, Any],
    ) -> dict[str, object]:
        self._require_world_sequence(expected_sequence)
        encounter_id = _payload_id(payload, "encounter_id")
        gate = self._world_encounter(encounter_id)
        self._require_gate_available(gate)
        if self.spell_tactical is None:
            raise ValidationError("tactical provider is unavailable")
        if self.active_world_encounter_id is not None:
            if self.spell_tactical.tactical.encounter.status.value != "ended":
                raise ValidationError(
                    "finish or lose the active tactical encounter first"
                )
        previous_sequence = self.spell_tactical.sequence
        party_actors = self._party_tactical_actors()
        self.spell_tactical = create_world_spell_tactical_session(
            encounter_id=encounter_id,
            party_actors=party_actors,
            campaign_id=self.engine.state.campaign_id,
            session_id=self.engine.state.session_id,
            seed=self._encounter_seed(encounter_id),
        )
        self.spell_tactical.tactical.sequence = previous_sequence + 1
        self.active_world_encounter_id = encounter_id
        tactical_snapshot = self.spell_tactical.snapshot()
        return _response(
            request,
            "command.accepted",
            payload={
                "snapshot": tactical_snapshot,
                "world_snapshot": self.world.snapshot(),
                "world_events": [],
                "presentation_events": [],
                "result": {
                    "world_sequence": self.world.state.sequence,
                    "active_encounter_id": encounter_id,
                    "tactical_encounter_id": (
                        self.spell_tactical.tactical.encounter.encounter_id
                    ),
                    "tactical_sequence": self.spell_tactical.sequence,
                    "tactical_party_ids": [actor.actor_id for actor in party_actors],
                },
            },
        )

    def _load_world(
        self,
        request: dict[str, Any],
        expected_sequence: int | None,
        payload: Mapping[str, Any],
    ) -> dict[str, object]:
        if self.active_world_encounter_id is not None:
            raise ValidationError(
                "finish the active tactical encounter before loading world state"
            )
        self._require_world_sequence(expected_sequence)
        snapshot_value = _world_snapshot_from_load_payload(payload)
        self.world = restore_world_runtime(
            self.world.definition,
            snapshot_value,
        )
        self.active_world_encounter_id = None
        return _response(
            request,
            "command.accepted",
            payload={
                "world_snapshot": self.world.snapshot(),
                "world_events": [],
                "presentation_events": [],
                "result": {
                    "world_sequence": self.world.state.sequence,
                    "active_encounter_id": None,
                },
            },
        )

    def _require_world_sequence(self, expected_sequence: int | None) -> None:
        if (
            expected_sequence is not None
            and expected_sequence != self.world.state.sequence
        ):
            raise SequenceError(
                "expected world sequence does not match active world"
            )

    def _authoritative_interaction_bonus(
        self,
        payload: dict[str, object],
    ) -> int:
        party = self.world.state.party_ids
        actor_id_value = payload.get("actor_id")
        actor_id = (
            actor_id_value.strip()
            if isinstance(actor_id_value, str) and actor_id_value.strip()
            else (party[0] if party else "")
        )
        if actor_id not in party:
            raise ValidationError(
                "interaction actor must belong to the active party"
            )
        interaction_id = payload.get("interaction_id")
        interaction = next(
            (
                item
                for item in self.world.definition.interactions
                if item.interaction_id == interaction_id
            ),
            None,
        )
        if interaction is None:
            raise ValidationError("unknown interaction")
        record = self.creator.records.get(actor_id)
        if record is None:
            return 0
        try:
            ability = Ability(interaction.ability)
        except ValueError as exc:
            raise ValidationError(
                "interaction references unsupported ability"
            ) from exc
        return record.actor.ability_score(ability).modifier

    def _world_encounter(self, encounter_id: str) -> EncounterGate:
        gate = next(
            (
                item
                for item in self.world.definition.encounters
                if item.encounter_id == encounter_id
            ),
            None,
        )
        if gate is None:
            raise ValidationError("unknown world encounter")
        return gate

    def _require_gate_available(self, gate: EncounterGate) -> None:
        if gate.area_id != self.world.state.current_area_id:
            raise ValidationError(
                "world encounter is not in the current area"
            )
        if gate.encounter_id in self.world.state.completed_encounters:
            raise ValidationError("world encounter is already complete")
        if not gate.required_flags.issubset(self.world.state.flags):
            raise ValidationError(
                "world encounter prerequisites are not satisfied"
            )

    def _party_tactical_actors(self) -> tuple[ActorState, ...]:
        if not self.world.state.party_ids:
            raise ValidationError("start the world campaign with a party before combat")
        actors: list[ActorState] = []
        missing: list[str] = []
        for actor_id in self.world.state.party_ids:
            record = self.creator.records.get(actor_id)
            if record is None:
                missing.append(actor_id)
                continue
            actors.append(record.actor)
        if missing:
            raise ValidationError(
                "active party character records are unavailable: "
                + ", ".join(sorted(missing))
            )
        return tuple(actors)

    def _encounter_seed(self, encounter_id: str) -> int:
        material = (
            f"{self.engine.state.campaign_id}|{encounter_id}|"
            f"{self.world.state.sequence}"
        ).encode("utf-8")
        digest = hashlib.sha256(material).digest()
        return int.from_bytes(digest[:8], "big")

    def _require_tactical_victory(self, encounter_id: str) -> None:
        if self.active_world_encounter_id != encounter_id:
            raise ValidationError(
                "tactical result is not bound to requested world encounter"
            )
        if self.spell_tactical is None:
            raise ValidationError(
                "world encounter completion requires a tactical provider"
            )
        status = self.spell_tactical.tactical.encounter.status.value
        if status != "ended":
            raise ValidationError(
                "finish the active tactical encounter before recording victory"
            )
        winner = self._tactical_winner_team()
        if winner != WORLD_PARTY_TEAM:
            self.active_world_encounter_id = None
            raise ValidationError(
                "the party did not win the bound tactical encounter"
            )

    def _tactical_winner_team(self) -> str | None:
        if self.spell_tactical is None:
            return None
        for event in reversed(self.spell_tactical.tactical.recent_events):
            if event.get("type") != "tactical.encounter_ended":
                continue
            payload = event.get("payload")
            if not isinstance(payload, dict):
                return None
            winner = payload.get("winner_team")
            return winner if isinstance(winner, str) else None
        return None


async def serve(
    *,
    host: str,
    port: int,
    campaign_id: str,
    session_id: str,
    seed: int,
    vertical_slice: bool = True,
) -> None:
    engine = SimulationEngine.create(
        campaign_id=campaign_id,
        session_id=session_id,
        seed=seed,
    )
    tactical = (
        SpellEnabledTacticalSession.create(
            campaign_id=campaign_id,
            session_id=session_id,
            seed=seed,
        )
        if vertical_slice
        else None
    )
    creator = CharacterCreatorService(
        CharacterCreatorRuntime(demo_character_catalog())
    )
    _seed_premade_characters(creator)
    definition = replace(demo_campaign(), campaign_id=campaign_id)
    world = WorldRuntime(definition, seed=seed)
    bridge = ClientBridgeServer(
        WorldClientBridgeSession(engine, tactical, creator, world)
    )
    server = await asyncio.start_server(
        bridge.handle_client,
        host,
        port,
        limit=MAX_MESSAGE_BYTES + 1,
    )
    addresses = ", ".join(
        str(sock.getsockname()) for sock in server.sockets or ()
    )
    print(
        f"Godot client bridge v{PROTOCOL_VERSION} + playable RPG "
        f"listening on {addresses}"
    )
    async with server:
        await server.serve_forever()


def _lossless_world_save_payload(world: WorldRuntime) -> dict[str, object]:
    snapshot = world.snapshot()
    area = next(
        item
        for item in world.definition.areas
        if item.area_id == world.state.current_area_id
    )
    return {
        "world_snapshot_json": dumps_canonical(snapshot),
        "save_metadata": {
            "campaign_id": world.definition.campaign_id,
            "sequence": world.state.sequence,
            "area_id": area.area_id,
            "area_name": area.name,
        },
    }


def _world_snapshot_from_load_payload(
    payload: Mapping[str, Any],
) -> dict[str, object]:
    if "world_snapshot_json" not in payload:
        return dict(
            _require_mapping(
                payload.get("world_snapshot"),
                "world_snapshot",
            )
        )
    serialized = payload.get("world_snapshot_json")
    if not isinstance(serialized, str) or not serialized.strip():
        raise ValidationError(
            "world_snapshot_json must be a non-empty JSON string"
        )
    if len(serialized.encode("utf-8")) > MAX_MESSAGE_BYTES:
        raise ValidationError("world_snapshot_json exceeds bridge size limit")
    try:
        decoded = json.loads(serialized)
    except json.JSONDecodeError as exc:
        raise ValidationError("world_snapshot_json is malformed JSON") from exc
    return dict(_require_mapping(decoded, "world_snapshot_json"))


def _ability_scores(
    strength: int,
    dexterity: int,
    constitution: int,
    intelligence: int,
    wisdom: int,
    charisma: int,
) -> dict[str, int]:
    return {
        "strength": strength,
        "dexterity": dexterity,
        "constitution": constitution,
        "intelligence": intelligence,
        "wisdom": wisdom,
        "charisma": charisma,
    }


def _seed_premade_characters(creator: CharacterCreatorService) -> None:
    rows = (
        (
            "actor:premade-mira",
            "Mira Quill",
            "species:stonekin",
            "background:wayfarer",
            "class:guardian",
            "skill:athletics",
            "skill:perception",
            "equipment:defender-kit",
            "featurechoice:interpose",
            _ability_scores(15, 12, 14, 8, 13, 10),
        ),
        (
            "actor:premade-aster",
            "Aster Vale",
            "species:riverborn",
            "background:archivist",
            "class:scholar",
            "skill:arcana",
            "skill:perception",
            "equipment:explorer-kit",
            "spellchoice:echo-burst",
            _ability_scores(8, 14, 13, 15, 12, 10),
        ),
        (
            "actor:premade-tovan",
            "Tovan Reed",
            "species:riverborn",
            "background:wayfarer",
            "class:guardian",
            "skill:athletics",
            "skill:insight",
            "equipment:defender-kit",
            "featurechoice:interpose",
            _ability_scores(14, 15, 13, 8, 12, 10),
        ),
        (
            "actor:premade-sable",
            "Sable Fen",
            "species:stonekin",
            "background:archivist",
            "class:scholar",
            "skill:arcana",
            "skill:insight",
            "equipment:explorer-kit",
            "spellchoice:echo-burst",
            _ability_scores(8, 13, 14, 15, 12, 10),
        ),
    )
    for (
        actor_id,
        name,
        species,
        background,
        class_id,
        skill_one,
        skill_two,
        equipment,
        feature,
        ability_scores,
    ) in rows:
        creator.command(
            "characters.create",
            {
                "actor_id": actor_id,
                "name": name,
                "selected_choice_ids": [
                    species,
                    background,
                    class_id,
                    skill_one,
                    skill_two,
                    equipment,
                    feature,
                ],
                "ability_method_id": "standard-array",
                "ability_scores": ability_scores,
                "appearance": {},
                "biography": (
                    "Premade hero for the Lanterns Below adventure."
                ),
                "personality": "Ready for adventure.",
            },
        )


def _payload_id(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{key} must be a non-empty string")
    return value.strip()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the v1.0 playable RPG bridge"
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4765)
    parser.add_argument("--campaign-id", default="campaign:local-dev")
    parser.add_argument("--session-id", default="session:local-dev")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument(
        "--core-only",
        action="store_true",
        help=(
            "Disable tactical/spell provider while retaining creator and world "
            "services"
        ),
    )
    args = parser.parse_args()
    asyncio.run(
        serve(
            host=args.host,
            port=args.port,
            campaign_id=args.campaign_id,
            session_id=args.session_id,
            seed=args.seed,
            vertical_slice=not args.core_only,
        )
    )


if __name__ == "__main__":
    main()
