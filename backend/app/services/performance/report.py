"""Report writers for generation performance runs."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable

from app.services.performance.schemas import PerformanceRunReport, StageMetric


class PerformanceReportWriter:
    """Persist Markdown, JSON, and CSV report artifacts."""

    def write(self, report: PerformanceRunReport, run_dir: Path) -> dict[str, str]:
        run_dir.mkdir(parents=True, exist_ok=True)
        artifacts = {
            "summary": str(run_dir / "summary.md"),
            "stage_metrics": str(run_dir / "stage_metrics.json"),
            "chapter_metrics": str(run_dir / "chapter_metrics.csv"),
            "errors": str(run_dir / "errors.md"),
            "optimization_plan": str(run_dir / "optimization_plan.md"),
            "run_config": str(run_dir / "run_config.json"),
        }
        self._write_summary(report, Path(artifacts["summary"]))
        self._write_stage_metrics(report, Path(artifacts["stage_metrics"]))
        self._write_chapter_metrics(report, Path(artifacts["chapter_metrics"]))
        self._write_errors(report, Path(artifacts["errors"]))
        self._write_optimization_plan(report, Path(artifacts["optimization_plan"]))
        self._write_run_config(report, Path(artifacts["run_config"]))
        return artifacts

    def _write_summary(self, report: PerformanceRunReport, path: Path) -> None:
        summary = report.summary
        slowest = sorted(report.chapters, key=lambda item: item.elapsed_ms, reverse=True)[:5]
        stage_totals = self._stage_totals(report.stage_metrics)
        completed_text = "是" if summary.completed else "否"
        minimum_text = "是" if summary.every_chapter_meets_minimum else "否"
        last_success = max(
            [chapter.chapter_no for chapter in report.chapters if chapter.status != "failed"],
            default=0,
        )
        fail_reason = "无"
        if not summary.completed:
            failures = [chapter for chapter in report.chapters if chapter.status == "failed"]
            fail_reason = failures[0].error if failures else f"只生成到第 {last_success} 章"
        memory_growth = self._memory_growth_line(report)
        db_ratio = summary.db_time_ms / summary.total_elapsed_ms if summary.total_elapsed_ms else 0.0
        memory_ms = stage_totals.get("memory.build_context_pack", 0.0)
        writer_ms = sum(value for stage, value in stage_totals.items() if stage.startswith("writer."))
        reviewer_ms = sum(value for stage, value in stage_totals.items() if stage.startswith("reviewer."))
        lines = [
            "# MyBook 60-Chapter Generation Performance Report",
            "",
            "## Completion",
            "",
            f"- 60 章是否成功完成: {completed_text}",
            f"- 如果未完成，跑到了第几章，为什么停止: 第 {last_success} 章；{fail_reason}",
            f"- 每章是否都不少于 {summary.min_body_chars} 个中文正文字符: {minimum_text}",
            f"- 成功章节数: {summary.generated_chapters}/{summary.total_chapters}",
            f"- 失败章节数: {summary.failed_chapters}",
            f"- 总字数/正文中文字符数: {summary.total_body_chars}",
            f"- 平均每章正文中文字符数: {summary.average_body_chars:.2f}",
            f"- 总耗时: {summary.total_elapsed_ms:.2f} ms",
            f"- 平均每章耗时: {summary.average_chapter_elapsed_ms:.2f} ms",
            f"- 实际 Provider: `{summary.actual_provider}`；请求 Provider: `{summary.requested_provider}`",
            "",
            "## Time Split",
            "",
            f"- LLM 等待时间: {summary.llm_time_ms:.2f} ms ({summary.llm_wait_ratio:.2%})",
            f"- 本地 Python 计算时间: {summary.total_elapsed_ms - summary.llm_time_ms:.2f} ms ({summary.local_compute_ratio:.2%})",
            f"- DB / Repository 耗时: {summary.db_time_ms:.2f} ms ({db_ratio:.2%})，查询 {summary.db_query_count} 次",
            f"- Memory / Context Pack 耗时: {memory_ms:.2f} ms",
            f"- Writer 模块耗时: {writer_ms:.2f} ms",
            f"- Reviewer 模块耗时: {reviewer_ms:.2f} ms；{'已启用' if reviewer_ms else '未启用'}",
            "",
            "## Slowest Chapters",
            "",
        ]
        if not slowest:
            lines.append("- 无章节结果。")
        for chapter in slowest:
            lines.append(
                f"- 第 {chapter.chapter_no} 章 `{chapter.title}`: "
                f"{chapter.elapsed_ms:.2f} ms，正文字符 {chapter.char_count}，"
                f"LLM {chapter.llm_time_ms:.2f} ms，DB {chapter.db_time_ms:.2f} ms，"
                f"Memory {chapter.memory_context_duration_ms:.2f} ms，"
                f"Writer {chapter.writer_duration_ms:.2f} ms，状态 `{chapter.status}`"
            )
        lines.extend(
            [
                "",
                "## Hotspots",
                "",
                "- CPU 热点: 见 `cpu_top.txt`，其中包含 cumulative time 与 internal time 两组排序。",
                "- 内存热点: 见 `memory_top.txt` 与 `tracemalloc_snapshot.txt`。",
                f"- 峰值内存: {summary.memory_peak_kb:.2f} KB；当前追踪内存: {summary.memory_current_kb:.2f} KB。",
                f"- 是否存在内存随章节增长的问题: {memory_growth}",
                "",
                "## Module Totals",
                "",
            ]
        )
        for stage, elapsed_ms in sorted(stage_totals.items(), key=lambda item: item[1], reverse=True):
            lines.append(f"- {stage}: {elapsed_ms:.2f} ms")
        functional = [issue for issue in report.issues if issue.category == "functional bug"]
        performance = [issue for issue in report.issues if issue.category == "performance issue"]
        environment = [issue for issue in report.issues if issue.category == "environment issue"]
        lines.extend(
            [
                "",
                "## Issue Classification",
                "",
                f"- 功能 bug: {len(functional)} 个",
                f"- 性能问题: {len(performance)} 个",
                f"- 环境限制: {len(environment)} 个",
                "- 已经做的修复: 见 `errors.md`。",
                "- 已经做的优化: 见 `optimization_plan.md`。",
                "- 优化前后指标是否有变化: 首轮报告记录基线；优化复测报告应在本节补充具体对比。",
                "",
                "## Next Top 5",
                "",
                "1. 用真实 LLM provider 复测端到端延迟，并继续保持 mock 基线用于本地热点定位。",
                "2. 如果 `memory.build_context_pack` 占比升高，缓存 StoryBible/角色静态数据并限制 recent chapter 文本长度。",
                "3. 如果 DB 查询占比升高，合并章节上下文读取并为 project/chapter 查询路径补索引。",
                "4. 如果 `writer.text_cleaning` 或 JSON parsing 进入 CPU top，预编译正则并收敛 fallback 解析次数。",
                "5. 保留 per-chapter checkpoint/resume，避免真实长跑失败后重跑已达标章节。",
            ]
        )
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _write_stage_metrics(self, report: PerformanceRunReport, path: Path) -> None:
        payload = [metric.model_dump(mode="json") for metric in report.stage_metrics]
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _write_chapter_metrics(self, report: PerformanceRunReport, path: Path) -> None:
        fieldnames = [
            "chapter_no",
            "chapter_id",
            "title",
            "word_count",
            "char_count",
            "total_duration_ms",
            "planner_duration_ms",
            "memory_context_duration_ms",
            "writer_duration_ms",
            "reviewer_duration_ms",
            "state_update_duration_ms",
            "db_query_count",
            "db_duration_ms",
            "llm_call_count",
            "llm_wait_duration_ms",
            "local_compute_duration_ms",
            "memory_current_kb",
            "memory_peak_kb",
            "retry_count",
            "error_count",
            "status",
            "error",
        ]
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for chapter in report.chapters:
                writer.writerow(
                    {
                        "chapter_no": chapter.chapter_no,
                        "chapter_id": chapter.chapter_id,
                        "title": chapter.title,
                        "word_count": chapter.word_count,
                        "char_count": chapter.char_count,
                        "total_duration_ms": f"{chapter.elapsed_ms:.4f}",
                        "planner_duration_ms": f"{chapter.planner_duration_ms:.4f}",
                        "memory_context_duration_ms": f"{chapter.memory_context_duration_ms:.4f}",
                        "writer_duration_ms": f"{chapter.writer_duration_ms:.4f}",
                        "reviewer_duration_ms": f"{chapter.reviewer_duration_ms:.4f}",
                        "state_update_duration_ms": f"{chapter.state_update_duration_ms:.4f}",
                        "db_query_count": chapter.db_query_count,
                        "db_duration_ms": f"{chapter.db_time_ms:.4f}",
                        "llm_call_count": chapter.llm_call_count,
                        "llm_wait_duration_ms": f"{chapter.llm_time_ms:.4f}",
                        "local_compute_duration_ms": f"{chapter.local_compute_ms:.4f}",
                        "memory_current_kb": f"{chapter.memory_current_kb:.4f}",
                        "memory_peak_kb": f"{chapter.memory_peak_kb:.4f}",
                        "retry_count": chapter.retry_count,
                        "error_count": chapter.error_count,
                        "status": chapter.status,
                        "error": chapter.error,
                    }
                )

    def _write_errors(self, report: PerformanceRunReport, path: Path) -> None:
        lines = ["# Errors and Fixes", ""]
        if not report.issues:
            lines.append("No issues were recorded during this run.")
        for issue in report.issues:
            chapter = f" chapter={issue.chapter_no}" if issue.chapter_no is not None else ""
            lines.extend(
                [
                    f"## {issue.category} / {issue.severity}{chapter}",
                    "",
                    f"- Module: `{issue.module}`",
                    f"- Function: `{issue.function}`",
                    f"- Message: {issue.message}",
                    f"- Root cause: {issue.root_cause or 'not specified'}",
                    f"- Fix: {issue.fix or 'not specified'}",
                    "",
                ]
            )
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _write_optimization_plan(self, report: PerformanceRunReport, path: Path) -> None:
        stage_totals = self._stage_totals(report.stage_metrics)
        ranked = sorted(stage_totals.items(), key=lambda item: item[1], reverse=True)[:10]
        lines = [
            "# Optimization Plan",
            "",
            "Evidence is based on this run's stage metrics, CPU profile, memory snapshot, and per-chapter CSV.",
            "",
            "## Ranked Stage Costs",
            "",
        ]
        if not ranked:
            lines.append("- No stage metrics were captured.")
        for stage, elapsed_ms in ranked:
            lines.append(f"- {stage}: {elapsed_ms:.2f} ms")
        lines.extend(
            [
                "",
                "## Applied Safeguards",
                "",
                "- Added deterministic long-form mock baseline for local CPU/memory profiling.",
                "- Added strict Chinese body-character validation and continuation retry loop.",
                "- Added per-chapter commit/checkpoint behavior so failed chapters do not force full reruns.",
                "- Avoided persisting empty AudienceHintPack rows when no AudienceSignal exists.",
                "- Removed an avoidable second body-character validation pass in the success path.",
                "- Added module timing for planner, memory context, audience mapping, writer, reviewer, DB, LLM, text cleaning, structured extraction, persistence, and word-count validation.",
                "",
                "## Candidate Optimizations",
                "",
                "- Cache static context components if memory context construction dominates.",
                "- Keep recent chapter context bounded to avoid prompt and memory growth.",
                "- Precompile hot regexes if text cleaning or parsing appears in CPU top.",
                "- Batch or reduce repeated repository calls when DB time exceeds local compute noise.",
                "- Keep review/state update disabled for baseline runs unless specifically measuring those modules.",
            ]
        )
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _write_run_config(self, report: PerformanceRunReport, path: Path) -> None:
        payload = {
            "summary": report.summary.model_dump(mode="json"),
            "run_config": report.run_config,
            "artifacts": report.artifacts,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _stage_totals(self, metrics: Iterable[StageMetric]) -> dict[str, float]:
        totals: dict[str, float] = {}
        for metric in metrics:
            totals[metric.stage] = totals.get(metric.stage, 0.0) + metric.elapsed_ms
        return totals

    def _memory_growth_line(self, report: PerformanceRunReport) -> str:
        if len(report.chapters) < 2:
            return "样本不足，无法判断。"
        first = report.chapters[0].memory_current_kb
        last = report.chapters[-1].memory_current_kb
        delta = last - first
        per_chapter = delta / max(len(report.chapters) - 1, 1)
        if delta > 1024 and per_chapter > 10:
            return f"疑似增长，首章 {first:.2f} KB，末章 {last:.2f} KB，约 {per_chapter:.2f} KB/章。"
        return f"未见明显线性增长，首章 {first:.2f} KB，末章 {last:.2f} KB，差值 {delta:.2f} KB。"
