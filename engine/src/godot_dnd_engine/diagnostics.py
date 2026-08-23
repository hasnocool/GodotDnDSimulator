# engine/src/godot_dnd_engine/diagnostics.py
"""Non-blocking structured JSONL diagnostics for bridge and agent tooling."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from queue import Empty, Full, Queue
from threading import Thread
from time import time_ns
from typing import Any

_STOP = object()


@dataclass(slots=True)
class JsonlDiagnosticWriter:
    """Bounded background JSONL writer that keeps disk I/O off async bridge threads."""

    path: Path
    max_queue: int = 10_000
    _queue: Queue[dict[str, object] | object] = field(init=False, repr=False)
    _thread: Thread = field(init=False, repr=False)
    _closed: bool = field(default=False, init=False, repr=False)
    _dropped: int = field(default=0, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.max_queue < 1:
            raise ValueError("max_queue must be >= 1")
        self.path = Path(self.path)
        self._queue = Queue(maxsize=self.max_queue)
        self._thread = Thread(
            target=self._writer_loop,
            name="godot-dnd-jsonl-log",
            daemon=True,
        )
        self._thread.start()

    @classmethod
    def for_directory(
        cls,
        directory: str | Path,
        *,
        prefix: str = "engine",
    ) -> JsonlDiagnosticWriter:
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
        return cls(Path(directory) / f"{prefix}-{timestamp}.jsonl")

    def write(
        self,
        category: str,
        message: str,
        **fields: Any,
    ) -> None:
        if self._closed:
            return
        entry: dict[str, object] = {
            "timestamp_unix_ns": time_ns(),
            "category": category,
            "message": message,
        }
        for key, value in fields.items():
            if value is not None:
                entry[key] = value
        try:
            self._queue.put_nowait(entry)
        except Full:
            self._dropped += 1

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._dropped:
            try:
                self._queue.put_nowait(
                    {
                        "timestamp_unix_ns": time_ns(),
                        "category": "diagnostics",
                        "message": "diagnostic entries dropped",
                        "dropped": self._dropped,
                    }
                )
            except Full:
                pass
        self._queue.put(_STOP)
        self._thread.join(timeout=5.0)

    def _writer_loop(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            while True:
                try:
                    item = self._queue.get(timeout=0.5)
                except Empty:
                    continue
                if item is _STOP:
                    break
                assert isinstance(item, dict)
                handle.write(
                    json.dumps(
                        item,
                        sort_keys=True,
                        separators=(",", ":"),
                        ensure_ascii=False,
                        default=str,
                    )
                )
                handle.write("\n")
                if self._queue.empty():
                    handle.flush()
            while True:
                try:
                    item = self._queue.get_nowait()
                except Empty:
                    break
                if item is _STOP:
                    continue
                assert isinstance(item, dict)
                handle.write(
                    json.dumps(
                        item,
                        sort_keys=True,
                        separators=(",", ":"),
                        ensure_ascii=False,
                        default=str,
                    )
                )
                handle.write("\n")
            handle.flush()
