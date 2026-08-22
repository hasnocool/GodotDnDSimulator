# engine/src/godot_dnd_engine/world_bridge.py
"""v1.0 bridge host adding the authoritative playable campaign/world runtime."""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import replace
from typing import Any

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
from .errors import ValidationError
from .rules import Ability
from .spell_slice import SpellEnabledTacticalSession
from .world import WorldRuntime, demo_campaign

WORLD_CAPABILITIES = (
    "world.runtime.v1",
    "world.commands.v1",
    "world.queries.v1",
    "world.save-replay.v1",
    "dialogue.v1",
    "quests.v1",
    "shops.v1",
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

    def capabilities(self) -> tuple[str, ...]:
        return (*super().capabilities(), *WORLD_CAPABILITIES)

    def _command(self, request: dict[str, Any]) -> dict[str, object]:
        payload = _require_mapping(request["payload"], "command payload")
        command_data = _require_mapping(payload.get("command"), "command")
        command = _command_from_dict(command_data)
        if command.command_type.startswith(("world.", "dialogue.", "shop.", "inventory.")):
            if command.campaign_id != self.engine.state.campaign_id:
                raise ValidationError("world command campaign does not match bridge campaign")
            world_payload = dict(command.payload)
            if command.command_type == "world.resolve_interaction":
                world_payload["bonus"] = self._authoritative_interaction_bonus(world_payload)
            if command.command_type == "world.complete_encounter":
                self._require_tactical_victory()
            result = self.world.handle_command(
                command.command_type,
                world_payload,
                expected_sequence=command.expected_sequence,
            )
            if command.command_type == "world.complete_encounter" and self.spell_tactical is not None:
                self.spell_tactical = SpellEnabledTacticalSession.create(
                    campaign_id=self.engine.state.campaign_id,
                    session_id=self.engine.state.session_id,
                    seed=1000 + self.world.state.sequence,
                )
            return _response(
                request,
                "command.accepted",
                payload={
                    "world_snapshot": result["snapshot"],
                    "world_events": result["events"],
                    "presentation_events": result["presentation_events"],
                    "result": {"world_sequence": self.world.state.sequence},
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
            result = self.world.query(query_type, query)
            if query_type == "world.snapshot":
                snapshot = result.get("snapshot")
                return _response(
                    request,
                    "query.result",
                    payload={"world_snapshot": snapshot},
                )
            if query_type == "world.actions":
                result = dict(result)
                result["dialogues"] = [
                    {
                        "dialogue_id": dialogue.dialogue_id,
                        "name": dialogue.nodes[0].speaker,
                    }
                    for dialogue in self.world.definition.dialogues
                ]
            return _response(request, "query.result", payload=result)
        return super()._query(request)

    def _authoritative_interaction_bonus(self, payload: dict[str, object]) -> int:
        party = self.world.state.party_ids
        actor_id_value = payload.get("actor_id")
        actor_id = (
            actor_id_value.strip()
            if isinstance(actor_id_value, str) and actor_id_value.strip()
            else (party[0] if party else "")
        )
        if actor_id not in party:
            raise ValidationError("interaction actor must belong to the active party")
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
            raise ValidationError("interaction references unsupported ability") from exc
        return record.actor.ability_score(ability).modifier

    def _require_tactical_victory(self) -> None:
        if self.spell_tactical is None:
            raise ValidationError("world encounter completion requires a tactical provider")
        status = self.spell_tactical.tactical.encounter.status.value
        if status != "ended":
            raise ValidationError("finish the current tactical encounter before recording victory")


async def serve(
    *,
    host: str,
    port: int,
    campaign_id: str,
    session_id: str,
    seed: int,
    vertical_slice: bool = True,
) -> None:
    engine = SimulationEngine.create(campaign_id=campaign_id, session_id=session_id, seed=seed)
    tactical = (
        SpellEnabledTacticalSession.create(
            campaign_id=campaign_id,
            session_id=session_id,
            seed=seed,
        )
        if vertical_slice
        else None
    )
    creator = CharacterCreatorService(CharacterCreatorRuntime(demo_character_catalog()))
    definition = replace(demo_campaign(), campaign_id=campaign_id)
    world = WorldRuntime(definition, seed=seed)
    bridge = ClientBridgeServer(WorldClientBridgeSession(engine, tactical, creator, world))
    server = await asyncio.start_server(
        bridge.handle_client,
        host,
        port,
        limit=MAX_MESSAGE_BYTES + 1,
    )
    addresses = ", ".join(str(sock.getsockname()) for sock in server.sockets or ())
    print(f"Godot client bridge v{PROTOCOL_VERSION} + playable RPG listening on {addresses}")
    async with server:
        await server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the v1.0 playable RPG bridge")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4765)
    parser.add_argument("--campaign-id", default="campaign:local-dev")
    parser.add_argument("--session-id", default="session:local-dev")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument(
        "--core-only",
        action="store_true",
        help="Disable tactical/spell provider while retaining creator and world services",
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
