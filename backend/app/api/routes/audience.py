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
from app.services.audience.analyzer import CommentAnalyzer, ReaderFeedbackView
from app.services.audience.aggregator import FeedbackAggregatorService
from app.services.audience.action_mapper import ActionMapperService
from app.llm.factory import create_llm_provider
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


class FeedbackSubmitRequest(BaseModel):
    """反馈提交请求"""
    feedback_type: str
    content: str
    rating: Optional[int] = None
    chapter_id: Optional[int] = None


@router.post("/feedback/{project_id}")
async def submit_feedback(
    project_id: int,
    request: FeedbackSubmitRequest,
    db=Depends(get_db)
):
    """
    提交读者反馈
    
    直接摄入一条反馈（不经过评论分析流程）
    """
    try:
        ingestion = CommentIngestionService(db)
        comment_data = CommentIngestRequest(
            project_id=project_id,
            platform="manual",  # 手动提交标记
            chapter_id=request.chapter_id,
            user_hash="manual_user",  # 占位
            content=request.content,
            like_count=0,
            reply_count=0
        )
        comment = await ingestion.ingest_comment(comment_data)
        await db.commit()
        return {"success": True, "comment_id": comment.id}
    except Exception as e:
        logger.error(f"Submit feedback failed: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis/{project_id}")
async def get_analysis_summary(
    project_id: int,
    db=Depends(get_db)
):
    """
    获取分析摘要
    
    返回项目的整体分析状态和统计
    """
    try:
        ingestion = CommentIngestionService(db)
        aggregator = FeedbackAggregatorService(db)
        
        # 获取评论统计
        stats = await ingestion.get_comment_stats(project_id)
        
        # 获取信号统计
        signals = await aggregator.aggregate_signals(project_id, WindowType.WINDOW_A)
        
        # 获取高置信度告警
        alerts = await aggregator.get_high_confidence_alerts(project_id)
        
        # 计算平均评分（如果有的话）
        avg_rating = None
        if stats.get("avg_like_count"):
            # 简单转换为 1-5 评分
            avg_rating = min(5, max(1, stats["avg_like_count"] / 2))
        
        return {
            "project_id": project_id,
            "comment_count": stats.get("total", 0),
            "platform_count": stats.get("platform_count", 0),
            "signal_count": len(signals),
            "alert_count": len(alerts),
            "average_rating": avg_rating,
            "analysis_status": "completed" if stats.get("total", 0) > 0 else "pending",
            "last_analyzed": stats.get("latest_timestamp")
        }
    except Exception as e:
        logger.error(f"Get analysis summary failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/behavior/{project_id}")
