"""Run a MyBook chapter-generation performance benchmark from the command line."""
from __future__ import annotations

import argparse
import asyncio
import json

from app.db.session import get_db_context
from app.llm.mock import MockLLMProvider
from app.services.performance.runner import PerformanceRunner
from app.services.performance.schemas import PerformanceRunRequest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run 30-chapter generation performance analysis.")
    parser.add_argument("project_id", type=int)
    parser.add_argument("--chapter-count", type=int, default=30)
    parser.add_argument("--start-chapter-no", type=int, default=1)
    parser.add_argument("--target-word-count", type=int, default=3000)
    parser.add_argument("--scene-mode", action="store_true")
    parser.add_argument("--scene-count", type=int, default=2)
    parser.add_argument("--include-review", action="store_true")
    parser.add_argument("--llm-provider", choices=["mock", "configured"], default="mock")
    parser.add_argument("--report-root", default="reports/performance")
    parser.add_argument("--no-cpu", action="store_true")
    parser.add_argument("--no-memory", action="store_true")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    request = PerformanceRunRequest(
        chapter_count=args.chapter_count,
        start_chapter_no=args.start_chapter_no,
        use_scene_mode=args.scene_mode,
        scene_count=args.scene_count,
        target_word_count=args.target_word_count,
        include_review=args.include_review,
        llm_provider=args.llm_provider,
        profile_cpu=not args.no_cpu,
        profile_memory=not args.no_memory,
        report_root=args.report_root,
    )
    async with get_db_context() as db:
        provider = MockLLMProvider() if request.llm_provider == "mock" else None
        report = await PerformanceRunner(db, provider).run(args.project_id, request)
        print(
            json.dumps(
                {
                    "run_id": report.summary.run_id,
                    "report_dir": report.summary.report_dir,
                    "generated_chapters": report.summary.generated_chapters,
                    "failed_chapters": report.summary.failed_chapters,
                    "total_elapsed_ms": report.summary.total_elapsed_ms,
                },
                ensure_ascii=False,
                indent=2,
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
