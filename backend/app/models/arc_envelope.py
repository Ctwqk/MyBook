"""Arc Envelope 模型 - v2.4 百分比 + 上下限 + 总长度分档

包含：
- ArcEnvelope: Arc 执行包络
- ArcStructureDraft: Arc 中层结构草案
- ArcEnvelopeAnalysis: Arc 包络分析结果
- ProvisionalPromotionRecord: Provisional 提升记录
"""
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Float, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class ArcTier(str, Enum):
    """全书长度分档"""
    SHORT = "short"                    # 1-150 章
    MEDIUM = "medium"                  # 151-400 章
    LONG = "long"                      # 401-800 章
    ULTRA_LONG = "ultra_long"          # 801+ 章


class ArcRecommendation(str, Enum):
    """Arc 调整建议"""
    KEEP = "keep"          # 保持当前 target
    EXPAND = "expand"      # 扩张 arc
    COMPRESS = "compress"   # 压缩 arc


class ArcPhase(str, Enum):
    """Arc 功能阶段"""
    SETUP = "setup"           # 铺垫
    ESCALATION = "escalation" # 升温
    CLIMAX = "climax"         # 高潮
    RESOLUTION = "resolution" # 收束
    TRANSITION = "transition" # 过渡


class ArcEnvelope(Base):
    """
    Arc 执行包络 - v2.4 核心数据结构
    
    记录每个 arc 的尺寸决策过程：
    - 基础公式计算值 (Layer 1)
    - 分档调整值 (Layer 2)
    - Provisional 预演修正值 (Layer 3)
    """
    __tablename__ = "arc_envelopes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    
    # Arc 标识
    arc_no: Mapped[int] = mapped_column(Integer, nullable=False)  # Arc 编号（从1开始）
    
    # === Layer 1: 基础 target 计算 ===
    # 百分比 + 上下限
    base_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=0.15)
    base_target_size: Mapped[int] = mapped_column(Integer, nullable=False)  # 基础目标章节数
    base_soft_min: Mapped[int] = mapped_column(Integer, nullable=False)  # 基础软下限
    base_soft_max: Mapped[int] = mapped_column(Integer, nullable=False)  # 基础软上限
    
    # === Layer 2: 分档信息 ===
    source_policy_tier: Mapped[str] = mapped_column(String(50), nullable=False)  # short/medium/long/ultra_long
    total_chapters_at_calculation: Mapped[int] = mapped_column(Integer, nullable=False)  # 计算时的全书总章节数
    
    # === Layer 3: Provisional 预演结果 ===
    # Provisional 预演后确定的最终值
    resolved_target_size: Mapped[int] = mapped_column(Integer, nullable=False)
    resolved_soft_min: Mapped[int] = mapped_column(Integer, nullable=False)
    resolved_soft_max: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Detailed band 和 frozen zone
    resolved_detailed_band_size: Mapped[int] = mapped_column(Integer, nullable=False)  # 近端详细规划章节数
    resolved_frozen_zone_size: Mapped[int] = mapped_column(Integer, nullable=False)  # 冻结区章节数
    
    # 当前预测
    current_projected_size: Mapped[int] = mapped_column(Integer, nullable=False)  # 运行时预测的当前 arc 长度
    
    # 状态
    current_confidence: Mapped[float] = mapped_column(Float, default=0.5)  # 0.0-1.0
    envelope_status: Mapped[str] = mapped_column(String(50), default="provisional")  # provisional/confirmed/adjusted
    
    # 关联分析
    latest_analysis_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    
    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="arc_envelopes")
    structure_draft: Mapped[Optional["ArcStructureDraft"]] = relationship(
        "ArcStructureDraft", back_populates="envelope", uselist=False, cascade="all, delete-orphan"
    )
    analyses: Mapped[list["ArcEnvelopeAnalysis"]] = relationship(
        "ArcEnvelopeAnalysis", back_populates="envelope", cascade="all, delete-orphan"
    )


