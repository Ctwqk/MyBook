"""记忆相关 Pydantic schemas"""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class StoryBibleBase(BaseModel):
    title: Optional[str] = None
    genre: Optional[str] = None
    theme: Optional[str] = None
    logline: Optional[str] = None
    synopsis: Optional[str] = None
    tone: Optional[str] = None
    target_audience: Optional[str] = None
    world_overview: Optional[str] = None
    world_rules: Optional[list[str]] = None
    magic_system: Optional[str] = None
    narrative_structure: Optional[dict[str, Any]] = None
    key_plot_points: Optional[list[str]] = None
    metadata: Optional[dict[str, Any]] = Field(None, validation_alias="meta_data")


class StoryBibleCreate(StoryBibleBase):
    project_id: int


class StoryBibleUpdate(BaseModel):
    title: Optional[str] = None
    genre: Optional[str] = None
    theme: Optional[str] = None
    logline: Optional[str] = None
    synopsis: Optional[str] = None
    tone: Optional[str] = None
    target_audience: Optional[str] = None
    world_overview: Optional[str] = None
    world_rules: Optional[list[str]] = None
    magic_system: Optional[str] = None
    narrative_structure: Optional[dict[str, Any]] = None
    key_plot_points: Optional[list[str]] = None
    metadata: Optional[dict[str, Any]] = None


class StoryBibleResponse(StoryBibleBase):
    id: int
    project_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChapterMemoryBase(BaseModel):
    summary: Optional[str] = None
    key_events: Optional[list[str]] = None
    new_world_details: Optional[list[str]] = None
    foreshadow_changes: Optional[list[str]] = None


class ChapterMemoryCreate(ChapterMemoryBase):
    project_id: int
    chapter_id: int


class ChapterMemoryResponse(ChapterMemoryBase):
    id: int
    project_id: int
    chapter_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ContextPackRequest(BaseModel):
    """上下文包构建请求"""
    chapter_id: Optional[int] = None
    include_story_bible: bool = True
    include_character_states: bool = True
    include_recent_chapters: int = Field(default=3, ge=0, le=10)
    include_foreshadows: bool = True
    include_pending_reviews: bool = False


class ContextPackResponse(BaseModel):
    """上下文包响应"""
    story_bible: Optional[StoryBibleResponse] = None
    character_states: list[dict[str, Any]] = []
    recent_chapters: list[dict[str, Any]] = []
    foreshadows: list[dict[str, Any]] = []
    pending_reviews: list[dict[str, Any]] = []
    formatted_context: str  # 格式化后的上下文文本


class ForeshadowRecordBase(BaseModel):
    content: str
    related_entities: Optional[list[str]] = None
    planned_resolution: Optional[str] = None


class ForeshadowRecordCreate(ForeshadowRecordBase):
    project_id: int
    chapter_id: int


class ForeshadowRecordResponse(ForeshadowRecordBase):
    id: int
    project_id: int
    chapter_id: int
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MemorySearchRequest(BaseModel):
    """记忆搜索请求"""
    query: str = Field(..., min_length=1)
    search_type: str = Field(default="all")  # all, character, world, plot
    limit: int = Field(default=10, ge=1, le=50)


class MemorySearchResponse(BaseModel):
    """记忆搜索响应"""
    results: list[dict[str, Any]]
    total: int


class CharacterBase(BaseModel):
    """角色基本信息"""
    name: str
    role_type: str
    profile: Optional[str] = None
    personality: Optional[str] = None
    motivation: Optional[str] = None
    secrets: Optional[str] = None
    relationships: Optional[dict[str, Any]] = None
    current_state: Optional[dict[str, Any]] = None
    power_level: Optional[int] = None
    tags: Optional[list[str]] = None


class CharacterResponse(CharacterBase):
    """角色响应"""
    id: int
    project_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
