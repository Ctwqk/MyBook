"""Action Mapper Service - v2.5

职责：
- 把聚合后的读者信号映射成系统动作建议
- 生成 AudienceHintPack
"""
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import (
    AudienceSignal, AudienceTrend, AudienceHintPack,
    SignalType, TargetType, WindowType
)
from app.schemas.comment import (
    ActionSuggestion, ResponseWindow, FeedbackLayerConfig,
    PacingHint, ClarityHint, CharacterHeatChange, RiskFlag
)


class ActionMapperService:
    """
    动作映射服务 - v2.5
    
    核心功能：
    1. 将 AudienceSignal 映射为 ActionSuggestion
    2. 生成 AudienceHintPack（给 Writer 用）
    3. 按响应窗口分类
    """
    
    # 默认配置
    DEFAULT_CONFIG = FeedbackLayerConfig()
    
    def __init__(self, db: AsyncSession, config: Optional[FeedbackLayerConfig] = None):
        self.db = db
        self.config = config or self.DEFAULT_CONFIG
    
    def _map_confusion_to_action(
        self,
        signal: AudienceSignal
    ) -> ActionSuggestion:
        """
        Confusion 信号映射为动作建议
        
        默认延迟响应（5-20章），只有高风险才快速响应
        """
        # 检查是否满足快速响应条件
        fast_response = (
            signal.confidence >= 0.8 and 
            signal.score >= 0.7 and
            signal.target_type == TargetType.PLOT.value
        )
        
        if fast_response:
            response_window = ResponseWindow.FAST
            priority = 2
        else:
            response_window = ResponseWindow.SLOW
            priority = 4
        
        return ActionSuggestion(
            action_type="clarification_backlog",
            target=f"clarify_{signal.target_type}_{signal.target_id or 'unknown'}",
            description=f"读者对{signal.target_type}存在困惑，建议在未来{response_window.value}内自然澄清",
            response_window=response_window,
            confidence=signal.confidence,
            priority=priority
        )
    
    def _map_pacing_to_action(
        self,
        signal: AudienceSignal
    ) -> ActionSuggestion:
        """
        Pacing 信号映射为动作建议
        
        中速响应（2-5章）
        """
        return ActionSuggestion(
            action_type="pacing_adjustment",
            target="current_band",
            description=f"读者反馈节奏偏慢/偏水，建议在未来{ResponseWindow.MEDIUM.value}内调整",
            response_window=ResponseWindow.MEDIUM,
            confidence=signal.confidence,
            priority=3
        )
    
    def _map_character_heat_to_action(
        self,
        signal: AudienceSignal
    ) -> ActionSuggestion:
        """
        Character Heat 信号映射为动作建议
        
        慢速响应（5-10章），需要持续趋势才触发
        """
        return ActionSuggestion(
            action_type="character_weight_adjustment",
            target=f"character_{signal.target_id or 'unknown'}",
            description=f"角色热度上升，建议在未来{ResponseWindow.SLOW.value}内顺势增加出场权重",
            response_window=ResponseWindow.SLOW,
            confidence=signal.confidence,
            priority=3
        )
    
    def _map_risk_to_action(
        self,
        signal: AudienceSignal
    ) -> ActionSuggestion:
        """
        Risk 信号映射为动作建议
        
        快速响应（1-3章），高优先级
        """
        return ActionSuggestion(
            action_type="urgent_repair",
            target=f"repair_{signal.target_type}_{signal.target_id or 'unknown'}",
            description=f"高风险反馈：{signal.evidence_summary}，建议在未来{ResponseWindow.FAST.value}内优先修补",
            response_window=ResponseWindow.FAST,
            confidence=signal.confidence,
            priority=1
        )
    
    def map_signal_to_action(self, signal: AudienceSignal) -> ActionSuggestion:
        """将信号映射为动作建议"""
        signal_type = signal.signal_type
        
        if signal_type == SignalType.CONFUSION.value:
            return self._map_confusion_to_action(signal)
        elif signal_type == SignalType.PACING.value:
            return self._map_pacing_to_action(signal)
        elif signal_type == SignalType.CHARACTER_HEAT.value:
            return self._map_character_heat_to_action(signal)
        elif signal_type == SignalType.RISK.value:
            return self._map_risk_to_action(signal)
        else:
            # 默认：不做动作
            return ActionSuggestion(
                action_type="no_action",
                target="",
                description="信号类型未知",
                response_window=ResponseWindow.SLOW,
                confidence=0.0,
                priority=5
            )
    
    def generate_action_mapping(
        self,
        signals: list[AudienceSignal],
        trends: list[AudienceTrend]
    ) -> dict:
        """
        生成完整的动作映射
        
        Returns:
            按信号类型分组的动作建议列表
        """
        confusion_actions = []
        pacing_actions = []
        character_heat_actions = []
        relationship_actions = []
        prediction_analysis = []
        risk_actions = []
        
        for signal in signals:
            action = self.map_signal_to_action(signal)
            
            if signal.signal_type == SignalType.CONFUSION.value:
                confusion_actions.append(action)
            elif signal.signal_type == SignalType.PACING.value:
                pacing_actions.append(action)
            elif signal.signal_type == SignalType.CHARACTER_HEAT.value:
                character_heat_actions.append(action)
            elif signal.signal_type == SignalType.RISK.value:
                risk_actions.append(action)
        
        # 按优先级排序
        confusion_actions.sort(key=lambda a: a.priority)
        pacing_actions.sort(key=lambda a: a.priority)
        character_heat_actions.sort(key=lambda a: a.priority)
        risk_actions.sort(key=lambda a: a.priority)
        
        return {
            "confusion_actions": confusion_actions,
            "pacing_actions": pacing_actions,
            "character_heat_actions": character_heat_actions,
            "relationship_actions": relationship_actions,
            "prediction_analysis": prediction_analysis,
            "risk_actions": risk_actions
        }
    
    def generate_hint_pack(
        self,
        signals: list[AudienceSignal],
        chapter_id: Optional[int] = None,
        band_id: Optional[str] = None
    ) -> AudienceHintPack:
        """
        生成 Writer 可用的极小提示包
        
        只包含高置信度的提示，且不暴露原始评论
        """
        pacing_hints = []
        clarity_hints = []
        character_heat_changes = []
        risk_flags = []
        
        for signal in signals:
            # 只包含高置信度的提示
            if signal.confidence < 0.6:
                continue
            
            if signal.signal_type == SignalType.PACING.value:
                pacing_hints.append(PacingHint(
                    target=signal.target_type or "general",
                    hint=f"读者反馈节奏问题",
                    urgency="medium" if signal.confidence < 0.8 else "high"
                ))
            
            elif signal.signal_type == SignalType.CONFUSION.value:
                clarity_hints.append(ClarityHint(
                    target=signal.target_type or "unknown",
                    hint=f"读者存在理解困惑",
                    urgency="low"  # 默认低优先级
                ))
            
            elif signal.signal_type == SignalType.CHARACTER_HEAT.value:
                if signal.target_type == TargetType.CHARACTER.value:
                    character_heat_changes.append(CharacterHeatChange(
                        character_id=signal.target_id or 0,
                        direction="up",
                        confidence=signal.confidence
                    ))
            
            elif signal.signal_type == SignalType.RISK.value:
                risk_flags.append(RiskFlag(
                    type="reader_feedback_risk",
                    target_id=signal.target_id,
                    description=signal.evidence_summary or "读者负面反馈",
                    urgency="high" if signal.confidence >= 0.8 else "medium"
                ))
        
        return AudienceHintPack(
            pacing_hints=pacing_hints,
            clarity_hints=clarity_hints,
            character_heat_changes=character_heat_changes,
            risk_flags=risk_flags
        )
    
    async def create_hint_pack(
        self,
        project_id: int,
        chapter_id: Optional[int] = None,
        band_id: Optional[str] = None
    ) -> AudienceHintPack:
        """
        创建并存储 Hint Pack
        """
        # 获取最近窗口的信号
        from app.models.comment import WindowType
        
        # 简化：使用最近的 AudienceSignal
        from sqlalchemy import select
        result = await self.db.execute(
            select(AudienceSignal)
            .where(AudienceSignal.project_id == project_id)
            .order_by(AudienceSignal.generated_at.desc())
            .limit(20)
        )
        signals = list(result.scalars().all())
        
        # 生成 Hint Pack
        hint_pack = self.generate_hint_pack(signals, chapter_id, band_id)
        
        # 补充元数据
        hint_pack.project_id = project_id
        hint_pack.chapter_id = chapter_id
        hint_pack.band_id = band_id
        hint_pack.generated_at = datetime.now()
        
        # 存储
        self.db.add(hint_pack)
        await self.db.flush()
        await self.db.refresh(hint_pack)
        
        return hint_pack
    
    def get_cooldown_status(
        self,
        project_id: int,
        signal_type: str
    ) -> dict:
        """
        检查冷却期状态
        
        同一类信号在冷却期内不应重复响应
        """
        # 简化实现：返回可响应状态
        return {
            "signal_type": signal_type,
            "in_cooldown": False,
            "cooldown_remaining_chapters": 0,
            "can_respond": True
        }
