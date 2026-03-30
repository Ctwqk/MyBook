"""完整的 Publish Service 测试"""
import pytest

from app.models.publish_task import (
    PublishStatus,
    PublishMode,
    PublishErrorCode,
    PublishTask,
)
from app.schemas.publish import (
    PlatformAccountRegister,
    PlatformAccountResponse,
    BookBindRequest,
    BookBindResponse,
    PublishDraftRequest,
    PublishSubmitRequest,
    PublishTaskResponse,
    PublishTaskListResponse,
    SyncPublishTaskRequest,
)
from app.services.publish.state_machine import PublishStateMachine
from app.services.publish.adapter import MockPlatformAdapter, PlatformAdapter


class TestPublishStatus:
    """发布状态测试"""
    
    def test_all_status_values(self):
        """测试所有发布状态"""
        assert PublishStatus.PENDING == "pending"
        assert PublishStatus.PREPARING == "preparing"
        assert PublishStatus.SUBMITTING == "submitting"
        assert PublishStatus.SUCCESS == "success"
        assert PublishStatus.FAILED == "failed"
        assert PublishStatus.CANCELLED == "cancelled"
    
    def test_status_from_string(self):
        """测试从字符串创建状态"""
        status = PublishStatus("pending")
        assert status == PublishStatus.PENDING
    
    def test_status_comparison(self):
        """测试状态比较"""
        assert PublishStatus.PENDING != PublishStatus.SUCCESS
        assert PublishStatus.FAILED == PublishStatus.FAILED


class TestPublishMode:
    """发布模式测试"""
    
    def test_all_mode_values(self):
        """测试所有发布模式"""
        assert PublishMode.DRAFT == "draft"
        assert PublishMode.IMMEDIATE == "immediate"


class TestPublishErrorCode:
    """发布错误码测试"""
    
    def test_all_error_codes(self):
        """测试所有错误码"""
        assert PublishErrorCode.SESSION_EXPIRED == "SESSION_EXPIRED"
        assert PublishErrorCode.BOOK_NOT_BOUND == "BOOK_NOT_BOUND"
        assert PublishErrorCode.NETWORK_ERROR == "NETWORK_ERROR"
        assert PublishErrorCode.PLATFORM_VALIDATION_ERROR == "PLATFORM_VALIDATION_ERROR"
        assert PublishErrorCode.DUPLICATE_SUBMISSION == "DUPLICATE_SUBMISSION"
        assert PublishErrorCode.PLATFORM_LAYOUT_CHANGED == "PLATFORM_LAYOUT_CHANGED"
        assert PublishErrorCode.CONTENT_FORMAT_ERROR == "CONTENT_FORMAT_ERROR"
        assert PublishErrorCode.RISK_CONTROL_BLOCKED == "RISK_CONTROL_BLOCKED"
        assert PublishErrorCode.UNKNOWN_ERROR == "UNKNOWN_ERROR"


