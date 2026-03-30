"""发布相关 API 路由"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
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
from app.services.publish.service import PublishService

router = APIRouter(tags=["publish"])


# ==================== 平台账户 API ====================

@router.post("/platform/accounts/register-session", response_model=PlatformAccountResponse)
async def register_platform_session(
    request: PlatformAccountRegister,
    db: AsyncSession = Depends(get_db)
):
    """注册平台会话"""
    service = PublishService(db)
    result = await service.register_session(request)
    
    return result


@router.get("/platform/accounts/{account_id}/status", response_model=PlatformAccountResponse)
async def get_account_status(
    account_id: str,
    platform: str,  # Query param
    db: AsyncSession = Depends(get_db)
):
    """获取账户状态"""
    service = PublishService(db)
    result = await service.get_account_status(platform, account_id)
    
    return result


@router.post("/platform/books/bind", response_model=BookBindResponse)
async def bind_book(
    request: BookBindRequest,
    db: AsyncSession = Depends(get_db)
):
    """绑定书籍"""
    service = PublishService(db)
    result = await service.bind_book(request)
    
    return result


# ==================== 发布任务 API ====================

@router.post("/projects/{project_id}/publish/draft", response_model=PublishTaskResponse)
async def create_publish_draft(
    project_id: int,
    request: PublishDraftRequest,
    db: AsyncSession = Depends(get_db)
):
    """创建草稿发布任务"""
    service = PublishService(db)
    task = await service.create_draft(project_id, request)
    
    return task


@router.post("/projects/{project_id}/publish/submit", response_model=PublishTaskResponse)
async def submit_for_publish(
    project_id: int,
    request: PublishSubmitRequest,
    db: AsyncSession = Depends(get_db)
):
    """提交发布"""
    service = PublishService(db)
    
    try:
        task = await service.submit_for_publish(project_id, request)
        return task
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/projects/{project_id}/publish/tasks", response_model=PublishTaskListResponse)
async def list_publish_tasks(
    project_id: int,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """获取发布任务列表"""
    service = PublishService(db)
    tasks, total = await service.get_publish_tasks(project_id, skip, limit)
    
    return PublishTaskListResponse(items=tasks, total=total)


@router.get("/projects/{project_id}/publish/tasks/{task_id}", response_model=PublishTaskResponse)
async def get_publish_task(
    project_id: int,
    task_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取发布任务详情"""
    service = PublishService(db)
    task = await db.get(PublishTask, task_id)
    
    if not task or task.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )
    
    return task


@router.post("/projects/{project_id}/publish/tasks/{task_id}/sync", response_model=PublishTaskResponse)
async def sync_publish_task(
    project_id: int,
    task_id: int,
    request: SyncPublishTaskRequest,
    db: AsyncSession = Depends(get_db)
):
    """同步发布任务状态"""
    service = PublishService(db)
    
    try:
        task = await service.sync_task_status(project_id, task_id, request.force_refresh)
        return task
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/projects/{project_id}/publish/tasks/{task_id}/cancel", response_model=PublishTaskResponse)
async def cancel_publish_task(
    project_id: int,
    task_id: int,
    db: AsyncSession = Depends(get_db)
):
    """取消发布任务"""
    service = PublishService(db)
    
    try:
        task = await service.cancel_task(project_id, task_id)
        return task
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


from app.models.publish_task import PublishTask
