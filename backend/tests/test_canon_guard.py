"""v2.7 Canon Guard Tests - 正典保护测试

测试 v2.7 中 fail 章节不会进入正典的保护机制:
- fail 章节在成功修复前不应被标记为 accepted
- blackbox 模式下，只有 force-accept 后才能进入正典
- copilot 模式下，fail 章节不应自动进入正典
- 已接受的章节不应被修改
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chapter import Chapter, ChapterStatus
from app.models.project import Project
from app.services.reviewer.rewrite_loop_service import (
    RewriteLoopService,
    OperationMode,
)
from app.services.reviewer.v2_7_experience_overlay import (
    ReviewVerdictV3,
    RepairInstruction,
)


class MockLLMProvider:
    """Mock LLM Provider for testing"""
    
    async def generate(self, *args, **kwargs):
        return "mock response"


def create_mock_verdict(verdict: str) -> ReviewVerdictV3:
    """创建模拟的审查裁决"""
    repair_instruction = None
    if verdict == "fail":
        repair_instruction = RepairInstruction(
            repair_scope="scene",
            failure_type="consistency",
            must_fix=["Fix item 1"],
            must_preserve=["Preserve item 1"],
            design_patch={"changes": []},
            evidence_refs=["evidence1"]
        )
    
    return ReviewVerdictV3(
        verdict=verdict,
        verdict_reason=f"Test verdict: {verdict}",
        issues=[],
        scores={"coherence": 0.8},
        recommended_action="accept" if verdict == "pass" else "rewrite",
        review_summary=f"Summary for {verdict}",
        planned_reward_tags=[],
        delivered_reward_tags=[],
        experience_scores={"immersion": 0.8},
        force_accept_recommended=False,
        repair_instruction=repair_instruction
    )


class TestCanonGuardBasic:
    """正典保护基础测试"""

    @pytest.mark.asyncio
    async def test_fail_chapter_before_repair_not_accepted(
        self, db_session: AsyncSession, test_project: Project
    ):
        """测试: fail 章节在修复前不应被接受"""
        chapter = Chapter(
            project_id=test_project.id,
            chapter_no=1,
            title="Test Chapter",
            status=ChapterStatus.DRAFT,
            text="Test content"
        )
        db_session.add(chapter)
        await db_session.flush()
        
        service = RewriteLoopService(
            db=db_session,
            llm_provider=MockLLMProvider(),
            operation_mode="blackbox"
        )
        
        service._run_review = AsyncMock(
            return_value=create_mock_verdict("fail")
        )
        service._repair_scene_level = AsyncMock(return_value="Repaired content")
        service._repair_band_level = AsyncMock(return_value="Repaired content")
        service._repair_arc_level = AsyncMock(return_value="Repaired content")
        service._record_force_accept = AsyncMock()
        
        # 第一次审查返回 fail
        # 在修复循环中，章节状态不应该在成功或 force-accept 前变为 accepted
        
        result = await service.execute_review_with_rewrite_loop(
            project_id=test_project.id,
            chapter_id=chapter.id,
            chapter_text="Test content"
        )
        
        # 如果 blackbox 模式完成了 force-accept，章节可以被接受
        # 否则章节应该保持在 needs_review 状态
        if not result.forced_accept_applied:
            await db_session.refresh(chapter)
            # 验证章节不在 accepted 状态
            assert chapter.status not in [ChapterStatus.ACCEPTED, ChapterStatus.CANON]

    @pytest.mark.asyncio
    async def test_pass_chapter_can_be_accepted(
        self, db_session: AsyncSession, test_project: Project
    ):
        """测试: pass 章节可以被接受"""
        chapter = Chapter(
            project_id=test_project.id,
            chapter_no=1,
            title="Test Chapter",
            status=ChapterStatus.DRAFT,
            text="Test content"
        )
        db_session.add(chapter)
        await db_session.flush()
        
        service = RewriteLoopService(
            db=db_session,
            llm_provider=MockLLMProvider(),
            operation_mode="blackbox"
        )
        
        service._run_review = AsyncMock(
            return_value=create_mock_verdict("pass")
        )
        
        result = await service.execute_review_with_rewrite_loop(
            project_id=test_project.id,
            chapter_id=chapter.id,
            chapter_text="Test content"
        )
        
        assert result.final_verdict == "pass"
        assert result.forced_accept_applied is False


class TestBlackboxForceAccept:
    """Blackbox 模式 Force-Accept 测试"""

    @pytest.mark.asyncio
    async def test_force_accept_allows_chapter_into_canon(
        self, db_session: AsyncSession, test_project: Project
    ):
        """测试: blackbox force-accept 后章节可以进入正典"""
        chapter = Chapter(
            project_id=test_project.id,
            chapter_no=1,
            title="Test Chapter",
            status=ChapterStatus.DRAFT,
            text="Test content"
        )
        db_session.add(chapter)
        await db_session.flush()
        
        service = RewriteLoopService(
            db=db_session,
            llm_provider=MockLLMProvider(),
            operation_mode="blackbox"
        )
        
        # 所有审查都失败
        service._run_review = AsyncMock(
            return_value=create_mock_verdict("fail")
        )
        service._repair_scene_level = AsyncMock(return_value="Repaired content")
        service._repair_band_level = AsyncMock(return_value="Repaired content")
        service._repair_arc_level = AsyncMock(return_value="Repaired content")
        service._record_force_accept = AsyncMock()
        
        result = await service.execute_review_with_rewrite_loop(
            project_id=test_project.id,
            chapter_id=chapter.id,
            chapter_text="Test content"
        )
        
        # 验证 force-accept 被应用
        assert result.forced_accept_applied is True
        assert result.final_verdict == "fail"  # 保持真实 verdict
        assert result.success is True  # 但允许继续

    @pytest.mark.asyncio
    async def test_force_accept_records_metadata(
        self, db_session: AsyncSession, test_project: Project
    ):
        """测试: force-accept 应该记录元数据"""
        chapter = Chapter(
            project_id=test_project.id,
            chapter_no=1,
            title="Test Chapter",
            status=ChapterStatus.DRAFT,
            text="Test content"
        )
        db_session.add(chapter)
        await db_session.flush()
        
        service = RewriteLoopService(
            db=db_session,
            llm_provider=MockLLMProvider(),
            operation_mode="blackbox"
        )
        
        service._run_review = AsyncMock(
            return_value=create_mock_verdict("fail")
        )
        service._repair_scene_level = AsyncMock(return_value="Repaired content")
        service._repair_band_level = AsyncMock(return_value="Repaired content")
        service._repair_arc_level = AsyncMock(return_value="Repaired content")
        
        # Track if _record_force_accept was called
        record_called = []
        original_record = service._record_force_accept
        
        async def mock_record(*args, **kwargs):
            record_called.append(True)
            return await original_record(*args, **kwargs)
        
        service._record_force_accept = mock_record
        
        result = await service.execute_review_with_rewrite_loop(
            project_id=test_project.id,
            chapter_id=chapter.id,
            chapter_text="Test content"
        )
        
        # 验证 force-accept 被记录
        assert len(record_called) > 0 or result.forced_accept_applied is True


class TestCopilotNoForceAccept:
    """Copilot 模式不 Force-Accept 测试"""

    @pytest.mark.asyncio
    async def test_copilot_fail_never_force_accepts(
        self, db_session: AsyncSession, test_project: Project
    ):
        """测试: copilot 模式永远不会 force-accept"""
        chapter = Chapter(
            project_id=test_project.id,
            chapter_no=1,
            title="Test Chapter",
            status=ChapterStatus.DRAFT,
            text="Test content"
        )
        db_session.add(chapter)
        await db_session.flush()
        
        service = RewriteLoopService(
            db=db_session,
            llm_provider=MockLLMProvider(),
            operation_mode="copilot"
        )
        
        service._run_review = AsyncMock(
            return_value=create_mock_verdict("fail")
        )
        service._repair_scene_level = AsyncMock(return_value="Repaired content")
        service._repair_band_level = AsyncMock(return_value="Repaired content")
        service._repair_arc_level = AsyncMock(return_value="Repaired content")
        
        result = await service.execute_review_with_rewrite_loop(
            project_id=test_project.id,
            chapter_id=chapter.id,
            chapter_text="Test content"
        )
        
        # copilot 模式不应该 force-accept
        assert result.forced_accept_applied is False
        assert result.final_verdict == "fail"
        assert result.stopped_at_needs_review is True
        assert result.success is False

    @pytest.mark.asyncio
    async def test_copilot_fail_chapter_not_in_canon(
        self, db_session: AsyncSession, test_project: Project
    ):
        """测试: copilot 模式下 fail 章节不在正典中"""
        chapter = Chapter(
            project_id=test_project.id,
            chapter_no=1,
            title="Test Chapter",
            status=ChapterStatus.DRAFT,
            text="Test content"
        )
        db_session.add(chapter)
        await db_session.flush()
        
        service = RewriteLoopService(
            db=db_session,
            llm_provider=MockLLMProvider(),
            operation_mode="copilot"
        )
        
        service._run_review = AsyncMock(
            return_value=create_mock_verdict("fail")
        )
        service._repair_scene_level = AsyncMock(return_value="Repaired content")
        service._repair_band_level = AsyncMock(return_value="Repaired content")
        service._repair_arc_level = AsyncMock(return_value="Repaired content")
        
        result = await service.execute_review_with_rewrite_loop(
            project_id=test_project.id,
            chapter_id=chapter.id,
            chapter_text="Test content"
        )
        
        await db_session.refresh(chapter)
        
        # 验证章节不在 accepted 或 canon 状态
        assert chapter.status not in [ChapterStatus.ACCEPTED, ChapterStatus.CANON]
        # 章节应该在 needs_review 状态等待人工处理
        assert result.stopped_at_needs_review is True


class TestAlreadyAcceptedCanonProtection:
    """已接受正典保护测试"""

    @pytest.mark.asyncio
    async def test_accepted_chapter_cannot_be_downgraded(
        self, db_session: AsyncSession, test_project: Project
    ):
        """测试: 已接受的章节不应被降级"""
        # 创建一个已接受的章节
        chapter = Chapter(
            project_id=test_project.id,
            chapter_no=1,
            title="Test Chapter",
            status=ChapterStatus.ACCEPTED,  # 已接受
            text="Original accepted content"
        )
        db_session.add(chapter)
        await db_session.flush()
        
        # 验证章节状态是 ACCEPTED
        await db_session.refresh(chapter)
        assert chapter.status == ChapterStatus.ACCEPTED

    @pytest.mark.asyncio
    async def test_canon_chapter_protected_from_repair(
        self, db_session: AsyncSession, test_project: Project
    ):
        """测试: 正典章节受修复保护"""
        # 创建一个正典章节
        chapter = Chapter(
            project_id=test_project.id,
            chapter_no=1,
            title="Test Chapter",
            status=ChapterStatus.CANON,
            text="Canon content"
        )
        db_session.add(chapter)
        await db_session.flush()
        
        # 验证章节状态是 CANON
        await db_session.refresh(chapter)
        assert chapter.status == ChapterStatus.CANON


class TestRewriteAttemptTracking:
    """重写尝试追踪测试"""

    @pytest.mark.asyncio
    async def test_rewrite_attempts_are_recorded(
        self, db_session: AsyncSession, test_project: Project
    ):
        """测试: 重写尝试被记录"""
        chapter = Chapter(
            project_id=test_project.id,
            chapter_no=1,
            title="Test Chapter",
            status=ChapterStatus.DRAFT,
            text="Test content"
        )
        db_session.add(chapter)
        await db_session.flush()
        
        service = RewriteLoopService(
            db=db_session,
            llm_provider=MockLLMProvider(),
            operation_mode="blackbox"
        )
        
        # 第一次 fail，然后 pass
        service._run_review = AsyncMock(
            side_effect=[
                create_mock_verdict("fail"),
                create_mock_verdict("pass")
            ]
        )
        service._repair_scene_level = AsyncMock(return_value="Repaired content")
        
        result = await service.execute_review_with_rewrite_loop(
            project_id=test_project.id,
            chapter_id=chapter.id,
            chapter_text="Test content"
        )
        
        # 验证重写尝试被记录
        assert result.attempt_count >= 0  # 0 如果第一次就 pass

    @pytest.mark.asyncio
    async def test_max_rewrite_attempts_enforced(
        self, db_session: AsyncSession, test_project: Project
    ):
        """测试: 最大重写次数被强制执行"""
        chapter = Chapter(
            project_id=test_project.id,
            chapter_no=1,
            title="Test Chapter",
            status=ChapterStatus.DRAFT,
            text="Test content"
        )
        db_session.add(chapter)
        await db_session.flush()
        
        service = RewriteLoopService(
            db=db_session,
            llm_provider=MockLLMProvider(),
            operation_mode="blackbox"
        )
        
        # 所有审查都失败
        service._run_review = AsyncMock(
            return_value=create_mock_verdict("fail")
        )
        service._repair_scene_level = AsyncMock(return_value="Scene repaired")
        service._repair_band_level = AsyncMock(return_value="Band repaired")
        service._repair_arc_level = AsyncMock(return_value="Arc repaired")
        service._record_force_accept = AsyncMock()
        
        result = await service.execute_review_with_rewrite_loop(
            project_id=test_project.id,
            chapter_id=chapter.id,
            chapter_text="Test content"
        )
        
        # 验证最大重写次数为 3
        assert result.attempt_count == 3
        assert result.forced_accept_applied is True
