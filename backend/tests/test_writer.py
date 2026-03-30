"""Writer Service 测试"""
import pytest
from app.services.writer.service import WriterService
from app.schemas.chapter import GenerateChapterRequest


class TestWriterService:
    """Writer Service 测试类"""
    
    @pytest.mark.asyncio
    async def test_generate_chapter(self, db_session, test_project):
        """测试章节生成"""
        # 先创建章节
        from app.models.chapter import Chapter, ChapterStatus
        chapter = Chapter(
            project_id=test_project.id,
            chapter_no=1,
            title="第一章：命运的相遇",
            outline="主角在图书馆发现神秘古籍...",
            hook="一本发光的古籍改变了他的命运",
            status=ChapterStatus.OUTLINE
        )
        db_session.add(chapter)
        await db_session.commit()
        
        service = WriterService(db_session)
        request = GenerateChapterRequest()
        
        result = await service.generate_chapter(
            project_id=test_project.id,
            chapter_id=chapter.id,
            request=request
        )
        
        assert result is not None
        assert "chapter" in result
        assert "text" in result
        assert len(result["text"]) > 0
    
    @pytest.mark.asyncio
    async def test_continue_chapter(self, db_session, test_project):
        """测试章节续写"""
        from app.models.chapter import Chapter, ChapterStatus
        chapter = Chapter(
            project_id=test_project.id,
            chapter_no=1,
            title="第一章",
            text="这是已有内容...",
            status=ChapterStatus.DRAFT,
            word_count=100
        )
        db_session.add(chapter)
        await db_session.commit()
        
        service = WriterService(db_session)
        
        from app.schemas.chapter import ContinueChapterRequest
        request = ContinueChapterRequest(target_word_count=500)
        
        result = await service.continue_chapter(
            project_id=test_project.id,
            chapter_id=chapter.id,
            request=request
        )
        
        assert result is not None
        assert "continuation" in result
