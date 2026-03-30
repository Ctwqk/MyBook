"""Planner Service 数据模型"""
from typing import Any, Optional

from pydantic import BaseModel, Field


class PremiseAnalysis(BaseModel):
    """Premise 分析结果"""
    genre: str
    theme: str
    tone: str
    target_audience: str
    key_elements: list[str]
    potential_conflicts: list[str]


class StoryBibleDraft(BaseModel):
    """Story Bible 初稿"""
    title: str
    genre: str
    theme: str
    logline: str
    synopsis: str
    world_overview: str
    narrative_structure: dict[str, Any]
    characters: list[str] = []


class CharacterCard(BaseModel):
    """角色卡"""
    name: str
    role_type: str = "supporting"  # protagonist, supporting, antagonist, minor
    profile: str
    personality: str
    motivation: str
    secrets: Optional[str] = None
    relationships: dict[str, Any] = {}


class ArcPlan(BaseModel):
    """弧线规划"""
    total_arcs: int
    volumes: list["VolumeSummary"] = []


class VolumeSummary(BaseModel):
    """卷摘要"""
    volume_no: int
    title: str
    goal: str
    conflict: str
    expected_chapter_count: int


class ChapterOutline(BaseModel):
    """章节大纲"""
    chapter_no: int
    title: str
    outline: str
    hook: str
    key_events: list[str] = []
