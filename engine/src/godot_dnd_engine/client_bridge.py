"""Versioned local TCP bridge between Godot and the authoritative simulation engine."""

from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .engine import SimulationEngine
from .errors import SequenceError, UnsupportedCommandError, ValidationError
from .models import CommandEnvelope, EventEnvelope
from .serialization import event_to_dict, snapshot_to_dict

PROTOCOL_NAME = "godot-dnd-bridge"
PROTOCOL_VERSION = 1
CAPABILITIES = (
    "commands.v1",
    "queries.v1",
    "previews.v1",
    "snapshots.v1",
    "events.v1",
    "request-cancel.v1",
    "request-generation.v1",
)


class BridgeProtocolError(ValidationError):
    """Raised when an incoming client bridge envelope is malformed."""


@dataclass(slots=True)
class ClientBridgeSession:
    """Stateful bridge facade over one authoritative simulation engine."""

    engine: SimulationEngine
    events: list[EventEnvelope] = field(default_factory=list)

    def handle_message(self, message: Mapping[str, Any]) -> dict[str, object] | None:
        request = _validate_envelope(message)
        kind = request["kind"]
        if request["bridge_version"] != PROTOCOL_VERSION:
            return _rejected(
                request,
                "bridge.hello.rejected" if kind == "bridge.hello" else "request.rejected",
                "incompatible_version",
                "Client and engine bridge versions are incompatible",
                f"received {request['bridge_version']!r}; expected {PROTOCOL_VERSION}",
            )
        try:
            if kind == "bridge.hello":
                return self._hello(request)
            if kind == "command.submit":
                return self._command(request)
            if kind == "query.request":
                return self._query(request)
            if kind == "preview.request":
                return _rejected(
                    request,
                    "preview.rejected",
                    "unsupported",
                    "That preview is not available yet",
                    "v0.6 spatial preview providers have not been registered",
                )
            if kind == "request.cancel":
                # Current v1 local handlers are short-lived. Cancellation is still a protocol
                # primitive so future async query/preview providers can honor it.
                return None
            return _rejected(
                request,
                "request.rejected",
                "unsupported",
                "Unsupported engine bridge request",
                f"unsupported kind: {kind!r}",
            )
        except SequenceError as exc:
            return _rejected(
                request,
                _rejection_kind(kind),
                "conflict",
                "Authoritative state changed; refresh and try again",
                str(exc),
            )
        except UnsupportedCommandError as exc:
            return _rejected(
                request,
                _rejection_kind(kind),
                "unsupported",
                "That action is not supported",
                str(exc),
            )
        except ValidationError as exc:
            return _rejected(
                request,
                _rejection_kind(kind),
                "validation",
                "The engine rejected the request",
                str(exc),
            )

    def _hello(self, request: dict[str, Any]) -> dict[str, object]:
        payload = _require_mapping(request["payload"], "hello payload")
        if payload.get("protocol") != PROTOCOL_NAME:
            return _rejected(
                request,
                "bridge.hello.rejected",
                "incompatible_version",
                "Client and engine bridge protocols are incompatible",
                f"unexpected protocol: {payload.get('protocol')!r}",
            )
        return _response(
            request,
            "bridge.hello.accepted",
            payload={"protocol": PROTOCOL_NAME, "capabilities": list(CAPABILITIES)},
        )

    def _command(self, request: dict[str, Any]) -> dict[str, object]:
        payload = _require_mapping(request["payload"], "command payload")
        command_data = _require_mapping(payload.get("command"), "command")
        command = _command_from_dict(command_data)
        emitted = self.engine.handle(command)
        self.events.extend(emitted)
        return _response(
            request,
            "command.accepted",
            payload={
                "events": [event_to_dict(event) for event in emitted],
                "snapshot": snapshot_to_dict(self.engine.snapshot()),
            },
        )

    def _query(self, request: dict[str, Any]) -> dict[str, object]:
        payload = _require_mapping(request["payload"], "query payload")
        query_type = payload.get("query_type")
        query = _require_mapping(payload.get("query", {}), "query")
        if not isinstance(query_type, str) or not query_type:
            raise BridgeProtocolError("query_type must be a non-empty string")
        if query_type == "bridge.resync":
            after_sequence = query.get("after_sequence", 0)
            if (
                isinstance(after_sequence, bool)
                or not isinstance(after_sequence, int)
                or after_sequence < 0
            ):
                raise BridgeProtocolError("after_sequence must be an integer >= 0")
            return _response(
                request,
                "query.result",
                payload={"snapshot": snapshot_to_dict(self.engine.snapshot())},
            )
        if query_type == "bridge.snapshot":
            return _response(
                request,
                "query.result",
                payload={"snapshot": snapshot_to_dict(self.engine.snapshot())},
            )
        if query_type == "bridge.capabilities":
            return _response(
                request,
                "query.result",
                payload={"capabilities": list(CAPABILITIES)},
            )
        return _rejected(
            request,
            "query.rejected",
            "unsupported",
            "That engine query is not supported",
            f"unsupported query_type: {query_type!r}",
        )


