# tools/rules_importer/cli.py
"""Command-line entry points for approved SRD fetching and deterministic builds."""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import asdict
from pathlib import Path

from .fetch import fetch_source
from .pipeline import build_source
from .serialization import dumps_canonical
from .sources import SourceRegistry

_DEFAULT_SOURCE = "wotc-srd-5.2.1-en"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rules-importer")
    parser.add_argument("--registry", type=Path, default=Path("config/rules/sources.json"))
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch = subparsers.add_parser("fetch", help="Fetch and verify an approved source")
    fetch.add_argument("--source-id", default=_DEFAULT_SOURCE)
    fetch.add_argument("--cache-dir", type=Path, default=Path(".cache/rules"))

    build = subparsers.add_parser("build", help="Fetch, extract, compile, validate, and export")
    build.add_argument("--source-id", default=_DEFAULT_SOURCE)
    build.add_argument("--cache-dir", type=Path, default=Path(".cache/rules"))
    build.add_argument("--schema-dir", type=Path, default=Path("schemas/rules/v1"))
    build.add_argument(
        "--output-dir",
        type=Path,
        default=Path("content/generated/srd-5.2.1"),
    )
    return parser


async def _run(args: argparse.Namespace) -> int:
    registry = SourceRegistry.from_path(args.registry)
    if args.command == "fetch":
        artifact = await fetch_source(registry.require(args.source_id), args.cache_dir)
        print(dumps_canonical(asdict(artifact)))
        return 0
    if args.command == "build":
        report = await build_source(
            registry=registry,
            source_id=args.source_id,
            cache_dir=args.cache_dir,
            schema_dir=args.schema_dir,
            output_dir=args.output_dir,
        )
        print(dumps_canonical(asdict(report)))
        return 0
    raise AssertionError(f"unhandled command: {args.command}")


def main() -> int:
    args = _parser().parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
