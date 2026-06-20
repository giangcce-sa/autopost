"""Entry point dòng lệnh — mặt tiền CLI của TrendOS.

    trendos run            # chạy pipeline đầy đủ (collect → detect → generate)
    trendos run --dry-run  # bỏ qua sinh nội dung (không gọi Claude API)

CLI và API cùng gọi vào Orchestrator — không nhân đôi logic.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging

from trendos.pipeline import Orchestrator


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="trendos", description="TrendOS CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Chạy một lần pipeline")
    run.add_argument(
        "--dry-run",
        action="store_true",
        help="Bỏ qua giai đoạn sinh nội dung (không gọi Claude API)",
    )
    return parser


async def _run(dry_run: bool) -> None:
    orch = Orchestrator()
    summary = await orch.run(dry_run=dry_run)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = _build_parser().parse_args()
    if args.command == "run":
        asyncio.run(_run(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
