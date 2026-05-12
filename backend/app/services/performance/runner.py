"""Sequential long-form generation performance runner."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import time
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

# Import comment models so Base.metadata includes AudienceHintPack tables in tests and app startup.
import app.models.comment  # noqa: F401

from app.llm.base import LLMProvider
from app.llm.factory import create_llm_provider
from app.models.chapter import Chapter
from app.repositories.chapter import ChapterRepository
from app.repositories.project import ProjectRepository
from app.services.orchestrator.schemas import WriterGenerationRequest
from app.services.performance.profiler import (
    ProfilingLLMProvider,
    QueryProfiler,
    RunProfiler,
    StageProfiler,
)
from app.services.performance.mock_provider import PerformanceMockLLMProvider
from app.services.performance.report import PerformanceReportWriter
from app.services.performance.schemas import (
    ChapterPerformanceMetric,
    PerformanceRunIssue,
    PerformanceRunReport,
    PerformanceRunRequest,
    PerformanceRunSummary,
)
from app.services.performance.text_metrics import count_chinese_body_chars, tail_for_continuation
from app.services.planner.service import PlannerService
from app.services.reviewer.service import ReviewerService
from app.services.writer.service import WriterService


class PerformanceRunner:
    """Run a batch generation benchmark and persist report artifacts."""

    def __init__(
        self,
        db: AsyncSession,
        llm_provider: Optional[LLMProvider] = None,
    ):
        self.db = db
        self.base_llm_provider = llm_provider
        self.project_repo = ProjectRepository(db)
        self.chapter_repo = ChapterRepository(db)
        self.issues: list[PerformanceRunIssue] = []

    async def run(
        self,
        project_id: int,
        request: PerformanceRunRequest,
    ) -> PerformanceRunReport:
        project = await self.project_repo.get(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        if request.concurrency != 1:
            raise ValueError("PerformanceRunner currently supports concurrency=1 only")

        started_at = datetime.now()
        self.issues = []
        run_id = request.run_id or started_at.strftime("run_%Y%m%d_%H%M%S_%f")
        run_dir = Path(request.report_root) / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        base_provider = self._create_llm_provider(request)
        llm_profiler = ProfilingLLMProvider(base_provider)
        query_profiler = QueryProfiler(self.db)
        stage_profiler = StageProfiler(query_profiler, llm_profiler)
        run_profiler = RunProfiler(
            profile_cpu=request.profile_cpu,
            profile_memory=request.profile_memory,
        )
        chapters: list[ChapterPerformanceMetric] = []
        query_profiler.install()
        total_started = time.perf_counter()
        run_profiler.start()
        try:
            await self._ensure_chapter_outlines(
                project_id,
                request,
                llm_profiler,
                stage_profiler,
            )
            await self.db.commit()
            selected_chapters = await self._select_chapters(project_id, request)
            if len(selected_chapters) < request.chapter_count:
                self.issues.append(
                    PerformanceRunIssue(
                        category="functional bug",
                        severity="error",
                        module="performance.runner",
                        function="_select_chapters",
                        message=(
                            f"Only {len(selected_chapters)} chapters available for "
                            f"requested {request.chapter_count} chapters."
                        ),
                        root_cause="Planner did not create enough chapter records.",
                        fix="Runner records the shortage and generates available chapters only.",
                    )
                )
            chapter_refs = [
                (chapter.id, chapter.chapter_no, chapter.title or "")
                for chapter in selected_chapters
            ]
            writer = WriterService(self.db, llm_profiler, stage_profiler=stage_profiler)
            reviewer = ReviewerService(self.db, llm_profiler)

            for chapter_id, chapter_no, chapter_title in chapter_refs:
                chapter = await self.chapter_repo.get(chapter_id)
                if chapter is None:
                    chapters.append(
                        ChapterPerformanceMetric(
                            chapter_id=chapter_id,
                            chapter_no=chapter_no,
                            title=chapter_title,
                            status="failed",
                            elapsed_ms=0.0,
                            error_count=1,
                            error="Chapter disappeared before generation",
                        )
                    )
                    continue
                metric = await self._run_chapter(
                    project_id=project_id,
                    chapter=chapter,
                    request=request,
                    writer=writer,
                    reviewer=reviewer,
                    stage_profiler=stage_profiler,
                    query_profiler=query_profiler,
                    llm_profiler=llm_profiler,
                    run_profiler=run_profiler,
                )
                chapters.append(metric)
                if metric.status == "failed":
                    await self.db.rollback()
                else:
                    await self.db.commit()
                self.db.expunge_all()
        finally:
            run_profiler.stop()
            query_profiler.uninstall()

        finished_at = datetime.now()
        generated = len([chapter for chapter in chapters if chapter.status != "failed"])
        failed = len([chapter for chapter in chapters if chapter.status == "failed"])
        total_elapsed_ms = (time.perf_counter() - total_started) * 1000.0
        total_body_chars = sum(chapter.char_count for chapter in chapters if chapter.status != "failed")
        average_body_chars = total_body_chars / generated if generated else 0.0
        average_elapsed_ms = (
            sum(chapter.elapsed_ms for chapter in chapters) / len(chapters) if chapters else 0.0
        )
        completed = (
            len(chapters) == request.chapter_count
            and failed == 0
            and all(chapter.char_count >= request.min_body_chars for chapter in chapters)
        )
        local_compute_ms = max(total_elapsed_ms - llm_profiler.time_ms, 0.0)
        summary = PerformanceRunSummary(
            run_id=run_id,
            project_id=project_id,
            started_at=started_at,
            finished_at=finished_at,
            total_elapsed_ms=total_elapsed_ms,
            total_chapters=request.chapter_count,
            generated_chapters=generated,
            failed_chapters=failed,
            min_body_chars=request.min_body_chars,
            completed=completed,
            every_chapter_meets_minimum=completed,
            total_body_chars=total_body_chars,
            average_body_chars=average_body_chars,
            average_chapter_elapsed_ms=average_elapsed_ms,
            llm_wait_ratio=(llm_profiler.time_ms / total_elapsed_ms) if total_elapsed_ms else 0.0,
            local_compute_ratio=(local_compute_ms / total_elapsed_ms) if total_elapsed_ms else 0.0,
            report_dir=str(run_dir),
            requested_provider=request.llm_provider,
            actual_provider=base_provider.model,
            db_query_count=query_profiler.query_count,
            db_time_ms=query_profiler.time_ms,
            llm_call_count=llm_profiler.call_count,
            llm_time_ms=llm_profiler.time_ms,
            memory_current_kb=run_profiler.memory_current_kb,
            memory_peak_kb=run_profiler.memory_peak_kb,
        )
        report = PerformanceRunReport(
            summary=summary,
            chapters=chapters,
            stage_metrics=stage_profiler.metrics,
            issues=self.issues,
            run_config=request.model_dump(mode="json"),
        )
        artifacts = PerformanceReportWriter().write(report, run_dir)
        artifacts.update(run_profiler.write_cpu_files(run_dir))
        artifacts.update(run_profiler.write_memory_file(run_dir))
        report.artifacts = artifacts
        return report

    def _create_llm_provider(self, request: PerformanceRunRequest) -> LLMProvider:
        if request.llm_provider == "mock":
            return PerformanceMockLLMProvider(
                chapter_body_chars=max(request.min_body_chars + 800, request.target_word_count)
            )
        if self.base_llm_provider is not None:
            return self.base_llm_provider
        try:
            return create_llm_provider(provider=request.llm_provider)
        except Exception as exc:  # noqa: BLE001 - benchmark should keep local baseline runnable.
            self.issues.append(
                PerformanceRunIssue(
                    category="environment issue",
                    severity="warning",
                    module="llm provider",
                    function="create_llm_provider",
                    message=f"Fell back to mock provider after provider creation failed: {exc}",
                    root_cause="Real provider was not configured or unavailable in this environment.",
                    fix="Used PerformanceMockLLMProvider so local CPU/memory baseline can still run.",
                )
            )
            return PerformanceMockLLMProvider(
                chapter_body_chars=max(request.min_body_chars + 800, request.target_word_count)
            )

    async def _ensure_chapter_outlines(
        self,
        project_id: int,
        request: PerformanceRunRequest,
        llm_provider: LLMProvider,
        stage_profiler: StageProfiler,
    ) -> None:
        existing = await self._select_chapters(project_id, request)
        missing = request.chapter_count - len(existing)
        if missing <= 0:
            return
        planner = PlannerService(self.db, llm_provider)
        with stage_profiler.stage(
            "planner.generate_chapter_outlines",
            metadata={"missing_count": missing},
        ):
            await planner.generate_chapter_outlines(project_id, count=missing)
        await self.db.flush()

    async def _select_chapters(
        self,
        project_id: int,
        request: PerformanceRunRequest,
    ) -> list[Chapter]:
        all_chapters = await self.chapter_repo.get_by_project(project_id, limit=1000)
        end_chapter_no = request.start_chapter_no + request.chapter_count - 1
        return [
            chapter
            for chapter in all_chapters
            if request.start_chapter_no <= chapter.chapter_no <= end_chapter_no
        ][: request.chapter_count]

    async def _run_chapter(
        self,
        *,
        project_id: int,
        chapter: Chapter,
        request: PerformanceRunRequest,
        writer: WriterService,
        reviewer: ReviewerService,
        stage_profiler: StageProfiler,
        query_profiler: QueryProfiler,
        llm_profiler: ProfilingLLMProvider,
        run_profiler: RunProfiler,
    ) -> ChapterPerformanceMetric:
        chapter_started = time.perf_counter()
        stage_start_index = len(stage_profiler.metrics)
        db_start = query_profiler.snapshot()
        llm_start = llm_profiler.snapshot()
        error = ""
        status = "generated"
        retry_count = 0
        error_count = 0
        word_count = 0
        char_count = 0
        chapter_id = chapter.id
        chapter_no = chapter.chapter_no
        title = chapter.title or ""
        try:
            if request.resume and chapter.text:
                with stage_profiler.stage("word_count_validation", chapter_no=chapter_no):
                    char_count = count_chinese_body_chars(chapter.text, title)
                if char_count >= request.min_body_chars:
                    status = "resumed_existing"
                    word_count = char_count
                    current_kb, peak_kb = run_profiler.memory_snapshot_kb()
                    return self._build_chapter_metric(
                        chapter_id=chapter_id,
                        chapter_no=chapter_no,
                        title=title,
                        status=status,
                        elapsed_ms=(time.perf_counter() - chapter_started) * 1000.0,
                        word_count=word_count,
                        char_count=char_count,
                        retry_count=retry_count,
                        error_count=error_count,
                        error=error,
                        stage_metrics=stage_profiler.metrics[stage_start_index:],
                        db_start=db_start,
                        db_end=query_profiler.snapshot(),
                        llm_start=llm_start,
                        llm_end=llm_profiler.snapshot(),
                        memory_current_kb=current_kb,
                        memory_peak_kb=peak_kb,
                    )
            writer_request = WriterGenerationRequest(
                chapter_id=chapter.id,
                outline=chapter.outline,
                use_scene_mode=request.use_scene_mode,
                scene_count=request.scene_count,
                target_word_count=request.target_word_count,
            )
            with stage_profiler.stage("orchestrator.chapter_generation", chapter_no=chapter_no):
                output = await writer.generate_chapter(project_id, chapter.id, writer_request)
            with stage_profiler.stage("word_count_validation", chapter_no=chapter_no):
                char_count = count_chinese_body_chars(output.draft_blob, title)
            retry_count, char_count = await self._ensure_min_body_chars(
                chapter=chapter,
                current_text=output.draft_blob,
                current_char_count=char_count,
                request=request,
                writer=writer,
                llm_profiler=llm_profiler,
                stage_profiler=stage_profiler,
            )
            word_count = char_count
            if char_count < request.min_body_chars:
                status = "failed"
                error_count = 1
                error = (
                    f"Body character minimum not met: {char_count} < "
                    f"{request.min_body_chars} after {retry_count} retries"
                )
                self.issues.append(
                    PerformanceRunIssue(
                        category="functional bug",
                        severity="error",
                        chapter_no=chapter_no,
                        module="writer",
                        function="word_count_validation",
                        message=error,
                        root_cause="Provider returned insufficient body text.",
                        fix="Runner attempted continuation retries and recorded failure.",
                    )
                )
            if request.include_review:
                with stage_profiler.stage("reviewer.review_chapter", chapter_no=chapter_no):
                    await reviewer.review_chapter(project_id, chapter.id)
        except Exception as exc:  # noqa: BLE001 - benchmark should record failures and continue.
            status = "failed"
            error = f"{exc.__class__.__name__}: {exc}"
            error_count = 1
            self.issues.append(
                PerformanceRunIssue(
                    category="functional bug",
                    severity="error",
                    chapter_no=chapter_no,
                    module="performance.runner",
                    function="_run_chapter",
                    message=error,
                    root_cause="Chapter generation raised an exception.",
                    fix="Runner recorded the failure, rolled back the chapter transaction, and continued.",
                )
            )
        db_end = query_profiler.snapshot()
        llm_end = llm_profiler.snapshot()
        current_kb, peak_kb = run_profiler.memory_snapshot_kb()
        return self._build_chapter_metric(
            chapter_id=chapter_id,
            chapter_no=chapter_no,
            title=title,
            status=status,
            elapsed_ms=(time.perf_counter() - chapter_started) * 1000.0,
            word_count=word_count,
            char_count=char_count,
            retry_count=retry_count,
            error_count=error_count,
            error=error,
            stage_metrics=stage_profiler.metrics[stage_start_index:],
            db_start=db_start,
            db_end=db_end,
            llm_start=llm_start,
            llm_end=llm_end,
            memory_current_kb=current_kb,
            memory_peak_kb=peak_kb,
        )

    async def _ensure_min_body_chars(
        self,
        *,
        chapter: Chapter,
        current_text: str,
        current_char_count: int,
        request: PerformanceRunRequest,
        writer: WriterService,
        llm_profiler: ProfilingLLMProvider,
        stage_profiler: StageProfiler,
    ) -> tuple[int, int]:
        retries = 0
        text = current_text
        char_count = current_char_count
        while char_count < request.min_body_chars and retries < request.max_word_count_retries:
            retries += 1
            needed = request.min_body_chars - char_count
            prompt = f"""请续写小说第 {chapter.chapter_no} 章正文。

