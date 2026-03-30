"""Planner Service 测试"""
import pytest
from app.services.planner.service import PlannerService
from app.services.planner.schemas import PremiseAnalysis, ChapterOutline


class TestPlannerService:
    """Planner Service 测试类"""
    
    @pytest.mark.asyncio
    async def test_parse_premise(self, db_session):
        """测试 premise 解析"""
        service = PlannerService(db_session)
        
        premise = "一个普通大学生意外获得超能力，开始了冒险之旅"
        result = await service.parse_premise(premise)
        
        assert isinstance(result, PremiseAnalysis)
        assert result.genre is not None
        assert result.theme is not None
    
    @pytest.mark.asyncio
    async def test_bootstrap_story(self, db_session, test_project):
        """测试 Story Bible 生成"""
        service = PlannerService(db_session)
        
        result = await service.bootstrap_story(
            project_id=test_project.id,
            premise="测试 premise",
            genre="都市异能"
        )
        
        assert result is not None
        assert result.title is not None
    
    @pytest.mark.asyncio
    async def test_generate_character_cards(self, db_session, test_project):
        """测试角色卡生成"""
        service = PlannerService(db_session)
        
        characters = await service.generate_character_cards(
            project_id=test_project.id,
            count=2
        )
        
        assert len(characters) == 2
        assert all(c.name is not None for c in characters)
    
    @pytest.mark.asyncio
    async def test_generate_chapter_outlines(self, db_session, test_project):
        """测试章节大纲生成"""
        service = PlannerService(db_session)
        
        outlines = await service.generate_chapter_outlines(
            project_id=test_project.id,
            count=3
        )
        
        assert len(outlines) == 3
        assert all(isinstance(o, ChapterOutline) for o in outlines)
        assert outlines[0].chapter_no == 1