class TestPublishStateMachine:
    """发布状态机测试"""
    
    def test_initial_state(self):
        """测试初始状态"""
        sm = PublishStateMachine()
        assert sm.get_next_status(PublishStatus.PENDING) == PublishStatus.PREPARING
    
    def test_valid_transitions(self):
        """测试有效状态转换"""
        sm = PublishStateMachine()
        
        # PENDING -> PREPARING
        assert sm.can_transition(PublishStatus.PENDING, PublishStatus.PREPARING)
        
        # PREPARING -> SUBMITTING
        assert sm.can_transition(PublishStatus.PREPARING, PublishStatus.SUBMITTING)
        
        # SUBMITTING -> SUCCESS
        assert sm.can_transition(PublishStatus.SUBMITTING, PublishStatus.SUCCESS)
        
        # SUBMITTING -> FAILED
        assert sm.can_transition(PublishStatus.SUBMITTING, PublishStatus.FAILED)
    
    def test_invalid_transitions(self):
        """测试无效状态转换"""
        sm = PublishStateMachine()
        
        # 不能从 SUCCESS 直接回退
        assert not sm.can_transition(PublishStatus.SUCCESS, PublishStatus.PENDING)
        
        # 不能从 CANCELLED 转换
        assert not sm.can_transition(PublishStatus.CANCELLED, PublishStatus.PENDING)
        
        # 不能跳过状态
        assert not sm.can_transition(PublishStatus.PENDING, PublishStatus.SUCCESS)
    
    def test_can_cancel(self):
        """测试取消权限"""
        sm = PublishStateMachine()
        
        assert sm.can_cancel(PublishStatus.PENDING) is True
        assert sm.can_cancel(PublishStatus.PREPARING) is True
        assert sm.can_cancel(PublishStatus.SUBMITTING) is False
        assert sm.can_cancel(PublishStatus.SUCCESS) is False
    
    def test_can_retry(self):
        """测试重试权限"""
        sm = PublishStateMachine()
        
        assert sm.can_retry(PublishStatus.FAILED) is True
        assert sm.can_retry(PublishStatus.SUCCESS) is False
        assert sm.can_retry(PublishStatus.PENDING) is False
    
    def test_is_terminal(self):
        """测试终态"""
        sm = PublishStateMachine()
        
        assert sm.is_terminal(PublishStatus.SUCCESS) is True
        assert sm.is_terminal(PublishStatus.CANCELLED) is True
        assert sm.is_terminal(PublishStatus.PENDING) is False
        assert sm.is_terminal(PublishStatus.FAILED) is False
    
    def test_complete_workflow(self):
        """测试完整工作流"""
        sm = PublishStateMachine()
        
        # 成功流程
        assert sm.can_transition(PublishStatus.PENDING, PublishStatus.PREPARING)
        assert sm.can_transition(PublishStatus.PREPARING, PublishStatus.SUBMITTING)
        assert sm.can_transition(PublishStatus.SUBMITTING, PublishStatus.SUCCESS)
        assert sm.is_terminal(PublishStatus.SUCCESS)
        
        # 失败流程
        assert sm.can_transition(PublishStatus.SUBMITTING, PublishStatus.FAILED)
        assert sm.can_retry(PublishStatus.FAILED)
        
        # 取消流程
        assert sm.can_transition(PublishStatus.PENDING, PublishStatus.CANCELLED)
        assert sm.is_terminal(PublishStatus.CANCELLED)