@dataclass(slots=True)
class ClientBridgeServer:
    """Async newline-delimited JSON/TCP host for local Godot development."""

    session: ClientBridgeSession

    async def handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        try:
            while not reader.at_eof():
                line = await reader.readline()
                if not line:
                    break
                response = self._handle_line(line)
                if response is None:
                    continue
                writer.write(_dumps_line(response))
                await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    def _handle_line(self, line: bytes) -> dict[str, object] | None:
        try:
            decoded = json.loads(line.decode("utf-8"))
            message = _require_mapping(decoded, "bridge message")
            return self.session.handle_message(message)
        except (UnicodeDecodeError, json.JSONDecodeError, BridgeProtocolError) as exc:
            return {
                "bridge_version": PROTOCOL_VERSION,
                "kind": "request.rejected",
                "request_id": "",
                "correlation_id": "",
                "generation": 0,
                "ok": False,
                "payload": {},
                "error": _error(
                    "validation",
                    "Received malformed bridge message",
                    str(exc),
                ),
            }


async def serve(
    *,
    host: str,
    port: int,
    campaign_id: str,
    session_id: str,
    seed: int,
) -> None:
    engine = SimulationEngine.create(
        campaign_id=campaign_id,
        session_id=session_id,
        seed=seed,
    )
    bridge = ClientBridgeServer(ClientBridgeSession(engine))
    server = await asyncio.start_server(bridge.handle_client, host, port)
    addresses = ", ".join(str(sock.getsockname()) for sock in server.sockets or ())
    print(f"Godot client bridge v{PROTOCOL_VERSION} listening on {addresses}")
    async with server:
        await server.serve_forever()


def _validate_envelope(message: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "bridge_version",
        "kind",
        "request_id",
        "correlation_id",
        "generation",
        "payload",
    }
    missing = required - set(message)
    if missing:
        raise BridgeProtocolError(f"bridge message missing fields: {sorted(missing)!r}")
    bridge_version = message["bridge_version"]
    generation = message["generation"]
    if isinstance(bridge_version, bool) or not isinstance(bridge_version, int):
        raise BridgeProtocolError("bridge_version must be an integer")
    if not isinstance(message["kind"], str) or not message["kind"]:
        raise BridgeProtocolError("kind must be a non-empty string")
    if not isinstance(message["request_id"], str):
        raise BridgeProtocolError("request_id must be a string")
    if not isinstance(message["correlation_id"], str):
        raise BridgeProtocolError("correlation_id must be a string")
    if isinstance(generation, bool) or not isinstance(generation, int) or generation < 0:
        raise BridgeProtocolError("generation must be an integer >= 0")
    _require_mapping(message["payload"], "payload")
    return dict(message)


def _command_from_dict(data: Mapping[str, Any]) -> CommandEnvelope:
    required = {
        "command_id",
        "campaign_id",
        "session_id",
        "command_type",
        "payload",
        "version",
        "actor_id",
        "expected_sequence",
    }
    if set(data) != required:
        raise BridgeProtocolError("command fields do not match command schema v1")
    payload = _require_mapping(data["payload"], "command payload")
    try:
        return CommandEnvelope(
            command_id=data["command_id"],
            campaign_id=data["campaign_id"],
            session_id=data["session_id"],
            command_type=data["command_type"],
            payload=dict(payload),
            version=data["version"],
            actor_id=data["actor_id"],
            expected_sequence=data["expected_sequence"],
        )
    except TypeError as exc:
        raise BridgeProtocolError("command contains invalid field types") from exc


def _require_mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise BridgeProtocolError(f"{label} must be a JSON object")
    return value


def _response(
    request: Mapping[str, Any],
    kind: str,
    *,
    payload: Mapping[str, object],
) -> dict[str, object]:
    return {
        "bridge_version": PROTOCOL_VERSION,
        "kind": kind,
        "request_id": request["request_id"],
        "correlation_id": request["correlation_id"],
        "generation": request["generation"],
        "ok": True,
        "payload": dict(payload),
        "error": {},
    }


def _rejected(
    request: Mapping[str, Any],
    kind: str,
    category: str,
    user_message: str,
    debug_detail: str,
) -> dict[str, object]:
    return {
        "bridge_version": PROTOCOL_VERSION,
        "kind": kind,
        "request_id": request.get("request_id", ""),
        "correlation_id": request.get("correlation_id", ""),
        "generation": request.get("generation", 0),
        "ok": False,
        "payload": {},
        "error": _error(category, user_message, debug_detail),
    }


def _error(category: str, user_message: str, debug_detail: str) -> dict[str, str]:
    return {
        "category": category,
        "user_message": user_message,
        "debug_detail": debug_detail,
    }


def _rejection_kind(request_kind: str) -> str:
    if request_kind == "command.submit":
        return "command.rejected"
    if request_kind == "query.request":
        return "query.rejected"
    if request_kind == "preview.request":
        return "preview.rejected"
    return "request.rejected"


def _dumps_line(message: Mapping[str, object]) -> bytes:
    return (
        json.dumps(message, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local Godot client engine bridge")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4765)
    parser.add_argument("--campaign-id", default="campaign:local-dev")
    parser.add_argument("--session-id", default="session:local-dev")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    asyncio.run(
        serve(
            host=args.host,
            port=args.port,
            campaign_id=args.campaign_id,
            session_id=args.session_id,
            seed=args.seed,
        )
    )


if __name__ == "__main__":
    main()