要求：
1. 只输出正文续写内容。
2. 不要重复已有段落。
3. 至少补充 {needed + 300} 个中文正文字符。

已有正文结尾：
{tail_for_continuation(text)}
"""
            with stage_profiler.stage(
                "writer.min_body_continuation",
                chapter_no=chapter.chapter_no,
                metadata={"attempt": retries, "needed_chars": needed},
            ):
                response = await llm_profiler.generate(prompt, "你是一个专业的小说续写助手。")
            with stage_profiler.stage("writer.text_cleaning", chapter_no=chapter.chapter_no):
                continuation = writer._clean_text(response.content)
            if not continuation:
                break
            text = text.rstrip() + "\n\n" + continuation.strip()
            with stage_profiler.stage("word_count_validation", chapter_no=chapter.chapter_no):
                char_count = count_chinese_body_chars(text, chapter.title or "")
            with stage_profiler.stage("writer.chapter_persistence", chapter_no=chapter.chapter_no):
                chapter.text = text
                chapter.word_count = char_count
                await self.db.flush()
        if char_count >= request.min_body_chars:
            with stage_profiler.stage("writer.chapter_persistence", chapter_no=chapter.chapter_no):
                chapter.word_count = char_count
                await self.db.flush()
        return retries, char_count

    def _build_chapter_metric(
        self,
        *,
        chapter_id: int,
        chapter_no: int,
        title: str,
        status: str,
        elapsed_ms: float,
        word_count: int,
        char_count: int,
        retry_count: int,
        error_count: int,
        error: str,
        stage_metrics,
        db_start,
        db_end,
        llm_start,
        llm_end,
        memory_current_kb: float,
        memory_peak_kb: float,
    ) -> ChapterPerformanceMetric:
        db_time_ms = db_end.db_time_ms - db_start.db_time_ms
        llm_time_ms = llm_end.llm_time_ms - llm_start.llm_time_ms
        return ChapterPerformanceMetric(
            chapter_id=chapter_id,
            chapter_no=chapter_no,
            title=title,
            status=status,
            elapsed_ms=elapsed_ms,
            word_count=word_count,
            char_count=char_count,
            planner_duration_ms=self._sum_stages(stage_metrics, "planner."),
            memory_context_duration_ms=self._sum_stages(stage_metrics, "memory."),
            writer_duration_ms=self._sum_stages(stage_metrics, "writer."),
            reviewer_duration_ms=self._sum_stages(stage_metrics, "reviewer."),
            state_update_duration_ms=self._sum_stages(stage_metrics, "writer.chapter_persistence"),
            db_query_count=db_end.db_query_count - db_start.db_query_count,
            db_time_ms=db_time_ms,
            llm_call_count=llm_end.llm_call_count - llm_start.llm_call_count,
            llm_time_ms=llm_time_ms,
            local_compute_ms=max(elapsed_ms - llm_time_ms, 0.0),
            memory_current_kb=memory_current_kb,
            memory_peak_kb=memory_peak_kb,
            retry_count=retry_count,
            error_count=error_count,
            error=error,
        )

    def _sum_stages(self, stage_metrics, prefix: str) -> float:
        return sum(metric.elapsed_ms for metric in stage_metrics if metric.stage.startswith(prefix))
