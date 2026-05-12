"""Schemas for long-form generation performance runs."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class PerformanceRunIssue(BaseModel):
    """Functional, performance, or environment issue found during a run."""

    category: str
    severity: str = "info"
    chapter_no: Optional[int] = None
    module: str = ""
    function: str = ""
    message: str
    root_cause: str = ""
    fix: str = ""


class PerformanceRunRequest(BaseModel):
    """Configuration for a batch generation performance run."""

    chapter_count: int = Field(default=60, ge=1, le=200)
    start_chapter_no: int = Field(default=1, ge=1)
    use_scene_mode: bool = False
    scene_count: int = Field(default=2, ge=1, le=8)
    target_word_count: int = Field(default=3000, ge=500, le=10000)
    min_body_chars: int = Field(default=2500, ge=1, le=20000)
    max_word_count_retries: int = Field(default=3, ge=0, le=10)
    include_review: bool = False
    concurrency: int = Field(default=1, ge=1, le=1)
    llm_provider: str = "mock"
    resume: bool = True
    profile_cpu: bool = True
    profile_memory: bool = True
    report_root: str = "reports/performance"
    run_id: Optional[str] = None
    project_title: Optional[str] = None
    project_genre: Optional[str] = None
    project_premise: Optional[str] = None


class StageMetric(BaseModel):
    """Timing and resource deltas for one named stage."""

    stage: str
    chapter_no: Optional[int] = None
    elapsed_ms: float
    db_query_count: int = 0
    db_time_ms: float = 0.0
    llm_call_count: int = 0
    llm_time_ms: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChapterPerformanceMetric(BaseModel):
    """Per-chapter result and resource summary."""

    chapter_id: int
    chapter_no: int
    title: str = ""
    status: str
    elapsed_ms: float
    word_count: int = 0
    char_count: int = 0
    planner_duration_ms: float = 0.0
    memory_context_duration_ms: float = 0.0
    writer_duration_ms: float = 0.0
    reviewer_duration_ms: float = 0.0
    state_update_duration_ms: float = 0.0
    db_query_count: int = 0
    db_time_ms: float = 0.0
    llm_call_count: int = 0
    llm_time_ms: float = 0.0
    local_compute_ms: float = 0.0
    memory_current_kb: float = 0.0
    memory_peak_kb: float = 0.0
    retry_count: int = 0
    error_count: int = 0
    error: str = ""


class PerformanceRunSummary(BaseModel):
    """Top-level run summary."""

    run_id: str
    project_id: int
    started_at: datetime
    finished_at: datetime
    total_elapsed_ms: float
    total_chapters: int
    generated_chapters: int
    failed_chapters: int
    min_body_chars: int = 2500
    completed: bool = False
    every_chapter_meets_minimum: bool = False
    total_body_chars: int = 0
    average_body_chars: float = 0.0
    average_chapter_elapsed_ms: float = 0.0
    llm_wait_ratio: float = 0.0
    local_compute_ratio: float = 0.0
    report_dir: str
    requested_provider: str = "mock"
    actual_provider: str = "mock"
    db_query_count: int = 0
    db_time_ms: float = 0.0
    llm_call_count: int = 0
    llm_time_ms: float = 0.0
    memory_current_kb: float = 0.0
    memory_peak_kb: float = 0.0


class PerformanceRunReport(BaseModel):
    """Complete performance run report returned by API and CLI."""

    summary: PerformanceRunSummary
    chapters: list[ChapterPerformanceMetric]
    stage_metrics: list[StageMetric]
    issues: list[PerformanceRunIssue] = Field(default_factory=list)
    run_config: dict[str, Any] = Field(default_factory=dict)
    optimization_notes: list[str] = Field(default_factory=list)
    artifacts: dict[str, str] = Field(default_factory=dict)
