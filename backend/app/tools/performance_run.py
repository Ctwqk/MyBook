"""CLI entry point for long-form generation performance runs."""
from __future__ import annotations

import argparse
import asyncio
import json
import random
from datetime import datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401 - register all models before create_all().
from app.db.session import Base
from app.models.project import Project, ProjectStatus
from app.services.performance.runner import PerformanceRunner
from app.services.performance.schemas import PerformanceRunRequest


GENRES = [
    ("都市异能", "一个失眠的城市安全工程师在地铁停运夜听见地下网络的求救信号。"),
    ("科幻悬疑", "边境空间站连续收到来自未来的维修日志，主角必须找出日志作者。"),
    ("玄幻冒险", "失去灵脉的少年在废弃书院发现能记录因果的青铜页。"),
    ("近未来犯罪", "算法审判系统第一次判错案，调查员发现错误来自不存在的证人。"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run MyBook long-form performance benchmark.")
    parser.add_argument("--chapters", type=int, default=60)
    parser.add_argument("--min-words", type=int, default=2500, dest="min_words")
    parser.add_argument("--target-word-count", type=int, default=3200)
    parser.add_argument("--profile", action="store_true", help="Enable CPU and memory profiling.")
    parser.add_argument("--profile-cpu", action="store_true")
    parser.add_argument("--profile-memory", action="store_true")
    parser.add_argument("--include-review", action="store_true")
    parser.add_argument("--use-scene-mode", action="store_true")
    parser.add_argument("--scene-count", type=int, default=2)
    parser.add_argument("--llm-provider", default="mock")
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--output", default=None)
    parser.add_argument("--project-id", type=int, default=None)
    parser.add_argument("--resume", action="store_true", default=True)
    parser.add_argument("--no-resume", action="store_false", dest="resume")
    return parser.parse_args()


async def main_async() -> None:
    args = parse_args()
    timestamp = datetime.now().strftime("run_%Y%m%d_%H%M%S")
    output = Path(args.output or Path("reports/performance") / timestamp)
    output.mkdir(parents=True, exist_ok=True)
    database_url = args.database_url or f"sqlite+aiosqlite:///{output / 'performance.sqlite3'}"

    engine = create_async_engine(database_url, echo=False, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        project_id = args.project_id
        if project_id is None:
            project = random_project(args.chapters, args.min_words)
            session.add(project)
            await session.commit()
            await session.refresh(project)
            project_id = project.id

        request = PerformanceRunRequest(
            chapter_count=args.chapters,
            min_body_chars=args.min_words,
            target_word_count=max(args.target_word_count, args.min_words),
            include_review=args.include_review,
            use_scene_mode=args.use_scene_mode,
            scene_count=args.scene_count,
            llm_provider=args.llm_provider,
            resume=args.resume,
            profile_cpu=args.profile or args.profile_cpu,
            profile_memory=args.profile or args.profile_memory,
            report_root=str(output.parent),
            run_id=output.name,
        )
        runner = PerformanceRunner(session)
        report = await runner.run(project_id, request)
        print(
            json.dumps(
                {
                    "project_id": project_id,
                    "report_dir": report.summary.report_dir,
                    "completed": report.summary.completed,
                    "generated_chapters": report.summary.generated_chapters,
                    "failed_chapters": report.summary.failed_chapters,
                    "total_body_chars": report.summary.total_body_chars,
                    "total_elapsed_ms": report.summary.total_elapsed_ms,
                    "actual_provider": report.summary.actual_provider,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    await engine.dispose()


def random_project(chapters: int, min_chars: int) -> Project:
    genre, premise = random.choice(GENRES)
    suffix = datetime.now().strftime("%H%M%S")
    title = f"{genre}性能实测-{suffix}"
    return Project(
        title=title,
        genre=genre,
        style="紧凑、悬疑、人物驱动",
        premise=premise,
        target_length=chapters * min_chars,
        target_chapters=chapters,
        chapter_length=min_chars,
        raw_prompt=f"随机性能实测项目：{premise}",
        status=ProjectStatus.PLANNING,
    )


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
