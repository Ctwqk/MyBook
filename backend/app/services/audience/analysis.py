"""Comment Analysis Service - v2.5

职责：
- 对单条评论做基础结构化分析
- 输出信号类型、目标、情绪、强度等
"""
import re
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import RawComment, CommentSignal
from app.schemas.comment import SignalType, TargetType


class CommentAnalysisService:
    """
    评论分析服务 - v2.5
    
    MVP 版本只实现 4 类信号：
    1. confusion - 困惑类
    2. pacing - 节奏类  
    3. character_heat - 角色热度
    4. risk - 风险类
    
    暂不实现：
    - relationship interest
    - prediction cluster
    """
    
    # 关键词模式（简化实现）
    # 实际应该使用 LLM 进行分析，这里用关键词匹配作为 fallback
    
    CONFUSION_PATTERNS = [
        # 中文
        r'看不懂', r'不理解', r'为什么', r'啥意思', r'怎么回', 
        r'没明白', r'蒙了', r'晕了', r'搞不懂', r'不懂',
        r'这个(角色|设定|情节|场景|是什么|干嘛)',
        # 英文
        r"don't understand", r"confused", r"why did", r"what happened",
        r"doesn't make sense", r"how come"
    ]
    
    PACING_PATTERNS = [
        # 中文
        r'水', r'拖', r'慢', r'节奏(慢|差|不好)', r'太慢', r'好水',
        r'铺垫太久', r'进度(慢|慢)', r'推进(慢|慢)', r'啥时候',
        r'还没', r'怎么还', r'等不及',
        # 英文
        r"slow", r"boring", r"dragging", r"pacing issue",
        r"nothing happened", r"stalling"
    ]
    
    CHARACTER_HEAT_PATTERNS = [
        # 中文
        r'帅', r'酷', r'萌', r'可爱', r'喜欢', r'爱了', r'太赞',
        r'有魅力', r'太有戏', r'比主角', r'抢戏', r'圈粉',
        r'这个角色', r'绝了',
        # 英文
        r"hot", r"cool", r"cute", r"love this character",
        r"favorite character", r"steals the show"
    ]
    
    RISK_PATTERNS = [
        # 中文
        r'降智', r'崩了', r'矛盾', r'逻辑(不|有问题)', r'三观',
        r'接受不了', r'太假', r'不合理', r'烂尾', r'写崩',
        r'人设崩', r'前后不一', r'打脸',
        # 英文
        r"stupid", r"idiot", r"out of character", r"contradiction",
        r"doesn't make sense", r"plot hole", r"inconsistent"
    ]
    
    # 目标识别（简化版）
    TARGET_PATTERNS = {
        TargetType.CHARACTER: [
            r'李青|张三|主角|男(主|角)|女(主|角)|反派|配角',
            r'character (liqing|zhangsan|the protagonist)',
        ],
        TargetType.PLOT: [
            r'剧情|情节|故事|发展|结局|转折',
            r'plot|storyline|development',
        ],
        TargetType.LORE: [
            r'设定|世界观|能力|规则|体系',
            r'setting|world building|power system',
        ],
        TargetType.PACING: [
            r'节奏|铺垫|进度|推进|快慢',
            r'pacing|pace',
        ]
    }
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    def _match_patterns(self, text: str, patterns: list[str]) -> tuple[bool, float]:
        """
        匹配模式
        
        Returns:
            (matched, intensity)
        """
        text_lower = text.lower()
        matches = 0
        
        for pattern in patterns:
            if re.search(pattern, text_lower):
                matches += 1
        
        if matches == 0:
            return False, 0.0
        
        # 强度基于匹配数量和文本长度
        intensity = min(1.0, matches / 3.0)
        return True, intensity
    
    def _detect_target(self, text: str) -> tuple[Optional[TargetType], Optional[int]]:
        """
        检测目标
        
        简化实现：只返回目标类型，ID 需要后续查询数据库
        """
        text_lower = text.lower()
        
        for target_type, patterns in self.TARGET_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return target_type, None
        
        return None, None
    
    def _detect_sentiment(self, text: str, signal_type: SignalType) -> str:
        """
        检测情绪
        """
        text_lower = text.lower()
        
        positive_words = ['好', '棒', '赞', '喜欢', '爱', '帅', '酷', '喜欢', 'love', 'good', 'great', 'awesome']
        negative_words = ['差', '烂', '崩', '无语', '糟糕', 'bad', 'terrible', 'awful']
        
        positive_count = sum(1 for w in positive_words if w in text_lower)
        negative_count = sum(1 for w in negative_words if w in text_lower)
        
        # 风险类通常是负面
        if signal_type == SignalType.RISK:
            return "negative"
        
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"
    
    def analyze_comment(self, comment: RawComment) -> list[CommentSignal]:
        """
        分析单条评论
        
        返回可能匹配的所有信号
        """
        signals = []
        text = comment.content
        
        # 1. Confusion 检测
        is_confusion, confusion_intensity = self._match_patterns(
            text, self.CONFUSION_PATTERNS
        )
        if is_confusion:
            target_type, target_id = self._detect_target(text)
            signals.append(CommentSignal(
                project_id=comment.project_id,
                source_comment_id=comment.id,
                signal_type=SignalType.CONFUSION.value,
                target_type=target_type.value if target_type else None,
                target_id=target_id,
                sentiment=self._detect_sentiment(text, SignalType.CONFUSION),
                intensity=confusion_intensity,
                confidence=min(0.8, confusion_intensity + 0.3),
                evidence_summary=f"困惑类评论，强度{confusion_intensity:.2f}",
                original_snippet=text[:200]
            ))
        
        # 2. Pacing 检测
        is_pacing, pacing_intensity = self._match_patterns(
            text, self.PACING_PATTERNS
        )
        if is_pacing:
            signals.append(CommentSignal(
                project_id=comment.project_id,
                source_comment_id=comment.id,
                signal_type=SignalType.PACING.value,
                target_type=TargetType.PACING.value,
                target_id=None,
                sentiment=self._detect_sentiment(text, SignalType.PACING),
                intensity=pacing_intensity,
                confidence=min(0.8, pacing_intensity + 0.3),
                evidence_summary=f"节奏类评论，强度{pacing_intensity:.2f}",
                original_snippet=text[:200]
            ))
        
        # 3. Character Heat 检测
        is_heat, heat_intensity = self._match_patterns(
            text, self.CHARACTER_HEAT_PATTERNS
        )
        if is_heat:
            target_type, target_id = self._detect_target(text)
            signals.append(CommentSignal(
                project_id=comment.project_id,
                source_comment_id=comment.id,
                signal_type=SignalType.CHARACTER_HEAT.value,
                target_type=target_type.value if target_type else TargetType.CHARACTER.value,
                target_id=target_id,
                sentiment="positive",
                intensity=heat_intensity,
                confidence=min(0.8, heat_intensity + 0.3),
                evidence_summary=f"角色热度评论，强度{heat_intensity:.2f}",
                original_snippet=text[:200]
            ))
        
        # 4. Risk 检测
        is_risk, risk_intensity = self._match_patterns(
            text, self.RISK_PATTERNS
        )
        if is_risk:
            target_type, target_id = self._detect_target(text)
            signals.append(CommentSignal(
                project_id=comment.project_id,
                source_comment_id=comment.id,
                signal_type=SignalType.RISK.value,
                target_type=target_type.value if target_type else TargetType.PLOT.value,
                target_id=target_id,
                sentiment="negative",
                intensity=risk_intensity,
                confidence=min(0.9, risk_intensity + 0.4),  # Risk 置信度稍高
                evidence_summary=f"风险类评论，强度{risk_intensity:.2f}",
                original_snippet=text[:200]
            ))
        
        return signals
    
    async def analyze_and_store(
        self, 
        comment: RawComment,
        use_llm: bool = False
    ) -> list[CommentSignal]:
        """
        分析评论并存储信号
        
        Args:
            comment: 原始评论
            use_llm: 是否使用 LLM 分析（更准确但更慢更贵）
        """
        if use_llm:
            # TODO: 使用 LLM 进行更准确的分析
            # 目前先用规则
            pass
        
        # 使用规则分析
        signals = self.analyze_comment(comment)
        
        # 存储信号
        for signal in signals:
            self.db.add(signal)
        
        # 标记评论已处理
        comment.processed = True
        
        await self.db.flush()
        
        return signals
    
    async def batch_analyze(
        self,
        comments: list[RawComment],
        use_llm: bool = False
    ) -> dict:
        """
        批量分析评论
        """
        total_signals = 0
        processed_comments = 0
        
        for comment in comments:
            signals = await self.analyze_and_store(comment, use_llm)
            total_signals += len(signals)
            processed_comments += 1
        
        await self.db.flush()
        
        return {
            "processed_comments": processed_comments,
            "generated_signals": total_signals,
            "avg_signals_per_comment": total_signals / processed_comments if processed_comments > 0 else 0
        }
