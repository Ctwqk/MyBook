"""Feedback Aggregator Service - v2.5

职责：
- 按窗口聚合评论信号
- 计算聚合分数
- 生成 AudienceSignal 和 AudienceTrend
"""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import (
    RawComment, CommentSignal, AudienceSignal, AudienceTrend, 
    SignalType, TargetType, WindowType, TrendType
)
from app.repositories.chapter import ChapterRepository


class SignalAggregator:
    """
    信号聚合器 - Phase B 3窗口设计
    
    窗口配置：
    - short: 最近 2~3 章 (窗口大小 3)
    - medium: 最近 5~10 章 (窗口大小 8)
    - long: 最近 10~20 章 (窗口大小 20)
    
    核心功能：
    1. 按窗口聚合信号
    2. 计算趋势
    3. 生成 AudienceSignal
    4. 估算读者规模
    """
    
    # Phase B 3窗口配置
    WINDOWS = [
        ("short", 3),   # 最近 2~3 章
        ("medium", 8),  # 最近 5~10 章
        ("long", 20),   # 最近 10~20 章
    ]
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.chapter_repo = ChapterRepository(db)
    
    async def _get_chapter_range(
        self, 
        project_id: int, 
        window_name: str
    ) -> tuple[int, int]:
        """获取窗口对应的章节范围"""
        window_size = None
        for name, size in self.WINDOWS:
            if name == window_name:
                window_size = size
                break
        
        if window_size is None:
            raise ValueError(f"Unknown window: {window_name}")
        
        # 获取最新章节
        result = await self.db.execute(
            select(func.max(RawComment.chapter_id))
            .where(RawComment.project_id == project_id)
        )
        latest_chapter = result.scalar() or 1
        
        start_chapter = max(1, latest_chapter - window_size + 1)
        
        return start_chapter, latest_chapter
    
    def estimate_reader_scale(self, total_comments_in_window: int, comment_to_reader_ratio: int = 100) -> int:
        """
        估算读者规模
        
        经验系数：1 条评论 ≈ 100 个沉默读者
        
        Args:
            total_comments_in_window: 窗口内评论总数
            comment_to_reader_ratio: 评论与读者比例，默认 100:1
        
        Returns:
            估算的读者数量
        """
        return total_comments_in_window * comment_to_reader_ratio
    
    async def aggregate(
        self,
        project_id: int,
        window_name: str = "short"
    ) -> list[AudienceSignal]:
        """
        聚合信号 - 支持 Phase B 3窗口设计
        
        Args:
            project_id: 项目 ID
            window_name: 窗口名称 (short/medium/long)
        
        Returns:
            AudienceSignal 列表
        """
        chapter_start, chapter_end = await self._get_chapter_range(
            project_id, window_name
        )
        
        # 查询该窗口内的所有信号
        result = await self.db.execute(
            select(CommentSignal)
            .join(RawComment, CommentSignal.source_comment_id == RawComment.id)
            .where(
                and_(
                    CommentSignal.project_id == project_id,
                    RawComment.chapter_id >= chapter_start,
                    RawComment.chapter_id <= chapter_end
                )
            )
        )
        signals = list(result.scalars().all())
        
        # 按信号类型和目标分组聚合
        aggregated = {}
        
        for signal in signals:
            # 组 key
            key = (
                signal.signal_type,
                signal.target_type,
                signal.target_id
            )
            
            if key not in aggregated:
                aggregated[key] = {
                    'signals': [],
                    'comment_ids': set(),
                    'user_hashes': set(),
                    'total_intensity': 0.0,
                    'total_confidence': 0.0
                }
            
            agg = aggregated[key]
            agg['signals'].append(signal)
            agg['total_intensity'] += signal.intensity
            agg['total_confidence'] += signal.confidence
            
            # 获取评论的用户哈希
            comment = await self.db.get(RawComment, signal.source_comment_id)
            if comment:
                agg['user_hashes'].add(comment.user_hash)
        
        # 创建 AudienceSignal
        audience_signals = []
        
        # 估算读者规模
        total_comments = len(signals)
        estimated_readers = self.estimate_reader_scale(total_comments)
        
        for (signal_type, target_type, target_id), agg in aggregated.items():
            signal_count = len(agg['signals'])
            user_count = len(agg['user_hashes'])
            
            # 聚合分数 = 平均强度 * 用户覆盖率 * 置信度
            avg_intensity = agg['total_intensity'] / signal_count if signal_count > 0 else 0
            avg_confidence = agg['total_confidence'] / signal_count if signal_count > 0 else 0
            
            # 简单评分公式
            score = avg_intensity * min(1.0, user_count / 5.0) * avg_confidence
            
            # 生成证据摘要（包含读者规模估算）
            evidence = f"共{signal_count}条评论，{user_count}位用户反馈，预估{estimated_readers}读者"
            
            audience_signal = AudienceSignal(
                project_id=project_id,
                window_type=window_name,
                chapter_start=chapter_start,
                chapter_end=chapter_end,
                signal_type=signal_type,
                target_type=target_type,
                target_id=target_id,
                score=score,
                comment_count=signal_count,
                user_count=user_count,
                confidence=avg_confidence,
                evidence_summary=evidence,
                generated_at=datetime.now()
            )
            
            self.db.add(audience_signal)
            audience_signals.append(audience_signal)
        
        await self.db.flush()
        
        return audience_signals
    
    async def calculate_trends(
        self,
        project_id: int,
        target_type: TargetType,
        target_id: Optional[int] = None
    ) -> list[AudienceTrend]:
        """
        计算趋势
        
        比较不同窗口的信号分数，判断趋势
        """
        trends = []
        
        # 获取 short 和 medium 窗口的分数
        current_window = "short"
        previous_window = "medium"
        
        # 查询当前窗口信号
        current_signals = await self._get_signals_for_window(
            project_id, current_window, target_type, target_id
        )
        
        # 查询前一窗口信号
        previous_signals = await self._get_signals_for_window(
            project_id, previous_window, target_type, target_id
        )
        
        # 计算趋势
        current_score = sum(s.score for s in current_signals) / len(current_signals) if current_signals else 0
        previous_score = sum(s.score for s in previous_signals) / len(previous_signals) if previous_signals else 0
        
        delta = current_score - previous_score
        
        # 判断趋势类型
        if abs(delta) < 0.1:
            trend_type = TrendType.STABLE
        elif delta > 0:
            trend_type = TrendType.RISING
        else:
            trend_type = TrendType.FALLING
        
        # 创建趋势记录
        trend = AudienceTrend(
            project_id=project_id,
            window_type=current_window,
            target_type=target_type.value,
            target_id=target_id,
            trend_type=trend_type.value,
            score_delta=delta,
            summary=f"{target_type.value} 趋势: {trend_type.value} (Δ={delta:.3f})",
            generated_at=datetime.now()
        )
        
        self.db.add(trend)
        trends.append(trend)
        
        await self.db.flush()
        
        return trends
    
    async def _get_signals_for_window(
        self,
        project_id: int,
        window_name: str,
        target_type: TargetType,
        target_id: Optional[int] = None
    ) -> list[AudienceSignal]:
        """获取指定窗口的信号"""
        chapter_start, chapter_end = await self._get_chapter_range(
            project_id, window_name
        )
        
        query = select(AudienceSignal).where(
            and_(
                AudienceSignal.project_id == project_id,
                AudienceSignal.window_type == window_name,
                AudienceSignal.target_type == target_type.value,
                AudienceSignal.chapter_start >= chapter_start,
                AudienceSignal.chapter_end <= chapter_end
            )
        )
        
        if target_id:
            query = query.where(AudienceSignal.target_id == target_id)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_high_confidence_alerts(
        self,
        project_id: int,
        min_confidence: float = 0.7,
        min_score: float = 0.5
    ) -> list[dict]:
        """
        获取高置信度告警
        
        用于快速响应风险类问题
        """
        result = await self.db.execute(
            select(AudienceSignal)
            .where(
                and_(
                    AudienceSignal.project_id == project_id,
                    AudienceSignal.confidence >= min_confidence,
                    AudienceSignal.score >= min_score
                )
            )
            .order_by(AudienceSignal.score.desc())
            .limit(10)
        )
        
        signals = list(result.scalars().all())
        
        alerts = []
        for signal in signals:
            # 只对 RISK 类型发出高优先级告警
            if signal.signal_type == SignalType.RISK.value:
                alerts.append({
                    "signal_type": signal.signal_type,
                    "target_type": signal.target_type,
                    "target_id": signal.target_id,
                    "score": signal.score,
                    "confidence": signal.confidence,
                    "comment_count": signal.comment_count,
                    "urgency": "high" if signal.confidence >= 0.8 else "medium",
                    "evidence": signal.evidence_summary
                })
        
        return alerts
    
    async def get_signals_for_arc_director(
        self,
        project_id: int
    ) -> dict:
        """
        获取 Arc Director 可用的信号
        
        主要关注：
        - Character Heat 趋势
        - Relationship Interest
        - Long-window Confusion
        """
        # 获取所有窗口的聚合信号
        all_signals = []
        
        for window_name, _ in self.WINDOWS:
            signals = await self.aggregate(project_id, window_name)
            all_signals.extend(signals)
        
        # 按类型分组
        by_type = {
            SignalType.CONFUSION.value: [],
            SignalType.PACING.value: [],
            SignalType.CHARACTER_HEAT.value: [],
            SignalType.RISK.value: []
        }
        
        for signal in all_signals:
            if signal.signal_type in by_type:
                by_type[signal.signal_type].append(signal)
        
        return {
            "confusion_signals": by_type[SignalType.CONFUSION.value],
            "pacing_signals": by_type[SignalType.PACING.value],
            "character_heat_signals": by_type[SignalType.CHARACTER_HEAT.value],
            "risk_signals": by_type[SignalType.RISK.value],
            "high_confidence_alerts": await self.get_high_confidence_alerts(project_id)
        }
    
    async def get_signals_for_pacing_strategist(
        self,
        project_id: int
    ) -> dict:
        """
        获取 Pacing Strategist 可用的信号
        """
        # 只关注 short 和 medium 窗口
        short_signals = await self.aggregate(project_id, "short")
        medium_signals = await self.aggregate(project_id, "medium")
        
        # 筛选 pacing 和 risk 类型
        pacing_signals = [
            s for s in short_signals + medium_signals
            if s.signal_type in [SignalType.PACING.value, SignalType.RISK.value]
        ]
        
        return {
            "immediate_signals": [
                s for s in short_signals 
                if s.signal_type in [SignalType.PACING.value, SignalType.RISK.value]
            ],
            "recent_signals": pacing_signals,
            "high_confidence_alerts": await self.get_high_confidence_alerts(project_id)
        }


# 保留旧类名作为别名，保持向后兼容
FeedbackAggregatorService = SignalAggregator
