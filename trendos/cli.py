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


def _print_json(value) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="trendos", description="TrendOS CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Chạy một lần pipeline")
    run.add_argument(
        "--dry-run",
        action="store_true",
        help="Bỏ qua giai đoạn sinh nội dung (không gọi Claude API)",
    )
    run.add_argument("--full", action="store_true", help="Chạy đầy đủ pipeline")

    trends = sub.add_parser("trends", help="Thao tác với xu hướng")
    trends_sub = trends.add_subparsers(dest="trends_command", required=True)
    trends_list = trends_sub.add_parser("list", help="Liệt kê xu hướng")
    trends_list.add_argument("--limit", type=int, default=10)

    content = sub.add_parser("content", help="Thao tác với nội dung")
    content_sub = content.add_subparsers(dest="content_command", required=True)
    content_list = content_sub.add_parser("list", help="Liệt kê nội dung")
    content_list.add_argument("--trend-id")
    content_list.add_argument("--format")

    runs = sub.add_parser("runs", help="Thao tác với lượt chạy")
    runs_sub = runs.add_subparsers(dest="runs_command", required=True)
    runs_list = runs_sub.add_parser("list", help="Liệt kê lượt chạy")
    runs_list.add_argument("--limit", type=int, default=10)

    sub.add_parser("init-db", help="Khởi tạo database theo cấu hình hiện tại")

    schedule = sub.add_parser("schedule", help="Chạy pipeline định kỳ")
    schedule.add_argument("--dry-run", action="store_true", help="Chạy scheduler ở chế độ dry-run")
    schedule.add_argument("--full", action="store_true", help="Chạy scheduler đầy đủ")
    schedule.add_argument(
        "--interval",
        type=int,
        default=None,
        help="Khoảng cách giữa các lần chạy, giây",
    )
    return parser


async def _run(dry_run: bool) -> None:
    orch = Orchestrator()
    summary = await orch.run(dry_run=dry_run)
    _print_json(summary)


async def _list_trends(limit: int) -> None:
    orch = Orchestrator()
    trends = await orch.repo.list_trends(limit=limit)
    _print_json([t.model_dump(mode="json") for t in trends])


async def _list_content(trend_id: str | None, fmt: str | None) -> None:
    from trendos.models import ContentFormat

    orch = Orchestrator()
    parsed_fmt = ContentFormat(fmt) if fmt else None
    content = await orch.repo.list_content(trend_id=trend_id, fmt=parsed_fmt)
    _print_json([c.model_dump(mode="json") for c in content])


async def _list_runs(limit: int) -> None:
    orch = Orchestrator()
    runs = await orch.repo.list_runs(limit=limit)
    _print_json([r.model_dump(mode="json") for r in runs])


async def _init_db() -> None:
    orch = Orchestrator()
    run = await orch.create_run(dry_run=True)
    _print_json({"status": "ok", "run_id": run.id, "message": "Database initialized"})


async def _schedule(*, dry_run: bool, interval: int | None) -> None:
    from trendos.pipeline.scheduler import PipelineScheduler

    scheduler = PipelineScheduler(interval_seconds=interval)
    await scheduler.run_forever(dry_run=dry_run)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = _build_parser().parse_args()
    if args.command == "run":
        asyncio.run(_run(dry_run=args.dry_run or not args.full))
    elif args.command == "trends" and args.trends_command == "list":
        asyncio.run(_list_trends(limit=args.limit))
    elif args.command == "content" and args.content_command == "list":
        asyncio.run(_list_content(trend_id=args.trend_id, fmt=args.format))
    elif args.command == "runs" and args.runs_command == "list":
        asyncio.run(_list_runs(limit=args.limit))
    elif args.command == "init-db":
        asyncio.run(_init_db())
    elif args.command == "schedule":
        asyncio.run(_schedule(dry_run=args.dry_run or not args.full, interval=args.interval))


if __name__ == "__main__":
    main()