async def get_behavior_data(
    project_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db=Depends(get_db)
):
    """
    获取读者行为数据
    
    按时间段聚合读者互动数据
    """
    try:
        ingestion = CommentIngestionService(db)
        
        # 获取原始评论
        comments = await ingestion.get_comments_by_project(
            project_id,
            limit=1000
        )
        
        # 按时间段聚合
        behavior_by_day = {}
        total_likes = 0
        total_replies = 0
        
        for comment in comments:
            day = comment.created_at.strftime("%Y-%m-%d") if hasattr(comment, 'created_at') else "unknown"
            if day not in behavior_by_day:
                behavior_by_day[day] = {
                    "date": day,
                    "comment_count": 0,
                    "total_likes": 0,
                    "total_replies": 0,
                    "unique_users": set()
                }
            
            behavior_by_day[day]["comment_count"] += 1
            behavior_by_day[day]["total_likes"] += comment.like_count or 0
            behavior_by_day[day]["total_replies"] += comment.reply_count or 0
            behavior_by_day[day]["unique_users"].add(comment.user_hash)
            total_likes += comment.like_count or 0
            total_replies += comment.reply_count or 0
        
        # 转换集合为计数
        for day_data in behavior_by_day.values():
            day_data["unique_users"] = len(day_data["unique_users"])
        
        return {
            "project_id": project_id,
            "start_date": start_date,
            "end_date": end_date,
            "total_comments": len(comments),
            "total_likes": total_likes,
            "total_replies": total_replies,
            "daily_behavior": list(behavior_by_day.values())
        }
    except Exception as e:
        logger.error(f"Get behavior data failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Phase A: LLM 增强分析 ====================

class LLMAnalyzeResponse(BaseModel):
    """LLM 分析响应"""
    processed_comments: int
    generated_signals: int
    llm_success: bool
    fallback_used: bool


@router.post("/analyze-llm/{project_id}", response_model=LLMAnalyzeResponse)
async def analyze_comments_llm(
    project_id: int,
    limit: int = 20,
    db=Depends(get_db)
):
    """
    Phase A: 使用 LLM 批量分析评论
    
    调用 LLM 解析评论，提取结构化信号
    失败时自动 fallback 到关键词匹配
    
    Args:
        project_id: 项目 ID
        limit: 最多分析的评论数 (默认 20)
    """
    try:
        # 创建 LLM provider
        llm = create_llm_provider()
        
        # 创建分析器
        analyzer = CommentAnalyzer(db, llm)
        
        # 执行分析
        result = await analyzer.analyze_batch(project_id, limit)
        
        await db.commit()
        
        return LLMAnalyzeResponse(**result)
        
    except Exception as e:
        logger.error(f"LLM analysis failed: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reader-feedback/{project_id}")
async def get_reader_feedback(
    project_id: int,
    chapter_number: Optional[int] = None,
    db=Depends(get_db)
):
    """
    Phase A: 获取读者反馈视图
    
    返回给 Writer 使用的结构化反馈视图
    包含：
    - dominant_sentiment: 综合情感 (如 "risk:confirmed")
    - feedback_summary: 反馈摘要
    - highlighted_topics: 高亮话题 (格式: "target_name:signal_type:level")
    - recent_highlights: 最近高亮评论
    """
    try:
        # 构建 ReaderFeedbackView
        feedback = await ReaderFeedbackView.from_candidates(
            db, project_id, chapter_number
        )
        
        return feedback.to_dict()
        
    except Exception as e:
        logger.error(f"Get reader feedback failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/candidates/{project_id}")
async def get_signal_candidates(
    project_id: int,
    signal_type: Optional[str] = None,
    signal_level: Optional[str] = None,
    limit: int = 50,
    db=Depends(get_db)
):
    """
    Phase A: 获取信号候选列表
    
    返回 CommentSignalCandidate 列表
    可按 signal_type 和 signal_level 过滤
    """
    try:
        from app.models.comment import CommentSignalCandidate
        from sqlalchemy import select
        
        query = select(CommentSignalCandidate).where(
            CommentSignalCandidate.project_id == project_id
        )
        
        if signal_type:
            query = query.where(CommentSignalCandidate.signal_type == signal_type)
        
        if signal_level:
            query = query.where(CommentSignalCandidate.signal_level == signal_level)
        
        query = query.order_by(
            CommentSignalCandidate.created_at.desc()
        ).limit(limit)
        
        result = await db.execute(query)
        candidates = list(result.scalars().all())
        
        return {
            "candidates": [
                {
                    "id": c.id,
                    "signal_type": c.signal_type,
                    "target_type": c.target_type,
                    "target_name": c.target_name,
                    "severity": c.severity,
                    "confidence": c.confidence,
                    "evidence_span": c.evidence_span,
                    "signal_level": c.signal_level,
                    "is_llm_generated": c.is_llm_generated,
                    "is_fallback": c.is_fallback,
                    "created_at": c.created_at.isoformat() if c.created_at else None
                }
                for c in candidates
            ],
            "count": len(candidates)
        }
        
    except Exception as e:
        logger.error(f"Get signal candidates failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recalculate-levels/{project_id}")
async def recalculate_signal_levels(
    project_id: int,
    signal_key: Optional[str] = None,
    db=Depends(get_db)
):
    """
    Phase A: 重新计算信号级别
    
    当有更多评论数据时，重新计算信号级别
    用于窗口聚合后更新级别
    
    Args:
        project_id: 项目 ID
        signal_key: 可选，格式 "signal_type:target_type:target_name"
    """
    try:
        analyzer = CommentAnalyzer(db)
        updated = await analyzer.recalculate_signal_levels(project_id, signal_key)
        
        await db.commit()
        
        return {
            "success": True,
            "updated_count": updated
        }
        
    except Exception as e:
        logger.error(f"Recalculate levels failed: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Phase B: 窗口聚合与冷却期 ====================

class CooldownStatusResponse(BaseModel):
    """冷却期状态响应"""
    signal_key: str
    project_id: int
    is_in_cooldown: bool
    cooldown_remaining_seconds: int
    cooldown_end_time: Optional[str] = None
    recent_signals_count: int
    cooldown_threshold: int


@router.get("/aggregated/{project_id}")
async def get_aggregated_signals(
    project_id: int,
    window: str = "short",  # short/medium/long
    db=Depends(get_db)
):
    """
    Phase B: 获取窗口聚合信号
    
    按指定窗口类型聚合读者信号
    
    Args:
        project_id: 项目 ID
        window: 窗口类型 (short/medium/long)
    """
    try:
        service = FeedbackAggregatorService(db)
        
        # 映射窗口类型
        window_map = {
            "short": WindowType.WINDOW_A,
            "medium": WindowType.WINDOW_B,
            "long": WindowType.WINDOW_C
        }
        window_type = window_map.get(window.lower(), WindowType.WINDOW_A)
        
        # 聚合信号
        signals = await service.aggregate_signals(project_id, window_type)
        
        # 计算聚合统计
        signal_stats = {}
        for s in signals:
            key = f"{s.signal_type}:{s.target_type}:{s.target_id}"
            if key not in signal_stats:
                signal_stats[key] = {
                    "signal_type": s.signal_type,
                    "target_type": s.target_type,
                    "target_id": s.target_id,
                    "total_score": 0.0,
                    "total_comments": 0,
                    "total_users": 0,
                    "max_confidence": 0.0,
                    "evidence_snippets": []
                }
            signal_stats[key]["total_score"] += s.score
            signal_stats[key]["total_comments"] += s.comment_count
            signal_stats[key]["total_users"] += s.user_count
            signal_stats[key]["max_confidence"] = max(
                signal_stats[key]["max_confidence"],
                s.confidence
            )
            if s.evidence_summary:
                signal_stats[key]["evidence_snippets"].append(s.evidence_summary[:100])
        
        return {
            "project_id": project_id,
            "window": window,
            "window_type": window_type.value,
            "signals": list(signal_stats.values()),
            "signal_count": len(signal_stats),
            "total_signals": len(signals)
        }
    except Exception as e:
        logger.error(f"Get aggregated signals failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cooldown/{project_id}/{signal_key}", response_model=CooldownStatusResponse)
async def get_cooldown_status(
    project_id: int,
    signal_key: str,
    chapter_number: Optional[int] = None,
    db=Depends(get_db)
):
    """
    Phase B: 查询冷却期状态
    
    检查特定信号是否处于冷却期
    用于避免对同一信号重复触发动作
    
    Args:
        project_id: 项目 ID
        signal_key: 信号标识，格式 "signal_type:target_type:target_name"
        chapter_number: 可选，章节号
    """
    try:
        from datetime import datetime, timedelta
        from app.models.comment import CommentSignalCandidate
        
        # 解析 signal_key
        parts = signal_key.split(":")
        if len(parts) < 3:
            raise ValueError(f"Invalid signal_key format: {signal_key}")
        
        signal_type, target_type, target_name = parts[0], parts[1], ":".join(parts[2:])
        
        # 查询最近的信号
        cooldown_threshold = 24  # 小时
        threshold_time = datetime.utcnow() - timedelta(hours=cooldown_threshold)
        
        query = select(CommentSignalCandidate).where(
            CommentSignalCandidate.project_id == project_id,
            CommentSignalCandidate.signal_type == signal_type,
            CommentSignalCandidate.target_type == target_type,
            CommentSignalCandidate.target_name == target_name,
            CommentSignalCandidate.created_at >= threshold_time
        )
        
        if chapter_number:
            query = query.where(CommentSignalCandidate.chapter_number == chapter_number)
        
        result = await db.execute(query)
        recent_signals = list(result.scalars().all())
        
        # 计算冷却状态
        is_in_cooldown = len(recent_signals) >= 3  # 阈值：3个信号
        cooldown_remaining = 0
        cooldown_end = None
        
        if is_in_cooldown and recent_signals:
            latest_signal = max(recent_signals, key=lambda x: x.created_at)
            cooldown_end = latest_signal.created_at + timedelta(hours=cooldown_threshold)
            remaining_delta = cooldown_end - datetime.utcnow()
            cooldown_remaining = max(0, int(remaining_delta.total_seconds()))
            
            if cooldown_remaining == 0:
                is_in_cooldown = False
        
        return CooldownStatusResponse(
            signal_key=signal_key,
            project_id=project_id,
            is_in_cooldown=is_in_cooldown,
            cooldown_remaining_seconds=cooldown_remaining,
            cooldown_end_time=cooldown_end.isoformat() if cooldown_end else None,
            recent_signals_count=len(recent_signals),
            cooldown_threshold=cooldown_threshold
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Get cooldown status failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
