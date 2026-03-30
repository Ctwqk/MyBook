"""Orchestrator 数据模型 - Story Package, Context Pack, Chapter Draft"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ========================================
# Story Package - Planner 输出的初始故事包
# ========================================

class StructuredPremise(BaseModel):
    """结构化的 premise"""
    core_conflict: str  # 核心冲突
    protagonist_goal: str  # 主角目标
    setting_direction: str  # 设定方向
    tone_and_style: str  # 基调与风格
    target_audience: Optional[str] = None  # 目标读者


class StoryBibleDraft(BaseModel):
    """Story Bible 初稿"""
    world_rules: list[str] = []  # 世界规则
    factions: list[dict] = []  # 势力/组织
    important_locations: list[dict] = []  # 重要地点
    items_systems: list[dict] = []  # 道具/系统
    writing_style_constraints: list[str] = []  # 写作风格约束


class CharacterCardDraft(BaseModel):
    """角色卡初稿"""
    name: str
    role_type: str  # protagonist/antagonist/supporting
    personality: str
    motivation: str
    secrets: list[str] = []
    relationships: list[dict] = []


class ArcPlanDraft(BaseModel):
    """卷纲初稿"""
    volume_no: int
    title: str
    goal: str  # 本卷目标
    conflict: str  # 本卷冲突
    expected_chapter_count: int
    key_events: list[str] = []


class ChapterOutlineDraft(BaseModel):
    """章纲初稿"""
    chapter_no: int
    title: str
    goal: str  # 本章目标
    conflict: str  # 本章冲突
    ending_hook: str  # 章末钩子
    key_scenes: list[str] = []


class StoryPackage(BaseModel):
    """完整的故事包 - Planner 一次生成的所有内容"""
    project_id: str
    structured_premise: StructuredPremise
    story_bible_draft: StoryBibleDraft
    character_cards: list[CharacterCardDraft] = []
    arc_plans: list[ArcPlanDraft] = []
    chapter_outlines: list[ChapterOutlineDraft] = []
    created_at: datetime = Field(default_factory=datetime.now)


# ========================================
# Context Pack - Memory 组装的上下文包
# ========================================

class RelevantWorldSetting(BaseModel):
    """相关的世界观设定"""
    category: str
    name: str
    content: str
    importance: str  # critical/major/minor


class RelevantCharacterState(BaseModel):
    """相关角色状态"""
    character_id: str
    name: str
    location: str
    goal: str
    emotional_state: str
    relationship_state: dict = {}  # 与其他角色的关系


class RecentChapterSummary(BaseModel):
    """近期章节摘要"""
    chapter_no: int
    title: str
    summary: str
    key_events: list[str] = []


class ForeshadowInfo(BaseModel):
    """伏笔信息"""
    foreshadow_id: str
    content: str
    related_entities: list[str] = []
    status: str  # active/partially_resolved/resolved


class ReviewWarning(BaseModel):
    """审查警告"""
    chapter_no: Optional[int]
    issue_type: str
    description: str
    severity: str  # critical/major/minor


class ContextPack(BaseModel):
    """Memory 给 Writer/Reviewer 组装的上下文包"""
    project_id: str
    chapter_id: str
    chapter_outline: ChapterOutlineDraft
    
    # 相关内容
    relevant_world_settings: list[RelevantWorldSetting] = []
    relevant_character_states: list[RelevantCharacterState] = []
    recent_chapter_memories: list[RecentChapterSummary] = []
    
    # 当前进度
    current_arc_summary: Optional[str] = None
    current_arc_goal: Optional[str] = None
    
    # 伏笔与警告
    active_foreshadows: list[ForeshadowInfo] = []
    review_warnings: list[ReviewWarning] = []
    
    # 写作约束
    style_constraints: list[str] = []
    word_count_target: int = 3000


# ========================================
# Chapter Draft - Writer 生成的章节草稿
# ========================================

class CharacterStateChange(BaseModel):
    """角色状态变化"""
    character_id: str
    character_name: str
    changes: dict  # 具体变化


class NewWorldDetail(BaseModel):
    """新世界观细节"""
    category: str
    name: str
    content: str
    importance: str = "minor"


class ForeshadowChange(BaseModel):
    """伏笔变化"""
    foreshadow_id: Optional[str]
    content: str
    change_type: str  # new/resolved/partially_resolved
    related_entities: list[str] = []


class ChapterDraft(BaseModel):
    """章节草稿"""
    project_id: str
    chapter_id: str
    outline: ChapterOutlineDraft
    
    # 正文内容
    chapter_text: str
    
    # 结构化提取
    chapter_summary: str  # 章节摘要
    character_state_changes: list[CharacterStateChange] = []
    new_world_details: list[NewWorldDetail] = []
    new_foreshadows: list[ForeshadowChange] = []
    resolved_foreshadows: list[ForeshadowChange] = []
    writer_notes: str = ""
    
    # 元数据
    word_count: int = 0
    created_at: datetime = Field(default_factory=datetime.now)


# ========================================
# Review Result - Reviewer 输出的审查结果
# ========================================

class IssueItem(BaseModel):
    """问题项"""
    issue_type: str  # consistency/pacing/hook/structure
    location: str  # 位置描述
    description: str
    severity: str  # critical/major/minor
    fix_suggestion: str


class ReviewResult(BaseModel):
    """审查结果"""
    project_id: str
    chapter_id: str
    
    # 总体判定
    overall_verdict: str  # pass/patch_required/rewrite_required
    verdict_reason: str
    
    # 问题列表
    issue_list: list[IssueItem] = []
    
    # 详细反馈
    rewrite_needed: bool = False
    rewrite_scope: Optional[str] = None  # full_chapter/partial/scenes_only
    
    #  rewrite instructions
    rewrite_instructions: Optional[str] = None
    
    # 反馈来源
    planner_feedback: Optional[str] = None  # 章纲层面的问题
    memory_feedback: Optional[str] = None  # 记忆一致性问题
    
    # 评分
    consistency_score: float = 1.0  # 一致性 0-1
    pacing_score: float = 1.0  # 节奏 0-1
    hook_score: float = 1.0  # 钩子 0-1
    
    created_at: datetime = Field(default_factory=datetime.now)


# ========================================
# Writing Session - 写作会话状态
# ========================================

class WritingSession(BaseModel):
    """写作会话 - 跟踪整个写作过程"""
    project_id: str
    current_arc_id: Optional[str] = None
    current_chapter_id: Optional[str] = None
    
    # 当前状态
    phase: str = "idle"  # idle/bootstrapping/generating/reviewing/patching/rewriting
    status: str = "pending"  # pending/in_progress/completed/failed
    
    # 审查循环计数
    review_attempts: int = 0
    max_review_attempts: int = 3
    
    # 最后结果
    last_result: Optional[ReviewResult] = None
    error_message: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
