# engine/src/godot_dnd_engine/ui_automation_client.py
"""Small localhost client for the Godot UI automation/debug RPC."""

from __future__ import annotations

import argparse
import json
import socket
from dataclasses import dataclass, field
from typing import Any

from .errors import ValidationError

MAX_RESPONSE_BYTES = 262_144
_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


@dataclass(slots=True)
class UiAutomationClient:
    host: str = "127.0.0.1"
    port: int = 4766
    token: str = ""
    timeout_seconds: float = 5.0
    _socket: socket.socket | None = field(default=None, init=False, repr=False)
    _buffer: bytes = field(default=b"", init=False, repr=False)
    _counter: int = field(default=0, init=False, repr=False)

    def connect(self) -> None:
        if self.host not in _LOOPBACK_HOSTS:
            raise ValidationError("UI automation client is restricted to loopback hosts")
        if not 1024 <= self.port <= 65535:
            raise ValidationError("UI automation port must be between 1024 and 65535")
        if self._socket is not None:
            return
        self._socket = socket.create_connection(
            (self.host, self.port),
            timeout=self.timeout_seconds,
        )
        self._socket.settimeout(self.timeout_seconds)

    def close(self) -> None:
        if self._socket is None:
            return
        try:
            self._socket.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self._socket.close()
        self._socket = None
        self._buffer = b""

    def __enter__(self) -> UiAutomationClient:
        self.connect()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def request(
        self,
        method: str,
        params: dict[str, object] | None = None,
    ) -> dict[str, object]:
        if not isinstance(method, str) or not method.strip():
            raise ValidationError("UI automation method must be a non-empty string")
        self.connect()
        assert self._socket is not None
        self._counter += 1
        request_id = f"python-ui-{self._counter}"
        message: dict[str, object] = {
            "id": request_id,
            "method": method,
            "params": {} if params is None else dict(params),
        }
        if self.token:
            message["token"] = self.token
        encoded = (
            json.dumps(message, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode("utf-8")
        self._socket.sendall(encoded)
        response = self._read_line()
        decoded = json.loads(response.decode("utf-8"))
        if not isinstance(decoded, dict):
            raise ValidationError("UI automation response must be a JSON object")
        if str(decoded.get("id", "")) != request_id:
            raise ValidationError("UI automation response ID does not match request")
        if not bool(decoded.get("ok", False)):
            error_value = decoded.get("error", {})
            if isinstance(error_value, dict):
                message_value = error_value.get("message", "UI automation request failed")
                raise ValidationError(str(message_value))
            raise ValidationError("UI automation request failed")
        result = decoded.get("result", {})
        if not isinstance(result, dict):
            raise ValidationError("UI automation result must be an object")
        return dict(result)

    def snapshot(self) -> dict[str, object]:
        return self.request("ui.snapshot")

    def inspect(self, path: str) -> dict[str, object]:
        return self.request("ui.inspect", {"path": path})

    def focus(self, path: str) -> dict[str, object]:
        return self.request("ui.focus", {"path": path})

    def activate(self, path: str) -> dict[str, object]:
        return self.request("ui.activate", {"path": path})

    def click_at(self, x: float, y: float) -> dict[str, object]:
        return self.request("ui.click_at", {"x": x, "y": y})

    def set_text(self, path: str, text: str) -> dict[str, object]:
        return self.request("ui.set_text", {"path": path, "text": text})

    def input_action(
        self,
        action: str,
        *,
        strength: float = 1.0,
    ) -> dict[str, object]:
        return self.request(
            "ui.input_action",
            {"action": action, "strength": strength},
        )

    def logs(
        self,
        *,
        category: str = "",
        limit: int = 100,
    ) -> dict[str, object]:
        return self.request("ui.logs", {"category": category, "limit": limit})

    def screenshot(self) -> dict[str, object]:
        return self.request("ui.screenshot")

    def _read_line(self) -> bytes:
        assert self._socket is not None
        while b"\n" not in self._buffer:
            chunk = self._socket.recv(16_384)
            if not chunk:
                raise ConnectionError("Godot UI automation server disconnected")
            self._buffer += chunk
            if len(self._buffer) > MAX_RESPONSE_BYTES:
                raise ValidationError("UI automation response exceeds size limit")
        line, self._buffer = self._buffer.split(b"\n", 1)
        return line


def main() -> None:
    parser = argparse.ArgumentParser(description="Call the local Godot UI automation API")
    parser.add_argument("method")
    parser.add_argument(
        "--params-json",
        default="{}",
        help="JSON object passed as method params",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4766)
    parser.add_argument("--token", default="")
    args = parser.parse_args()
    params = json.loads(args.params_json)
    if not isinstance(params, dict):
        raise SystemExit("--params-json must decode to an object")
    with UiAutomationClient(
        host=args.host,
        port=args.port,
        token=args.token,
    ) as client:
        result = client.request(args.method, params)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
