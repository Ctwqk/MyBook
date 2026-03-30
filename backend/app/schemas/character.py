"""角色相关 Pydantic schemas"""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class CharacterBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    role_type: str = Field(default="supporting", max_length=50)
    profile: Optional[str] = None
    personality: Optional[str] = None
    motivation: Optional[str] = None
    secrets: Optional[str] = None
    relationships: Optional[dict[str, Any]] = None
    current_state: Optional[dict[str, Any]] = None
    power_level: Optional[int] = Field(None, ge=0)
    tags: Optional[list[str]] = None


class CharacterCreate(BaseModel):
    """创建角色 - project_id 从路径参数获取"""
    name: str = Field(..., min_length=1, max_length=100)
    role_type: Optional[str] = Field(default="supporting", max_length=50)
    profile: Optional[str] = None
    personality: Optional[str] = None
    motivation: Optional[str] = None
    secrets: Optional[str] = None
    relationships: Optional[dict[str, Any]] = None
    current_state: Optional[dict[str, Any]] = None
    power_level: Optional[int] = Field(None, ge=0)
    tags: Optional[list[str]] = None


class CharacterUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    role_type: Optional[str] = Field(None, max_length=50)
    profile: Optional[str] = None
    personality: Optional[str] = None
    motivation: Optional[str] = None
    secrets: Optional[str] = None
    relationships: Optional[dict[str, Any]] = None
    current_state: Optional[dict[str, Any]] = None
    power_level: Optional[int] = Field(None, ge=0)
    tags: Optional[list[str]] = None


class CharacterResponse(CharacterBase):
    id: int
    project_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CharacterStateBase(BaseModel):
    location: Optional[str] = None
    goal: Optional[str] = None
    emotional_state: Optional[str] = None
    power_level: Optional[int] = None
    relationship_state: Optional[dict[str, Any]] = None
    last_event: Optional[str] = None


class CharacterStateCreate(CharacterStateBase):
    project_id: int
    character_id: int


class CharacterStateResponse(CharacterStateBase):
    id: int
    project_id: int
    character_id: int
    updated_at: datetime

    model_config = {"from_attributes": True}
