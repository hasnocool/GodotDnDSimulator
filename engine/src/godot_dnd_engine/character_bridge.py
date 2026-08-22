# engine/src/godot_dnd_engine/character_bridge.py
"""v0.9 bridge host adding character creation and level-up services."""

from __future__ import annotations

import argparse
import asyncio
from typing import Any

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
from .spell_bridge import SpellClientBridgeSession
from .spell_slice import SpellEnabledTacticalSession

CHARACTER_CREATOR_CAPABILITIES = (
    "characters.creator.v1",
    "characters.creator.commands.v1",
    "characters.levelup.v1",
)


class CharacterClientBridgeSession(SpellClientBridgeSession):
    """Spell-aware bridge plus an independent rules-driven creator service."""

    def __init__(
        self,
        engine: SimulationEngine,
        tactical: SpellEnabledTacticalSession | None,
        creator: CharacterCreatorService,
    ) -> None:
        super().__init__(engine, tactical)
        self.creator = creator

    def capabilities(self) -> tuple[str, ...]:
        return (*super().capabilities(), *CHARACTER_CREATOR_CAPABILITIES)

    def _command(self, request: dict[str, Any]) -> dict[str, object]:
        payload = _require_mapping(request["payload"], "command payload")
        command_data = _require_mapping(payload.get("command"), "command")
        command = _command_from_dict(command_data)
        if command.command_type.startswith("characters."):
            result = self.creator.command(
                command.command_type,
                dict(command.payload),
            )
            return _response(
                request,
                "command.accepted",
                payload={"result": result},
            )
        return super()._command(request)

    def _query(self, request: dict[str, Any]) -> dict[str, object]:
        payload = _require_mapping(request["payload"], "query payload")
        query_type = payload.get("query_type")
        query = _require_mapping(payload.get("query", {}), "query")
        if isinstance(query_type, str) and query_type.startswith("characters."):
            return _response(
                request,
                "query.result",
                payload=self.creator.query(query_type, dict(query)),
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
    bridge = ClientBridgeServer(
        CharacterClientBridgeSession(engine, tactical, creator)
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
        f"Godot client bridge v{PROTOCOL_VERSION} + character creator "
        f"listening on {addresses}"
    )
    async with server:
        await server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the v0.9 Godot character creator bridge"
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
            "Disable tactical/spell providers while retaining character "
            "creator services"
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
