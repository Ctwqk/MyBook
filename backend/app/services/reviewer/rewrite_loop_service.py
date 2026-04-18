"""Rewrite Loop Service - v2.7 核心功能

模式特定的失败-重写循环机制：
- checkpoint: 保持不变
- blackbox: 自动重写，3次失败后 force-accept
- copilot: 自动重写，3次失败后停止在 needs_review
"""
import json
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chapter import Chapter, ChapterStatus
from app.models.chapter_rewrite_attempt import ChapterRewriteAttempt
from app.models.project import Project
from app.repositories.chapter import ChapterRepository
from app.repositories.project import ProjectRepository
from app.services.reviewer.v2_7_experience_overlay import (
    ReviewVerdictV3,
    RepairInstruction,
)
from app.services.reviewer.historical_review_hub import HistoricalReviewHub
from app.services.reviewer.web_novel_reviewer import WebNovelExperienceReviewer
from app.services.reviewer.prompts import WRITER_REPAIR_PROMPT


class RewriteScope(str, Enum):
    """修复范围枚举"""
    SCENE = "scene"
    BAND = "band"
    ARC = "arc"


class OperationMode(str, Enum):
    """系统运行模式"""
    BLACKBOX = "blackbox"
    CHECKPOINT = "checkpoint"
    COPAYILOT = "copilot"  # 注意：与 orchestrator 保持一致


class RewriteLoopResult(BaseModel):
    """重写循环结果"""
    success: bool
    final_verdict: str  # pass/warn/fail
    attempt_count: int
    final_draft_id: Optional[int] = None
    forced_accept_applied: bool = False
    rewrite_attempts: list[dict] = []
    
    # 审查摘要
    review_summary: Optional[str] = None
    
    # 模式信息
    mode: str
    stopped_at_needs_review: bool = False