class TestPublishSchemas:
    """发布 Schemas 测试"""
    
    def test_platform_account_register(self):
        """测试平台账户注册"""
        data = PlatformAccountRegister(
            platform="mock",
            session_token="token_123",
            extra_data={"key": "value"}
        )
        
        assert data.platform == "mock"
        assert data.session_token == "token_123"
    
    def test_platform_account_response(self):
        """测试平台账户响应"""
        data = PlatformAccountResponse(
            account_id="acc_123",
            platform="mock",
            status="active",
            bound_books=["book_1", "book_2"]
        )
        
        assert data.account_id == "acc_123"
        assert len(data.bound_books) == 2
    
    def test_book_bind_request(self):
        """测试书籍绑定请求"""
        data = BookBindRequest(
            platform="mock",
            account_id="acc_123",
            remote_book_id="remote_book",
            book_title="我的小说",
            extra_data={"category": "玄幻"}
        )
        
        assert data.book_title == "我的小说"
    
    def test_book_bind_response(self):
        """测试书籍绑定响应"""
        data = BookBindResponse(
            local_book_id=1,
            remote_book_id="remote_book",
            platform="mock",
            bound=True
        )
        
        assert data.local_book_id == 1
        assert data.bound is True
    
    def test_publish_draft_request(self):
        """测试草稿发布请求"""
        data = PublishDraftRequest(
            chapter_id=1,
            platform="mock",
            account_id="acc_123",
            remote_book_id="book_456",
            mode=PublishMode.DRAFT
        )
        
        assert data.chapter_id == 1
        assert data.mode == PublishMode.DRAFT
    
    def test_publish_submit_request(self):
        """测试提交发布请求"""
        data = PublishSubmitRequest(
            chapter_id=2,
            platform="mock",
            account_id="acc_123",
            remote_book_id="book_456",
            mode=PublishMode.IMMEDIATE
        )
        
        assert data.mode == PublishMode.IMMEDIATE
    
    def test_sync_publish_task_request(self):
        """测试同步任务请求"""
        data = SyncPublishTaskRequest(force_refresh=True)
        
        assert data.force_refresh is True
    
    def test_publish_task_list_response(self):
        """测试发布任务列表响应"""
        from app.schemas.publish import PublishTaskResponse
        from datetime import datetime
        
        # 创建模拟任务
        tasks = [
            PublishTaskResponse(
                id=1,
                project_id=1,
                chapter_id=1,
                platform="mock",
                account_id="acc",
                remote_book_id="book",
                mode=PublishMode.DRAFT,
                status=PublishStatus.SUCCESS,
                error_code=None,
                error_message=None,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        ]
        
        response = PublishTaskListResponse(items=tasks, total=1)
        
        assert response.total == 1
        assert len(response.items) == 1


class TestMockPlatformAdapter:
    """Mock 平台适配器测试"""
    
    @pytest.mark.asyncio
    async def test_register_session(self):
        """测试注册会话"""
        adapter = MockPlatformAdapter()
        
        result = await adapter.register_session(
            session_token="test_token",
            extra_data={"key": "value"}
        )
        
        assert "account_id" in result
        assert result["status"] == "active"
    
    @pytest.mark.asyncio
    async def test_get_account_status(self):
        """测试获取账户状态"""
        adapter = MockPlatformAdapter()
        
        # 先注册
        await adapter.register_session(session_token="test")
        
        result = await adapter.get_account_status("mock_account_1")
        
        assert "status" in result
    
    @pytest.mark.asyncio
    async def test_bind_book(self):
        """测试绑定书籍"""
        adapter = MockPlatformAdapter()
        
        result = await adapter.bind_book(
            account_id="acc_1",
            remote_book_id="book_1",
            book_title="测试小说"
        )
        
        assert result["bound"] is True
    
    @pytest.mark.asyncio
    async def test_publish_chapter_success(self):
        """测试发布章节成功"""
        adapter = MockPlatformAdapter()
        
        result = await adapter.publish_chapter(
            account_id="acc_1",
            book_id="book_1",
            chapter_no=1,
            title="第一章",
            content="章节内容...",
            mode="immediate"
        )
        
        # Mock 有 90% 成功率
        if result["success"]:
            assert "task_id" in result
        else:
            assert "error_code" in result
    
    @pytest.mark.asyncio
    async def test_get_task_status(self):
        """测试获取任务状态"""
        adapter = MockPlatformAdapter()
        
        result = await adapter.get_task_status("acc_1", "task_1")
        
        assert "status" in result


class TestPlatformAdapterInterface:
    """平台适配器接口测试"""
    
    def test_adapter_has_required_methods(self):
        """测试适配器有所需方法"""
        adapter = MockPlatformAdapter()
        
        assert hasattr(adapter, 'register_session')
        assert hasattr(adapter, 'get_account_status')
        assert hasattr(adapter, 'bind_book')
        assert hasattr hasattr(adapter, 'publish_chapter')
        assert hasattr(adapter, 'get_task_status')
    
    def test_adapter_is_instance(self):
        """测试适配器实例"""
        adapter = MockPlatformAdapter()
        
        assert isinstance(adapter, PlatformAdapter)


class TestPublishWorkflow:
    """发布工作流测试"""
    
    def test_create_publish_task(self):
        """测试创建发布任务"""
        task = PublishTask(
            project_id=1,
            chapter_id=1,
            platform="mock",
            account_id="acc_123",
            remote_book_id="book_456",
            mode=PublishMode.DRAFT,
            status=PublishStatus.PENDING
        )
        
        assert task.status == PublishStatus.PENDING
        assert task.mode == PublishMode.DRAFT
    
    def test_publish_task_with_error(self):
        """测试带错误的发布任务"""
        task = PublishTask(
            project_id=1,
            chapter_id=1,
            platform="mock",
            status=PublishStatus.FAILED,
            error_code=PublishErrorCode.NETWORK_ERROR,
            error_message="网络连接失败"
        )
        
        assert task.status == PublishStatus.FAILED
        assert task.error_code == PublishErrorCode.NETWORK_ERROR
    
    def test_publish_task_success(self):
        """测试成功的发布任务"""
        task = PublishTask(
            project_id=1,
            chapter_id=1,
            platform="mock",
            status=PublishStatus.SUCCESS
        )
        
        assert task.status == PublishStatus.SUCCESS
        assert task.error_code is None
