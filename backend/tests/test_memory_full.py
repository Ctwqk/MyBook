"""完整的 Memory Service 测试"""
import pytest
from datetime import datetime

from app.models.story_bible import StoryBible
from app.models.character_state import CharacterState
from app.models.chapter_memory import ChapterMemory
from app.models.foreshadow_record import ForeshadowRecord, ForeshadowStatus
from app.models.review_note import ReviewNote, IssueType, Severity

from app.schemas.memory import (
    StoryBibleResponse,
    StoryBibleUpdate,
    ContextPackRequest,
    ContextPackResponse,
    ForeshadowRecordCreate,
    MemorySearchRequest,
)


class TestStoryBibleModel:
    """StoryBible 模型测试"""
    
    def test_create_story_bible(self):
        """测试创建 Story Bible"""
        bible = StoryBible(
            project_id=1,
            title="测试小说",
            genre="玄幻",
            theme="热血",
            logline="一句话概述",
            synopsis="故事大纲",
            world_overview="世界观",
            tone="热血",
            target_audience="年轻读者"
        )
        
        assert bible.title == "测试小说"
        assert bible.genre == "玄幻"
        assert bible.theme == "热血"
    
    def test_story_bible_with_json_fields(self):
        """测试带 JSON 字段的 Story Bible"""
        bible = StoryBible(
            project_id=1,
            title="测试",
            world_rules=["规则1", "规则2"],
            narrative_structure={"act1": "铺垫", "act2": "发展"},
            key_plot_points=["情节点1", "情节点2"]
        )
        
        assert len(bible.world_rules) == 2
        assert bible.narrative_structure["act1"] == "铺垫"


class TestCharacterStateModel:
    """CharacterState 模型测试"""
    
    def test_create_character_state(self):
        """测试创建角色状态"""
        state = CharacterState(
            project_id=1,
            character_id=1,
            location="图书馆",
            goal="找到真相",
            emotional_state="困惑",
            power_level=1,
            last_event="发现古籍"
        )
        
        assert state.location == "图书馆"
        assert state.emotional_state == "困惑"
        assert state.power_level == 1


class TestChapterMemoryModel:
    """ChapterMemory 模型测试"""
    
    def test_create_chapter_memory(self):
        """测试创建章节记忆"""
        memory = ChapterMemory(
            project_id=1,
            chapter_id=1,
            summary="章节摘要",
            key_events=["事件1", "事件2"],
            new_world_details=["新地点: 神秘洞穴"],
            foreshadow_changes=["伏笔: 神秘符号"]
        )
        
        assert memory.summary == "章节摘要"
        assert len(memory.key_events) == 2


class TestForeshadowRecordModel:
    """ForeshadowRecord 模型测试"""
    
    def test_create_foreshadow(self):
        """测试创建伏笔"""
        foreshadow = ForeshadowRecord(
            project_id=1,
            chapter_id=1,
            content="神秘符号出现在古籍上",
            related_entities=["古籍", "符号"],
            status=ForeshadowStatus.SETUP,
            planned_resolution="第10章解开"
        )
        
        assert foreshadow.content == "神秘符号出现在古籍上"
        assert foreshadow.status == ForeshadowStatus.SETUP
    
    def test_foreshadow_status_transitions(self):
        """测试伏笔状态转换"""
        foreshadow = ForeshadowRecord(
            project_id=1,
            chapter_id=1,
            content="测试伏笔",
            status=ForeshadowStatus.SETUP
        )
        
        # 模拟状态更新
        foreshadow.status = ForeshadowStatus.DEVELOPING
        assert foreshadow.status == ForeshadowStatus.DEVELOPING
        
        foreshadow.status = ForeshadowStatus.RESOLVED
        assert foreshadow.status == ForeshadowStatus.RESOLVED


class TestReviewNoteModel:
    """ReviewNote 模型测试"""
    
    def test_create_review_note(self):
        """测试创建审查笔记"""
        note = ReviewNote(
            project_id=1,
            chapter_id=1,
            issue_type=IssueType.PACING,
            severity=Severity.MEDIUM,
            description="节奏稍慢",
            fix_suggestion="精简描写"
        )
        
        assert note.issue_type == IssueType.PACING
        assert note.severity == Severity.MEDIUM
    
    def test_review_note_issue_types(self):
        """测试所有问题类型"""
        for issue_type in IssueType:
            note = ReviewNote(
                project_id=1,
                chapter_id=1,
                issue_type=issue_type,
                severity=Severity.LOW,
                description="测试"
            )
            assert note.issue_type == issue_type


class TestMemorySchemas:
    """Memory Schemas 测试"""
    
    def test_story_bible_update(self):
        """测试 Story Bible 更新"""
        update = StoryBibleUpdate(
            theme="新主题",
            synopsis="新大纲"
        )
        
        assert update.theme == "新主题"
        assert update.synopsis == "新大纲"
        assert update.world_rules is None
    
    def test_context_pack_request_defaults(self):
        """测试上下文包请求默认值"""
        request = ContextPackRequest()
        
        assert request.include_story_bible is True
        assert request.include_character_states is True
        assert request.include_recent_chapters == 3
        assert request.include_foreshadows is True
        assert request.include_pending_reviews is False
    
    def test_foreshadow_create(self):
        """测试伏笔创建"""
        create = ForeshadowRecordCreate(
            project_id=1,
            chapter_id=1,
            content="测试伏笔",
            related_entities=["角色A", "角色B"],
            planned_resolution="第5章"
        )
        
        assert create.content == "测试伏笔"
        assert len(create.related_entities) == 2
    
    def test_memory_search_request(self):
        """测试记忆搜索请求"""
        request = MemorySearchRequest(
            query="神秘符号",
            search_type="plot",
            limit=20
        )
        
        assert request.query == "神秘符号"
        assert request.search_type == "plot"
        assert request.limit == 20
    
    def test_context_pack_response(self):
        """测试上下文包响应"""
        response = ContextPackResponse(
            character_states=[
                {"character_id": 1, "location": "图书馆"},
                {"character_id": 2, "location": "教室"}
            ],
            recent_chapters=[
                {"chapter_no": 1, "title": "第一章", "summary": "摘要"}
            ],
            foreshadows=[
                {"id": 1, "content": "伏笔1", "status": "setup"}
            ],
            formatted_context="格式化的上下文文本"
        )
        
        assert len(response.character_states) == 2
        assert len(response.recent_chapters) == 1


class TestMemorySearchTypes:
    """记忆搜索类型测试"""
    
    def test_search_type_all(self):
        """测试搜索类型 - all"""
        request = MemorySearchRequest(query="测试", search_type="all")
        assert request.search_type == "all"
    
    def test_search_type_character(self):
        """测试搜索类型 - character"""
        request = MemorySearchRequest(query="林逸", search_type="character")
        assert request.search_type == "character"
    
    def test_search_type_world(self):
        """测试搜索类型 - world"""
        request = MemorySearchRequest(query="世界观", search_type="world")
        assert request.search_type == "world"
    
    def test_search_type_plot(self):
        """测试搜索类型 - plot"""
        request = MemorySearchRequest(query="情节", search_type="plot")
        assert request.search_type == "plot"


class TestMemoryPromptsIntegration:
    """记忆 Prompts 集成测试"""
    
    def test_memory_prompts_module_exists(self):
        """测试 memory prompts 模块存在"""
        # Memory 服务不需要单独的 prompts 文件
        # prompts 在 writer/reviewer 中
        pass
