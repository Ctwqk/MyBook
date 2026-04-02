"""
Audience Feedback API 路由 - v2.5

提供：
- 评论摄入
- 反馈查询
- 动作映射
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import logging

from app.schemas.comment import (
    CommentIngestRequest,
    BatchCommentIngestRequest,
    FeedbackQueryRequest,
    WindowType,
    SignalType,
    AudienceHintPackResponse,
    AggregatedFeedbackResponse,
    ActionMappingResponse,
)
from app.services.audience.ingestion import CommentIngestionService
from app.services.audience.analysis import CommentAnalysisService
from app.services.audience.aggregator import FeedbackAggregatorService
from app.services.audience.action_mapper import ActionMapperService
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audience", tags=["audience"])


# ==================== Comment Ingestion ====================

class CommentIngestResponse(BaseModel):
    """评论摄入响应"""
    success: bool
    comment_id: Optional[int] = None
    error: Optional[str] = None


class BatchCommentIngestResponse(BaseModel):
    """批量评论摄入响应"""
    inserted: int
    duplicates: int
    errors: list
    total: int


@router.post("/comments", response_model=CommentIngestResponse)
async def ingest_comment(request: CommentIngestRequest, db=Depends(get_db)):
    """
    摄入单条评论
    
    用于平台评论数据同步
    """
    try:
        service = CommentIngestionService(db)
        comment = await service.ingest_comment(request)
        return CommentIngestResponse(
            success=True,
            comment_id=comment.id
        )
    except ValueError as e:
        return CommentIngestResponse(success=False, error=str(e))
    except Exception as e:
        logger.error(f"Comment ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/comments/batch", response_model=BatchCommentIngestResponse)
async def ingest_batch(request: BatchCommentIngestRequest, db=Depends(get_db)):
    """
    批量摄入评论
    
    用于平台评论数据同步
    """
    try:
        service = CommentIngestionService(db)
        result = await service.ingest_batch(request)
        return BatchCommentIngestResponse(**result)
    except Exception as e:
        logger.error(f"Batch ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/comments/stats/{project_id}")
async def get_comment_stats(project_id: int, db=Depends(get_db)):
    """获取项目评论统计"""
    try:
        service = CommentIngestionService(db)
        stats = await service.get_comment_stats(project_id)
        return stats
    except Exception as e:
        logger.error(f"Get stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Comment Analysis ====================

class AnalyzeCommentsResponse(BaseModel):
    """分析评论响应"""
    processed_comments: int
    generated_signals: int
    avg_signals_per_comment: float


@router.post("/analyze/{project_id}", response_model=AnalyzeCommentsResponse)
async def analyze_comments(project_id: int, db=Depends(get_db)):
    """
    分析项目的未处理评论
    
    处理新摄入的评论，生成信号
    """
    try:
        ingestion = CommentIngestionService(db)
        analysis = CommentAnalysisService(db)
        
        # 获取未处理的评论
        comments = await ingestion.get_unprocessed_comments(project_id, limit=100)
        
        if not comments:
            return AnalyzeCommentsResponse(
                processed_comments=0,
                generated_signals=0,
                avg_signals_per_comment=0.0
            )
        
        # 分析评论
        result = await analysis.batch_analyze(comments)
        
        # 标记已处理
        comment_ids = [c.id for c in comments]
        await ingestion.mark_as_processed(comment_ids)
        
        await db.commit()
        
        return AnalyzeCommentsResponse(**result)
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Feedback Aggregation ====================

@router.get("/signals/{project_id}")
async def get_signals(
    project_id: int,
    window_type: WindowType = WindowType.WINDOW_A,
    db=Depends(get_db)
):
    """
    获取聚合后的读者信号
    
    按窗口聚合
    """
    try:
        service = FeedbackAggregatorService(db)
        signals = await service.aggregate_signals(project_id, window_type)
        
        return {
            "signals": [
                {
                    "id": s.id,
                    "signal_type": s.signal_type,
                    "target_type": s.target_type,
                    "target_id": s.target_id,
                    "score": s.score,
                    "comment_count": s.comment_count,
                    "user_count": s.user_count,
                    "confidence": s.confidence,
                    "evidence_summary": s.evidence_summary,
                    "chapter_range": f"{s.chapter_start}-{s.chapter_end}"
                }
                for s in signals
            ],
            "count": len(signals)
        }
    except Exception as e:
        logger.error(f"Get signals failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts/{project_id}")
async def get_high_confidence_alerts(project_id: int, db=Depends(get_db)):
    """获取高置信度告警（用于快速响应）"""
    try:
        service = FeedbackAggregatorService(db)
        alerts = await service.get_high_confidence_alerts(project_id)
        return {"alerts": alerts, "count": len(alerts)}
    except Exception as e:
        logger.error(f"Get alerts failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/arc-director/{project_id}")
async def get_arc_director_signals(project_id: int, db=Depends(get_db)):
    """
    获取 Arc Director 可用的信号
    
    包含 Character Heat、Relationship Interest、Long-window Confusion 等
    """
    try:
        service = FeedbackAggregatorService(db)
        signals = await service.get_signals_for_arc_director(project_id)
        return signals
    except Exception as e:
        logger.error(f"Get arc director signals failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pacing/{project_id}")
async def get_pacing_signals(project_id: int, db=Depends(get_db)):
    """
    获取 Pacing Strategist 可用的信号
    """
    try:
        service = FeedbackAggregatorService(db)
        signals = await service.get_signals_for_pacing_strategist(project_id)
        return signals
    except Exception as e:
        logger.error(f"Get pacing signals failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Action Mapping ====================

@router.get("/actions/{project_id}")
async def get_action_mapping(project_id: int, db=Depends(get_db)):
    """
    获取动作映射
    
    将读者信号映射为系统动作建议
    """
    try:
        aggregator = FeedbackAggregatorService(db)
        mapper = ActionMapperService(db)
        
        # 获取所有窗口的信号
        all_signals = []
        for window in [WindowType.WINDOW_A, WindowType.WINDOW_B, WindowType.WINDOW_C]:
            signals = await aggregator.aggregate_signals(project_id, window)
            all_signals.extend(signals)
        
        # 生成动作映射
        actions = mapper.generate_action_mapping(all_signals, [])
        
        return ActionMappingResponse(
            project_id=project_id,
            chapter_id=None,
            confusion_actions=actions["confusion_actions"],
            pacing_actions=actions["pacing_actions"],
            character_heat_actions=actions["character_heat_actions"],
            relationship_actions=actions["relationship_actions"],
            prediction_analysis=actions["prediction_analysis"],
            risk_actions=actions["risk_actions"],
            generated_at=aggregator.db.execute("select now()").scalar()
        )
    except Exception as e:
        logger.error(f"Get action mapping failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Audience Hint Pack ====================

@router.get("/hint-pack/{project_id}")
async def get_hint_pack(
    project_id: int,
    chapter_id: Optional[int] = None,
    band_id: Optional[str] = None,
    db=Depends(get_db)
):
    """
    获取 Writer 可用的极小提示包
    
    只包含高置信度的提示，且不暴露原始评论
    """
    try:
        mapper = ActionMapperService(db)
        hint_pack = await mapper.create_hint_pack(project_id, chapter_id, band_id)
        
        return AudienceHintPackResponse(
            project_id=hint_pack.project_id,
            chapter_id=hint_pack.chapter_id,
            band_id=hint_pack.band_id,
            pacing_hints=hint_pack.pacing_hints or [],
            clarity_hints=hint_pack.clarity_hints or [],
            character_heat_changes=hint_pack.character_heat_changes or [],
            relationship_interest=hint_pack.relationship_interest or [],
            prediction_clusters=hint_pack.prediction_clusters or [],
            risk_flags=hint_pack.risk_flags or [],
            generated_at=hint_pack.generated_at,
            version=hint_pack.version
        )
    except Exception as e:
        logger.error(f"Get hint pack failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Aggregated Feedback ====================

@router.get("/feedback/{project_id}")
async def get_aggregated_feedback(
    project_id: int,
    window_type: WindowType = WindowType.WINDOW_A,
    db=Depends(get_db)
):
    """
    获取聚合反馈（供查看用）
    """
    try:
        aggregator = FeedbackAggregatorService(db)
        mapper = ActionMapperService(db)
        
        # 聚合信号
        signals = await aggregator.aggregate_signals(project_id, window_type)
        
        # 获取高置信度告警
        alerts = await aggregator.get_high_confidence_alerts(project_id)
        
        # 生成动作映射
        action_mapping = mapper.generate_action_mapping(signals, [])
        
        # 生成汇总
        summary = {
            "total_signals": len(signals),
            "by_type": {
                "confusion": len([s for s in signals if s.signal_type == SignalType.CONFUSION.value]),
                "pacing": len([s for s in signals if s.signal_type == SignalType.PACING.value]),
                "character_heat": len([s for s in signals if s.signal_type == SignalType.CHARACTER_HEAT.value]),
                "risk": len([s for s in signals if s.signal_type == SignalType.RISK.value])
            },
            "high_confidence_count": len(alerts)
        }
        
        return AggregatedFeedbackResponse(
            project_id=project_id,
            window_type=window_type,
            signals=signals,
            trends=[],  # 简化
            summary=summary,
            high_confidence_alerts=alerts,
            generated_at=aggregator.db.execute("select now()").scalar()
        )
    except Exception as e:
        logger.error(f"Get aggregated feedback failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
