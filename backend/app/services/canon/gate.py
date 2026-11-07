"""ReviewGate - 审查门控

基于设计文档的 Canon 提交路径 Gate 设计
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.graph_deltas import GraphDelta, SourceType


class GateDecision(str, Enum):
    """Gate 决策"""
    APPROVED = "approved"           # 直接通过
    NEEDS_REVIEW = "needs_review"   # 需要审阅
    REJECTED = "rejected"           # 拒绝
    CONDITIONAL = "conditional"     # 有条件通过


@dataclass
class GateContext:
    """Gate 上下文"""
    project_id: int
    chapter_number: Optional[int]
    source_type: SourceType
    source_id: Optional[str]
    node_count: int
    edge_count: int
    has_conflicts: bool
    risk_score: float  # 0-10


@dataclass
class GateResult:
    """Gate 结果"""
    decision: GateDecision
    reason: str
    conditions: list[str] = None
    requires_approvals: list[str] = None  # 需要哪些人审批


class ReviewGate:
    """
    Canon 提交审查门控
    
    根据变更的来源、规模、风险决定是否需要人工审查
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def evaluate(self, context: GateContext) -> GateResult:
        """
        评估是否通过 Gate
        
        决策规则：
        1. 高风险变更（risk_score > 7）-> REJECTED
        2. 手动编辑 -> NEEDS_REVIEW
        3. 重大变更（节点数 > 10 或边数 > 20）-> NEEDS_REVIEW
        4. 有冲突 -> NEEDS_REVIEW
        5. Writer/Reviewer 小规模变更 -> APPROVED
        6. ArcPlanner -> CONDITIONAL
        """
        # 1. 风险评估
        if context.risk_score > 7:
            return GateResult(
                decision=GateDecision.REJECTED,
                reason=f"High risk score: {context.risk_score}",
                conditions=[f"Reduce risk score to < 7 before submission"]
            )
        
        # 2. 冲突检查
        if context.has_conflicts:
            return GateResult(
                decision=GateDecision.NEEDS_REVIEW,
                reason="Changes contain conflicts that require resolution",
                requires_approvals=["conflict_resolver"]
            )
        
        # 3. 来源类型判断
        if context.source_type == SourceType.MANUAL:
            return GateResult(
                decision=GateDecision.NEEDS_REVIEW,
                reason="Manual edits require review",
                requires_approvals=["editor"]
            )
        
        if context.source_type == SourceType.ARC_PLANNER:
            # Arc 变更需要验证
            arc_valid = await self._validate_arc_change(context)
            if not arc_valid:
                return GateResult(
                    decision=GateDecision.NEEDS_REVIEW,
                    reason="Arc planning changes need validation",
                    requires_approvals=["arc_planner_reviewer"]
                )
            return GateResult(
                decision=GateDecision.CONDITIONAL,
                reason="Arc changes approved with conditions",
                conditions=["Changes must align with established arcs"]
            )
        
        # 4. 规模判断
        if context.node_count > 10 or context.edge_count > 20:
            return GateResult(
                decision=GateDecision.NEEDS_REVIEW,
                reason=f"Large change: {context.node_count} nodes, {context.edge_count} edges",
                requires_approvals=["senior_editor"]
            )
        
        # 5. Writer/Reviewer 小规模变更
        if context.source_type in (SourceType.WRITER, SourceType.REVIEWER):
            if context.risk_score > 5:
                return GateResult(
                    decision=GateDecision.NEEDS_REVIEW,
                    reason=f"Moderate risk writer/reviewer change: {context.risk_score}",
                    requires_approvals=["editor"]
                )
            return GateResult(
                decision=GateDecision.APPROVED,
                reason="Small-scale writer/reviewer change approved"
            )
        
        # 6. Import
        if context.source_type == SourceType.IMPORT:
            return GateResult(
                decision=GateDecision.NEEDS_REVIEW,
                reason="Imported changes require validation",
                requires_approvals=["import_validator"]
            )
        
        # 默认需要审阅
        return GateResult(
            decision=GateDecision.NEEDS_REVIEW,
            reason="Default review required"
        )
    
    async def _validate_arc_change(self, context: GateContext) -> bool:
        """验证 Arc 变更是否符合规范"""
        # TODO: 集成 ArcEnvelope 验证
        return True
    
    async def get_approval_requirements(self, source_type: SourceType) -> list[str]:
        """获取特定来源类型的审批要求"""
        requirements = {
            SourceType.WRITER: [],
            SourceType.REVIEWER: [],
            SourceType.ARC_PLANNER: ["arc_planner_reviewer"],
            SourceType.MANUAL: ["editor"],
            SourceType.IMPORT: ["import_validator"],
            SourceType.REVERT: ["editor", "senior_editor"]
        }
        return requirements.get(source_type, ["senior_editor"])
    
    async def check_permissions(
        self,
        user_id: int,
        source_type: SourceType,
        decision: GateDecision
    ) -> bool:
        """
        检查用户是否有权限执行该决策
        
        TODO: 集成用户权限系统
        """
        # TODO: 实现权限检查
        return True
