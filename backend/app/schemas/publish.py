"""发布相关 Pydantic schemas"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.publish_task import PublishErrorCode, PublishMode, PublishStatus


class PlatformAccountRegister(BaseModel):
    """平台账户注册"""
    platform: str = Field(..., min_length=1)
    session_token: str
    extra_data: Optional[dict] = None


class PlatformAccountResponse(BaseModel):
    """平台账户响应"""
    account_id: str
    platform: str
    status: str
    bound_books: list[str] = []


class BookBindRequest(BaseModel):
    """书籍绑定请求"""
    platform: str
    account_id: str
    remote_book_id: str
    book_title: str
    extra_data: Optional[dict] = None


class BookBindResponse(BaseModel):
    """书籍绑定响应"""
    local_book_id: Optional[int] = None  # 本地关联的项目ID
    remote_book_id: str
    platform: str
    bound: bool


class PublishDraftRequest(BaseModel):
    """发布草稿请求"""
    chapter_id: int
    platform: str
    account_id: str
    remote_book_id: Optional[str] = None
    mode: PublishMode = PublishMode.DRAFT


class PublishSubmitRequest(BaseModel):
    """发布提交请求"""
    chapter_id: int
    platform: str
    account_id: str
    remote_book_id: str
    mode: PublishMode = PublishMode.IMMEDIATE


class PublishTaskResponse(BaseModel):
    """发布任务响应"""
    id: int
    project_id: int
    chapter_id: int
    platform: str
    account_id: Optional[str]
    remote_book_id: Optional[str]
    mode: PublishMode
    status: PublishStatus
    error_code: Optional[PublishErrorCode]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PublishTaskListResponse(BaseModel):
    """发布任务列表响应"""
    items: list[PublishTaskResponse]
    total: int


class SyncPublishTaskRequest(BaseModel):
    """同步发布任务状态请求"""
    force_refresh: bool = False