class ArcStructureDraft(Base):
    """
    Arc 中层结构草案 - v2.4
    
    在 Provisional 预演前生成，记录 arc 的结构规划
    """
    __tablename__ = "arc_structure_drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    envelope_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("arc_envelopes.id", ondelete="CASCADE"), nullable=False
    )
    arc_id: Mapped[int] = mapped_column(Integer, nullable=False)  # 关联的 arc_no
    
    # 主要矛盾
    primary_conflict: Mapped[str] = mapped_column(Text, nullable=True)
    
    # 活跃角色
    active_characters: Mapped[str] = mapped_column(JSON, default=list)  # JSON array of character IDs/names
    
    # Thread 优先级
    thread_priorities: Mapped[str] = mapped_column(JSON, default=dict)  # {thread_id: priority}
    
    # Phase 布局
    phase_layout: Mapped[str] = mapped_column(JSON, default=list)  # [phase_info,...]
    
    # 关键 beats
    key_beats: Mapped[str] = mapped_column(JSON, default=list)  # [beat_info,...]
    
    # 高潮候选位置
    hotspot_candidates: Mapped[str] = mapped_column(JSON, default=list)  # [chapter_no,...]
    
    # 压缩候选位置
    compression_candidates: Mapped[str] = mapped_column(JSON, default=list)  # [chapter_range,...]
    
    # Arc 功能
    arc_function: Mapped[str] = mapped_column(String(50), nullable=True)  # setup/escalation/climax/resolution/transition
    
    # LLM 生成的结构化内容
    raw_structure: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # v2.7: 读者承诺 JSON
    reader_promise_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # v2.7: Arc 回报图 JSON
    arc_payoff_map_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    
    # Relationships
    envelope: Mapped["ArcEnvelope"] = relationship("ArcEnvelope", back_populates="structure_draft")


class ArcEnvelopeAnalysis(Base):
    """
    Arc 包络分析 - v2.4 Provisional 预演结果
    
    记录每个 arc 的 provisional 预演分析和调整建议
    """
    __tablename__ = "arc_envelope_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    envelope_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("arc_envelopes.id", ondelete="CASCADE"), nullable=False
    )
    arc_id: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # 基于哪个 band 进行分析
    based_on_band_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # 建议
    recommendation: Mapped[str] = mapped_column(String(20), nullable=False)  # keep/expand/compress
    
    # 建议理由
    evidence: Mapped[str] = mapped_column(Text, nullable=True)
    
    # 扩张信号
    expansion_signals: Mapped[str] = mapped_column(JSON, default=list)  # [signal,...]
    # 压缩信号
    compression_signals: Mapped[str] = mapped_column(JSON, default=list)  # [signal,...]
    
    # 建议的新 target
    suggested_target: Mapped[int] = mapped_column(Integer, nullable=True)
    suggested_soft_min: Mapped[int] = mapped_column(Integer, nullable=True)
    suggested_soft_max: Mapped[int] = mapped_column(Integer, nullable=True)
    
    # 置信度
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    
    # 状态
    is_final: Mapped[bool] = mapped_column(default=False)
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    
    # Relationships
    envelope: Mapped["ArcEnvelope"] = relationship("ArcEnvelope", back_populates="analyses")
    promotion_records: Mapped[list["ProvisionalPromotionRecord"]] = relationship(
        "ProvisionalPromotionRecord", back_populates="analysis", cascade="all, delete-orphan"
    )


class ProvisionalPromotionRecord(Base):
    """
    Provisional 提升记录 - v2.4
    
    记录从 provisional 提升到 canonical 的内容
    """
    __tablename__ = "provisional_promotion_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    arc_id: Mapped[int] = mapped_column(Integer, nullable=False)
    band_id: Mapped[str] = mapped_column(String(100), nullable=True)
    
    # 提升的章节
    promoted_chapter_ids: Mapped[str] = mapped_column(JSON, default=list)  # [chapter_id,...]
    
    # 提升原因
    promotion_reason: Mapped[str] = mapped_column(Text, nullable=True)
    
    # 基于的分析
    based_on_analysis_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("arc_envelope_analyses.id"), nullable=True
    )
    
    # 内容摘要
    content_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    
    # Relationships
    analysis: Mapped[Optional["ArcEnvelopeAnalysis"]] = relationship(
        "ArcEnvelopeAnalysis", back_populates="promotion_records"
    )


# Forward references
from app.models.project import Project
