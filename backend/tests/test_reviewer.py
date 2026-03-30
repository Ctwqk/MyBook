"""Reviewer Service 测试"""
import pytest
from app.services.reviewer.service import ReviewerService
from app.schemas.review import ReviewRequest


class TestReviewerService:
    """Reviewer Service 测试类"""
    
    @pytest.mark.asyncio
    async def test_review_chapter(self, db_session, test_project):
        """测试章节审查"""
        from app.models.chapter import Chapter, ChapterStatus
        chapter = Chapter(
            project_id=test_project.id,
            chapter_no=1,
            title="第一章",
            text="这是一段测试小说正文内容..." * 50,
            status=ChapterStatus.DRAFT
        )
        db_session.add(chapter)
        await db_session.commit()
        
        service = ReviewerService(db_session)
        request = ReviewRequest()
        
        result = await service.review_chapter(
            project_id=test_project.id,
            chapter_id=chapter.id,
            request=request
        )
        
        assert result is not None
        assert hasattr(result, "verdict")
        assert hasattr(result.verdict, "approved")
        assert hasattr(result.verdict, "score")
    
    @pytest.mark.asyncio
    async def test_build_rewrite_instructions(self, db_session, test_project):
        """测试重写指令构建"""
        from app.models.chapter import Chapter, ChapterStatus
        chapter = Chapter(
            project_id=test_project.id,
            chapter_no=1,
            title="第一章",
            text="测试内容",
            status=ChapterStatus.DRAFT
        )
        db_session.add(chapter)
        await db_session.commit()
        
        service = ReviewerService(db_session)
        
        result = await service.build_rewrite_instructions(
            project_id=test_project.id,
            chapter_id=chapter.id
        )
        
        assert result is not None
        assert hasattr(result, "instructions")
