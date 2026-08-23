# engine/src/godot_dnd_engine/agent_world_bridge.py
"""Agent-aware playable-world bridge with structured disk diagnostics."""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from .agent_api import AGENT_CAPABILITIES, AgentService
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
from .diagnostics import JsonlDiagnosticWriter
from .engine import SimulationEngine
from .spell_slice import SpellEnabledTacticalSession
from .world import WorldRuntime, demo_campaign
from .world_bridge import WorldClientBridgeSession, _seed_premade_characters


class AgentWorldClientBridgeSession(WorldClientBridgeSession):
    """Playable-world bridge plus non-authoritative AI/test orchestration."""

    def __init__(
        self,
        engine: SimulationEngine,
        tactical: SpellEnabledTacticalSession | None,
        creator: CharacterCreatorService,
        world: WorldRuntime,
        *,
        diagnostics: JsonlDiagnosticWriter | None = None,
    ) -> None:
        super().__init__(engine, tactical, creator, world)
        self.agent = AgentService(self, diagnostics=diagnostics)

    def capabilities(self) -> tuple[str, ...]:
        return (*super().capabilities(), *AGENT_CAPABILITIES)

    def world_actions_for_client(self) -> dict[str, object]:
        return self._world_actions_with_bridge_state(
            self.world.query("world.actions", {})
        )

    def _query(self, request: dict[str, Any]) -> dict[str, object]:
        payload = _require_mapping(request["payload"], "query payload")
        query_type = payload.get("query_type")
        query = _require_mapping(payload.get("query", {}), "query")
        if isinstance(query_type, str) and query_type.startswith("agent."):
            return _response(
                request,
                "query.result",
                payload=self.agent.query(query_type, dict(query)),
            )
        return super()._query(request)

    def _command(self, request: dict[str, Any]) -> dict[str, object]:
        payload = _require_mapping(request["payload"], "command payload")
        command_data = _require_mapping(payload.get("command"), "command")
        command = _command_from_dict(command_data)
        if command.command_type.startswith("agent."):
            return _response(
                request,
                "command.accepted",
                payload=self.agent.command(
                    command.command_type,
                    dict(command.payload),
                ),
            )
        return super()._command(request)


@dataclass(slots=True)
class DiagnosticClientBridgeServer(ClientBridgeServer):
    diagnostics: JsonlDiagnosticWriter | None = None

    def _handle_line(self, line: bytes) -> dict[str, object] | None:
        request_kind = ""
        request_id = ""
        correlation_id = ""
        operation = ""
        try:
            decoded = json.loads(line.decode("utf-8"))
            if isinstance(decoded, dict):
                request_kind = str(decoded.get("kind", ""))
                request_id = str(decoded.get("request_id", ""))
                correlation_id = str(decoded.get("correlation_id", ""))
                payload = decoded.get("payload", {})
                if isinstance(payload, dict):
                    operation = str(
                        payload.get(
                            "query_type",
                            payload.get("preview_type", ""),
                        )
                    )
                    command = payload.get("command")
                    if isinstance(command, dict):
                        operation = str(command.get("command_type", operation))
        except (UnicodeDecodeError, json.JSONDecodeError):
            pass
        response = super()._handle_line(line)
        if self.diagnostics is not None:
            self.diagnostics.write(
                "bridge",
                "exchange",
                request_kind=request_kind,
                request_id=request_id,
                correlation_id=correlation_id,
                operation=operation,
                frame_bytes=len(line),
                response_kind=(
                    str(response.get("kind", ""))
                    if isinstance(response, dict)
                    else None
                ),
                ok=(
                    bool(response.get("ok", False))
                    if isinstance(response, dict)
                    else None
                ),
            )
        return response


async def serve(
    *,
    host: str,
    port: int,
    campaign_id: str,
    session_id: str,
    seed: int,
    vertical_slice: bool = True,
    log_dir: str | Path | None = ".logs/godot-dnd",
) -> None:
    diagnostics = (
        JsonlDiagnosticWriter.for_directory(log_dir, prefix="engine")
        if log_dir is not None
        else None
    )
    if diagnostics is not None:
        diagnostics.write(
            "session",
            "bridge starting",
            campaign_id=campaign_id,
            session_id=session_id,
            seed=seed,
            host=host,
            port=port,
        )
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
    session = AgentWorldClientBridgeSession(
        engine,
        tactical,
        creator,
        world,
        diagnostics=diagnostics,
    )
    bridge = DiagnosticClientBridgeServer(session, diagnostics)
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
        f"Godot client bridge v{PROTOCOL_VERSION} + agent API "
        f"listening on {addresses}"
    )
    try:
        async with server:
            await server.serve_forever()
    finally:
        if diagnostics is not None:
            diagnostics.write("session", "bridge stopped")
            await asyncio.to_thread(diagnostics.close)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the playable RPG bridge with AI/test-agent APIs"
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4765)
    parser.add_argument("--campaign-id", default="campaign:local-dev")
    parser.add_argument("--session-id", default="session:local-dev")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument(
        "--log-dir",
        default=".logs/godot-dnd",
        help="Directory for structured engine/agent JSONL diagnostics",
    )
    parser.add_argument(
        "--no-disk-log",
        action="store_true",
        help="Disable structured disk logging",
    )
    parser.add_argument(
        "--core-only",
        action="store_true",
        help=(
            "Disable tactical/spell provider while retaining creator, world, and agent services"
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
            log_dir=None if args.no_disk_log else args.log_dir,
        )
    )


if __name__ == "__main__":
    main()