class RewriteLoopService:
    """重写循环服务 - v2.7 核心
    
    模式特定行为：
    - checkpoint: 不自动重写，保持 needs_review
    - blackbox: 自动重写 scene->band->arc，3次后 force-accept
    - copilot: 自动重写，3次后停止在 needs_review
    """
    
    MAX_REWRITE_ATTEMPTS = 3
    
    def __init__(
        self,
        db: AsyncSession,
        llm_provider=None,
        operation_mode: str = "checkpoint"
    ):
        self.db = db
        self.llm = llm_provider
        self.operation_mode = OperationMode(operation_mode)
        
        # 初始化服务
        self.review_hub = HistoricalReviewHub(llm_provider)
        self.wner = WebNovelExperienceReviewer(llm_provider)
        self.chapter_repo = ChapterRepository(db)
        self.project_repo = ProjectRepository(db)
    
    async def execute_review_with_rewrite_loop(
        self,
        project_id: int,
        chapter_id: int,
        chapter_text: str,
        planned_experience: Optional[dict[str, Any]] = None,
        context: Optional[dict[str, Any]] = None
    ) -> RewriteLoopResult:
        """
        执行审查并处理重写循环
        
        Args:
            project_id: 项目 ID
            chapter_id: 章节 ID
            chapter_text: 章节正文
            planned_experience: 计划的体验内容
            context: 上下文
            
        Returns:
            RewriteLoopResult: 重写循环结果
        """
        chapter = await self.chapter_repo.get(chapter_id)
        if not chapter:
            raise ValueError(f"Chapter {chapter_id} not found")
        
        rewrite_attempts = []
        current_text = chapter_text
        current_attempt = 0
        
        # Step 1: 首次审查
        first_verdict = await self._run_review(
            project_id, chapter_id, current_text, planned_experience, context
        )
        
        # checkpoint 模式：不自动重写
        if self.operation_mode == OperationMode.CHECKPOINT:
            return RewriteLoopResult(
                success=first_verdict.verdict != "fail",
                final_verdict=first_verdict.verdict,
                attempt_count=0,
                final_draft_id=None,
                forced_accept_applied=False,
                rewrite_attempts=[],
                review_summary=first_verdict.review_summary,
                mode=self.operation_mode.value,
                stopped_at_needs_review=True
            )
        
        # 检查首次 verdict
        if first_verdict.verdict in ["pass", "warn"]:
            # 不需要重写
            return RewriteLoopResult(
                success=True,
                final_verdict=first_verdict.verdict,
                attempt_count=0,
                final_draft_id=None,
                forced_accept_applied=False,
                rewrite_attempts=[],
                review_summary=first_verdict.review_summary,
                mode=self.operation_mode.value,
                stopped_at_needs_review=first_verdict.verdict == "warn"
            )
        
        # 首次失败，进入重写循环
        current_attempt = 1
        repair_scope = RewriteScope.SCENE
        
        while current_attempt <= self.MAX_REWRITE_ATTEMPTS:
            # 记录尝试
            attempt_record = await self._record_rewrite_attempt(
                project_id=project_id,
                chapter_id=chapter_id,
                chapter_number=chapter.chapter_no,
                attempt_no=current_attempt,
                repair_scope=repair_scope.value,
                source_draft_text=current_text,
                trigger_review=first_verdict
            )
            
            # 根据 repair_scope 执行修复
            if repair_scope == RewriteScope.SCENE:
                current_text = await self._repair_scene_level(
                    project_id, chapter, current_text, first_verdict.repair_instruction
                )
            elif repair_scope == RewriteScope.BAND:
                current_text = await self._repair_band_level(
                    project_id, chapter, current_text, first_verdict.repair_instruction
                )
            elif repair_scope == RewriteScope.ARC:
                current_text = await self._repair_arc_level(
                    project_id, chapter, current_text, first_verdict.repair_instruction
                )
            
            # 重新审查
            review_result = await self._run_review(
                project_id, chapter_id, current_text, planned_experience, context
            )
            
            # 更新尝试记录
            attempt_record.result_verdict = review_result.verdict
            attempt_record.result_draft_id = chapter.id  # 简化处理
            await self.db.flush()
            
            rewrite_attempts.append({
                "attempt_no": current_attempt,
                "repair_scope": repair_scope.value,
                "verdict": review_result.verdict,
                "review_summary": review_result.review_summary
            })
            
            # 检查 verdict
            if review_result.verdict == "pass":
                return RewriteLoopResult(
                    success=True,
                    final_verdict=review_result.verdict,
                    attempt_count=current_attempt,
                    final_draft_id=chapter.id,
                    forced_accept_applied=False,
                    rewrite_attempts=rewrite_attempts,
                    review_summary=review_result.review_summary,
                    mode=self.operation_mode.value,
                    stopped_at_needs_review=False
                )
            
            if review_result.verdict == "warn":
                # copilot: 停止在 needs_review
                # blackbox: 继续重写
                if self.operation_mode == OperationMode.COPAYILOT:
                    return RewriteLoopResult(
                        success=True,
                        final_verdict="warn",
                        attempt_count=current_attempt,
                        final_draft_id=chapter.id,
                        forced_accept_applied=False,
                        rewrite_attempts=rewrite_attempts,
                        review_summary=review_result.review_summary,
                        mode=self.operation_mode.value,
                        stopped_at_needs_review=True
                    )
            
            # 递增修复范围
            current_attempt += 1
            if current_attempt <= self.MAX_REWRITE_ATTEMPTS:
                repair_scope = self._escalate_scope(repair_scope)
        
        # 3 次重写后仍然失败
        if self.operation_mode == OperationMode.BLACKBOX:
            # blackbox: force-accept
            final_verdict = await self._run_review(
                project_id, chapter_id, current_text, planned_experience, context
            )
            
            # 记录强制接受
            await self._record_force_accept(
                project_id, chapter_id, chapter.chapter_no,
                current_attempt, final_verdict
            )
            
            return RewriteLoopResult(
                success=True,  # 虽然失败但 force-accept
                final_verdict="fail",  # 保持真实 verdict
                attempt_count=current_attempt,
                final_draft_id=chapter.id,
                forced_accept_applied=True,
                rewrite_attempts=rewrite_attempts,
                review_summary=final_verdict.review_summary,
                mode=self.operation_mode.value,
                stopped_at_needs_review=False
            )
        else:
            # copilot: 停止在 needs_review
            return RewriteLoopResult(
                success=False,
                final_verdict="fail",
                attempt_count=current_attempt,
                final_draft_id=None,
                forced_accept_applied=False,
                rewrite_attempts=rewrite_attempts,
                review_summary="重写循环耗尽，章节需要人工审查",
                mode=self.operation_mode.value,
                stopped_at_needs_review=True
            )
    
    async def _run_review(
        self,
        project_id: int,
        chapter_id: int,
        chapter_text: str,
        planned_experience: Optional[dict[str, Any]],
        context: Optional[dict[str, Any]]
    ) -> ReviewVerdictV3:
        """运行审查"""
        return await self.review_hub.review_chapter(
            chapter_text=chapter_text,
            chapter_no=0,  # 需要传入真实值
            chapter_id=chapter_id,
            context=context or {},
            planned_experience=planned_experience
        )
    
    async def _record_rewrite_attempt(
        self,
        project_id: int,
        chapter_id: int,
        chapter_number: int,
        attempt_no: int,
        repair_scope: str,
        source_draft_text: str,
        trigger_review: ReviewVerdictV3
    ) -> ChapterRewriteAttempt:
        """记录重写尝试"""
        attempt = ChapterRewriteAttempt(
            project_id=project_id,
            chapter_id=chapter_id,
            chapter_number=chapter_number,
            attempt_no=attempt_no,
            repair_scope=repair_scope,
            trigger_review_id=None,  # 需要关联 review_notes 表
            design_patch_json=json.dumps(
                trigger_review.repair_instruction.model_dump()
                if trigger_review.repair_instruction else {}
            ),
            source_draft_id=None,
            result_verdict=None,
            forced_accept_applied=False,
            repair_instruction_summary=trigger_review.review_summary
        )
        self.db.add(attempt)
        await self.db.flush()
        return attempt
    
    async def _record_force_accept(
        self,
        project_id: int,
        chapter_id: int,
        chapter_number: int,
        attempt_count: int,
        final_verdict: ReviewVerdictV3
    ):
        """记录强制接受"""
        attempt = ChapterRewriteAttempt(
            project_id=project_id,
            chapter_id=chapter_id,
            chapter_number=chapter_number,
            attempt_no=attempt_count,
            repair_scope="arc",  # 最终尝试是 arc 级别
            design_patch_json=json.dumps({"force_accept": True}),
            result_verdict="fail",  # 保持真实 verdict
            forced_accept_applied=True,
            repair_instruction_summary="Force-accept: 自动重写循环耗尽"
        )
        self.db.add(attempt)
        await self.db.flush()
    
    def _escalate_scope(self, current: RewriteScope) -> RewriteScope:
        """升级修复范围"""
        if current == RewriteScope.SCENE:
            return RewriteScope.BAND
        elif current == RewriteScope.BAND:
            return RewriteScope.ARC
        else:
            return RewriteScope.ARC
    
    async def _repair_scene_level(
        self,
        project_id: int,
        chapter: Chapter,
        current_text: str,
        repair_instruction: Optional[RepairInstruction]
    ) -> str:
        """Scene 级别修复
        
        重新生成：
        - 章节级体验计划
        - 场景分解
        - 必须进展点
        - 钩子、锚点、进度标记
        """
        # 更新章节状态
        chapter.text = current_text
        chapter.status = ChapterStatus.DRAFT
        await self.db.flush()
        
        # 调用 writer 进行 scene 级别重写
        # 这里简化处理，实际需要调用 WriterService
        return await self._invoke_writer_repair(
            project_id, chapter, current_text, repair_instruction, "scene"
        )
    
    async def _repair_band_level(
        self,
        project_id: int,
        chapter: Chapter,
        current_text: str,
        repair_instruction: Optional[RepairInstruction]
    ) -> str:
        """Band 级别修复
        
        调整：
        - 当前 Band 的愉悦时刻表
        - 刷新章节体验计划
        """
        # TODO: 刷新 BandDelightSchedule
        return await self._invoke_writer_repair(
            project_id, chapter, current_text, repair_instruction, "band"
        )
    
    async def _repair_arc_level(
        self,
        project_id: int,
        chapter: Chapter,
        current_text: str,
        repair_instruction: Optional[RepairInstruction]
    ) -> str:
        """Arc 级别修复
        
        应用最小化的 near-term active-arc 补丁到：
        - ArcPayoffMap
        - ArcStructureDraft
        """
        # TODO: 应用 Arc 级别补丁
        return await self._invoke_writer_repair(
            project_id, chapter, current_text, repair_instruction, "arc"
        )
    
    async def _invoke_writer_repair(
        self,
        project_id: int,
        chapter: Chapter,
        current_text: str,
        repair_instruction: Optional[RepairInstruction],
        scope: str
    ) -> str:
        """调用 Writer 进行修复重写"""
        if not self.llm:
            return current_text  # 无 LLM 时返回原文
        
        # 构建修复提示
        must_fix = []
        must_preserve = []
        if repair_instruction:
            must_fix = repair_instruction.must_fix
            must_preserve = repair_instruction.must_preserve
        
        prompt = WRITER_REPAIR_PROMPT.format(
            chapter_no=chapter.chapter_no,
            title=chapter.title or f"第{chapter.chapter_no}章",
            existing_text=current_text,
            repair_scope=scope,
            must_fix="\n".join([f"- {m}" for m in must_fix]) if must_fix else "无",
            must_preserve="\n".join([f"- {m}" for m in must_preserve]) if must_preserve else "无"
        )
        
        try:
            response = await self.llm.generate(prompt, system_prompt="你是一个专业的小说编辑。")
            return response.content.strip()
        except Exception:
            return current_text


# Pydantic BaseModel 导入
from pydantic import BaseModel
