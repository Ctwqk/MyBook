"""卷/篇章 Pydantic schemas"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class VolumeBase(BaseModel):
    volume_no: int = Field(..., ge=1)
    title: str = Field(..., min_length=1, max_length=200)
    goal: Optional[str] = None
    conflict: Optional[str] = None
    expected_chapter_count: int = Field(default=10, ge=1)
    summary: Optional[str] = None


class VolumeCreate(VolumeBase):
    project_id: int


class VolumeUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    goal: Optional[str] = None
    conflict: Optional[str] = None
    expected_chapter_count: Optional[int] = Field(None, ge=1)
    summary: Optional[str] = None


class VolumeResponse(VolumeBase):
    id: int
    project_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ArcPlanRequest(BaseModel):
    """卷/弧线规划请求"""
    total_arcs: int = Field(default=3, ge=1, le=10)
    target_chapters_per_arc: int = Field(default=30, ge=5)
    arc_goals: Optional[list[str]] = None  # 每个弧线的主要目标
    arc_conflicts: Optional[list[str]] = None  # 每个弧线的主要冲突


class ArcPlanResponse(BaseModel):
    """卷/弧线规划响应"""
    volumes: list[VolumeResponse]
