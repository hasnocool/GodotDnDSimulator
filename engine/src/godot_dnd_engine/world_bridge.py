# engine/src/godot_dnd_engine/world_bridge.py
"""v1.0 bridge host adding the authoritative playable campaign/world runtime."""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import replace
from typing import Any

from .character_bridge import CharacterClientBridgeSession
from .character_creator import CharacterCreatorRuntime, CharacterCreatorService, demo_character_catalog
from .client_bridge import MAX_MESSAGE_BYTES, PROTOCOL_VERSION, ClientBridgeServer, _command_from_dict, _require_mapping, _response
from .engine import SimulationEngine
from .errors import ValidationError
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
    """Character/spell/tactical bridge plus one authoritative campaign runtime."""

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
            result = self.world.handle_command(
                command.command_type,
                command.payload,
                expected_sequence=command.expected_sequence,
            )
            return _response(
                request,
                "command.accepted",
                payload={
                    "snapshot": result["snapshot"],
                    "events": result["events"],
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
            return _response(
                request,
                "query.result",
                payload=self.world.query(query_type, query),
            )
        return super()._query(request)


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
