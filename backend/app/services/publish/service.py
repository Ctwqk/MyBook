"""Publish Service - 发布服务"""
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.publish_task import (
    PublishTask,
    PublishStatus,
    PublishMode,
    PublishErrorCode,
)
from app.models.chapter import Chapter
from app.repositories.chapter import ChapterRepository
from app.services.publish.adapter import PlatformAdapter, MockPlatformAdapter
from app.services.publish.state_machine import PublishStateMachine
from app.schemas.publish import (
    PlatformAccountRegister,
    PlatformAccountResponse,
    BookBindRequest,
    BookBindResponse,
    PublishDraftRequest,
    PublishSubmitRequest,
    PublishTaskResponse,
)


class PublishService:
    """发布服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.chapter_repo = ChapterRepository(db)
        self.state_machine = PublishStateMachine()

    def _get_adapter(self, platform: str) -> PlatformAdapter:
        """
        获取平台适配器
        
        Args:
            platform: 平台标识
            
        Returns:
            PlatformAdapter: 平台适配器实例
        """
        # TODO: 根据 platform 返回对应的 adapter
        # 目前返回 mock adapter
        return MockPlatformAdapter()

    # ==================== Platform Account ====================
    
    async def register_session(
        self,
        request: PlatformAccountRegister
    ) -> PlatformAccountResponse:
        """
        注册平台会话
        
        Args:
            request: 注册请求
            
        Returns:
            PlatformAccountResponse: 账户响应
        """
        adapter = self._get_adapter(request.platform)
        
        # 调用 adapter 注册会话
        result = await adapter.register_session(
            session_token=request.session_token,
            extra_data=request.extra_data
        )
        
        return PlatformAccountResponse(
            account_id=result.get("account_id", "mock_account"),
            platform=request.platform,
            status=result.get("status", "active"),
            bound_books=result.get("bound_books", [])
        )

    async def get_account_status(
        self,
        platform: str,
        account_id: str
    ) -> PlatformAccountResponse:
        """
        获取账户状态
        
        Args:
            platform: 平台标识
            account_id: 账户 ID
            
        Returns:
            PlatformAccountResponse: 账户响应
        """
        adapter = self._get_adapter(platform)
        
        result = await adapter.get_account_status(account_id)
        
        return PlatformAccountResponse(
            account_id=account_id,
            platform=platform,
            status=result.get("status", "unknown"),
            bound_books=result.get("bound_books", [])
        )

    # ==================== Book Binding ====================
    
    async def bind_book(
        self,
        request: BookBindRequest
    ) -> BookBindResponse:
        """
        绑定书籍
        
        Args:
            request: 绑定请求
            
        Returns:
            BookBindResponse: 绑定响应
        """
        adapter = self._get_adapter(request.platform)
        
        result = await adapter.bind_book(
            account_id=request.account_id,
            remote_book_id=request.remote_book_id,
            book_title=request.book_title,
            extra_data=request.extra_data
        )
        
        return BookBindResponse(
            local_book_id=result.get("local_book_id"),
            remote_book_id=request.remote_book_id,
            platform=request.platform,
            bound=result.get("bound", True)
        )

    # ==================== Publish Operations ====================
    
    async def create_draft(
        self,
        project_id: int,
        request: PublishDraftRequest
    ) -> PublishTask:
        """
        创建草稿发布任务
        
        Args:
            project_id: 项目 ID
            request: 发布请求
            
        Returns:
            PublishTask: 发布任务
        """
        chapter = await self.chapter_repo.get(request.chapter_id)
        if not chapter:
            raise ValueError(f"Chapter {request.chapter_id} not found")
        
        # 创建发布任务
        task = PublishTask(
            project_id=project_id,
            chapter_id=request.chapter_id,
            platform=request.platform,
            account_id=request.account_id,
            remote_book_id=request.remote_book_id,
            mode=PublishMode.DRAFT,
            status=PublishStatus.PENDING
        )
        self.db.add(task)
        
        await self.db.flush()
        await self.db.refresh(task)
        
        return task

    async def submit_for_publish(
        self,
        project_id: int,
        request: PublishSubmitRequest
    ) -> PublishTask:
        """
        提交发布
        
        Args:
            project_id: 项目 ID
            request: 发布请求
            
        Returns:
            PublishTask: 发布任务
        """
        chapter = await self.chapter_repo.get(request.chapter_id)
        if not chapter:
            raise ValueError(f"Chapter {request.chapter_id} not found")
        
        if not chapter.text:
            raise ValueError("Chapter text is empty, cannot publish")
        
        # 创建发布任务
        task = PublishTask(
            project_id=project_id,
            chapter_id=request.chapter_id,
            platform=request.platform,
            account_id=request.account_id,
            remote_book_id=request.remote_book_id,
            mode=PublishMode.IMMEDIATE,
            status=PublishStatus.PENDING
        )
        self.db.add(task)
        
        await self.db.flush()
        
        # 执行发布
        adapter = self._get_adapter(request.platform)
        try:
            # 更新状态为准备中
            task.status = PublishStatus.PREPARING
            await self.db.flush()
            
            # 调用 adapter 发布
            result = await adapter.publish_chapter(
                account_id=request.account_id,
                book_id=request.remote_book_id,
                chapter_no=chapter.chapter_no,
                title=chapter.title or f"第{chapter.chapter_no}章",
                content=chapter.text,
                mode=request.mode.value
            )
            
            if result.get("success"):
                task.status = PublishStatus.SUCCESS
            else:
                task.status = PublishStatus.FAILED
                task.error_code = result.get("error_code", PublishErrorCode.UNKNOWN_ERROR)
                task.error_message = result.get("error_message")
                
        except Exception as e:
            task.status = PublishStatus.FAILED
            task.error_code = PublishErrorCode.UNKNOWN_ERROR
            task.error_message = str(e)
        
        await self.db.flush()
        await self.db.refresh(task)
        
        return task

    async def get_publish_tasks(
        self,
        project_id: int,
        skip: int = 0,
        limit: int = 50
    ) -> tuple[list[PublishTask], int]:
        """
        获取发布任务列表
        
        Args:
            project_id: 项目 ID
            skip: 跳过数量
            limit: 限制数量
            
        Returns:
            tuple: (任务列表, 总数)
        """
        from sqlalchemy import select, func
        
        # 获取总数
        count_result = await self.db.execute(
            select(func.count(PublishTask.id))
            .where(PublishTask.project_id == project_id)
        )
        total = count_result.scalar_one()
        
        # 获取列表
        result = await self.db.execute(
            select(PublishTask)
            .where(PublishTask.project_id == project_id)
            .order_by(PublishTask.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        tasks = list(result.scalars().all())
        
        return tasks, total

    async def sync_task_status(
        self,
        project_id: int,
        task_id: int,
        force_refresh: bool = False
    ) -> PublishTask:
        """
        同步任务状态
        
        Args:
            project_id: 项目 ID
            task_id: 任务 ID
            force_refresh: 是否强制刷新
            
        Returns:
            PublishTask: 更新后的任务
        """
        task = await self.db.get(PublishTask, task_id)
        if not task or task.project_id != project_id:
            raise ValueError(f"Task {task_id} not found")
        
        if task.status not in [PublishStatus.PENDING, PublishStatus.SUBMITTING]:
            if not force_refresh:
                return task
        
        adapter = self._get_adapter(task.platform)
        
        try:
            status = await adapter.get_task_status(
                account_id=task.account_id,
                task_id=str(task.id)
            )
            
            # 更新状态
            new_status = status.get("status")
            if new_status:
                task.status = PublishStatus(new_status)
            
            if status.get("error"):
                task.error_message = status.get("error")
                
        except Exception as e:
            task.error_message = str(e)
        
        await self.db.flush()
        await self.db.refresh(task)
        
        return task

    async def cancel_task(
        self,
        project_id: int,
        task_id: int
    ) -> PublishTask:
        """
        取消发布任务
        
        Args:
            project_id: 项目 ID
            task_id: 任务 ID
            
        Returns:
            PublishTask: 更新后的任务
        """
        task = await self.db.get(PublishTask, task_id)
        if not task or task.project_id != project_id:
            raise ValueError(f"Task {task_id} not found")
        
        # 使用状态机检查是否可以取消
        if not self.state_machine.can_cancel(task.status):
            raise ValueError(f"Cannot cancel task with status {task.status}")
        
        task.status = PublishStatus.CANCELLED
        await self.db.flush()
        await self.db.refresh(task)
        
        return task
