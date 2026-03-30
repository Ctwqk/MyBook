"""Memory Service 测试"""
import pytest
from app.services.memory.service import MemoryService
from app.schemas.memory import ContextPackRequest


class TestMemoryService:
    """Memory Service 测试类"""
    
    @pytest.mark.asyncio
    async def test_update_story_bible(self, db_session, test_project):
        """测试 Story Bible 更新"""
        service = MemoryService(db_session)
        
        # 初始更新（创建）
        result = await service.update_story_bible(
            project_id=test_project.id,
            updates={"title": "测试标题", "theme": "测试主题"}
        )
        
        assert result is not None
        assert result.title == "测试标题"
        
        # 再次更新
        result2 = await service.update_story_bible(
            project_id=test_project.id,
            updates={"synopsis": "测试大纲"}
        )
        
        assert result2.synopsis == "测试大纲"
    
    @pytest.mark.asyncio
    async def test_build_context_pack(self, db_session, test_project):
        """测试上下文包构建"""
        service = MemoryService(db_session)
        
        request = ContextPackRequest(
            include_story_bible=True,
            include_character_states=True,
            include_recent_chapters=2,
            include_foreshadows=True
        )
        
        result = await service.build_context_pack(test_project.id, request)
        
        assert result is not None
        assert hasattr(result, "formatted_context")
        assert isinstance(result.formatted_context, str)
    
    @pytest.mark.asyncio
    async def test_record_foreshadow(self, db_session, test_project):
        """测试伏笔记录"""
        service = MemoryService(db_session)
        
        # 需要先创建一个章节
        from app.models.chapter import Chapter, ChapterStatus
        chapter = Chapter(
            project_id=test_project.id,
            chapter_no=1,
            title="第一章",
            status=ChapterStatus.OUTLINE
        )
        db_session.add(chapter)
        await db_session.commit()
        
        foreshadow = await service.record_foreshadow(
            project_id=test_project.id,
            chapter_id=chapter.id,
            content="神秘符号出现了",
            related_entities=["古籍", "符号"]
        )
        
        assert foreshadow is not None
        assert foreshadow.content == "神秘符号出现了"
    
    @pytest.mark.asyncio
    async def test_get_active_foreshadows(self, db_session, test_project):
        """测试获取活跃伏笔"""
        service = MemoryService(db_session)
        
        # 先创建章节
        from app.models.chapter import Chapter, ChapterStatus
        chapter = Chapter(
            project_id=test_project.id,
            chapter_no=1,
            title="第一章",
            status=ChapterStatus.OUTLINE
        )
        db_session.add(chapter)
        await db_session.commit()
        
        # 记录伏笔
        await service.record_foreshadow(
            project_id=test_project.id,
            chapter_id=chapter.id,
            content="测试伏笔"
        )
        
        foreshadows = await service.get_active_foreshadows(test_project.id)
        
        assert len(foreshadows) >= 1
