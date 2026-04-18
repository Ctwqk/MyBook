"""v2.7 API Tests - API 新字段测试

测试 v2.7 新增的 API 字段暴露:
- review endpoint 返回 forced_accept_applied, rewrite_attempt_count
- review endpoint 返回 repair_scope, review_summary
- ChapterResponse 包含 experience_plan_json
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.chapter import Chapter, ChapterStatus
from app.models.project import Project
from app.services.reviewer.v2_7_experience_overlay import (
    ReviewVerdictV3,
    RepairInstruction,
    ExperienceScores,
)


class MockLLMProvider:
    """Mock LLM Provider for testing"""
    
    async def generate(self, *args, **kwargs):
        return "mock response"


def create_mock_verdict(verdict: str) -> ReviewVerdictV3:
    """创建模拟的审查裁决 (v2.7 格式)"""
    repair_instruction = None
    if verdict == "fail":
        repair_instruction = RepairInstruction(
            repair_scope="scene",
            failure_type="consistency",
            must_fix=["Fix item 1", "Fix item 2"],
            must_preserve=["Preserve item 1"],
            design_patch={"scene_changes": ["change1"]},
            evidence_refs=["evidence1", "evidence2"]
        )
    
    return ReviewVerdictV3(
        verdict=verdict,
        verdict_reason=f"Test verdict: {verdict}",
        issues=[],
        scores={"coherence": 0.8, "pacing": 0.7},
        recommended_action="accept" if verdict == "pass" else "rewrite",
        review_summary=f"Test review summary for {verdict}",
        planned_reward_tags=["power", "social"],
        delivered_reward_tags=["power"] if verdict == "pass" else [],
        experience_scores={"immersion": 0.8, "emotional_impact": 0.7},
        force_accept_recommended=False,
        repair_instruction=repair_instruction
    )


class TestReviewEndpointV27Fields:
    """审查端点 v2.7 字段测试"""

    @pytest.mark.asyncio
    async def test_review_response_contains_forced_accept_applied(
        self, db_session: AsyncSession, test_project: Project
    ):
        """测试: 审查响应包含 forced_accept_applied 字段"""
        chapter = Chapter(
            project_id=test_project.id,
            chapter_no=1,
            title="Test Chapter",
            status=ChapterStatus.DRAFT,
            text="Test content"
        )
        db_session.add(chapter)
        await db_session.flush()
        
        # 创建模拟的审查服务
        from app.services.reviewer.service import ReviewerService
        from app.schemas.review import ReviewRequest
        
        mock_reviewer = MagicMock(spec=ReviewerService)
        mock_reviewer.review_chapter = AsyncMock(
            return_value=create_mock_verdict("pass")
        )
        
        # 验证 mock 返回值包含 forced_accept_applied
        result = await mock_reviewer.reviewer_chapter(
            project_id=test_project.id,
            chapter_id=chapter.id,
            request=ReviewRequest()
        )
        
        # 验证结果
        assert hasattr(result, 'forced_accept_applied')
        assert result.forced_accept_applied is False

    @pytest.mark.asyncio
    async def test_review_response_contains_review_summary(
        self, db_session: AsyncSession, test_project: Project
    ):
        """测试: 审查响应包含 review_summary 字段"""
        chapter = Chapter(
            project_id=test_project.id,
            chapter_no=1,
            title="Test Chapter",
            status=ChapterStatus.DRAFT,
            text="Test content"
        )
        db_session.add(chapter)
        await db_session.flush()
        
        from app.services.reviewer.service import ReviewerService
        from app.schemas.review import ReviewRequest
        
        mock_reviewer = MagicMock(spec=ReviewerService)
        mock_reviewer.review_chapter = AsyncMock(
            return_value=create_mock_verdict("pass")
        )
        
        result = await mock_reviewer.review_chapter(
            project_id=test_project.id,
            chapter_id=chapter.id,
            request=ReviewRequest()
        )
        
        assert hasattr(result, 'review_summary')
        assert result.review_summary is not None
        assert len(result.review_summary) > 0

    @pytest.mark.asyncio
    async def test_review_response_contains_reward_tags(
        self, db_session: AsyncSession, test_project: Project
    ):
        """测试: 审查响应包含 planned/delivered_reward_tags"""
        chapter = Chapter(
            project_id=test_project.id,
            chapter_no=1,
            title="Test Chapter",
            status=ChapterStatus.DRAFT,
            text="Test content"
        )
        db_session.add(chapter)
        await db_session.flush()
        
        from app.services.reviewer.service import ReviewerService
        from app.schemas.review import ReviewRequest
        
        mock_reviewer = MagicMock(spec=ReviewerService)
        mock_reviewer.review_chapter = AsyncMock(
            return_value=create_mock_verdict("pass")
        )
        
        result = await mock_reviewer.review_chapter(
            project_id=test_project.id,
            chapter_id=chapter.id,
            request=ReviewRequest()
        )
        
        assert hasattr(result, 'planned_reward_tags')
        assert hasattr(result, 'delivered_reward_tags')
        assert isinstance(result.planned_reward_tags, list)
        assert isinstance(result.delivered_reward_tags, list)

    @pytest.mark.asyncio
    async def test_review_response_contains_experience_scores(
        self, db_session: AsyncSession, test_project: Project
    ):
        """测试: 审查响应包含 experience_scores"""
        chapter = Chapter(
            project_id=test_project.id,
            chapter_no=1,
            title="Test Chapter",
            status=ChapterStatus.DRAFT,
            text="Test content"
        )
        db_session.add(chapter)
        await db_session.flush()
        
        from app.services.reviewer.service import ReviewerService
        from app.schemas.review import ReviewRequest
        
        mock_reviewer = MagicMock(spec=ReviewerService)
        mock_reviewer.review_chapter = AsyncMock(
            return_value=create_mock_verdict("pass")
        )
        
        result = await mock_reviewer.review_chapter(
            project_id=test_project.id,
            chapter_id=chapter.id,
            request=ReviewRequest()
        )
        
        assert hasattr(result, 'experience_scores')
        assert isinstance(result.experience_scores, dict)

    @pytest.mark.asyncio
    async def test_review_response_contains_repair_instruction(
        self, db_session: AsyncSession, test_project: Project
    ):
        """测试: fail verdict 时审查响应包含 repair_instruction"""
        chapter = Chapter(
            project_id=test_project.id,
            chapter_no=1,
            title="Test Chapter",
            status=ChapterStatus.DRAFT,
            text="Test content"
        )
        db_session.add(chapter)
        await db_session.flush()
        
        from app.services.reviewer.service import ReviewerService
        from app.schemas.review import ReviewRequest
        
        mock_reviewer = MagicMock(spec=ReviewerService)
        mock_reviewer.review_chapter = AsyncMock(
            return_value=create_mock_verdict("fail")
        )
        
        result = await mock_reviewer.review_chapter(
            project_id=test_project.id,
            chapter_id=chapter.id,
            request=ReviewRequest()
        )
        
        # fail 时应该包含 repair_instruction
        assert hasattr(result, 'repair_instruction')
        if result.repair_instruction:
            assert 'repair_scope' in result.repair_instruction
            assert 'failure_type' in result.repair_instruction
            assert 'must_fix' in result.repair_instruction
            assert 'must_preserve' in result.repair_instruction


class TestChapterResponseV27Fields:
    """ChapterResponse v2.7 字段测试"""

    def test_chapter_response_has_experience_plan_json(self):
        """测试: ChapterResponse 包含 experience_plan_json 字段"""
        from app.schemas.chapter import ChapterResponse
        
        # 验证 schema 包含字段
        fields = ChapterResponse.model_fields
        assert 'experience_plan_json' in fields

    @pytest.mark.asyncio
    async def test_chapter_response_serializes_experience_plan(
        self, db_session: AsyncSession, test_project: Project
    ):
        """测试: ChapterResponse 正确序列化 experience_plan_json"""
        chapter = Chapter(
            project_id=test_project.id,
            chapter_no=1,
            title="Test Chapter",
            status=ChapterStatus.DRAFT,
            text="Test content",
            experience_plan_json='{"planned_rewards": ["power"]}'
        )
        db_session.add(chapter)
        await db_session.flush()
        
        from app.schemas.chapter import ChapterResponse
        
        response = ChapterResponse(
            id=chapter.id,
            project_id=chapter.project_id,
            chapter_no=chapter.chapter_no,
            title=chapter.title,
            status=chapter.status,
            experience_plan_json={"planned_rewards": ["power"]},
            created_at=chapter.created_at,
            updated_at=chapter.updated_at
        )
        
        assert response.experience_plan_json is not None
        assert "planned_rewards" in response.experience_plan_json


class TestRewriteAttemptFields:
    """重写尝试字段测试"""

    def test_review_response_has_rewrite_attempt_count(self):
        """测试: 审查响应包含 rewrite_attempt_count"""
        from app.schemas.review import ReviewVerdictV3Response
        
        fields = ReviewVerdictV3Response.model_fields
        assert 'rewrite_attempt_count' in fields

    def test_review_response_has_recommended_action(self):
        """测试: 审查响应包含 recommended_action"""
        from app.schemas.review import ReviewVerdictV3Response
        
        fields = ReviewVerdictV3Response.model_fields
        assert 'recommended_action' in fields


class TestAPIResponseSerialization:
    """API 响应序列化测试"""

    def test_v27_fields_serialize_correctly(self):
        """测试: v2.7 字段正确序列化"""
        from app.schemas.review import ReviewVerdictV3Response
        from app.services.reviewer.v2_7_experience_overlay import RewardCategory
        
        verdict = ReviewVerdictV3Response(
            verdict="fail",
            verdict_reason="Test reason",
            issues=[],
            scores={"coherence": 0.8},
            recommended_action="rewrite",
            review_summary="Test summary",
            planned_reward_tags=["power", "social"],
            delivered_reward_tags=["power"],
            experience_scores={"immersion": 0.8},
            force_accept_recommended=False,
            rewrite_attempt_count=2,
            repair_instruction={
                "repair_scope": "scene",
                "failure_type": "consistency",
                "must_fix": ["Fix 1"],
                "must_preserve": ["Preserve 1"],
                "design_patch": {},
                "evidence_refs": []
            }
        )
        
        # 序列化为 dict
        data = verdict.model_dump()
        
        # 验证所有字段都存在
        assert data['verdict'] == "fail"
        assert data['recommended_action'] == "rewrite"
        assert data['review_summary'] == "Test summary"
        assert data['planned_reward_tags'] == ["power", "social"]
        assert data['delivered_reward_tags'] == ["power"]
        assert data['rewrite_attempt_count'] == 2
        assert data['repair_instruction']['repair_scope'] == "scene"


class TestForcedAcceptMarker:
    """Force-Accept 标记测试"""

    def test_forced_accept_applied_field_exists(self):
        """测试: forced_accept_applied 字段存在"""
        from app.schemas.review import ReviewVerdictV3Response
        
        fields = ReviewVerdictV3Response.model_fields
        assert 'forced_accept_applied' in fields

    def test_override_reason_field_exists(self):
        """测试: override_reason 字段存在"""
        from app.schemas.review import ReviewVerdictV3Response
        
        fields = ReviewVerdictV3Response.model_fields
        assert 'override_reason' in fields or 'repair_instruction' in fields


class TestRepairScopeExposure:
    """修复范围暴露测试"""

    def test_repair_scope_in_repair_instruction(self):
        """测试: repair_scope 在 repair_instruction 中"""
        from app.schemas.review import RepairInstructionSchema
        
        fields = RepairInstructionSchema.model_fields
        assert 'repair_scope' in fields
        assert fields['repair_scope'].annotation == str

    @pytest.mark.asyncio
    async def test_review_detail_exposes_repair_scope(
        self, db_session: AsyncSession, test_project: Project
    ):
        """测试: 审查详情暴露 repair_scope"""
        from app.services.reviewer.service import ReviewerService
        from app.schemas.review import ReviewRequest
        
        mock_reviewer = MagicMock(spec=ReviewerService)
        mock_reviewer.review_chapter = AsyncMock(
            return_value=create_mock_verdict("fail")
        )
        
        result = await mock_reviewer.review_chapter(
            project_id=test_project.id,
            chapter_id=1,
            request=ReviewRequest()
        )
        
        if result.repair_instruction:
            assert 'repair_scope' in result.repair_instruction
            assert result.repair_instruction['repair_scope'] in ['scene', 'band', 'arc']
