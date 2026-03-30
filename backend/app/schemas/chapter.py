"""章节相关 Pydantic schemas"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.chapter import ChapterStatus


class ChapterBase(BaseModel):
    chapter_no: int = Field(..., ge=1)
    title: Optional[str] = Field(None, max_length=200)
    outline: Optional[str] = None
    text: Optional[str] = None
    summary: Optional[str] = None
    hook: Optional[str] = None


class ChapterCreate(ChapterBase):
    project_id: int
    volume_id: Optional[int] = None


class ChapterUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    outline: Optional[str] = None
    text: Optional[str] = None
    summary: Optional[str] = None
    hook: Optional[str] = None
    status: Optional[ChapterStatus] = None
    word_count: Optional[int] = Field(None, ge=0)


class ChapterResponse(ChapterBase):
    id: int
    project_id: int
    volume_id: Optional[int]
    status: ChapterStatus
    word_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChapterOutlineRequest(BaseModel):
    """章节大纲生成请求"""
    volume_id: Optional[int] = None
    chapter_count: int = Field(default=10, ge=1, le=100)
    existing_outlines: Optional[list[str]] = None  # 已有的大纲摘要


class ChapterOutlineResponse(BaseModel):
    """章节大纲响应"""
    chapters: list[ChapterResponse]


class GenerateChapterRequest(BaseModel):
    """生成章节正文请求"""
    outline: Optional[str] = None  # 可选自定义大纲
    context_pack_id: Optional[int] = None  # 上下文包ID
    style_hints: Optional[str] = None  # 风格提示


class ContinueChapterRequest(BaseModel):
    """续写章节请求"""
    last_paragraph: Optional[str] = None  # 最后一段内容
    target_word_count: int = Field(default=3000, ge=500, le=10000)


class RewriteChapterRequest(BaseModel):
    """重写章节请求"""
    rewrite_instructions: str  # 重写指令


class PatchChapterRequest(BaseModel):
    """修补章节段落请求"""
    segment_id: str  # 段落标识
    segment_content: str  # 需要修补的段落内容
    patch_instructions: str  # 修补指令
