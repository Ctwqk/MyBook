"""Audience Feedback 数据模型 - v2.5

新增：
- RawComment: 原始评论
- CommentSignal: 结构化评论信号
- AudienceSignal: 聚合读者信号
- AudienceTrend: 读者趋势
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Float, Boolean
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class SignalType(str, Enum):
    """评论信号类型"""
    CONFUSION = "confusion"           # 困惑类
    PACING = "pacing"                 # 节奏类
    CHARACTER_HEAT = "character_heat"  # 角色热度
    RELATIONSHIP = "relationship"     # 关系线/CP类
    PREDICTION = "prediction"         # 预测类
    RISK = "risk"                    # 风险类


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
    WINDOW_A = "3chap"   # 最近 2-3 章
    WINDOW_B = "10chap"  # 最近 5-10 章
    WINDOW_C = "20chap"  # 最近 10-20 章
    ARC = "arc"          # 当前 arc 窗口


class TrendType(str, Enum):
    """趋势类型"""
    RISING = "rising"
    FALLING = "falling"
    STABLE = "stable"


class RawComment(Base):
    """原始评论"""
    __tablename__ = "raw_comments"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    platform = Column(String(50), nullable=False)  # fanqie, qidian, jjwxc, etc.
    
    # 关联章节（可选，有些评论可能关联整个项目）
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=True)
    paragraph_id = Column(String(100), nullable=True)  # 段落位置
    
    # 用户标识（去重用，不存储个人隐私）
    user_hash = Column(String(64), nullable=False, index=True)
    
    # 评论内容
    content = Column(Text, nullable=False)
    
    # 互动数据
    like_count = Column(Integer, default=0)
    reply_count = Column(Integer, default=0)
    
    # 元数据
    created_at = Column(DateTime, default=datetime.now, index=True)
    processed = Column(Boolean, default=False)  # 是否已分析
    processed_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<RawComment id={self.id} project={self.project_id} platform={self.platform}>"


class CommentSignal(Base):
    """单条评论分析后的结构化信号"""
    __tablename__ = "comment_signals"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    source_comment_id = Column(Integer, ForeignKey("raw_comments.id"), nullable=False)
    
    # 信号类型
    signal_type = Column(String(20), nullable=False, index=True)  # SignalType
    
    # 目标
    target_type = Column(String(20), nullable=True)  # TargetType
    target_id = Column(Integer, nullable=True)  # 角色ID、章节ID等
    
    # 分析结果
    sentiment = Column(String(20), nullable=True)  # positive, negative, neutral
    intensity = Column(Float, default=0.5)  # 0.0-1.0
    confidence = Column(Float, default=0.5)  # 分析置信度
    
    # 证据摘要
    evidence_summary = Column(Text, nullable=True)
    
    # 原始评论引用（用于追溯）
    original_snippet = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.now, index=True)
    
    def __repr__(self):
        return f"<CommentSignal id={self.id} type={self.signal_type} target={self.target_type}:{self.target_id}>"


class AudienceSignal(Base):
    """聚合后的读者信号"""
    __tablename__ = "audience_signals"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    
    # 窗口信息
    window_type = Column(String(10), nullable=False, index=True)  # WindowType
    chapter_start = Column(Integer, nullable=False)
    chapter_end = Column(Integer, nullable=False)
    
    # 聚合信号类型
    signal_type = Column(String(20), nullable=False, index=True)
    target_type = Column(String(20), nullable=True)
    target_id = Column(Integer, nullable=True)
    
    # 聚合结果
    score = Column(Float, default=0.0)  # 聚合分数
    comment_count = Column(Integer, default=0)  # 涉及评论数
    user_count = Column(Integer, default=0)  # 去重用户数
    confidence = Column(Float, default=0.5)
    
    # 证据摘要
    evidence_summary = Column(Text, nullable=True)
    
    generated_at = Column(DateTime, default=datetime.now, index=True)
    
    def __repr__(self):
        return f"<AudienceSignal id={self.id} window={self.window_type} type={self.signal_type} score={self.score}>"


class AudienceTrend(Base):
    """读者趋势分析"""
    __tablename__ = "audience_trends"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    
    # 窗口类型
    window_type = Column(String(10), nullable=False, index=True)
    
    # 趋势目标
    target_type = Column(String(20), nullable=False)
    target_id = Column(Integer, nullable=True)
    
    # 趋势方向
    trend_type = Column(String(20), nullable=False)  # TrendType
    score_delta = Column(Float, default=0.0)  # 分数变化
    
    # 分析摘要
    summary = Column(Text, nullable=True)
    
    generated_at = Column(DateTime, default=datetime.now, index=True)
    
    def __repr__(self):
        return f"<AudienceTrend id={self.id} target={self.target_type}:{self.target_id} trend={self.trend_type}>"


class AudienceHintPack(Base):
    """Writer 可用的极小提示包（不暴露原始评论）"""
    __tablename__ = "audience_hint_packs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=True)
    band_id = Column(String(50), nullable=True)  # 关联的 band
    
    # 提示内容（JSON 格式，不暴露原始评论）
    pacing_hints = Column(JSON, default=list)  # [{"target": "...", "hint": "...", "urgency": "medium"}]
    clarity_hints = Column(JSON, default=list)  # [{"target": "...", "hint": "...", "urgency": "low"}]
    character_heat_changes = Column(JSON, default=list)  # [{"character_id": 1, "direction": "up", "confidence": 0.7}]
    relationship_interest = Column(JSON, default=list)  # [{"pair": [1, 2], "direction": "up"}]
    prediction_clusters = Column(JSON, default=list)  # [{"prediction": "...", "count": 5}]
    risk_flags = Column(JSON, default=list)  # [{"type": "character_inconsistency", "target_id": 1, "urgency": "high"}]
    
    # 元数据
    generated_at = Column(DateTime, default=datetime.now)
    version = Column(Integer, default=1)
    
    def __repr__(self):
        return f"<AudienceHintPack id={self.id} project={self.project_id} chapter={self.chapter_id}>"
