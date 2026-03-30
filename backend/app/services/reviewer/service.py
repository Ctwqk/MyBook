"""Reviewer Service - 审查服务"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.base import LLMProvider
from app.llm.mock import MockLLMProvider
from app.models.chapter import Chapter
from app.models.review_note import IssueType, Severity, ReviewNote
from app.schemas.review import (
    ReviewRequest,
    ReviewResponse,
    ReviewVerdict,
    ReviewIssue,
    PartialReviewRequest,
    RewriteInstructionsResponse,
    ReviewNoteResponse,
)
from app.schemas.memory import ContextPackRequest
from app.repositories.chapter import ChapterRepository
from app.services.memory.service import MemoryService
from app.services.reviewer.prompts import (
    CHAPTER_REVIEW_PROMPT,
    PARTIAL_REVIEW_PROMPT,
    REWRITE_INSTRUCTIONS_PROMPT,
)


class ReviewerService:
    """审查服务"""

    def __init__(
        self,
        db: AsyncSession,
        llm_provider: Optional[LLMProvider] = None
    ):
        self.db = db
        self.llm = llm_provider or MockLLMProvider()
        self.chapter_repo = ChapterRepository(db)
        self.memory_service = MemoryService(db)

    async def review_chapter(
        self,
        project_id: int,
        chapter_id: int,
        request: ReviewRequest
    ) -> ReviewResponse:
        """
        审查章节
        
        Args:
            project_id: 项目 ID
            chapter_id: 章节 ID
            request: 审查请求
            
        Returns:
            ReviewResponse: 审查响应
        """
        chapter = await self.chapter_repo.get(chapter_id)
        if not chapter:
            raise ValueError(f"Chapter {chapter_id} not found")
        
        if not chapter.text:
            return ReviewResponse(
                chapter_id=chapter_id,
                verdict=ReviewVerdict(
                    approved=False,
                    score=0,
                    issues=[],
                    summary="章节正文为空，无法审查"
                )
            )
        
        # 获取上下文
        context_request = ContextPackRequest(
            chapter_id=chapter_id,
            include_story_bible=True,
            include_character_states=True,
            include_recent_chapters=2,
            include_foreshadows=True
        )
        context_pack = await self.memory_service.build_context_pack(project_id, context_request)
        
        # 构建审查类型
        check_types = request.check_types or ["consistency", "pacing", "hook"]
        check_types_str = ", ".join(check_types)
        
        system_prompt = """你是一个专业的小说编辑和批评家。你的任务是审查小说章节，
        从多个维度评估章节质量，并提供具体的改进建议。"""
        
        prompt = CHAPTER_REVIEW_PROMPT.format(
            chapter_no=chapter.chapter_no,
            title=chapter.title or f"第{chapter.chapter_no}章",
            text=chapter.text,
            outline=chapter.outline or "",
            context=context_pack.formatted_context,
            check_types=check_types_str
        )
        
        response = await self.llm.generate(prompt, system_prompt)
        
        # TODO: 解析 LLM 返回的审查结果
        # 暂时返回模拟数据
        verdict = self._parse_mock_verdict(response.content, chapter_id)
        
        # 创建审查笔记
        review_notes = []
        for issue in verdict.issues:
            note = await self.memory_service.record_review_note(
                project_id=project_id,
                chapter_id=chapter_id,
                issue_type=issue.issue_type.value,
                severity=issue.severity.value,
                description=issue.description,
                fix_suggestion=issue.fix_suggestion
            )
            # 手动转换 ORM 对象到 Schema
            review_notes.append(ReviewNoteResponse(
                id=note.id,
                chapter_id=note.chapter_id,
                issue_type=note.issue_type.value,
                severity=note.severity.value,
                description=note.description,
                fix_suggestion=note.fix_suggestion,
                created_at=note.created_at
            ))
        
        return ReviewResponse(
            chapter_id=chapter_id,
            verdict=verdict,
            review_notes=review_notes
        )

    async def review_partial(
        self,
        project_id: int,
        chapter_id: int,
        request: PartialReviewRequest
    ) -> ReviewResponse:
        """
        部分审查 - 审查章节的特定段落
        
        Args:
            project_id: 项目 ID
            chapter_id: 章节 ID
            request: 部分审查请求
            
        Returns:
            ReviewResponse: 审查响应
        """
        check_types = request.check_types or ["consistency", "pacing"]
        check_types_str = ", ".join(check_types)
        
        system_prompt = """你是一个专业的小说编辑。请审查以下段落，给出改进建议。"""
        
        prompt = PARTIAL_REVIEW_PROMPT.format(
            segment_text=request.segment_text,
            segment_location=request.segment_location or "未指定",
            check_types=check_types_str
        )
        
        response = await self.llm.generate(prompt, system_prompt)
        
        # 解析审查结果
        verdict = ReviewVerdict(
            approved=True,
            score=7.0,
            issues=[],
            summary="段落审查完成",
            strengths=["文笔流畅"]
        )
        
        return ReviewResponse(
            chapter_id=chapter_id,
            verdict=verdict,
            review_notes=[]
        )

    async def build_rewrite_instructions(
        self,
        project_id: int,
        chapter_id: int
    ) -> RewriteInstructionsResponse:
        """
        构建重写指令
        
        Args:
            project_id: 项目 ID
            chapter_id: 章节 ID
            
        Returns:
            RewriteInstructionsResponse: 重写指令
        """
        chapter = await self.chapter_repo.get(chapter_id)
        if not chapter:
            raise ValueError(f"Chapter {chapter_id} not found")
        
        # 获取待处理的审查问题
        pending_reviews = await self.memory_service.get_pending_reviews(project_id)
        chapter_reviews = [r for r in pending_reviews if r.chapter_id == chapter_id]
        
        if not chapter_reviews:
            return RewriteInstructionsResponse(
                chapter_id=chapter_id,
                instructions="无需重写，章节质量良好。",
                prioritized_fixes=[]
            )
        
        # 按严重程度排序
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        chapter_reviews.sort(
            key=lambda x: severity_order.get(x.severity.value, 99)
        )
        
        # 构建问题列表
        issues_text = "\n".join([
            f"- [{r.severity.value}] {r.description} (修复建议: {r.fix_suggestion or '无'})"
            for r in chapter_reviews
        ])
        
        system_prompt = """你是一个专业的小说编辑。根据审查问题列表，
        生成清晰、可执行的重写指令。"""
        
        prompt = REWRITE_INSTRUCTIONS_PROMPT.format(
            chapter_no=chapter.chapter_no,
            issues=issues_text,
            existing_text=chapter.text[:1000] if chapter.text else ""
        )
        
        response = await self.llm.generate(prompt, system_prompt)
        
        prioritized_fixes = [r.description for r in chapter_reviews[:5]]
        
        return RewriteInstructionsResponse(
            chapter_id=chapter_id,
            instructions=response.content,
            prioritized_fixes=prioritized_fixes
        )

    def _parse_mock_verdict(self, llm_response: str, chapter_id: int) -> ReviewVerdict:
        """解析 mock 审查结果"""
        # 简单的 mock 解析
        issues = [
            ReviewIssue(
                issue_type=IssueType.PACING,
                severity=Severity.LOW,
                description="第3段节奏稍慢",
                fix_suggestion="精简描写，加快节奏"
            )
        ]
        
        return ReviewVerdict(
            approved=True,
            score=7.5,
            issues=issues,
            summary="章节整体质量良好，建议小幅修改后通过。",
            strengths=["开篇钩子设置得当", "场景描写细腻"]
        )
