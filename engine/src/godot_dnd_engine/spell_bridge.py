# engine/src/godot_dnd_engine/spell_bridge.py
"""v0.8 bridge host that adds spell services to the v0.7 tactical provider."""

from __future__ import annotations

import argparse
import asyncio
from typing import Any

from .client_bridge import (
    BASE_CAPABILITIES,
    MAX_MESSAGE_BYTES,
    PROTOCOL_VERSION,
    ClientBridgeServer,
    ClientBridgeSession,
    _command_from_dict,
    _rejected,
    _require_mapping,
    _response,
)
from .engine import SimulationEngine
from .spell_slice import SPELL_SLICE_CAPABILITIES, SpellEnabledTacticalSession
from .vertical_slice import VERTICAL_SLICE_CAPABILITIES


class SpellClientBridgeSession(ClientBridgeSession):
    """Bridge session with one spell-enabled authoritative tactical provider."""

    def __init__(
        self,
        engine: SimulationEngine,
        tactical: SpellEnabledTacticalSession | None,
    ) -> None:
        super().__init__(engine=engine, tactical=None)
        self.spell_tactical = tactical

    def capabilities(self) -> tuple[str, ...]:
        if self.spell_tactical is None:
            return BASE_CAPABILITIES
        return (
            *BASE_CAPABILITIES,
            *VERTICAL_SLICE_CAPABILITIES,
            *SPELL_SLICE_CAPABILITIES,
        )

    def _command(self, request: dict[str, Any]) -> dict[str, object]:
        payload = _require_mapping(request["payload"], "command payload")
        command_data = _require_mapping(payload.get("command"), "command")
        command = _command_from_dict(command_data)
        if self.spell_tactical is not None and command.command_type.startswith("tactical."):
            result = self.spell_tactical.handle_command(command)
            return _response(
                request,
                "command.accepted",
                payload={
                    "snapshot": result.snapshot,
                    "presentation_events": list(result.presentation_events),
                    "result": result.result,
                },
            )
        if self.spell_tactical is not None:
            return _rejected(
                request,
                "command.rejected",
                "unsupported",
                "That action is not supported in the tactical session",
                f"unsupported tactical command: {command.command_type!r}",
            )
        return super()._command(request)

    def _query(self, request: dict[str, Any]) -> dict[str, object]:
        payload = _require_mapping(request["payload"], "query payload")
        query_type = payload.get("query_type")
        query = _require_mapping(payload.get("query", {}), "query")
        if not isinstance(query_type, str) or not query_type:
            return super()._query(request)
        if query_type in {"bridge.resync", "bridge.snapshot"}:
            return _response(
                request,
                "query.result",
                payload={"snapshot": self._authoritative_snapshot()},
            )
        if query_type == "bridge.capabilities":
            return _response(
                request,
                "query.result",
                payload={"capabilities": list(self.capabilities())},
            )
        if self.spell_tactical is not None and query_type.startswith(
            ("tactical.", "spatial.", "spells.")
        ):
            return _response(
                request,
                "query.result",
                payload=self.spell_tactical.query(query_type, query),
            )
        return super()._query(request)

    def _preview(self, request: dict[str, Any]) -> dict[str, object]:
        payload = _require_mapping(request["payload"], "preview payload")
        preview_type = payload.get("preview_type")
        preview = _require_mapping(payload.get("preview", {}), "preview")
        if not isinstance(preview_type, str) or not preview_type:
            return super()._preview(request)
        if self.spell_tactical is not None and (
            preview_type.startswith(("tactical.", "spatial."))
            or preview_type == "spells.preview"
        ):
            return _response(
                request,
                "preview.result",
                payload=self.spell_tactical.preview(preview_type, preview),
            )
        return super()._preview(request)

    def _authoritative_snapshot(self) -> dict[str, object]:
        if self.spell_tactical is not None:
            return self.spell_tactical.snapshot()
        return super()._authoritative_snapshot()


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
    bridge = ClientBridgeServer(SpellClientBridgeSession(engine, tactical))
    server = await asyncio.start_server(
        bridge.handle_client,
        host,
        port,
        limit=MAX_MESSAGE_BYTES + 1,
    )
    addresses = ", ".join(str(sock.getsockname()) for sock in server.sockets or ())
    print(f"Godot client bridge v{PROTOCOL_VERSION} + spells listening on {addresses}")
    async with server:
        await server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the v0.8 Godot spell client bridge")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4765)
    parser.add_argument("--campaign-id", default="campaign:local-dev")
    parser.add_argument("--session-id", default="session:local-dev")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument(
        "--core-only",
        action="store_true",
        help="Disable tactical/spell providers and expose only the core engine",
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
