"""Arc Envelope Service Schemas - v2.4

包含所有 Arc Envelope 相关的 Pydantic schemas。
"""
from datetime import datetime
from typing import Optional, Tuple

from pydantic import BaseModel, Field


class TierInfoResponse(BaseModel):
    """分档信息响应"""
    tier: str
    ratio: float
    min_size: int
    max_size: int
    soft_min_mult: float
    soft_max_mult: float


class ArcEnvelopeResponse(BaseModel):
    """Arc Envelope 响应"""
    id: int
    project_id: int
    arc_no: int
    
    # Layer 1
    base_ratio: float
    base_target_size: int
    base_soft_min: int
    base_soft_max: int
    
    # Layer 2
    source_policy_tier: str
    total_chapters_at_calculation: int
    
    # Layer 3
    resolved_target_size: int
    resolved_soft_min: int
    resolved_soft_max: int
    resolved_detailed_band_size: int
    resolved_frozen_zone_size: int
    
    # 当前状态
    current_projected_size: int
    current_confidence: float
    envelope_status: str
    
    # 关联
    latest_analysis_id: Optional[int] = None
    
    # 时间戳
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ArcEnvelopePreviewResponse(BaseModel):
    """Arc Envelope 预览响应（不创建记录）"""
    arc_no: int
    tier: str
    base_target: int
    resolved_target: int
    soft_range: Tuple[int, int]
    detailed_band: int
    frozen_zone: int
    recommendation: str
    confidence: float


class ActivateArcRequest(BaseModel):
    """激活 Arc 请求"""
    arc_no: int = Field(..., ge=1, description="Arc 编号（从1开始）")


class ArcAdjustmentRequest(BaseModel):
    """Arc 调整请求"""
    adjustment: str = Field(
        ...,
        description="调整类型: expand (扩张 15%) / compress (压缩 15%) / keep (保持)"
    )


class ArcStructureDraftResponse(BaseModel):
    """Arc 结构草案响应"""
    id: int
    envelope_id: int
    arc_id: int
    primary_conflict: Optional[str] = None
    active_characters: list = []
    thread_priorities: dict = {}
    phase_layout: list = []
    key_beats: list = []
    hotspot_candidates: list = []
    compression_candidates: list = []
    arc_function: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ArcEnvelopeAnalysisResponse(BaseModel):
    """Arc 包络分析响应"""
    id: int
    envelope_id: int
    arc_id: int
    based_on_band_id: Optional[str] = None
    recommendation: str
    evidence: Optional[str] = None
    expansion_signals: list = []
    compression_signals: list = []
    suggested_target: Optional[int] = None
    suggested_soft_min: Optional[int] = None
    suggested_soft_max: Optional[int] = None
    confidence: float
    is_final: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ProvisionalPromotionRecordResponse(BaseModel):
    """Provisional 提升记录响应"""
    id: int
    project_id: int
    arc_id: int
    band_id: Optional[str] = None
    promoted_chapter_ids: list = []
    promotion_reason: Optional[str] = None
    based_on_analysis_id: Optional[int] = None
    content_summary: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class LayerConfigInfo(BaseModel):
    """Layer 配置信息（用于文档）"""
    layer_name: str
    description: str
    key_parameters: dict


class ExpansionSignals(BaseModel):
    """扩张信号定义"""
    signals: list[str] = Field(
        default=[
            "主高潮尚未到来",
            "关键 thread 仍在升温",
            "最近 2~3 章冲突递增，不重复",
            "高价值角色活跃度上升",
            "时间推进合理",
            "hook 强且指向 arc 主问题"
        ],
        description="判断 Arc 应该扩张的信号"
    )


class CompressionSignals(BaseModel):
    """压缩信号定义"""
    signals: list[str] = Field(
        default=[
            "主问题已解",
            "最近章节功能重复",
            "没有新冲突，只是在搬运信息",
            "高潮已过，只剩拖尾",
            "时间推进过载",
            "Pacing 分析判定'水'"
        ],
        description="判断 Arc 应该压缩的信号"
    )
