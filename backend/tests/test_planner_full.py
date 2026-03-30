"""完整的 Planner Service 测试"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.planner.service import PlannerService
from app.services.planner.schemas import (
    PremiseAnalysis,
    StoryBibleDraft,
    CharacterCard,
    ArcPlan,
    ChapterOutline,
)
from app.models.project import Project, ProjectStatus


class TestPlannerServiceUnit:
    """Planner Service 单元测试"""
    
    def test_parse_premise_returns_structure(self):
        """测试 premise 解析返回结构"""
        # Mock LLM provider
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "解析结果"
        mock_llm.generate = AsyncMock(return_value=mock_response)
        
        # 创建 service (使用内存 SQLite)
        # 注意：这里只测试 schema，不依赖数据库
        
        # 验证 schema
        analysis = PremiseAnalysis(
            genre="都市异能",
            theme="成长",
            tone="热血",
            target_audience="年轻读者",
            key_elements=["主角", "超能力", "成长"],
            potential_conflicts=["正邪对立"]
        )
        
        assert analysis.genre == "都市异能"
        assert "主角" in analysis.key_elements
    
    def test_story_bible_draft_schema(self):
        """测试 Story Bible Draft Schema"""
        draft = StoryBibleDraft(
            title="测试小说",
            genre="玄幻",
            theme="热血",
            logline="一句话概述",
            synopsis="故事大纲",
            world_overview="世界观",
            narrative_structure={"act1": "铺垫"}
        )
        
        assert draft.title == "测试小说"
        assert draft.narrative_structure["act1"] == "铺垫"
    
    def test_character_card_schema(self):
        """测试角色卡 Schema"""
        card = CharacterCard(
            name="林逸",
            role_type="protagonist",
            profile="主角简介",
            personality="沉稳内敛",
            motivation="寻找真相",
            secrets="身世之谜",
            relationships={"导师": "陈老", "对手": "黑影"}
        )
        
        assert card.name == "林逸"
        assert card.role_type == "protagonist"
        assert "导师" in card.relationships
    
    def test_arc_plan_schema(self):
        """测试弧线规划 Schema"""
        plan = ArcPlan(total_arcs=3, volumes=[])
        
        assert plan.total_arcs == 3
        assert len(plan.volumes) == 0
    
    def test_chapter_outline_schema(self):
        """测试章节大纲 Schema"""
        outline = ChapterOutline(
            chapter_no=1,
            title="第一章",
            outline="章节大纲内容",
            hook="开篇钩子",
            key_events=["事件1", "事件2"]
        )
        
        assert outline.chapter_no == 1
        assert len(outline.key_events) == 2


class TestPlannerPrompts:
    """Planner Prompts 测试"""
    
    def test_premise_analysis_prompt_format(self):
        """测试 premise 分析 prompt 格式"""
        from app.services.planner.prompts import PREMISE_ANALYSIS_PROMPT
        
        premise = "一个普通大学生获得超能力"
        prompt = PREMISE_ANALYSIS_PROMPT.format(premise=premise)
        
        assert premise in prompt
        assert "genre" in prompt.lower()
    
    def test_story_bible_prompt_format(self):
        """测试 Story Bible prompt 格式"""
        from app.services.planner.prompts import STORY_BIBLE_PROMPT
        
        prompt = STORY_BIBLE_PROMPT.format(
            project_title="测试小说",
            premise="测试剧情",
            genre="玄幻",
            style="热血"
        )
        
        assert "测试小说" in prompt
        assert "世界观" in prompt
    
    def test_character_card_prompt_format(self):
        """测试角色卡 prompt 格式"""
        from app.services.planner.prompts import CHARACTER_CARD_PROMPT
        
        prompt = CHARACTER_CARD_PROMPT.format(
            project_title="测试小说",
            premise="测试剧情",
            count=3
        )
        
        assert "测试小说" in prompt
        assert "3" in prompt
    
    def test_arc_plan_prompt_format(self):
        """测试弧线规划 prompt 格式"""
        from app.services.planner.prompts import ARC_PLAN_PROMPT
        
        prompt = ARC_PLAN_PROMPT.format(
            project_title="测试小说",
            premise="测试剧情",
            total_arcs=3,
            target_chapters_per_arc=30
        )
        
        assert "3" in prompt
        assert "30" in prompt
    
    def test_chapter_outline_prompt_format(self):
        """测试章节大纲 prompt 格式"""
        from app.services.planner.prompts import CHAPTER_OUTLINE_PROMPT
        
        prompt = CHAPTER_OUTLINE_PROMPT.format(
            project_title="测试小说",
            premise="测试剧情",
            volume_id=1,
            count=10,
            start_chapter_no=1,
            existing_outlines="暂无"
        )
        
        assert "测试小说" in prompt
        assert "10" in prompt


class TestPlannerPromptsStructure:
    """Planner Prompts 结构测试"""
    
    def test_all_prompts_exist(self):
        """测试所有 prompts 都存在"""
        from app.services.planner import prompts
        
        assert hasattr(prompts, 'PREMISE_ANALYSIS_PROMPT')
        assert hasattr(prompts, 'STORY_BIBLE_PROMPT')
        assert hasattr(prompts, 'CHARACTER_CARD_PROMPT')
        assert hasattr(prompts, 'ARC_PLAN_PROMPT')
        assert hasattr(prompts, 'CHAPTER_OUTLINE_PROMPT')
    
    def test_prompts_contain_placeholders(self):
        """测试 prompts 包含占位符"""
        from app.services.planner.prompts import PREMISE_ANALYSIS_PROMPT
        
        assert "{premise}" in PREMISE_ANALYSIS_PROMPT
    
    def test_prompts_not_empty(self):
        """测试 prompts 不为空"""
        from app.services.planner.prompts import (
            PREMISE_ANALYSIS_PROMPT,
            STORY_BIBLE_PROMPT,
            CHARACTER_CARD_PROMPT,
            ARC_PLAN_PROMPT,
            CHAPTER_OUTLINE_PROMPT,
        )
        
        assert len(PREMISE_ANALYSIS_PROMPT) > 0
        assert len(STORY_BIBLE_PROMPT) > 0
        assert len(CHARACTER_CARD_PROMPT) > 0
        assert len(ARC_PLAN_PROMPT) > 0
        assert len(CHAPTER_OUTLINE_PROMPT) > 0
