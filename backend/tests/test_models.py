"""完整的模型和 Schema 测试"""
import pytest
from datetime import datetime
from pydantic import ValidationError

from app.models.project import Project, ProjectStatus
from app.models.character import Character, CharacterRoleType
from app.models.chapter import Chapter, ChapterStatus
from app.models.volume import Volume
from app.models.story_bible import StoryBible
from app.models.chapter_memory import ChapterMemory
from app.models.character_state import CharacterState
from app.models.foreshadow_record import ForeshadowRecord, ForeshadowStatus
from app.models.review_note import ReviewNote, IssueType, Severity
from app.models.publish_task import PublishTask, PublishStatus, PublishMode, PublishErrorCode

from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from app.schemas.character import CharacterCreate, CharacterResponse
from app.schemas.chapter import ChapterCreate, ChapterResponse, GenerateChapterRequest
from app.schemas.volume import VolumeCreate, ArcPlanRequest
from app.schemas.memory import ContextPackRequest, StoryBibleUpdate
from app.schemas.review import ReviewRequest, ReviewVerdict, ReviewIssue
from app.schemas.publish import PublishDraftRequest, PlatformAccountRegister


class TestProjectModel:
    """Project 模型测试"""
    
    def test_create_project(self):
        """测试创建项目"""
        project = Project(
            title="测试小说",
            genre="都市异能",
            style="热血",
            premise="测试 premise",
            target_length=500000,
            status=ProjectStatus.DRAFT
        )
        
        assert project.title == "测试小说"
        assert project.genre == "都市异能"
        assert project.status == ProjectStatus.DRAFT
    
    def test_project_status_enum(self):
        """测试项目状态枚举"""
        assert ProjectStatus.DRAFT == "draft"
        assert ProjectStatus.PLANNING == "planning"
        assert ProjectStatus.WRITING == "writing"


class TestCharacterModel:
    """Character 模型测试"""
    
    def test_create_character(self):
        """测试创建角色"""
        character = Character(
            project_id=1,
            name="林逸",
            role_type=CharacterRoleType.PROTAGONIST,
            profile="主角小传",
            personality="沉稳内敛",
            motivation="寻找身世真相",
            power_level=1
        )
        
        assert character.name == "林逸"
        assert character.role_type == CharacterRoleType.PROTAGONIST
        assert character.power_level == 1


class TestChapterModel:
    """Chapter 模型测试"""
    
    def test_create_chapter(self):
        """测试创建章节"""
        chapter = Chapter(
            project_id=1,
            chapter_no=1,
            title="第一章",
            outline="章节大纲",
            hook="开篇钩子",
            status=ChapterStatus.OUTLINE,
            word_count=0
        )
        
        assert chapter.chapter_no == 1
        assert chapter.status == ChapterStatus.OUTLINE
        assert chapter.word_count == 0


class TestVolumeModel:
    """Volume 模型测试"""
    
    def test_create_volume(self):
        """测试创建卷"""
        volume = Volume(
            project_id=1,
            volume_no=1,
            title="第一卷：觉醒",
            goal="主角觉醒超能力",
            conflict="正邪对立",
            expected_chapter_count=30
        )
        
        assert volume.volume_no == 1
        assert volume.expected_chapter_count == 30


class TestPublishTaskModel:
    """PublishTask 模型测试"""
    
    def test_create_publish_task(self):
        """测试创建发布任务"""
        task = PublishTask(
            project_id=1,
            chapter_id=1,
            platform="mock",
            account_id="account_123",
            remote_book_id="book_456",
            mode=PublishMode.DRAFT,
            status=PublishStatus.PENDING
        )
        
        assert task.platform == "mock"
        assert task.status == PublishStatus.PENDING
    
    def test_publish_error_codes(self):
        """测试发布错误码"""
        assert PublishErrorCode.SESSION_EXPIRED == "SESSION_EXPIRED"
        assert PublishErrorCode.NETWORK_ERROR == "NETWORK_ERROR"
        assert PublishErrorCode.RISK_CONTROL_BLOCKED == "RISK_CONTROL_BLOCKED"


