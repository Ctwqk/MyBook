"""项目相关 Pydantic schemas"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.project import ProjectStatus


class ProjectBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    genre: Optional[str] = Field(None, max_length=100)
    style: Optional[str] = Field(None, max_length=100)
    premise: Optional[str] = None
    target_length: Optional[int] = Field(None, ge=0)
    target_chapters: Optional[int] = Field(None, ge=1)  # 目标章节数
    chapter_length: Optional[int] = Field(None, ge=500)  # 每章节字数
    raw_prompt: Optional[str] = None  # 原始 Prompt


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    genre: Optional[str] = Field(None, max_length=100)
    style: Optional[str] = Field(None, max_length=100)
    premise: Optional[str] = None
    target_length: Optional[int] = Field(None, ge=0)
    target_chapters: Optional[int] = Field(None, ge=1)
    chapter_length: Optional[int] = Field(None, ge=500)
    raw_prompt: Optional[str] = None
    status: Optional[ProjectStatus] = None


class ProjectResponse(ProjectBase):
    id: int
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    total: int
