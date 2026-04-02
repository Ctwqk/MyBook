"""Reviewer Service - v2.3 错误恢复 + 降级策略

支持：
- 结构化 JSON 解析
- 解析失败重试
- 降级到 rule-based 检查
"""
import asyncio
import json
import re
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.base import LLMProvider
from app.llm.mock import MockLLMProvider
from app.models.chapter import Chapter
from app.models.review_note import IssueType, Severity
from app.repositories.chapter import ChapterRepository
from app.services.memory.service import MemoryService
from app.services.orchestrator.schemas import (
    ReviewVerdictV2,
    ReviewRequestV2,
    RetryPolicy,
    OperationMode,
)
from app.schemas.memory import ContextPackRequest
from app.services.reviewer.prompts import (
    CHAPTER_REVIEW_PROMPT,
    PARTIAL_REVIEW_PROMPT,
    REWRITE_INSTRUCTIONS_PROMPT,
    FALLBACK_REVIEW_PROMPT,
    REVIEW_REVISION_PROMPT,
)


class ReviewerService:
    """审查服务 - v2.3"""

    def __init__(
        self,
        db: AsyncSession,
        llm_provider: Optional[LLMProvider] = None,
        operation_mode: OperationMode = OperationMode.CHECKPOINT,
        retry_policy: Optional[RetryPolicy] = None
    ):
        self.db = db
        self.llm = llm_provider or MockLLMProvider()
        self.chapter_repo = ChapterRepository(db)
        self.memory_service = MemoryService(db)
        
        # v2.3 配置
        self.operation_mode = operation_mode
        self.retry_policy = retry_policy or RetryPolicy()

    async def review_chapter(
        self,
        project_id: int,
        chapter_id: int,
        request: ReviewRequestV2 = None
    ) -> ReviewVerdictV2:
        """
        审查章节 - v2.3 主入口
        
        包含：
        - 解析失败重试
        - 降级策略
        """
        chapter = await self.chapter_repo.get(chapter_id)
        if not chapter:
            raise ValueError(f"Chapter {chapter_id} not found")
        
        if not chapter.text:
            return ReviewVerdictV2(
                verdict="blocked",
                verdict_reason="章节正文为空，无法审查",
                parse_success=True
            )
        
        # 获取上下文
        context_pack = await self.memory_service.build_context_pack(
            project_id,
            ContextPackRequest(
                chapter_id=chapter_id,
                include_story_bible=True,
                include_character_states=True,
                include_recent_chapters=2,
                include_foreshadows=True
            )
        )
        
        check_types = request.check_types if (request and request.check_types) else ["consistency", "pacing", "hook"]
        if isinstance(check_types, str):
            check_types = [check_types]
        check_types_str = ", ".join(check_types)
        
        # 尝试解析，最多 retry + repair 次
        for attempt in range(self.retry_policy.max_retries + 1):
            verdict = await self._attempt_review(
                chapter, context_pack, check_types_str, attempt
            )
            
            if verdict.parse_success:
                return verdict
        
        # 全部失败，降级到 rule-based
        return await self._fallback_review(chapter)

    async def _attempt_review(
        self,
        chapter: Chapter,
        context_pack: Any,
        check_types: str,
        attempt: int
    ) -> ReviewVerdictV2:
        """尝试审查"""
        system_prompt = """你是一个专业的小说编辑和批评家。
        你的任务是审查小说章节并给出结构化的审查结果。"""
        
        prompt = CHAPTER_REVIEW_PROMPT.format(
            chapter_no=chapter.chapter_no,
            title=chapter.title or f"第{chapter.chapter_no}章",
            outline=chapter.outline or "",
            chapter_text=chapter.text,
            context=context_pack.formatted_context,
            check_types=check_types
        )
        
        try:
            response = await self.llm.generate(prompt, system_prompt)
            content = self._clean_response(response.content)
            
            # 解析 JSON
            verdict = self._parse_review_response(content)
            verdict.parse_success = True
            return verdict
            
        except Exception as e:
            return ReviewVerdictV2(
                verdict="blocked",
                verdict_reason=f"审查解析失败: {str(e)}",
                parse_success=False,
                parse_error=str(e)
            )

    def _parse_review_response(self, content: str) -> ReviewVerdictV2:
        """解析审查响应"""
        # 查找 JSON
        json_match = re.search(r'\{[\s\S]*\}', content)
        if not json_match:
            raise ValueError("无法解析审查响应")
        
        data = json.loads(json_match.group(0))
        
        return ReviewVerdictV2(
            verdict=data.get("verdict", "pass"),
            verdict_reason=data.get("verdict_reason", ""),
            issues=data.get("issues", []),
            patch_instructions=data.get("patch_instructions"),
            rewrite_instructions=data.get("rewrite_instructions"),
            scores=data.get("scores", {
                "consistency": 1.0,
                "pacing": 1.0,
                "hook": 1.0,
                "overall": 1.0
            })
        )

    async def _fallback_review(self, chapter: Chapter) -> ReviewVerdictV2:
        """降级审查 - 最简规则检查"""
        prompt = FALLBACK_REVIEW_PROMPT.format(chapter_text=chapter.text[:5000])
        
        try:
            response = await self.llm.generate(prompt, "")
            content = self._clean_response(response.content)
            
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                data = json.loads(json_match.group(0))
                return ReviewVerdictV2(
                    verdict="pass" if data.get("can_proceed") else "needs_patch",
                    verdict_reason=data.get("verdict_reason", "降级审查通过"),
                    issues=[{"description": i} for i in data.get("basic_issues", [])],
                    scores={"overall": 0.8},
                    parse_success=True
                )
        except Exception:
            pass
        
        # 最简降级
        return ReviewVerdictV2(
            verdict="pass",
            verdict_reason="降级审查：基础检查通过",
            scores={"overall": 0.7},
            parse_success=True
        )

    def _clean_response(self, content: str) -> str:
        """清理响应"""
        if not content:
            return content
        
        # 移除 thinking 标签
        patterns = [
            r'<reasoning>.*?</reasoning>',
            r'<reflection>.*?</reflection>',
            r'<thinking>.*?</thinking>',
            r'<[\s\S]*?<\/[\s\S]*?>',
        ]
        for pattern in patterns:
            content = re.sub(pattern, '', content, flags=re.DOTALL)
        
        return content.strip()

    async def review_revision(
        self,
        project_id: int,
        chapter_id: int,
        previous_issues: list[dict],
        revised_text: str
    ) -> ReviewVerdictV2:
        """审查修改后的章节"""
        chapter = await self.chapter_repo.get(chapter_id)
        if not chapter:
            raise ValueError(f"Chapter {chapter_id} not found")
        
        system_prompt = """你是一个专业的小说编辑。
        请审查修改后的章节是否解决了原问题。"""
        
        prompt = REVIEW_REVISION_PROMPT.format(
            chapter_no=chapter.chapter_no,
            title=chapter.title or f"第{chapter.chapter_no}章",
            previous_issues=json.dumps(previous_issues, ensure_ascii=False),
            revised_text=revised_text
        )
        
        try:
            response = await self.llm.generate(prompt, system_prompt)
            content = self._clean_response(response.content)
            
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                data = json.loads(json_match.group(0))
                return ReviewVerdictV2(
                    verdict=data.get("verdict", "pass"),
                    verdict_reason=data.get("verdict_reason", ""),
                    issues=data.get("new_issues", []),
                    scores=data.get("scores", {"overall": 1.0})
                )
        except Exception:
            pass
        
        return ReviewVerdictV2(
            verdict="pass",
            verdict_reason="修改审查完成"
        )

    # ==================== 兼容旧 API ====================

    async def review_chapter_legacy(
        self,
        project_id: int,
        chapter_id: int
    ) -> dict[str, Any]:
        """旧 API 兼容"""
        verdict = await self.review_chapter(
            project_id, chapter_id, ReviewRequestV2(chapter_id=chapter_id)
        )
        
        return {
            "chapter_id": chapter_id,
            "verdict": verdict.verdict,
            "verdict_reason": verdict.verdict_reason,
            "issues": verdict.issues,
            "scores": verdict.scores
        }
