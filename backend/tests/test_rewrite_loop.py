"""v2.7 Rewrite Loop Integration Tests - 重写循环集成测试

测试 v2.7 模式特定的重写循环行为:
- checkpoint 模式: 保持不变，无自动重写
- blackbox 模式: 自动重写，scene->band->arc，3次失败后 force-accept
- copilot 模式: 自动重写，3次失败后停止在 needs_review
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chapter import Chapter, ChapterStatus
from app.models.project import Project
from app.services.reviewer.rewrite_loop_service import (
    RewriteLoopService,
    RewriteScope,
    OperationMode,
    RewriteLoopResult,
)
from app.services.reviewer.v2_7_experience_overlay import (
    ReviewVerdictV3,
    RepairInstruction,
    ReviewIssue,
)


class MockLLMProvider:
    """Mock LLM Provider for testing"""
    
    async def generate(self, *args, **kwargs):
        return "mock response"


def create_mock_verdict(
    verdict: str,
    repair_scope: str = "scene",
    failure_type: str = "consistency"
) -> ReviewVerdictV3:
    """创建模拟的审查裁决"""
    repair_instruction = None
    if verdict == "fail":
        repair_instruction = RepairInstruction(
            repair_scope=repair_scope,
            failure_type=failure_type,
            must_fix=["Fix item 1", "Fix item 2"],
            must_preserve=["Preserve item 1"],
            design_patch={"changes": ["change1"]},
            evidence_refs=["evidence1"]
        )
    
    return ReviewVerdictV3(
        verdict=verdict,
        verdict_reason=f"Test verdict: {verdict}",
        issues=[],
        scores={"coherence": 0.8, "pacing": 0.7},
        recommended_action="accept" if verdict == "pass" else "rewrite",
        review_summary=f"Summary for {verdict}",
        planned_reward_tags=[],
        delivered_reward_tags=[],
        experience_scores={"immersion": 0.8},
        force_accept_recommended=False,
        repair_instruction=repair_instruction
    )


class TestCheckpointMode:
    """checkpoint 模式测试 - 应该保持不变，无自动重写"""

    @pytest.mark.asyncio
    async def test_checkpoint_pass_verdict(
        self, db_session: AsyncSession, test_project: Project
    ):
        """checkpoint 模式: pass verdict 不重写"""
        chapter = Chapter(
            project_id=test_project.id,
            chapter_no=1,
            title="Test Chapter",
            status=ChapterStatus.DRAFT,
            text="Test chapter content"
        )
        db_session.add(chapter)
        await db_session.flush()
        
        service = RewriteLoopService(
            db=db_session,
            llm_provider=MockLLMProvider(),
            operation_mode="checkpoint"
        )
        
        # Mock review to return pass
        service._run_review = AsyncMock(
            return_value=create_mock_verdict("pass")
        )
        
        result = await service.execute_review_with_rewrite_loop(
            project_id=test_project.id,
            chapter_id=chapter.id,
            chapter_text="Test chapter content"
        )
        
        assert result.final_verdict == "pass"
        assert result.attempt_count == 0
        assert result.stopped_at_needs_review is True
        assert result.forced_accept_applied is False

    @pytest.mark.asyncio
    async def test_checkpoint_fail_verdict_no_auto_rewrite(
        self, db_session: AsyncSession, test_project: Project
    ):
        """checkpoint 模式: fail verdict 不自动重写"""
        chapter = Chapter(
            project_id=test_project.id,
            chapter_no=1,
            title="Test Chapter",
            status=ChapterStatus.DRAFT,
            text="Test chapter content"
        )
        db_session.add(chapter)
        await db_session.flush()
        
        service = RewriteLoopService(
            db=db_session,
            llm_provider=MockLLMProvider(),
            operation_mode="checkpoint"
        )
        
        # Mock review to return fail
        service._run_review = AsyncMock(
            return_value=create_mock_verdict("fail")
        )
        
        result = await service.execute_review_with_rewrite_loop(
            project_id=test_project.id,
            chapter_id=chapter.id,
            chapter_text="Test chapter content"
        )
        
        # checkpoint 模式不应该自动重写
        assert result.final_verdict == "fail"
        assert result.attempt_count == 0
        assert result.stopped_at_needs_review is True
        assert result.forced_accept_applied is False


class TestBlackboxMode:
    """blackbox 模式测试 - 自动重写，3次失败后 force-accept"""

    @pytest.mark.asyncio
    async def test_blackbox_pass_verdict_no_rewrite(
        self, db_session: AsyncSession, test_project: Project
    ):
        """blackbox 模式: pass verdict 不重写"""
        chapter = Chapter(
            project_id=test_project.id,
            chapter_no=1,
            title="Test Chapter",
            status=ChapterStatus.DRAFT,
            text="Test chapter content"
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
            chapter_text="Test chapter content"
        )
        
        assert result.final_verdict == "pass"
        assert result.attempt_count == 0
        assert result.forced_accept_applied is False

    @pytest.mark.asyncio
    async def test_blackbox_repair_to_pass(
        self, db_session: AsyncSession, test_project: Project
    ):
        """blackbox 模式: 修复后变成 pass"""
        chapter = Chapter(
            project_id=test_project.id,
            chapter_no=1,
            title="Test Chapter",
            status=ChapterStatus.DRAFT,
            text="Test chapter content"
        )
        db_session.add(chapter)
        await db_session.flush()
        
        service = RewriteLoopService(
            db=db_session,
            llm_provider=MockLLMProvider(),
            operation_mode="blackbox"
        )
        
        # First review returns fail, second returns pass
        service._run_review = AsyncMock(
            side_effect=[
                create_mock_verdict("fail"),
                create_mock_verdict("pass")
            ]
        )
        
        # Mock the repair methods
        service._repair_scene_level = AsyncMock(return_value="Repaired chapter content")
        
        result = await service.execute_review_with_rewrite_loop(
            project_id=test_project.id,
            chapter_id=chapter.id,
            chapter_text="Test chapter content"
        )
        
        assert result.final_verdict == "pass"
        assert result.attempt_count == 1
        assert result.forced_accept_applied is False
        assert result.success is True

    @pytest.mark.asyncio
    async def test_blackbox_force_accept_after_3_fails(
        self, db_session: AsyncSession, test_project: Project
    ):
        """blackbox 模式: 3次失败后 force-accept"""
        chapter = Chapter(
            project_id=test_project.id,
            chapter_no=1,
            title="Test Chapter",
            status=ChapterStatus.DRAFT,
            text="Test chapter content"
        )
        db_session.add(chapter)
        await db_session.flush()
        
        service = RewriteLoopService(
            db=db_session,
            llm_provider=MockLLMProvider(),
            operation_mode="blackbox"
        )
        
        # All reviews return fail
        service._run_review = AsyncMock(
            return_value=create_mock_verdict("fail")
        )
        
        # Mock repair methods
        service._repair_scene_level = AsyncMock(return_value="Scene repaired")
        service._repair_band_level = AsyncMock(return_value="Band repaired")
        service._repair_arc_level = AsyncMock(return_value="Arc repaired")
        service._record_force_accept = AsyncMock()
        
        result = await service.execute_review_with_rewrite_loop(
            project_id=test_project.id,
            chapter_id=chapter.id,
            chapter_text="Test chapter content"
        )
        
        # 3次失败后应该 force-accept
        assert result.final_verdict == "fail"  # 保持真实 verdict
        assert result.attempt_count == 3
        assert result.forced_accept_applied is True
        assert result.success is True  # 虽然失败但 force-accept 了

    @pytest.mark.asyncio
    async def test_blackbox_scope_escalation(
        self, db_session: AsyncSession, test_project: Project
    ):
        """blackbox 模式: 修复范围升级 scene -> band -> arc"""
        chapter = Chapter(
            project_id=test_project.id,
            chapter_no=1,
            title="Test Chapter",
            status=ChapterStatus.DRAFT,
            text="Test chapter content"
        )
        db_session.add(chapter)
        await db_session.flush()
        
        service = RewriteLoopService(
            db=db_session,
            llm_provider=MockLLMProvider(),
            operation_mode="blackbox"
        )
        
        # All reviews return fail
        service._run_review = AsyncMock(
            return_value=create_mock_verdict("fail")
        )
        
        # Track which repair methods are called
        repair_calls = []
        
        async def mock_scene_repair(*args, **kwargs):
            repair_calls.append("scene")
            return "Scene repaired"
        
        async def mock_band_repair(*args, **kwargs):
            repair_calls.append("band")
            return "Band repaired"
        
        async def mock_arc_repair(*args, **kwargs):
            repair_calls.append("arc")
            return "Arc repaired"
        
        service._repair_scene_level = mock_scene_repair
        service._repair_band_level = mock_band_repair
        service._repair_arc_level = mock_arc_repair
        service._record_force_accept = AsyncMock()
        
        result = await service.execute_review_with_rewrite_loop(
            project_id=test_project.id,
            chapter_id=chapter.id,
            chapter_text="Test chapter content"
        )
        
        # 验证范围升级
        assert "scene" in repair_calls
        assert "band" in repair_calls
        assert "arc" in repair_calls
        assert len(repair_calls) == 3


class TestCopilotMode:
    """copilot 模式测试 - 自动重写，3次失败后停止在 needs_review"""

    @pytest.mark.asyncio
    async def test_copilot_pass_verdict_continues(
        self, db_session: AsyncSession, test_project: Project
    ):
        """copilot 模式: pass verdict 继续"""
        chapter = Chapter(
            project_id=test_project.id,
            chapter_no=1,
            title="Test Chapter",
            status=ChapterStatus.DRAFT,
            text="Test chapter content"
        )
        db_session.add(chapter)
        await db_session.flush()
        
        service = RewriteLoopService(
            db=db_session,
            llm_provider=MockLLMProvider(),
            operation_mode="copilot"
        )
        
        service._run_review = AsyncMock(
            return_value=create_mock_verdict("pass")
        )
        
        result = await service.execute_review_with_rewrite_loop(
            project_id=test_project.id,
            chapter_id=chapter.id,
            chapter_text="Test chapter content"
        )
        
        assert result.final_verdict == "pass"
        assert result.attempt_count == 0
        assert result.stopped_at_needs_review is False

    @pytest.mark.asyncio
    async def test_copilot_warn_verdict_pauses(
        self, db_session: AsyncSession, test_project: Project
    ):
        """copilot 模式: warn verdict 暂停"""
        chapter = Chapter(
            project_id=test_project.id,
            chapter_no=1,
            title="Test Chapter",
            status=ChapterStatus.DRAFT,
            text="Test chapter content"
        )
        db_session.add(chapter)
        await db_session.flush()
        
        service = RewriteLoopService(
            db=db_session,
            llm_provider=MockLLMProvider(),
            operation_mode="copilot"
        )
        
        service._run_review = AsyncMock(
            return_value=create_mock_verdict("warn")
        )
        
        result = await service.execute_review_with_rewrite_loop(
            project_id=test_project.id,
            chapter_id=chapter.id,
            chapter_text="Test chapter content"
        )
        
        assert result.final_verdict == "warn"
        assert result.stopped_at_needs_review is True

    @pytest.mark.asyncio
    async def test_copilot_repair_to_pass_continues(
        self, db_session: AsyncSession, test_project: Project
    ):
        """copilot 模式: 修复后变成 pass 继续"""
        chapter = Chapter(
            project_id=test_project.id,
            chapter_no=1,
            title="Test Chapter",
            status=ChapterStatus.DRAFT,
            text="Test chapter content"
        )
        db_session.add(chapter)
        await db_session.flush()
        
        service = RewriteLoopService(
            db=db_session,
            llm_provider=MockLLMProvider(),
            operation_mode="copilot"
        )
        
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
            chapter_text="Test chapter content"
        )
        
        assert result.final_verdict == "pass"
        assert result.attempt_count == 1
        assert result.stopped_at_needs_review is False

    @pytest.mark.asyncio
    async def test_copilot_repair_to_warn_pauses(
        self, db_session: AsyncSession, test_project: Project
    ):
        """copilot 模式: 修复后变成 warn 暂停"""
        chapter = Chapter(
            project_id=test_project.id,
            chapter_no=1,
            title="Test Chapter",
            status=ChapterStatus.DRAFT,
            text="Test chapter content"
        )
        db_session.add(chapter)
        await db_session.flush()
        
        service = RewriteLoopService(
            db=db_session,
            llm_provider=MockLLMProvider(),
            operation_mode="copilot"
        )
        
        service._run_review = AsyncMock(
            side_effect=[
                create_mock_verdict("fail"),
                create_mock_verdict("warn")
            ]
        )
        
        service._repair_scene_level = AsyncMock(return_value="Repaired content")
        
        result = await service.execute_review_with_rewrite_loop(
            project_id=test_project.id,
            chapter_id=chapter.id,
            chapter_text="Test chapter content"
        )
        
        assert result.final_verdict == "warn"
        assert result.attempt_count == 1
        assert result.stopped_at_needs_review is True

    @pytest.mark.asyncio
    async def test_copilot_stops_after_3_fails(
        self, db_session: AsyncSession, test_project: Project
    ):
        """copilot 模式: 3次失败后停止在 needs_review (不 force-accept)"""
        chapter = Chapter(
            project_id=test_project.id,
            chapter_no=1,
            title="Test Chapter",
            status=ChapterStatus.DRAFT,
            text="Test chapter content"
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
        
        service._repair_scene_level = AsyncMock(return_value="Scene repaired")
        service._repair_band_level = AsyncMock(return_value="Band repaired")
        service._repair_arc_level = AsyncMock(return_value="Arc repaired")
        
        result = await service.execute_review_with_rewrite_loop(
            project_id=test_project.id,
            chapter_id=chapter.id,
            chapter_text="Test chapter content"
        )
        
        # copilot 不应该 force-accept
        assert result.final_verdict == "fail"
        assert result.attempt_count == 3
        assert result.forced_accept_applied is False
        assert result.success is False
        assert result.stopped_at_needs_review is True


class TestRepairScopeRules:
    """修复范围规则测试"""

    def test_scope_escalation_scene_to_band(self):
        """scene -> band 升级"""
        service = RewriteLoopService(
            db=MagicMock(),
            operation_mode="blackbox"
        )
        
        next_scope = service._escalate_scope(RewriteScope.SCENE)
        assert next_scope == RewriteScope.BAND

    def test_scope_escalation_band_to_arc(self):
        """band -> arc 升级"""
        service = RewriteLoopService(
            db=MagicMock(),
            operation_mode="blackbox"
        )
        
        next_scope = service._escalate_scope(RewriteScope.BAND)
        assert next_scope == RewriteScope.ARC

    def test_scope_escalation_arc_stays_arc(self):
        """arc 保持 arc"""
        service = RewriteLoopService(
            db=MagicMock(),
            operation_mode="blackbox"
        )
        
        next_scope = service._escalate_scope(RewriteScope.ARC)
        assert next_scope == RewriteScope.ARC
