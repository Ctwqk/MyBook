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


# ========================================
# Phase A: CommentSignalCandidate (v2.6)
# ========================================

class CommentSignalCandidate(Base):
    """
    LLM 解析后的结构化信号候选 - Phase A 新增
    
    存储从单条评论中提取的信号，包含：
    - signal_type: confusion / pacing / character_heat / risk
    - target_type: character / arc / plot / setting
    - target_name: 自由文本，如 "主角动机"
    - severity: 1~4
    - confidence: 0~1
    - evidence_span: 原文摘录
    
    注意：不替代现有的 CommentSignal，是独立的新表
    """
    __tablename__ = "comment_signal_candidates"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    source_comment_id = Column(Integer, ForeignKey("raw_comments.id"), nullable=False, index=True)
    
    # 信号类型 (v2.6 完整支持 6 类，Phase A/B 只启用前 4 类)
    signal_type = Column(String(20), nullable=False, index=True)  # confusion/pacing/character_heat/relationship/prediction/risk
    
    # 目标类型
    target_type = Column(String(20), nullable=True, index=True)  # character/arc/plot/setting
    
    # 目标名称（自由文本）
    target_name = Column(String(200), nullable=True)  # 如 "主角动机"
    
    # 严重程度 1~4
    severity = Column(Integer, default=1)
    
    # 置信度 0~1
    confidence = Column(Float, default=0.5)
    
    # 原文摘录
    evidence_span = Column(Text, nullable=True)
    
    # 信号级别（Phase A 硬规则分级）
    signal_level = Column(String(20), default="candidate", index=True)  # noise/candidate/confirmed/watchlist
    
    # 来源标记
    is_llm_generated = Column(Boolean, default=True)  # True=LLM生成, False=关键词匹配fallback
    is_fallback = Column(Boolean, default=False)     # 是否是 fallback 到关键词的结果
    
    # 元数据
    created_at = Column(DateTime, default=datetime.now, index=True)
    
    def __repr__(self):
        return f"<CommentSignalCandidate id={self.id} type={self.signal_type} level={self.signal_level}>"


# ========================================
# Phase B: 3 张新表 (v2.7)
# ========================================

class SignalWindowAggregate(Base):
    """
    窗口聚合统计 - Phase B 新增
    
    按信号类型和章节窗口聚合统计，用于：
    - 热点窗口识别
    - 信号强度趋势
    - Writer 决策支持
    
    字段说明：
    - signal_key: signal_type:target_type:target_name 的组合键
    - window_chapter_start/end: 章节窗口范围
    - hit_comment_count: 命中该信号的评论数
    - unique_user_count: 去重用户数
    - total_comment_count: 窗口内总评论数
    - reader_estimate: 预估受影响读者规模
    - signal_level: 信号级别 (noise/candidate/confirmed/watchlist)
    """
    __tablename__ = "signal_window_aggregates"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    
    # 信号标识
    signal_key = Column(String(100), nullable=False, index=True)  # signal_type:target_type:target_name
    
    # 窗口范围
    window_chapter_start = Column(Integer, nullable=False)
    window_chapter_end = Column(Integer, nullable=False)
    
    # 聚合统计
    hit_comment_count = Column(Integer, default=0)    # 命中该信号的评论数
    unique_user_count = Column(Integer, default=0)    # 去重用户数
    total_comment_count = Column(Integer, default=0)   # 窗口内总评论数
    
    # 读者规模估算
    reader_estimate = Column(Integer, nullable=True)   # 预估受影响读者规模
    
    # 信号级别
    signal_level = Column(String(20), default="candidate", index=True)  # noise/candidate/confirmed/watchlist
    
    # 元数据
    created_at = Column(DateTime, default=datetime.now, index=True)
    
    def __repr__(self):
        return f"<SignalWindowAggregate id={self.id} signal_key={self.signal_key} window={self.window_chapter_start}-{self.window_chapter_end}>"


class ReaderScaleSnapshot(Base):
    """
    读者规模快照 - Phase B 新增
    
    定期记录读者规模估算，用于：
    - 读者增长趋势
    - 各章节读者覆盖
    - 规模分级管理
    
    字段说明：
    - reader_estimate: 读者规模估算值
    - estimation_method: 估算方法 (sampling/extrapolation/model)
    - tier: 规模等级 (S/A/B/C/D)
    """
    __tablename__ = "reader_scale_snapshots"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    
    # 章节位置
    chapter_number = Column(Integer, nullable=False)
    
    # 读者规模
    reader_estimate = Column(Integer, nullable=False)
    
    # 估算方法
    estimation_method = Column(String(50), nullable=True)  # sampling/extrapolation/model
    
    # 规模等级
    tier = Column(String(10), nullable=True, index=True)  # S/A/B/C/D
    
    # 元数据
    created_at = Column(DateTime, default=datetime.now, index=True)
    
    def __repr__(self):
        return f"<ReaderScaleSnapshot id={self.id} chapter={self.chapter_number} estimate={self.reader_estimate}>"


class FeedbackActionRecord(Base):
    """
    响应动作记录 (冷却期管理) - Phase B 新增
    
    记录 Writer 对信号的响应动作，用于：
    - 冷却期管理 (避免频繁响应同一信号)
    - 动作历史追踪
    - 响应效果评估
    
    字段说明：
    - signal_key: 关联的信号标识
    - action_type: 动作类型 (adjust/ignore/enhance/investigate)
    - target: 响应目标 (章节号/角色名等)
    - cooldown_until: 冷却截止时间
    """
    __tablename__ = "feedback_action_records"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    
    # 信号标识
    signal_key = Column(String(100), nullable=False, index=True)  # signal_type:target_type:target_name
    
    # 动作类型
    action_type = Column(String(50), nullable=False)  # adjust/ignore/enhance/investigate
    
    # 响应目标
    target = Column(String(200), nullable=True)  # 章节号/角色名等
    
    # 章节位置
    chapter_number = Column(Integer, nullable=True)
    
    # 冷却期管理
    cooldown_until = Column(DateTime, nullable=True, index=True)
    
    # 元数据
    created_at = Column(DateTime, default=datetime.now, index=True)
    
    def __repr__(self):
        return f"<FeedbackActionRecord id={self.id} action={self.action_type} target={self.target}>"
