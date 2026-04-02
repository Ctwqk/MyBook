"""Arc Envelope API Routes - v2.4

提供 Arc Envelope 相关的 REST API。
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.services.arc_envelope.service import ArcEnvelopeService
from app.services.arc_envelope.schemas import (
    ArcEnvelopeResponse,
    ArcEnvelopePreviewResponse,
    ArcAdjustmentRequest,
    ActivateArcRequest,
    TierInfoResponse,
)

router = APIRouter(prefix="/arc-envelopes", tags=["arc-envelopes"])


def get_arc_service(db: AsyncSession = Depends(get_db)) -> ArcEnvelopeService:
    """获取 ArcEnvelopeService 实例"""
    return ArcEnvelopeService(db)


@router.get("/project/{project_id}/tier")
async def get_project_tier(
    project_id: int,
    service: ArcEnvelopeService = Depends(get_arc_service),
    current_user: dict = Depends(get_current_user),
) -> TierInfoResponse:
    """
    获取项目的分档信息
    
    根据全书总章节数确定分档（short/medium/long/ultra_long）
    """
    tier = await service.get_tier_for_project(project_id)
    config = service.ARC_TIER_CONFIGS.get(tier)
    
    if not config:
        raise HTTPException(status_code=500, detail="Invalid tier configuration")
    
    return TierInfoResponse(
        tier=tier.value,
        ratio=config.ratio,
        min_size=config.min_size,
        max_size=config.max_size,
        soft_min_mult=config.soft_min_mult,
        soft_max_mult=config.soft_max_mult,
    )


@router.get("/project/{project_id}/preview")
async def preview_project_arcs(
    project_id: int,
    total_chapters: Optional[int] = None,
    service: ArcEnvelopeService = Depends(get_arc_service),
    current_user: dict = Depends(get_current_user),
) -> list[ArcEnvelopePreviewResponse]:
    """
    预览项目中所有 arc 的 envelope
    
    用于在正式激活前展示预估结果。
    不创建实际的 envelope 记录。
    """
    previews = await service.preview_all_arcs(project_id, total_chapters)
    return [
        ArcEnvelopePreviewResponse(
            arc_no=p["arc_no"],
            tier=p["tier"],
            base_target=p["base_target"],
            resolved_target=p["resolved_target"],
            soft_range=p["soft_range"],
            detailed_band=p["detailed_band"],
            frozen_zone=p["frozen_zone"],
            recommendation=p["recommendation"],
            confidence=p["confidence"],
        )
        for p in previews
    ]


@router.post("/project/{project_id}/activate")
async def activate_arc(
    project_id: int,
    request: ActivateArcRequest,
    service: ArcEnvelopeService = Depends(get_arc_service),
    current_user: dict = Depends(get_current_user),
) -> ArcEnvelopeResponse:
    """
    激活一个 arc - 执行完整的三层决定 + Provisional 预演
    
    这会：
    1. 执行 Layer 1: 百分比 + 上下限计算
    2. 执行 Layer 2: 分档调整
    3. 执行 Layer 3: Provisional 预演
    4. 创建/更新 ArcEnvelope 记录
    """
    envelope = await service.activate_arc(project_id, request.arc_no)
    
    return ArcEnvelopeResponse(
        id=envelope.id,
        project_id=envelope.project_id,
        arc_no=envelope.arc_no,
        base_ratio=envelope.base_ratio,
        base_target_size=envelope.base_target_size,
        base_soft_min=envelope.base_soft_min,
        base_soft_max=envelope.base_soft_max,
        source_policy_tier=envelope.source_policy_tier,
        total_chapters_at_calculation=envelope.total_chapters_at_calculation,
        resolved_target_size=envelope.resolved_target_size,
        resolved_soft_min=envelope.resolved_soft_min,
        resolved_soft_max=envelope.resolved_soft_max,
        resolved_detailed_band_size=envelope.resolved_detailed_band_size,
        resolved_frozen_zone_size=envelope.resolved_frozen_zone_size,
        current_projected_size=envelope.current_projected_size,
        current_confidence=envelope.current_confidence,
        envelope_status=envelope.envelope_status,
        latest_analysis_id=envelope.latest_analysis_id,
        created_at=envelope.created_at,
        updated_at=envelope.updated_at,
    )


@router.get("/project/{project_id}/arc/{arc_no}")
async def get_arc_envelope(
    project_id: int,
    arc_no: int,
    service: ArcEnvelopeService = Depends(get_arc_service),
    current_user: dict = Depends(get_current_user),
) -> ArcEnvelopeResponse:
    """获取指定 arc 的 envelope"""
    envelope = await service.get_arc_envelope(project_id, arc_no)
    
    if not envelope:
        raise HTTPException(
            status_code=404,
            detail=f"Arc envelope not found for arc {arc_no}"
        )
    
    return ArcEnvelopeResponse(
        id=envelope.id,
        project_id=envelope.project_id,
        arc_no=envelope.arc_no,
        base_ratio=envelope.base_ratio,
        base_target_size=envelope.base_target_size,
        base_soft_min=envelope.base_soft_min,
        base_soft_max=envelope.base_soft_max,
        source_policy_tier=envelope.source_policy_tier,
        total_chapters_at_calculation=envelope.total_chapters_at_calculation,
        resolved_target_size=envelope.resolved_target_size,
        resolved_soft_min=envelope.resolved_soft_min,
        resolved_soft_max=envelope.resolved_soft_max,
        resolved_detailed_band_size=envelope.resolved_detailed_band_size,
        resolved_frozen_zone_size=envelope.resolved_frozen_zone_size,
        current_projected_size=envelope.current_projected_size,
        current_confidence=envelope.current_confidence,
        envelope_status=envelope.envelope_status,
        latest_analysis_id=envelope.latest_analysis_id,
        created_at=envelope.created_at,
        updated_at=envelope.updated_at,
    )


@router.get("/project/{project_id}")
async def get_project_arcs(
    project_id: int,
    service: ArcEnvelopeService = Depends(get_arc_service),
    current_user: dict = Depends(get_current_user),
) -> list[ArcEnvelopeResponse]:
    """获取项目的所有 arc envelopes"""
    envelopes = await service.get_project_arcs(project_id)
    
    return [
        ArcEnvelopeResponse(
            id=e.id,
            project_id=e.project_id,
            arc_no=e.arc_no,
            base_ratio=e.base_ratio,
            base_target_size=e.base_target_size,
            base_soft_min=e.base_soft_min,
            base_soft_max=e.base_soft_max,
            source_policy_tier=e.source_policy_tier,
            total_chapters_at_calculation=e.total_chapters_at_calculation,
            resolved_target_size=e.resolved_target_size,
            resolved_soft_min=e.resolved_soft_min,
            resolved_soft_max=e.resolved_soft_max,
            resolved_detailed_band_size=e.resolved_detailed_band_size,
            resolved_frozen_zone_size=e.resolved_frozen_zone_size,
            current_projected_size=e.current_projected_size,
            current_confidence=e.current_confidence,
            envelope_status=e.envelope_status,
            latest_analysis_id=e.latest_analysis_id,
            created_at=e.created_at,
            updated_at=e.updated_at,
        )
        for e in envelopes
    ]


@router.post("/project/{project_id}/arc/{arc_no}/adjust")
async def adjust_arc_envelope(
    project_id: int,
    arc_no: int,
    request: ArcAdjustmentRequest,
    service: ArcEnvelopeService = Depends(get_arc_service),
    current_user: dict = Depends(get_current_user),
) -> ArcEnvelopeResponse:
    """
    运行时调整 arc envelope
    
    当检测到 expansion/compression signals 时调用。
    adjustment: expand (扩张 15%) / compress (压缩 15%) / keep (保持)
    """
    envelope = await service.adjust_arc_envelope(
        project_id, arc_no, request.adjustment
    )
    
    return ArcEnvelopeResponse(
        id=envelope.id,
        project_id=envelope.project_id,
        arc_no=envelope.arc_no,
        base_ratio=envelope.base_ratio,
        base_target_size=envelope.base_target_size,
        base_soft_min=envelope.base_soft_min,
        base_soft_max=envelope.base_soft_max,
        source_policy_tier=envelope.source_policy_tier,
        total_chapters_at_calculation=envelope.total_chapters_at_calculation,
        resolved_target_size=envelope.resolved_target_size,
        resolved_soft_min=envelope.resolved_soft_min,
        resolved_soft_max=envelope.resolved_soft_max,
        resolved_detailed_band_size=envelope.resolved_detailed_band_size,
        resolved_frozen_zone_size=envelope.resolved_frozen_zone_size,
        current_projected_size=envelope.current_projected_size,
        current_confidence=envelope.current_confidence,
        envelope_status=envelope.envelope_status,
        latest_analysis_id=envelope.latest_analysis_id,
        created_at=envelope.created_at,
        updated_at=envelope.updated_at,
    )
