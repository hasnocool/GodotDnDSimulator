# tools/rules_importer/serialization.py
"""Canonical serialization helpers for reproducible rules output."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


def _default(value: object) -> Any:
    if is_dataclass(value):
        return asdict(value)
    raise TypeError(f"unsupported canonical JSON value: {type(value).__name__}")


def dumps_canonical(value: object) -> str:
    return json.dumps(
        value,
        default=_default,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def write_canonical_json(path: Path, value: object) -> str:
    text = dumps_canonical(value) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return sha256_text(text)
