"""Publish Service 测试"""
import pytest
from app.services.publish.service import PublishService
from app.services.publish.state_machine import PublishStateMachine
from app.models.publish_task import PublishStatus


class TestPublishStateMachine:
    """发布状态机测试"""
    
    def test_can_transition(self):
        """测试状态转换"""
        sm = PublishStateMachine()
        
        # 允许的转换
        assert sm.can_transition(PublishStatus.PENDING, PublishStatus.PREPARING)
        assert sm.can_transition(PublishStatus.PREPARING, PublishStatus.SUBMITTING)
        assert sm.can_transition(PublishStatus.SUBMITTING, PublishStatus.SUCCESS)
        
        # 不允许的转换
        assert not sm.can_transition(PublishStatus.SUCCESS, PublishStatus.PENDING)
        assert not sm.can_transition(PublishStatus.CANCELLED, PublishStatus.PENDING)
    
    def test_can_cancel(self):
        """测试取消权限"""
        sm = PublishStateMachine()
        
        assert sm.can_cancel(PublishStatus.PENDING)
        assert sm.can_cancel(PublishStatus.PREPARING)
        assert not sm.can_cancel(PublishStatus.SUBMITTING)
        assert not sm.can_cancel(PublishStatus.SUCCESS)
    
    def test_is_terminal(self):
        """测试终态"""
        sm = PublishStateMachine()
        
        assert sm.is_terminal(PublishStatus.SUCCESS)
        assert sm.is_terminal(PublishStatus.CANCELLED)
        assert not sm.is_terminal(PublishStatus.PENDING)
        assert not sm.is_terminal(PublishStatus.FAILED)


class TestPublishService:
    """Publish Service 测试类"""
    
    @pytest.mark.asyncio
    async def test_create_draft(self, db_session, test_project):
        """测试创建草稿"""
        from app.models.chapter import Chapter, ChapterStatus
        chapter = Chapter(
            project_id=test_project.id,
            chapter_no=1,
            title="第一章",
            status=ChapterStatus.OUTLINE
        )
        db_session.add(chapter)
        await db_session.commit()
        
        service = PublishService(db_session)
        
        from app.schemas.publish import PublishDraftRequest, PublishMode
        request = PublishDraftRequest(
            chapter_id=chapter.id,
            platform="mock",
            account_id="test_account",
            mode=PublishMode.DRAFT
        )
        
        task = await service.create_draft(test_project.id, request)
        
        assert task is not None
        assert task.status == PublishStatus.PENDING
