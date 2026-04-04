"""CommentAnalyzer - Phase A LLM 增强分析 (v2.6)

职责：
- 用 LLM 批量解析评论，替换简单的关键词匹配
- 提取结构化信号：signal_type, target_type, target_name, severity, confidence, evidence_span
- 硬规则分级：noise / candidate / confirmed / watchlist
- Fallback 到关键词匹配（LLM 失败时）

与现有 CommentAnalysisService 的区别：
- CommentAnalysisService: 关键词匹配，MVP 版本
- CommentAnalyzer: LLM 增强分析，Phase A 新增
"""
import json
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import (
    RawComment, CommentSignalCandidate,
    SignalType, TargetType
)
from app.services.audience.analysis import CommentAnalysisService
from app.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class CommentAnalyzer:
    """
    LLM 增强评论分析器 - Phase A
    
    核心流程：
    1. 批量收集未处理的评论
    2. 调用 LLM 解析（走 llm_client.chat → parse_llm_json 路径）
    3. Fallback 到关键词匹配（LLM 失败时）
    4. 存储 CommentSignalCandidate
    
    输出给 _load_reader_feedback 使用
    """
    
    # LLM prompt 配置
    SYSTEM_PROMPT = "你是网文评论分析器，只输出 JSON。"
    
    USER_PROMPT_TEMPLATE = """请分析以下读者评论，提取信号。一条评论可产出多个信号。

signal_type 只能是：confusion / pacing / character_heat / risk
- confusion: 读者表示困惑、不理解、疑问
- pacing: 读者反馈节奏问题（水、拖、慢）
- character_heat: 读者对某个角色的喜爱/关注
- risk: 读者反馈逻辑矛盾、人设崩塌等严重问题

target_type 只能是：character / arc / plot / setting
- character: 目标是人名/角色名
- arc: 目标是故事线/情节弧
- plot: 目标是具体剧情/事件
- setting: 目标是世界观/设定

target_name: 自由文本，描述具体目标，如 "主角动机"、"林黛玉与贾宝玉"、"大结局"

severity: 1~4，1最轻微，4最严重
- 1: 轻微吐槽
- 2: 一般反馈
- 3: 较严重问题
- 4: 严重问题，可能影响阅读

confidence: 0~1，LLM 对判断的置信度

evidence_span: 原文摘录，用于证据

返回格式：
{{"signals":[{{"comment_index":0,"signal_type":"confusion","target_type":"character","target_name":"主角动机","severity":2,"confidence":0.8,"evidence_span":"为什么主角要这样做？"}}]}}

评论列表：
{comments_json}"""

    def __init__(
        self,
        db: AsyncSession,
        llm_provider: Optional[LLMProvider] = None
    ):
        self.db = db
        self.llm = llm_provider
        # 复用现有的关键词分析器作为 fallback
        self._keyword_analyzer = CommentAnalysisService(db)

    async def analyze_batch(
        self,
        project_id: int,
        limit: int = 20
    ) -> dict:
        """
        批量分析评论
        
        Args:
            project_id: 项目 ID
            limit: 最多分析的评论数
            
        Returns:
            分析结果统计
        """
        # 1. 获取未处理的评论
        comments = await self._get_unprocessed_comments(project_id, limit)
        
        if not comments:
            return {
                "processed_comments": 0,
                "generated_signals": 0,
                "llm_success": True,
                "fallback_used": False
            }
        
        # 2. 尝试 LLM 分析
        llm_success = False
        fallback_used = False
        
        try:
            candidates = await self._analyze_comments_with_llm(comments)
            if candidates:
                # 存储 LLM 结果
                await self._store_candidates(candidates, is_llm=True)
                llm_success = True
            else:
                # LLM 返回空，使用 fallback
                candidates = await self._analyze_with_fallback(comments)
                fallback_used = True
        except Exception as e:
            logger.warning(f"LLM analysis failed, using fallback: {e}")
            candidates = await self._analyze_with_fallback(comments)
            fallback_used = True
        
        # 3. 标记评论已处理
        comment_ids = [c.id for c in comments]
        await self._mark_comments_processed(comment_ids)
        
        return {
            "processed_comments": len(comments),
            "generated_signals": len(candidates),
            "llm_success": llm_success,
            "fallback_used": fallback_used
        }

    async def analyze_single(
        self,
        comment: RawComment
    ) -> list[CommentSignalCandidate]:
        """
        分析单条评论
        
        Args:
            comment: 原始评论
            
        Returns:
            信号候选列表
        """
        # 尝试 LLM 分析
        try:
            candidates = await self._analyze_comments_with_llm([comment])
            if candidates:
                await self._store_candidates(candidates, is_llm=True)
                return candidates
        except Exception as e:
            logger.warning(f"LLM analysis failed for comment {comment.id}: {e}")
        
        # Fallback 到关键词匹配
        candidates = await self._analyze_with_fallback([comment])
        if candidates:
            await self._store_candidates(candidates, is_llm=False)
        return candidates

    async def _analyze_comments_with_llm(
        self,
        comments: list[RawComment]
    ) -> list[CommentSignalCandidate] | None:
        """
        用 LLM 批量解析评论
        
        模式跟现有 NPCIntentGenerator._generate_with_llm 完全一致：
        - 走 llm_client.chat → parse_llm_json 路径
        
        Returns:
            信号候选列表，失败返回 None
        """
        if not self.llm:
            logger.warning("No LLM provider available")
            return None
        
        # 构造 prompt
        comments_data = [
            {
                "index": i,
                "content": c.content,
                "chapter_id": c.chapter_id,
                "user_hash": c.user_hash
            }
            for i, c in enumerate(comments)
        ]
        
        user_prompt = self.USER_PROMPT_TEMPLATE.format(
            comments_json=json.dumps(comments_data, ensure_ascii=False)
        )
        
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
        
        # 调用 LLM
        try:
            response = await self.llm.chat(messages)
            
            # 解析 JSON 响应
            content = response.content.strip()
            # 尝试提取 JSON（可能有 markdown 包装）
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            
            result = json.loads(content.strip())
            signals = result.get("signals", [])
            
            if not signals:
                return None
            
            # 构建 CommentSignalCandidate
            candidates = []
            for sig in signals:
                comment_index = sig.get("comment_index", 0)
                if comment_index >= len(comments):
                    continue
                    
                comment = comments[comment_index]
                
                # 硬规则分级
                signal_level = self.classify_signal_level(
                    unique_users=1,  # 单条评论默认 1
                    spans_chapters=1,  # 单条评论默认 1
                    severity=sig.get("severity", 1),
                    signal_type=sig.get("signal_type", "confusion")
                )
                
                candidate = CommentSignalCandidate(
                    project_id=comment.project_id,
                    source_comment_id=comment.id,
                    signal_type=sig.get("signal_type", "confusion"),
                    target_type=sig.get("target_type", "plot"),
                    target_name=sig.get("target_name", ""),
                    severity=sig.get("severity", 1),
                    confidence=sig.get("confidence", 0.5),
                    evidence_span=sig.get("evidence_span", ""),
                    signal_level=signal_level,
                    is_llm_generated=True,
                    is_fallback=False
                )
                candidates.append(candidate)
            
            return candidates
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return None

    async def _analyze_with_fallback(
        self,
        comments: list[RawComment]
    ) -> list[CommentSignalCandidate]:
        """
        使用关键词匹配作为 fallback
        
        复用 CommentAnalysisService 的逻辑
        """
        candidates = []
        
        for comment in comments:
            # 使用关键词分析器
            signals = self._keyword_analyzer.analyze_comment(comment)
            
            for sig in signals:
                # 转换为 CommentSignalCandidate
                candidate = CommentSignalCandidate(
                    project_id=comment.project_id,
                    source_comment_id=comment.id,
                    signal_type=sig.signal_type,
                    target_type=sig.target_type,
                    target_name="",  # 关键词分析没有 target_name
                    severity=int(sig.intensity * 4) or 1,  # 0.0-1.0 -> 1-4
                    confidence=sig.confidence,
                    evidence_span=sig.original_snippet or "",
                    signal_level=self.classify_signal_level(
                        unique_users=1,
                        spans_chapters=1,
                        severity=int(sig.intensity * 4) or 1,
                        signal_type=sig.signal_type
                    ),
                    is_llm_generated=False,
                    is_fallback=True
                )
                candidates.append(candidate)
        
        return candidates

    @staticmethod
    def classify_signal_level(
        unique_users: int,
        spans_chapters: int,
        severity: int,
        signal_type: str,
    ) -> str:
        """
        硬规则分级，不用加权公式
        
        4 个 if，没有超参数：
        - risk 特殊通道：severity >= 3 时进入 watchlist/confirmed
        - unique_users < 2：noise
        - spans_chapters < 2 且 character_heat：noise
        - unique_users >= 3 且 spans_chapters >= 2：confirmed
        - 其他：candidate
        
        Args:
            unique_users: 涉及的去重用户数
            spans_chapters: 涉及的章节数
            severity: 严重程度 1~4
            signal_type: 信号类型
            
        Returns:
            signal_level: noise / candidate / confirmed / watchlist
        """
        # risk 特殊通道
        if signal_type == "risk":
            if severity >= 3:
                return "watchlist" if unique_users < 2 else "confirmed"
            elif severity >= 2 and unique_users >= 2:
                return "confirmed"
            else:
                return "candidate"
        
        # 通用规则
        if unique_users < 2:
            return "noise"
        
        if spans_chapters < 2 and signal_type in ("character_heat",):
            return "noise"
        
        if unique_users >= 3 and spans_chapters >= 2:
            return "confirmed"
        
        return "candidate"

    async def _get_unprocessed_comments(
        self,
        project_id: int,
        limit: int
    ) -> list[RawComment]:
        """获取未处理的评论"""
        result = await self.db.execute(
            select(RawComment)
            .where(
                and_(
                    RawComment.project_id == project_id,
                    RawComment.processed == False
                )
            )
            .order_by(RawComment.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def _store_candidates(
        self,
        candidates: list[CommentSignalCandidate],
        is_llm: bool
    ) -> int:
        """存储信号候选"""
        for candidate in candidates:
            self.db.add(candidate)
        
        await self.db.flush()
        return len(candidates)

    async def _mark_comments_processed(self, comment_ids: list[int]) -> int:
        """标记评论已处理"""
        from sqlalchemy import update
        
        stmt = (
            update(RawComment)
            .where(RawComment.id.in_(comment_ids))
            .values(processed=True, processed_at=datetime.now())
        )
        
        result = await self.db.execute(stmt)
        await self.db.flush()
        
        return result.rowcount

    async def recalculate_signal_levels(
        self,
        project_id: int,
        signal_key: Optional[str] = None
    ) -> int:
        """
        重新计算信号级别
        
        当有更多评论数据时，可以重新计算信号级别
        用于后续窗口聚合后更新级别
        
        Args:
            project_id: 项目 ID
            signal_key: 可选，只更新特定信号
            
        Returns:
            更新的数量
        """
        # 获取所有候选信号
        query = select(CommentSignalCandidate).where(
            CommentSignalCandidate.project_id == project_id
        )
        
        if signal_key:
            # signal_key 格式: "signal_type:target_type:target_name"
            parts = signal_key.split(":")
            if len(parts) >= 1:
                query = query.where(
                    CommentSignalCandidate.signal_type == parts[0]
                )
            if len(parts) >= 2:
                query = query.where(
                    CommentSignalCandidate.target_type == parts[1]
                )
        
        result = await self.db.execute(query)
        candidates = list(result.scalars().all())
        
        # 按 (signal_type, target_type, target_name) 分组
        groups: dict[tuple, dict] = {}
        for c in candidates:
            key = (c.signal_type, c.target_type, c.target_name)
            if key not in groups:
                groups[key] = {
                    "unique_users": set(),
                    "chapters": set(),
                    "max_severity": 0,
                    "candidates": []
                }
            
            # 获取评论的用户和章节信息
            comment = await self.db.get(RawComment, c.source_comment_id)
            if comment:
                groups[key]["unique_users"].add(comment.user_hash)
                if comment.chapter_id:
                    groups[key]["chapters"].add(comment.chapter_id)
            
            groups[key]["max_severity"] = max(
                groups[key]["max_severity"], c.severity
            )
            groups[key]["candidates"].append(c)
        
        # 重新计算每个组的信号级别
        updated = 0
        for key, group in groups.items():
            new_level = self.classify_signal_level(
                unique_users=len(group["unique_users"]),
                spans_chapters=len(group["chapters"]),
                severity=group["max_severity"],
                signal_type=key[0]
            )
            
            for c in group["candidates"]:
                if c.signal_level != new_level:
                    c.signal_level = new_level
                    updated += 1
        
        await self.db.flush()
        return updated


# ========================================
# ReaderFeedbackView - Phase A 扩展
# ========================================

class ReaderFeedbackView:
    """
    读者反馈视图 - Phase A 扩展
    
    提供给 Writer 的结构化反馈视图
    包含：
    - dominant_sentiment: 综合情感
    - feedback_summary: 反馈摘要
    - highlighted_topics: 高亮话题 (格式: "target_name:signal_type:level")
    - recent_highlights: 最近高亮评论
    - confirmed_signals: 确认的信号 (Phase B 扩展)
    - reader_tier: 读者规模等级 (Phase B 扩展)
    
    示例:
        dominant_sentiment = "risk:confirmed"
        highlighted_topics = [
            "主角动机:confusion:candidate",
            "节奏:pacing:confirmed"
        ]
    """
    
    def __init__(
        self,
        comment_count: int = 0,
        dominant_sentiment: str = "neutral",
        feedback_summary: str = "",
        highlighted_topics: Optional[list[str]] = None,
        recent_highlights: Optional[list[dict]] = None,
        confirmed_signals: Optional[list[dict]] = None,
        reader_tier: int = 0
    ):
        self.comment_count = comment_count
        self.dominant_sentiment = dominant_sentiment
        self.feedback_summary = feedback_summary
        self.highlighted_topics = highlighted_topics or []
        self.recent_highlights = recent_highlights or []
        self.confirmed_signals = confirmed_signals or []
        self.reader_tier = reader_tier
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "comment_count": self.comment_count,
            "dominant_sentiment": self.dominant_sentiment,
            "feedback_summary": self.feedback_summary,
            "highlighted_topics": self.highlighted_topics,
            "recent_highlights": self.recent_highlights,
            "confirmed_signals": self.confirmed_signals,
            "reader_tier": self.reader_tier
        }
    
    @classmethod
    async def from_candidates(
        cls,
        db: AsyncSession,
        project_id: int,
        chapter_number: Optional[int] = None,
        limit: int = 20
    ) -> "ReaderFeedbackView":
        """
        从 CommentSignalCandidate 构建 ReaderFeedbackView
        
        Args:
            db: 数据库会话
            project_id: 项目 ID
            chapter_number: 可选，限定章节范围
            limit: 最多返回的高亮数
            
        Returns:
            ReaderFeedbackView 实例
        """
        # 查询候选信号
        query = select(CommentSignalCandidate).where(
            CommentSignalCandidate.project_id == project_id
        )
        
        if chapter_number:
            # 关联评论的章节
            query = query.join(
                RawComment,
                CommentSignalCandidate.source_comment_id == RawComment.id
            ).where(
                RawComment.chapter_id <= chapter_number
            )
        
        query = query.order_by(
            CommentSignalCandidate.created_at.desc()
        ).limit(limit * 2)  # 多查一些以便过滤
        
        result = await db.execute(query)
        candidates = list(result.scalars().all())
        
        # 查询评论数量
        count_result = await db.execute(
            select(func.count(RawComment.id)).where(
                RawComment.project_id == project_id
            )
        )
        comment_count = count_result.scalar() or 0
        
        # 统计各信号级别
        level_counts: dict[str, int] = {}
        topic_signals: dict[str, dict] = {}
        
        for c in candidates:
            # 级别统计
            level = c.signal_level
            level_counts[level] = level_counts.get(level, 0) + 1
            
            # 话题信号
            key = f"{c.target_name or 'unknown'}:{c.signal_type}:{c.signal_level}"
            if key not in topic_signals:
                topic_signals[key] = {
                    "signal_type": c.signal_type,
                    "target_name": c.target_name,
                    "level": c.signal_level,
                    "severity": c.severity,
                    "confidence": c.confidence,
                    "count": 0
                }
            topic_signals[key]["count"] += 1
        
        # 确定主导情感
        dominant_sentiment = "neutral"
        if level_counts.get("watchlist", 0) > 0:
            dominant_sentiment = "risk:watchlist"
        elif level_counts.get("confirmed", 0) > level_counts.get("candidate", 0):
            dominant_sentiment = "negative:confirmed"
        elif level_counts.get("candidate", 0) > 0:
            dominant_sentiment = "mixed:candidate"
        
        # 构建 highlighted_topics（只包含 candidate 及以上）
        highlighted_topics = []
        for key, info in topic_signals.items():
            if info["level"] in ("candidate", "confirmed", "watchlist"):
                highlighted_topics.append(key)
        
        # 排序：watchlist > confirmed > candidate
        def topic_sort_key(t: str) -> tuple[int, int]:
            parts = t.split(":")
            level = parts[-1] if len(parts) >= 3 else "noise"
            level_order = {"watchlist": 0, "confirmed": 1, "candidate": 2, "noise": 3}
            return (level_order.get(level, 3), -topic_signals[t].get("count", 0))
        
        highlighted_topics.sort(key=topic_sort_key)
        highlighted_topics = highlighted_topics[:limit]
        
        # 生成反馈摘要
        feedback_summary = cls._generate_summary(level_counts, topic_signals)
        
        # 获取最近高亮评论
        recent_highlights = []
        for c in candidates[:limit]:
            if c.signal_level in ("candidate", "confirmed", "watchlist"):
                recent_highlights.append({
                    "signal_type": c.signal_type,
                    "target_name": c.target_name,
                    "evidence_span": c.evidence_span,
                    "severity": c.severity,
                    "level": c.signal_level
                })
        
        return cls(
            comment_count=comment_count,
            dominant_sentiment=dominant_sentiment,
            feedback_summary=feedback_summary,
            highlighted_topics=highlighted_topics,
            recent_highlights=recent_highlights
        )
    
    @staticmethod
    def _generate_summary(
        level_counts: dict[str, int],
        topic_signals: dict[str, dict]
    ) -> str:
        """生成反馈摘要"""
        confirmed = level_counts.get("confirmed", 0)
        candidate = level_counts.get("candidate", 0)
        watchlist = level_counts.get("watchlist", 0)
        noise = level_counts.get("noise", 0)
        
        parts = []
        if watchlist > 0:
            parts.append(f"{watchlist}个高优先级问题需处理")
        if confirmed > 0:
            parts.append(f"{confirmed}个确认反馈")
        if candidate > 0:
            parts.append(f"{candidate}个待确认信号")
        
        if not parts:
            return "暂无明显反馈"
        
        # 找出最严重的信号类型
        risk_count = sum(1 for k in topic_signals if "risk" in k)
        pacing_count = sum(1 for k in topic_signals if "pacing" in k)
        confusion_count = sum(1 for k in topic_signals if "confusion" in k)
        
        if risk_count > 0:
            parts.append("风险类问题最受关注")
        elif pacing_count > 0:
            parts.append("节奏类反馈较多")
        elif confusion_count > 0:
            parts.append("困惑类反馈较多")
        
        return "，".join(parts)
