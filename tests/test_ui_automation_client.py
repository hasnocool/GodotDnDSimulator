from __future__ import annotations

import json
import socket
from threading import Thread

import pytest

from godot_dnd_engine.errors import ValidationError
from godot_dnd_engine.ui_automation_client import UiAutomationClient


def test_ui_automation_client_round_trips_local_rpc() -> None:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = int(server.getsockname()[1])
    received: list[dict[str, object]] = []

    def serve_once() -> None:
        connection, _address = server.accept()
        with connection:
            buffer = b""
            while b"\n" not in buffer:
                buffer += connection.recv(4096)
            line, _rest = buffer.split(b"\n", 1)
            request = json.loads(line.decode("utf-8"))
            assert isinstance(request, dict)
            received.append(request)
            response = {
                "id": request["id"],
                "ok": True,
                "result": {"controls": [], "client_log_path": "user://logs/test.jsonl"},
            }
            connection.sendall((json.dumps(response) + "\n").encode("utf-8"))
        server.close()

    thread = Thread(target=serve_once)
    thread.start()
    with UiAutomationClient(port=port, token="test-token") as client:
        result = client.snapshot()
    thread.join(timeout=2.0)

    assert result["client_log_path"] == "user://logs/test.jsonl"
    assert received[0]["method"] == "ui.snapshot"
    assert received[0]["token"] == "test-token"
    assert received[0]["params"] == {}


def test_ui_automation_client_rejects_non_loopback_hosts() -> None:
    client = UiAutomationClient(host="example.com")
    with pytest.raises(ValidationError, match="loopback"):
        client.connect()
