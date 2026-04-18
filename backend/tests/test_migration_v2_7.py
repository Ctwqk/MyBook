"""v2.7 Migration Tests - 数据库迁移测试

测试 v2.7 新增的数据库列和表:
- chapters.experience_plan_json
- arc_structure_drafts.reader_promise_json
- arc_structure_drafts.arc_payoff_map_json
- chapter_rewrite_attempts 表
- band_experience_plans 表
- review_notes.forced_accept_applied
- review_notes.override_reason
- review_notes.rewrite_attempt_count
"""
import pytest
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chapter import Chapter, ChapterStatus
from app.models.chapter_rewrite_attempt import ChapterRewriteAttempt
from app.models.band_experience_plan import BandExperiencePlan
from app.models.review_note import ReviewNote
from app.models.project import Project
from app.models.arc_envelope import ArcEnvelope, ArcStructureDraft


class TestV27Migration:
    """v2.7 数据库迁移测试"""

    @pytest.mark.asyncio
    async def test_chapters_experience_plan_json_column_exists(
        self, db_session: AsyncSession
    ):
        """测试 chapters.experience_plan_json 列存在"""
        inspector = inspect(db_session.bind)
        columns = await db_session.run_sync(
            lambda sync_session: [
                c["name"] for c in inspector.get_columns("chapters")
            ]
        )
        assert "experience_plan_json" in columns

    @pytest.mark.asyncio
    async def test_arc_structure_drafts_new_columns_exist(
        self, db_session: AsyncSession
    ):
        """测试 arc_structure_drafts 表的新列存在"""
        inspector = inspect(db_session.bind)
        columns = await db_session.run_sync(
            lambda sync_session: [
                c["name"] for c in inspector.get_columns("arc_structure_drafts")
            ]
        )
        assert "reader_promise_json" in columns
        assert "arc_payoff_map_json" in columns

    @pytest.mark.asyncio
    async def test_chapter_rewrite_attempts_table_exists(
        self, db_session: AsyncSession
    ):
        """测试 chapter_rewrite_attempts 表存在"""
        inspector = inspect(db_session.bind)
        tables = await db_session.run_sync(
            lambda sync_session: inspector.get_table_names()
        )
        assert "chapter_rewrite_attempts" in tables

    @pytest.mark.asyncio
    async def test_chapter_rewrite_attempts_columns(
        self, db_session: AsyncSession
    ):
        """测试 chapter_rewrite_attempts 表的列"""
        inspector = inspect(db_session.bind)
        columns = await db_session.run_sync(
            lambda sync_session: [
                c["name"] for c in inspector.get_columns("chapter_rewrite_attempts")
            ]
        )
        
        required_columns = [
            "id", "project_id", "chapter_id", "chapter_number", "attempt_no",
            "trigger_review_id", "repair_scope", "design_patch_json",
            "source_draft_id", "result_draft_id", "result_verdict",
            "forced_accept_applied", "repair_instruction_summary", "created_at"
        ]
        for col in required_columns:
            assert col in columns, f"Missing column: {col}"

    @pytest.mark.asyncio
    async def test_band_experience_plans_table_exists(
        self, db_session: AsyncSession
    ):
        """测试 band_experience_plans 表存在"""
        inspector = inspect(db_session.bind)
        tables = await db_session.run_sync(
            lambda sync_session: inspector.get_table_names()
        )
        assert "band_experience_plans" in tables

    @pytest.mark.asyncio
    async def test_band_experience_plans_columns(
        self, db_session: AsyncSession
    ):
        """测试 band_experience_plans 表的列"""
        inspector = inspect(db_session.bind)
        columns = await db_session.run_sync(
            lambda sync_session: [
                c["name"] for c in inspector.get_columns("band_experience_plans")
            ]
        )
        
        required_columns = [
            "id", "project_id", "arc_no", "band_no", "band_name",
            "start_chapter", "end_chapter", "delight_schedule_json",
            "delight_per_chapter_avg", "distribution", "is_active",
            "created_at", "updated_at"
        ]
        for col in required_columns:
            assert col in columns, f"Missing column: {col}"

    @pytest.mark.asyncio
    async def test_review_notes_new_columns_exist(
        self, db_session: AsyncSession
    ):
        """测试 review_notes 表的新列存在"""
        inspector = inspect(db_session.bind)
        columns = await db_session.run_sync(
            lambda sync_session: [
                c["name"] for c in inspector.get_columns("review_notes")
            ]
        )
        assert "forced_accept_applied" in columns
        assert "override_reason" in columns
        assert "rewrite_attempt_count" in columns

    @pytest.mark.asyncio
    async def test_chapters_experience_plan_json_nullable(
        self, db_session: AsyncSession, test_project: Project
    ):
        """测试 chapters.experience_plan_json 可以为 NULL (向后兼容)"""
        chapter = Chapter(
            project_id=test_project.id,
            chapter_no=1,
            title="Test Chapter",
            status=ChapterStatus.OUTLINE
        )
        # 不设置 experience_plan_json，应该能正常保存
        db_session.add(chapter)
        await db_session.flush()
        await db_session.refresh(chapter)
        
        assert chapter.experience_plan_json is None

    @pytest.mark.asyncio
    async def test_chapter_rewrite_attempt_crud(
        self, db_session: AsyncSession, test_project: Project
    ):
        """测试 ChapterRewriteAttempt 模型的 CRUD 操作"""
        chapter = Chapter(
            project_id=test_project.id,
            chapter_no=1,
            title="Test Chapter",
            status=ChapterStatus.OUTLINE
        )
        db_session.add(chapter)
        await db_session.flush()
        
        # 创建重写尝试记录
        attempt = ChapterRewriteAttempt(
            project_id=test_project.id,
            chapter_id=chapter.id,
            chapter_number=1,
            attempt_no=1,
            repair_scope="scene",
            design_patch_json='{"changes": []}',
            result_verdict="pass",
            forced_accept_applied=False,
            repair_instruction_summary="Test repair"
        )
        db_session.add(attempt)
        await db_session.flush()
        
        # 验证保存成功
        assert attempt.id is not None
        assert attempt.repair_scope == "scene"
        assert attempt.forced_accept_applied is False

    @pytest.mark.asyncio
    async def test_band_experience_plan_crud(
        self, db_session: AsyncSession, test_project: Project
    ):
        """测试 BandExperiencePlan 模型的 CRUD 操作"""
        plan = BandExperiencePlan(
            project_id=test_project.id,
            arc_no=1,
            band_no=1,
            band_name="Test Band",
            start_chapter=1,
            end_chapter=10,
            delight_schedule_json='{"power": 0.3, "social": 0.2}',
            delight_per_chapter_avg=5.0,
            distribution={"power": 0.3, "social": 0.2},
            is_active=True
        )
        db_session.add(plan)
        await db_session.flush()
        
        # 验证保存成功
        assert plan.id is not None
        assert plan.band_name == "Test Band"
        assert plan.is_active is True

    @pytest.mark.asyncio
    async def test_review_note_force_accept_fields(
        self, db_session: AsyncSession, test_project: Project
    ):
        """测试 ReviewNote 的 forced_accept 相关字段"""
        note = ReviewNote(
            project_id=test_project.id,
            chapter_id=1,
            issue_type="consistency",
            severity="high",
            description="Test issue",
            fix_suggestion="Test fix",
            forced_accept_applied=True,
            override_reason="Auto repair exhausted",
            rewrite_attempt_count=3
        )
        db_session.add(note)
        await db_session.flush()
        
        assert note.forced_accept_applied is True
        assert note.override_reason == "Auto repair exhausted"
        assert note.rewrite_attempt_count == 3
