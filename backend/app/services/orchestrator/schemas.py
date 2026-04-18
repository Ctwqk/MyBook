"""Orchestrator 数据模型 - v2.3 增强版

包含：
- Scene 模式支持
- 多项目隔离
- 错误恢复策略
- 黑箱/人工双模式
"""
from datetime import datetime
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field


# ========================================
# 枚举定义
# ========================================

class OperationMode(str, Enum):
    """系统运行模式"""
    BLACKBOX = "blackbox"       # 完全黑箱，无需人工
    CHECKPOINT = "checkpoint"   # 检查点模式，关键节点等待确认
    COLLABORATIVE = "collaborative"  # 共驾编辑模式
    COPAYILOT = "copilot"      # 共驾模式，v2.7 新增


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_ATTENTION = "needs_attention"


class FailureStrategy(str, Enum):
    """失败策略"""
    RETRY = "retry"
    REPAIR = "repair"
    FALLBACK = "fallback"
    ESCALATE = "escalate"


# ========================================
# Retry Policy 配置
# ========================================

class RetryPolicy(BaseModel):
    """重试策略配置"""
    max_retries: int = 2
    max_repairs: int = 1
    retry_delay_seconds: int = 5
    exponential_backoff: bool = True
    
    # 各阶段重试配置
    writer_retry_config: dict[str, Any] = Field(default_factory=lambda: {
        "max_retries": 2,
        "repair_strategies": ["shorten_context", "reduce_scene_count", "relax_structure"]
    })
    reviewer_retry_config: dict[str, Any] = Field(default_factory=lambda: {
        "max_retries": 2,
        "repair_strategies": ["strict_parse", "relaxed_parse", "minimal_rule_check"]
    })
    updater_retry_config: dict[str, Any] = Field(default_factory=lambda: {
        "max_retries": 1,
        "rollback_on_failure": True
    })


# ========================================
# Scene 模式 - Writer v2.3
# ========================================

class ScenePlan(BaseModel):
    """Scene 计划 - v2.7 扩展
    
    新增字段：
    - reward_beat_tag: 奖励节拍标签
    - immersion_anchor: 沉浸锚点
    - progress_marker: 进度标记
    """
    scene_no: int
    scene_objective: str
    scene_time_point: Optional[str] = None
    scene_location: Optional[str] = None
    involved_entities: list[str] = []
    must_progress_points: list[str] = []
    micro_hook: Optional[str] = None
    
    # v2.7 新增字段
    reward_beat_tag: Optional[str] = None  # 奖励节拍标签
    immersion_anchor: Optional[str] = None  # 沉浸锚点描述
    progress_marker: Optional[str] = None  # 进度标记


class SceneOutput(BaseModel):
    """Scene 生成输出"""
    scene_no: int
    scene_objective: str
    text_blob: str
    micro_summary: str
    state_hints: list[dict] = []
    
    # 原始 LLM 输出路径（用于调试）
    raw_response_path: Optional[str] = None


class WriterOutput(BaseModel):
    """Writer 生成输出 - v2.3 增强版
    
    包含完整的结构化输出，支持 scene 模式
    """
    project_id: int
    chapter_id: int
    
    # 正文内容
    draft_blob: str  # 完整章节草稿
    draft_version: int = 1
    
    # Scene 模式
    scene_outputs: list[SceneOutput] = []
    use_scene_mode: bool = False
    
    # 结构化提取
    chapter_summary: str = ""
    event_candidates: list[dict] = []
    state_change_candidates: list[dict] = []
    thread_beat_candidates: list[dict] = []
    lore_candidates: list[dict] = []
    timeline_hints: list[dict] = []
    
    # 元数据
    writer_notes: str = ""
    generation_meta: dict[str, Any] = Field(default_factory=dict)
    
    # 错误恢复
    parse_success: bool = True
    parse_error: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.now)


class WriterGenerationRequest(BaseModel):
    """Writer 生成请求 - v2.3"""
    chapter_id: int
    outline: Optional[str] = None
    use_scene_mode: bool = False  # 是否使用 scene 模式
    scene_count: int = 2  # 默认 2 scenes
    target_word_count: int = 3000
    style_hints: Optional[str] = None


# ========================================
# Review Result - v2.3
# ========================================

class ReviewVerdictV2(BaseModel):
    """审查判决 - v2.3"""
    # 总体判定
    verdict: str = "pass"  # pass/patch_required/rewrite_required/blocked
    verdict_reason: str = ""
    
    # 问题列表
    issues: list[dict] = []
    
    # patch/rewrite instructions
    patch_instructions: Optional[str] = None
    rewrite_instructions: Optional[str] = None
    
    # 评分
    scores: dict[str, float] = Field(default_factory=lambda: {
        "consistency": 1.0,
        "pacing": 1.0,
        "hook": 1.0,
        "overall": 1.0
    })
    
    # 错误恢复
    parse_success: bool = True
    parse_error: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.now)


class ReviewRequestV2(BaseModel):
    """审查请求 - v2.3"""
    chapter_id: int
    writer_output: Optional[WriterOutput] = None
    check_types: list[str] = ["consistency", "pacing", "hook"]
    force_full_review: bool = False


# ========================================
# Task - 多项目隔离
# ========================================

