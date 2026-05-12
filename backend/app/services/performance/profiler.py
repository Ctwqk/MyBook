"""Small standard-library profilers for batch generation runs."""
from __future__ import annotations

import cProfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
import pstats
import time
import tracemalloc
from typing import Any, Iterator, Optional

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.base import LLMProvider, LLMResponse
from app.services.performance.schemas import StageMetric


@dataclass
class CounterSnapshot:
    db_query_count: int = 0
    db_time_ms: float = 0.0
    llm_call_count: int = 0
    llm_time_ms: float = 0.0


class QueryProfiler:
    """Collect SQLAlchemy query count and cursor elapsed time."""

    def __init__(self, db: AsyncSession):
        bind = db.get_bind()
        self.engine = getattr(bind, "sync_engine", bind)
        self.query_count = 0
        self.time_ms = 0.0
        self._installed = False

    def install(self) -> None:
        if self._installed:
            return
        event.listen(self.engine, "before_cursor_execute", self._before_cursor_execute)
        event.listen(self.engine, "after_cursor_execute", self._after_cursor_execute)
        self._installed = True

    def uninstall(self) -> None:
        if not self._installed:
            return
        event.remove(self.engine, "before_cursor_execute", self._before_cursor_execute)
        event.remove(self.engine, "after_cursor_execute", self._after_cursor_execute)
        self._installed = False

    def snapshot(self) -> CounterSnapshot:
        return CounterSnapshot(db_query_count=self.query_count, db_time_ms=self.time_ms)

    def _before_cursor_execute(
        self,
        conn,
        cursor,
        statement,
        parameters,
        context,
        executemany,
    ) -> None:
        context._mybook_perf_start = time.perf_counter()

    def _after_cursor_execute(
        self,
        conn,
        cursor,
        statement,
        parameters,
        context,
        executemany,
    ) -> None:
        started = getattr(context, "_mybook_perf_start", None)
        if started is not None:
            self.time_ms += (time.perf_counter() - started) * 1000.0
        self.query_count += 1


class ProfilingLLMProvider(LLMProvider):
    """Wrap any provider and measure LLM call count and latency."""

    def __init__(self, inner: LLMProvider):
        super().__init__(inner.model, inner.temperature, inner.max_tokens)
        self.inner = inner
        self.call_count = 0
        self.time_ms = 0.0

    def snapshot(self) -> CounterSnapshot:
        return CounterSnapshot(llm_call_count=self.call_count, llm_time_ms=self.time_ms)

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        started = time.perf_counter()
        try:
            return await self.inner.generate(prompt, system_prompt, **kwargs)
        finally:
            self.call_count += 1
            self.time_ms += (time.perf_counter() - started) * 1000.0

    async def generate_structured(
        self,
        prompt: str,
        system_prompt: Optional[str],
        response_schema: dict[str, Any],
        **kwargs,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        try:
            return await self.inner.generate_structured(
                prompt,
                system_prompt,
                response_schema,
                **kwargs,
            )
        finally:
            self.call_count += 1
            self.time_ms += (time.perf_counter() - started) * 1000.0

    async def chat(self, messages: list[dict[str, str]], **kwargs) -> LLMResponse:
        started = time.perf_counter()
        try:
            return await self.inner.chat(messages, **kwargs)
        finally:
            self.call_count += 1
            self.time_ms += (time.perf_counter() - started) * 1000.0


class StageProfiler:
    """Build StageMetric rows from query and LLM counter deltas."""

    def __init__(self, query_profiler: QueryProfiler, llm_profiler: ProfilingLLMProvider):
        self.query_profiler = query_profiler
        self.llm_profiler = llm_profiler
        self.metrics: list[StageMetric] = []

    @contextmanager
    def stage(
        self,
        name: str,
        *,
        chapter_no: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Iterator[None]:
        started = time.perf_counter()
        db_start = self.query_profiler.snapshot()
        llm_start = self.llm_profiler.snapshot()
        try:
            yield
        finally:
            db_end = self.query_profiler.snapshot()
            llm_end = self.llm_profiler.snapshot()
            self.metrics.append(
                StageMetric(
                    stage=name,
                    chapter_no=chapter_no,
                    elapsed_ms=(time.perf_counter() - started) * 1000.0,
                    db_query_count=db_end.db_query_count - db_start.db_query_count,
                    db_time_ms=db_end.db_time_ms - db_start.db_time_ms,
                    llm_call_count=llm_end.llm_call_count - llm_start.llm_call_count,
                    llm_time_ms=llm_end.llm_time_ms - llm_start.llm_time_ms,
                    metadata=metadata or {},
                )
            )


class RunProfiler:
    """Own cProfile and tracemalloc lifecycle for one performance run."""

    def __init__(self, *, profile_cpu: bool, profile_memory: bool):
        self.profile_cpu = profile_cpu
        self.profile_memory = profile_memory
        self.cpu_profiler = cProfile.Profile() if profile_cpu else None
        self.memory_current_kb = 0.0
        self.memory_peak_kb = 0.0
        self._memory_snapshot = None

    def start(self) -> None:
        if self.profile_memory:
            tracemalloc.start()
        if self.cpu_profiler is not None:
            self.cpu_profiler.enable()

    def stop(self) -> None:
        if self.cpu_profiler is not None:
            self.cpu_profiler.disable()
        if self.profile_memory and tracemalloc.is_tracing():
            current, peak = tracemalloc.get_traced_memory()
            self.memory_current_kb = current / 1024.0
            self.memory_peak_kb = peak / 1024.0
            self._memory_snapshot = tracemalloc.take_snapshot()
            tracemalloc.stop()

    def memory_snapshot_kb(self) -> tuple[float, float]:
        if not self.profile_memory or not tracemalloc.is_tracing():
            return self.memory_current_kb, self.memory_peak_kb
        current, peak = tracemalloc.get_traced_memory()
        return current / 1024.0, peak / 1024.0

    def write_cpu_files(self, run_dir: Path) -> dict[str, str]:
        if self.cpu_profiler is None:
            return {}
        prof_path = run_dir / "raw_profile.prof"
        top_path = run_dir / "cpu_top.txt"
        self.cpu_profiler.dump_stats(prof_path)
        with top_path.open("w", encoding="utf-8") as handle:
            handle.write("Top cumulative time\n")
            handle.write("===================\n")
            stats = pstats.Stats(self.cpu_profiler, stream=handle)
            stats.strip_dirs().sort_stats("cumulative").print_stats(50)
            handle.write("\nTop internal time\n")
            handle.write("=================\n")
            stats = pstats.Stats(self.cpu_profiler, stream=handle)
            stats.strip_dirs().sort_stats("tottime").print_stats(50)
        return {"cpu_profile": str(prof_path), "cpu_top": str(top_path)}

    def write_memory_file(self, run_dir: Path) -> dict[str, str]:
        top_path = run_dir / "memory_top.txt"
        snapshot_path = run_dir / "tracemalloc_snapshot.txt"
        text_lines: list[str] = []
        if self._memory_snapshot is None:
            text_lines.append("tracemalloc disabled")
        else:
            for index, stat in enumerate(
                self._memory_snapshot.statistics("lineno")[:50],
                start=1,
            ):
                text_lines.append(f"{index:02d}. {stat}")
        with top_path.open("w", encoding="utf-8") as handle:
            handle.write("\n".join(text_lines) + "\n")
        with snapshot_path.open("w", encoding="utf-8") as handle:
            handle.write("\n".join(text_lines) + "\n")
        return {
            "memory_top": str(top_path),
            "tracemalloc_snapshot": str(snapshot_path),
        }
