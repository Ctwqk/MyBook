"""
Writing Orchestrator - 写作编排器

核心职责：
1. 统一调度 Planner, Memory, Writer, Reviewer 四个模块
2. 管理写作会话状态
3. 处理审查失败的重试逻辑
4. 提供完整的主流程闭环

调用顺序：
用户输入想法 → Planner 出蓝图 → Memory 组上下文 → Writer 写章节 → Reviewer 审查 → Memory 回写

审查失败分支：
- patch_required: Writer 局部修补 → Reviewer 再审
- rewrite_required + outline_ok: Writer 重写 → Reviewer 再审
- rewrite_required + outline_bad: Planner 修章纲 → Memory 重组 → Writer 重写 → Reviewer 再审
"""

import logging
from typing import Optional
from datetime import datetime

from app.core.exceptions import BusinessError
from app.services.planner.service import PlannerService
from app.services.memory.service import MemoryService
from app.services.writer.service import WriterService
from app.services.reviewer.service import ReviewerService

from .schemas import (
    StoryPackage,
    ContextPack,
    ChapterDraft,
    ReviewResult,
    WritingSession,
)

logger = logging.getLogger(__name__)


class WritingOrchestrator:
    """
    写作编排器
    
    统一调度四个写作 Agent，提供完整的主流程闭环。
    """

    def __init__(
        self,
        planner_service: Optional[PlannerService] = None,
        memory_service: Optional[MemoryService] = None,
        writer_service: Optional[WriterService] = None,
        reviewer_service: Optional[ReviewerService] = None,
    ):
        """
        初始化 Orchestrator
        
        Args:
            planner_service: Planner 服务实例
            memory_service: Memory 服务实例
            writer_service: Writer 服务实例
            reviewer_service: Reviewer 服务实例
        """
        self.planner = planner_service or PlannerService()
        self.memory = memory_service or MemoryService()
        self.writer = writer_service or WriterService()
        self.reviewer = reviewer_service or ReviewerService()
        
        # 会话状态
        self._sessions: dict[str, WritingSession] = {}

    # ========================================
    # 阶段一：项目初始化
    # ========================================

    async def run_bootstrap(
        self,
        project_id: str,
        premise: str,
        genre: Optional[str] = None,
        style: Optional[str] = None,
        target_length: Optional[int] = None,
    ) -> StoryPackage:
        """
        运行项目引导流程
        
        执行顺序：
        1. Planner 解析 premise
        2. Planner 生成 Story Bible
        3. Planner 生成角色卡
        4. Planner 生成卷纲
        5. Planner 生成章纲
        
        Args:
            project_id: 项目 ID
            premise: 用户输入的想法/剧情
            genre: 类型（可选）
            style: 风格（可选）
            target_length: 目标字数（可选）
            
        Returns:
            StoryPackage: 完整的故事包
        """
        logger.info(f"[Orchestrator] Starting bootstrap for project {project_id}")
        
        try:
            # Step 1: 解析 premise
            logger.info("[Orchestrator] Step 1: Parsing premise...")
            structured_premise = await self.planner.parse_premise(premise, genre, style)
            
            # Step 2: 生成 Story Bible
            logger.info("[Orchestrator] Step 2: Generating Story Bible...")
            story_bible = await self.planner.generate_story_bible(
                structured_premise=structured_premise,
                target_length=target_length,
            )
            
            # Step 3: 生成角色卡
            logger.info("[Orchestrator] Step 3: Generating Character Cards...")
            characters = await self.planner.generate_character_cards(
                structured_premise=structured_premise,
                story_bible=story_bible,
            )
            
            # Step 4: 生成卷纲
            logger.info("[Orchestrator] Step 4: Generating Arc Plans...")
            arcs = await self.planner.generate_arc_plan(
                story_bible=story_bible,
                characters=characters,
                target_length=target_length,
            )
            
            # Step 5: 生成章纲
            logger.info("[Orchestrator] Step 5: Generating Chapter Outlines...")
            outlines = await self.planner.generate_chapter_outlines(
                project_id=project_id,
                arcs=arcs,
                story_bible=story_bible,
                characters=characters,
            )
            
            # 组装 Story Package
            story_package = StoryPackage(
                project_id=project_id,
                structured_premise=structured_premise,
                story_bible_draft=story_bible,
                character_cards=characters,
                arc_plans=arcs,
                chapter_outlines=outlines,
            )
            
            # 写入数据库
            await self._persist_story_package(story_package)
            
            logger.info(f"[Orchestrator] Bootstrap completed for project {project_id}")
            return story_package
            
        except Exception as e:
            logger.error(f"[Orchestrator] Bootstrap failed: {str(e)}")
            raise BusinessError(f"项目引导失败: {str(e)}")

    async def _persist_story_package(self, package: StoryPackage):
        """持久化 Story Package 到数据库"""
        # 更新 Story Bible
        await self.memory.update_story_bible(
            project_id=package.project_id,
            content=package.story_bible_draft.model_dump(),
        )
        
        # 保存角色
        for char in package.character_cards:
            await self.memory.save_character_card(
                project_id=package.project_id,
                character=char.model_dump(),
            )
        
        # 保存卷纲
        for arc in package.arc_plans:
            await self.memory.save_arc_memory(
                project_id=package.project_id,
                arc_id=f"arc_{arc.volume_no}",
                summary=arc.model_dump(),
            )
        
        # 保存章纲
        for outline in package.chapter_outlines:
            await self.memory.save_chapter_outline(
                project_id=package.project_id,
                chapter_no=outline.chapter_no,
                outline=outline.model_dump(),
            )

    # ========================================
    # 阶段二：单章生成主流程
    # ========================================

    async def run_generate_chapter(
        self,
        project_id: str,
        chapter_id: str,
    ) -> ChapterDraft:
        """
        运行单章生成流程
        
        执行顺序：
        1. Memory 组装 Context Pack
        2. Writer 生成章节草稿
        
        Args:
            project_id: 项目 ID
            chapter_id: 章节 ID
            
        Returns:
            ChapterDraft: 章节草稿
        """
        logger.info(f"[Orchestrator] Starting chapter generation: {chapter_id}")
        
        # 创建/获取会话
        session = self._get_or_create_session(project_id)
        session.phase = "generating"
        session.current_chapter_id = chapter_id
        
        try:
            # Step 1: Memory 组装 Context Pack
            logger.info("[Orchestrator] Step 1: Building Context Pack...")
            context_pack = await self.memory.build_context_pack(
                project_id=project_id,
                chapter_id=chapter_id,
            )
            
            # Step 2: Writer 生成草稿
            logger.info("[Orchestrator] Step 2: Generating Chapter Draft...")
            chapter_draft = await self.writer.generate_chapter(
                project_id=project_id,
                chapter_id=chapter_id,
                outline=context_pack.chapter_outline,
                context_pack=context_pack,
            )
            
            session.status = "completed"
            logger.info(f"[Orchestrator] Chapter generation completed: {chapter_id}")
            
            return chapter_draft
            
        except Exception as e:
            session.status = "failed"
            session.error_message = str(e)
            logger.error(f"[Orchestrator] Chapter generation failed: {str(e)}")
            raise BusinessError(f"章节生成失败: {str(e)}")

    # ========================================
    # 阶段三：审查循环
    # ========================================

    async def run_review_loop(
        self,
        project_id: str,
        chapter_id: str,
        chapter_draft: ChapterDraft,
    ) -> tuple[ChapterDraft, ReviewResult]:
        """
        运行审查循环
        
        处理三种审查结果：
        1. pass: 直接返回
        2. patch_required: Writer 修补 → 再审
        3. rewrite_required: 
           - outline_ok: Writer 重写 → 再审
           - outline_bad: Planner 修章纲 → Memory 重组 → Writer 重写 → 再审
        
        Args:
            project_id: 项目 ID
            chapter_id: 章节 ID
            chapter_draft: 章节草稿
            
        Returns:
            (最终草稿, 最终审查结果)
        """
        logger.info(f"[Orchestrator] Starting review loop for {chapter_id}")
        
        session = self._get_or_create_session(project_id)
        session.current_chapter_id = chapter_id
        session.review_attempts = 0
        
        current_draft = chapter_draft
        
        while session.review_attempts < session.max_review_attempts:
            session.review_attempts += 1
            logger.info(f"[Orchestrator] Review attempt {session.review_attempts}/{session.max_review_attempts}")
            
            # 调用 Reviewer 审查
            review_result = await self.reviewer.review_chapter(
                project_id=project_id,
                chapter_id=chapter_id,
                chapter_draft=current_draft,
            )
            
            session.last_result = review_result
            
            # 分支处理
            if review_result.overall_verdict == "pass":
                logger.info(f"[Orchestrator] Review PASSED for {chapter_id}")
                return current_draft, review_result
            
            elif review_result.overall_verdict == "patch_required":
                logger.info(f"[Orchestrator] Patch required, attempting patch...")
                session.phase = "patching"
                
                current_draft = await self._handle_patch(
                    project_id, chapter_id, current_draft, review_result
                )
            
            elif review_result.overall_verdict == "rewrite_required":
                logger.info(f"[Orchestrator] Rewrite required, checking outline...")
                session.phase = "rewriting"
                
                if review_result.planner_feedback:
                    # 章纲有问题
                    logger.info("[Orchestrator] Outline issue detected, revising outline...")
                    current_draft = await self._handle_outline_rewrite(
                        project_id, chapter_id, review_result
                    )
                else:
                    # 正文问题，只需要重写
                    logger.info("[Orchestrator] Content issue, rewriting chapter...")
                    current_draft = await self._handle_content_rewrite(
                        project_id, chapter_id, current_draft, review_result
                    )
            else:
                # 未知 verdict
                logger.warning(f"[Orchestrator] Unknown verdict: {review_result.overall_verdict}")
                return current_draft, review_result
        
        # 达到最大重试次数
        logger.warning(f"[Orchestrator] Max review attempts reached for {chapter_id}")
        session.status = "failed"
        session.error_message = f"审查重试次数已达上限 ({session.max_review_attempts})"
        
        return current_draft, session.last_result

    async def _handle_patch(
        self,
        project_id: str,
        chapter_id: str,
        draft: ChapterDraft,
        review_result: ReviewResult,
    ) -> ChapterDraft:
        """处理局部修补"""
        return await self.writer.patch_chapter(
            project_id=project_id,
            chapter_id=chapter_id,
            original_draft=draft,
            patch_instructions=review_result.rewrite_instructions or "",
            scope=review_result.rewrite_scope or "partial",
        )

    async def _handle_content_rewrite(
        self,
        project_id: str,
        chapter_id: str,
        draft: ChapterDraft,
        review_result: ReviewResult,
    ) -> ChapterDraft:
        """处理正文重写（章纲没问题）"""
        return await self.writer.rewrite_chapter(
            project_id=project_id,
            chapter_id=chapter_id,
            original_outline=draft.outline,
            rewrite_instructions=review_result.rewrite_instructions or "",
            context_pack=await self.memory.build_context_pack(project_id, chapter_id),
        )

    async def _handle_outline_rewrite(
        self,
        project_id: str,
        chapter_id: str,
        review_result: ReviewResult,
    ) -> ChapterDraft:
        """处理章纲问题（需要先修章纲）"""
        # Step 1: Planner 修订章纲
        logger.info("[Orchestrator] Revising chapter outline...")
        new_outline = await self.planner.revise_outline(
            project_id=project_id,
            chapter_id=chapter_id,
            original_outline=review_result.planner_feedback or "",
            review_notes=review_result.rewrite_instructions or "",
        )
        
        # Step 2: Memory 重组上下文
        logger.info("[Orchestrator] Rebuilding context pack...")
        context_pack = await self.memory.build_context_pack(
            project_id=project_id,
            chapter_id=chapter_id,
            updated_outline=new_outline,
        )
        
        # Step 3: Writer 按新章纲重写
        logger.info("[Orchestrator] Rewriting chapter with new outline...")
        return await self.writer.generate_chapter(
            project_id=project_id,
            chapter_id=chapter_id,
            outline=new_outline,
            context_pack=context_pack,
        )

    # ========================================
    # 阶段四：最终化章节
    # ========================================

    async def run_finalize_chapter(
        self,
        project_id: str,
        chapter_id: str,
        chapter_draft: ChapterDraft,
        review_result: ReviewResult,
    ) -> None:
        """
        最终化章节 - Memory 回写所有变更
        
        回写内容：
        1. Chapter Memory
        2. Character State
        3. Arc Memory
        4. Foreshadow Records
        5. Review Notes
        6. Story Bible（仅限稳定的长期设定）
        
        Args:
            project_id: 项目 ID
            chapter_id: 章节 ID
            chapter_draft: 最终草稿
            review_result: 最终审查结果
        """
        logger.info(f"[Orchestrator] Finalizing chapter {chapter_id}")
        
        session = self._get_or_create_session(project_id)
        session.phase = "finalizing"
        
        try:
            # 1. 保存章节正文
            await self.memory.save_chapter_text(
                project_id=project_id,
                chapter_id=chapter_id,
                text=chapter_draft.chapter_text,
                summary=chapter_draft.chapter_summary,
            )
            
            # 2. 回写角色状态
            for state_change in chapter_draft.character_state_changes:
                await self.memory.update_character_states(
                    project_id=project_id,
                    character_id=state_change.character_id,
                    changes=state_change.changes,
                )
            
            # 3. 回写新世界观细节
            for detail in chapter_draft.new_world_details:
                await self.memory.record_world_detail(
                    project_id=project_id,
                    detail=detail.model_dump(),
                )
            
            # 4. 回写伏笔变化
            for fs_change in chapter_draft.new_foreshadows:
                await self.memory.record_foreshadow(
                    project_id=project_id,
                    chapter_id=chapter_id,
                    content=fs_change.content,
                    related_entities=fs_change.related_entities,
                )
            
            for fs_change in chapter_draft.resolved_foreshadows:
                await self.memory.resolve_foreshadow(
                    project_id=project_id,
                    foreshadow_id=fs_change.foreshadow_id or "",
                    resolution=fs_change.content,
                )
            
            # 5. 记录审查笔记
            for issue in review_result.issue_list:
                await self.memory.record_review_note(
                    project_id=project_id,
                    chapter_id=chapter_id,
                    issue_type=issue.issue_type,
                    description=issue.description,
                    fix_suggestion=issue.fix_suggestion,
                    severity=issue.severity,
                )
            
            # 6. 更新章节状态
            await self.memory.update_chapter_status(
                project_id=project_id,
                chapter_id=chapter_id,
                status="reviewed_passed",
            )
            
            session.status = "completed"
            logger.info(f"[Orchestrator] Chapter finalized: {chapter_id}")
            
        except Exception as e:
            session.status = "failed"
            session.error_message = f"章节最终化失败: {str(e)}"
            logger.error(f"[Orchestrator] Finalization failed: {str(e)}")
            raise BusinessError(f"章节最终化失败: {str(e)}")

    # ========================================
    # 辅助方法
    # ========================================

    def _get_or_create_session(self, project_id: str) -> WritingSession:
        """获取或创建会话"""
        if project_id not in self._sessions:
            self._sessions[project_id] = WritingSession(project_id=project_id)
        return self._sessions[project_id]

    def get_session(self, project_id: str) -> Optional[WritingSession]:
        """获取会话"""
        return self._sessions.get(project_id)

    async def run_full_chapter_workflow(
        self,
        project_id: str,
        chapter_id: str,
    ) -> tuple[ChapterDraft, ReviewResult]:
        """
        运行完整的单章工作流
        
        这是最常用的入口方法，串起整个流程：
        1. 生成章节
        2. 审查循环
        3. 最终化
        
        Args:
            project_id: 项目 ID
            chapter_id: 章节 ID
            
        Returns:
            (最终草稿, 最终审查结果)
        """
        # 1. 生成
        chapter_draft = await self.run_generate_chapter(project_id, chapter_id)
        
        # 2. 审查循环
        final_draft, final_result = await self.run_review_loop(
            project_id, chapter_id, chapter_draft
        )
        
        # 3. 最终化（只有通过才回写）
        if final_result.overall_verdict == "pass":
            await self.run_finalize_chapter(
                project_id, chapter_id, final_draft, final_result
            )
        
        return final_draft, final_result

    async def run_batch_chapters(
        self,
        project_id: str,
        chapter_ids: list[str],
    ) -> dict[str, tuple[ChapterDraft, ReviewResult]]:
        """
        批量生成章节
        
        按顺序生成多章，每章都经过完整流程
        
        Args:
            project_id: 项目 ID
            chapter_ids: 章节 ID 列表
            
        Returns:
            {chapter_id: (草稿, 审查结果)}
        """
        results = {}
        
        for chapter_id in chapter_ids:
            logger.info(f"[Orchestrator] Processing chapter {chapter_id}")
            try:
                result = await self.run_full_chapter_workflow(project_id, chapter_id)
                results[chapter_id] = result
            except Exception as e:
                logger.error(f"[Orchestrator] Failed to process {chapter_id}: {str(e)}")
                results[chapter_id] = (None, None)  # 或抛出异常
        
        return results