class Task(BaseModel):
    """任务 - v2.3 多项目隔离"""
    task_id: str
    project_id: int
    
    # 任务类型
    task_type: str  # bootstrap/outline/generate/review/patch/rewrite/replan
    
    # 关联 ID
    chapter_id: Optional[int] = None
    arc_id: Optional[int] = None
    volume_id: Optional[int] = None
    
    # 状态
    status: TaskStatus = TaskStatus.PENDING
    retry_count: int = 0
    error_message: Optional[str] = None
    
    # 优先级
    priority: int = 0  # 越高越先执行
    
    # 时间戳
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # 错误恢复
    failure_strategy: FailureStrategy = FailureStrategy.RETRY
    next_retry_at: Optional[datetime] = None


# ========================================
# State Updater - 事务边界
# ========================================

class StateUpdateCandidate(BaseModel):
    """状态更新候选 - 待人工/自动确认"""
    candidate_id: str
    project_id: int
    chapter_id: int
    
    # 更新类型
    update_type: str  # event/state_change/thread_beat/lore/timeline
    
    # 更新内容
    content: dict[str, Any]
    
    # 状态
    status: str = "pending"  # pending/approved/rejected/failed
    auto_approved: bool = False
    
    # 错误信息
    error_message: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.now)


class StateUpdateResult(BaseModel):
    """状态更新结果"""
    success: bool
    applied_candidates: list[str] = []  # 成功应用的 candidate_id
    rejected_candidates: list[str] = []  # 被拒绝的
    failed_candidates: list[str] = []  # 失败的
    
    # 事务回滚信息
    rollback_performed: bool = False
    rollback_reason: Optional[str] = None
    
    # 错误信息
    error_message: Optional[str] = None


# ========================================
# Context Pack - v2.3
# ========================================

class ContextPackV2(BaseModel):
    """上下文包 - v2.3"""
    project_id: int
    chapter_id: int
    
    # 预算控制
    max_token_budget: int = 128000
    actual_token_count: int = 0
    
    # 内容
    story_bible: Optional[dict] = None
    arc_plan: Optional[dict] = None
    chapter_outline: Optional[dict] = None
    
    # 相关内容
    character_states: list[dict] = []
    recent_chapters: list[dict] = []
    active_foreshadows: list[dict] = []
    relevant_world_settings: list[dict] = []
    
    # 警告
    review_warnings: list[dict] = []
    
    # 写作约束
    style_constraints: list[str] = []
    word_count_target: int = 3000
    
    # 元数据
    retrieval_sources: list[str] = []  # 从哪些来源检索的


# ========================================
# System Config - v2.3
# ========================================

class SystemConfigV2(BaseModel):
    """系统配置 - v2.3"""
    # 运行模式
    operation_mode: OperationMode = OperationMode.CHECKPOINT
    
    # 重试策略
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    
    # LLM 配置
    llm_provider: str = "openai"
    llm_model: str = "MiniMax-M2.7"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 128000
    
    # 调用预算
    calls_per_hour: int = 300
    cost_per_1k_tokens: float = 0.01
    
    # Writer 配置
    writer_default_scene_count: int = 2
    writer_target_word_count: int = 3000
    writer_max_word_count: int = 4500
    
    # Review 配置
    review_max_attempts: int = 3
    
    # 项目隔离
    enable_project_isolation: bool = True


# ========================================
# 保持向后兼容的旧模型
# ========================================

class StructuredPremise(BaseModel):
    """结构化的 premise - 保持兼容"""
    core_conflict: str = ""
    protagonist_goal: str = ""
    setting_direction: str = ""
    tone_and_style: str = ""
    target_audience: Optional[str] = None


class StoryBibleDraft(BaseModel):
    """Story Bible 初稿 - 保持兼容"""
    world_rules: list[str] = []
    factions: list[dict] = []
    important_locations: list[dict] = []
    items_systems: list[dict] = []
    writing_style_constraints: list[str] = []


class CharacterCardDraft(BaseModel):
    """角色卡初稿 - 保持兼容"""
    name: str = ""
    role_type: str = "supporting"
    personality: str = ""
    motivation: str = ""
    secrets: list[str] = []
    relationships: list[dict] = []


class ArcPlanDraft(BaseModel):
    """卷纲初稿 - 保持兼容"""
    volume_no: int = 1
    title: str = ""
    goal: str = ""
    conflict: str = ""
    expected_chapter_count: int = 30
    key_events: list[str] = []


class ChapterOutlineDraft(BaseModel):
    """章纲初稿 - 保持兼容"""
    chapter_no: int = 1
    title: str = ""
    goal: str = ""
    conflict: str = ""
    ending_hook: str = ""
    key_scenes: list[str] = []


class StoryPackage(BaseModel):
    """完整的故事包 - 保持兼容"""
    project_id: int = 0
    structured_premise: StructuredPremise = Field(default_factory=StructuredPremise)
    story_bible_draft: StoryBibleDraft = Field(default_factory=StoryBibleDraft)
    character_cards: list[CharacterCardDraft] = []
    arc_plans: list[ArcPlanDraft] = []
    chapter_outlines: list[ChapterOutlineDraft] = []
    created_at: datetime = Field(default_factory=datetime.now)


class ChapterDraft(BaseModel):
    """章节草稿 - v2.3 scene 支持"""
    project_id: int = 0
    chapter_id: int = 0
    outline: Optional[ChapterOutlineDraft] = None
    
    # 正文内容
    chapter_text: str = ""
    
    # Scene 模式
    scene_outputs: list[SceneOutput] = []
    use_scene_mode: bool = False
    
    # 结构化提取
    chapter_summary: str = ""
    event_candidates: list[dict] = []
    state_change_candidates: list[dict] = []
    new_foreshadows: list[dict] = []
    resolved_foreshadows: list[dict] = []
    writer_notes: str = ""
    
    # 元数据
    word_count: int = 0
    created_at: datetime = Field(default_factory=datetime.now)
