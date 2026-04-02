"""Audience Feedback Schemas - v2.5"""
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field
from enum import Enum


class SignalType(str, Enum):
    """评论信号类型"""
    CONFUSION = "confusion"
    PACING = "pacing"
    CHARACTER_HEAT = "character_heat"
    RELATIONSHIP = "relationship"
    PREDICTION = "prediction"
    RISK = "risk"


class TargetType(str, Enum):
    """信号目标类型"""
    CHARACTER = "character"
    PLOT = "plot"
    LORE = "lore"
    RELATIONSHIP = "relationship"
    ARC = "arc"
    LOCATION = "location"
    THREAD = "thread"
    PACING = "pacing"


class WindowType(str, Enum):
    """反馈窗口类型"""
    WINDOW_A = "3chap"
    WINDOW_B = "10chap"
    WINDOW_C = "20chap"
    ARC = "arc"


class TrendType(str, Enum):
    """趋势类型"""
    RISING = "rising"
    FALLING = "falling"
    STABLE = "stable"


class ResponseWindow(str, Enum):
    """响应窗口"""
    FAST = "1-3chap"      # 快速响应 (1-3章)
    MEDIUM = "2-5chap"    # 中速响应 (2-5章)
    SLOW = "5-20chap"     # 慢速响应 (5-20章)


# ==================== Request Schemas ====================

class CommentIngestRequest(BaseModel):
    """评论摄入请求"""
    project_id: int
    platform: str
    chapter_id: Optional[int] = None
    paragraph_id: Optional[str] = None
    user_hash: str
    content: str
    like_count: int = 0
    reply_count: int = 0
    timestamp: Optional[datetime] = None


class BatchCommentIngestRequest(BaseModel):
    """批量评论摄入请求"""
    project_id: int
    platform: str
    comments: list[CommentIngestRequest]


class FeedbackQueryRequest(BaseModel):
    """反馈查询请求"""
    project_id: int
    window_type: WindowType = WindowType.WINDOW_A
    signal_types: Optional[list[SignalType]] = None
    target_type: Optional[TargetType] = None
    include_raw: bool = False  # 是否包含原始评论（仅管理员）


# ==================== Response Schemas ====================

class RawCommentResponse(BaseModel):
    """原始评论响应"""
    id: int
    project_id: int
    platform: str
    chapter_id: Optional[int]
    user_hash: str
    content: str
    like_count: int
    reply_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class CommentSignalResponse(BaseModel):
    """单条评论信号响应"""
    id: int
    project_id: int
    signal_type: SignalType
    target_type: Optional[TargetType]
    target_id: Optional[int]
    sentiment: Optional[str]
    intensity: float
    confidence: float
    evidence_summary: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class AudienceSignalResponse(BaseModel):
    """聚合读者信号响应"""
    id: int
    project_id: int
    window_type: WindowType
    chapter_start: int
    chapter_end: int
    signal_type: SignalType
    target_type: Optional[TargetType]
    target_id: Optional[int]
    score: float
    comment_count: int
    user_count: int
    confidence: float
    evidence_summary: Optional[str]
    generated_at: datetime
    
    class Config:
        from_attributes = True


class AudienceTrendResponse(BaseModel):
    """读者趋势响应"""
    id: int
    project_id: int
    window_type: WindowType
    target_type: TargetType
    target_id: Optional[int]
    trend_type: TrendType
    score_delta: float
    summary: Optional[str]
    generated_at: datetime
    
    class Config:
        from_attributes = True


# ==================== Audience Hint Pack ====================

class PacingHint(BaseModel):
    """节奏提示"""
    target: str
    hint: str
    urgency: str  # low, medium, high


class ClarityHint(BaseModel):
    """清晰度提示"""
    target: str
    hint: str
    urgency: str  # low, medium, high


class CharacterHeatChange(BaseModel):
    """角色热度变化"""
    character_id: int
    character_name: Optional[str] = None
    direction: str  # up, down, stable
    confidence: float


class RelationshipInterestItem(BaseModel):
    """关系线关注"""
    character_id_1: int
    character_id_2: int
    direction: str  # up, down


class PredictionCluster(BaseModel):
    """预测聚类"""
    prediction: str
    count: int


class RiskFlag(BaseModel):
    """风险标记"""
    type: str  # character_inconsistency, plot_hole, pacing_issue, etc.
    target_id: Optional[int]
    description: str
    urgency: str  # low, medium, high


class AudienceHintPackResponse(BaseModel):
    """Writer 可用的极小提示包"""
    project_id: int
    chapter_id: Optional[int]
    band_id: Optional[str]
    
    pacing_hints: list[PacingHint] = []
    clarity_hints: list[ClarityHint] = []
    character_heat_changes: list[CharacterHeatChange] = []
    relationship_interest: list[RelationshipInterestItem] = []
    prediction_clusters: list[PredictionCluster] = []
    risk_flags: list[RiskFlag] = []
    
    generated_at: datetime
    version: int = 1
    
    class Config:
        from_attributes = True


# ==================== Aggregated Feedback ====================

class AggregatedFeedbackResponse(BaseModel):
    """聚合反馈响应（供 Arc Director 等使用）"""
    project_id: int
    window_type: WindowType
    
    # 聚合信号
    signals: list[AudienceSignalResponse]
    
    # 趋势
    trends: list[AudienceTrendResponse]
    
    # 汇总
    summary: dict[str, Any]
    
    # 高置信度提示
    high_confidence_alerts: list[dict[str, Any]]
    
    generated_at: datetime


# ==================== Action Mapping ====================

class ActionSuggestion(BaseModel):
    """动作建议"""
    action_type: str  # clarification_backlog, pacing_adjustment, urgent_repair, etc.
    target: str
    description: str
    response_window: ResponseWindow
    confidence: float
    priority: int  # 1-5, 1 is highest


class ActionMappingResponse(BaseModel):
    """动作映射响应"""
    project_id: int
    chapter_id: Optional[int]
    
    confusion_actions: list[ActionSuggestion] = []
    pacing_actions: list[ActionSuggestion] = []
    character_heat_actions: list[ActionSuggestion] = []
    relationship_actions: list[ActionSuggestion] = []
    prediction_analysis: list[dict] = []  # 仅分析，不直接响应
    risk_actions: list[ActionSuggestion] = []
    
    generated_at: datetime


# ==================== Configuration ====================

class FeedbackLayerConfig(BaseModel):
    """反馈层配置"""
    enabled: bool = True
    
    # 响应窗口配置
    confusion_window: tuple[int, int] = (5, 20)  # 默认 5-20 章
    pacing_window: tuple[int, int] = (2, 5)     # 默认 2-5 章
    character_heat_window: tuple[int, int] = (5, 10)
    relationship_window: tuple[int, int] = (5, 15)
    risk_window: tuple[int, int] = (1, 3)       # 快速响应
    
    # 聚合阈值
    min_comment_count: int = 3       # 最少评论数
    min_user_count: int = 2         # 最少用户数
    min_confidence: float = 0.5     # 最低置信度
    
    # 冷却期（同一类反馈的最小间隔）
    signal_cooldown_chapters: int = 3
    
    # 角色热度触发门槛
    character_heat_trigger_windows: int = 2  # 连续 2 个窗口
