"""Audience Feedback Services - v2.6 Phase A

包含：
- CommentIngestionService: 评论摄入
- CommentAnalysisService: 评论基础分析（关键词匹配）
- CommentAnalyzer: LLM 增强分析 + 硬规则分级（Phase A 新增）
- FeedbackAggregatorService: 反馈聚合
- ActionMapperService: 动作映射
"""
from app.services.audience.ingestion import CommentIngestionService
from app.services.audience.analysis import CommentAnalysisService
from app.services.audience.analyzer import CommentAnalyzer
from app.services.audience.aggregator import FeedbackAggregatorService
from app.services.audience.action_mapper import ActionMapperService

__all__ = [
    "CommentIngestionService",
    "CommentAnalysisService",
    "CommentAnalyzer",
    "FeedbackAggregatorService",
    "ActionMapperService",
]