class TestProjectSchemas:
    """Project Schemas 测试"""
    
    def test_project_create_valid(self):
        """测试有效项目创建"""
        data = ProjectCreate(
            title="新小说",
            genre="玄幻",
            style="热血",
            premise="一个少年的成长之路",
            target_length=300000
        )
        
        assert data.title == "新小说"
        assert data.target_length == 300000
    
    def test_project_create_minimal(self):
        """测试最小项目创建"""
        data = ProjectCreate(title="最短小说")
        
        assert data.title == "最短小说"
        assert data.genre is None
    
    def test_project_update_partial(self):
        """测试部分更新"""
        data = ProjectUpdate(title="更新标题")
        
        assert data.title == "更新标题"
        assert data.genre is None


class TestChapterSchemas:
    """Chapter Schemas 测试"""
    
    def test_generate_request_defaults(self):
        """测试生成请求默认值"""
        request = GenerateChapterRequest()
        
        assert request.outline is None
        assert request.style_hints is None
    
    def test_generate_request_with_values(self):
        """测试带值的生成请求"""
        request = GenerateChapterRequest(
            outline="自定义大纲",
            style_hints="风格提示"
        )
        
        assert request.outline == "自定义大纲"


class TestContextPackSchemas:
    """ContextPack Schemas 测试"""
    
    def test_context_pack_defaults(self):
        """测试上下文包默认值"""
        request = ContextPackRequest()
        
        assert request.include_story_bible is True
        assert request.include_character_states is True
        assert request.include_recent_chapters == 3
        assert request.include_foreshadows is True
    
    def test_context_pack_custom(self):
        """测试自定义上下文包"""
        request = ContextPackRequest(
            include_story_bible=False,
            include_recent_chapters=5
        )
        
        assert request.include_story_bible is False
        assert request.include_recent_chapters == 5


class TestReviewSchemas:
    """Review Schemas 测试"""
    
    def test_review_verdict(self):
        """测试审查判决"""
        verdict = ReviewVerdict(
            approved=True,
            score=8.5,
            issues=[
                ReviewIssue(
                    issue_type=IssueType.PACING,
                    severity=Severity.LOW,
                    description="节奏稍慢",
                    fix_suggestion="精简描写"
                )
            ],
            summary="整体良好",
            strengths=["文笔流畅", "情节紧凑"]
        )
        
        assert verdict.approved is True
        assert verdict.score == 8.5
        assert len(verdict.issues) == 1
        assert verdict.issues[0].severity == Severity.LOW


class TestPublishSchemas:
    """Publish Schemas 测试"""
    
    def test_platform_register(self):
        """测试平台注册"""
        data = PlatformAccountRegister(
            platform="mock",
            session_token="test_token_123"
        )
        
        assert data.platform == "mock"
        assert data.session_token == "test_token_123"
    
    def test_publish_draft_request(self):
        """测试草稿发布请求"""
        data = PublishDraftRequest(
            chapter_id=1,
            platform="mock",
            account_id="account_1"
        )
        
        assert data.chapter_id == 1
        assert data.mode == PublishMode.DRAFT


class TestForeshadowSchemas:
    """Foreshadow Schemas 测试"""
    
    def test_foreshadow_status(self):
        """测试伏笔状态"""
        assert ForeshadowStatus.SETUP == "setup"
        assert ForeshadowStatus.DEVELOPING == "developing"
        assert ForeshadowStatus.RESOLVED == "resolved"


class TestReviewNoteSchemas:
    """ReviewNote Schemas 测试"""
    
    def test_issue_types(self):
        """测试问题类型"""
        assert IssueType.CONSISTENCY == "consistency"
        assert IssueType.PLOT_HOLE == "plot_hole"
        assert IssueType.PACING == "pacing"
        assert IssueType.HOOK == "hook"
    
    def test_severity_levels(self):
        """测试严重级别"""
        assert Severity.LOW == "low"
        assert Severity.MEDIUM == "medium"
        assert Severity.HIGH == "high"
        assert Severity.CRITICAL == "critical"
