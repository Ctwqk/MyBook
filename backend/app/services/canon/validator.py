"""CanonValidator - Canon 验证器

验证世界状态的一致性和完整性
"""
from dataclasses import dataclass
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.world_nodes import WorldNode, WorldNodeType
from app.models.world_edges import WorldEdge, EdgeType
from app.models.graph_deltas import GraphDelta


@dataclass
class ValidationResult:
    """验证结果"""
    valid: bool
    errors: list[str]
    warnings: list[str]
    info: list[str]


class CanonValidator:
    """
    Canon 验证器
    
    验证世界状态的一致性：
    1. 节点完整性
    2. 边一致性
    3. 角色状态有效性
    4. Arc 引用有效性
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def validate_project(self, project_id: int) -> ValidationResult:
        """验证项目的 Canon 状态"""
        errors = []
        warnings = []
        info = []
        
        # 1. 检查孤立节点
        orphan_nodes = await self._find_orphan_nodes(project_id)
        if orphan_nodes:
            warnings.append(f"Found {len(orphan_nodes)} orphan nodes")
        
        # 2. 检查无效引用
        invalid_refs = await self._find_invalid_references(project_id)
        if invalid_refs:
            errors.extend([f"Invalid reference: {ref}" for ref in invalid_refs])
        
        # 3. 检查冲突边
        conflicts = await self._find_edge_conflicts(project_id)
        if conflicts:
            warnings.append(f"Found {len(conflicts)} edge conflicts")
        
        # 4. 检查状态一致性
        state_issues = await self._check_state_consistency(project_id)
        if state_issues:
            errors.extend(state_issues)
        
        # 5. 检查必填字段
        missing_fields = await self._check_required_fields(project_id)
        if missing_fields:
            warnings.extend([f"Missing required field: {f}" for f in missing_fields])
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            info=info
        )
    
    async def validate_delta(self, delta_id: int) -> ValidationResult:
        """验证单个 Delta"""
        result = await self.db.execute(
            select(GraphDelta).where(GraphDelta.id == delta_id)
        )
        delta = result.scalar_one_or_none()
        
        if not delta:
            return ValidationResult(
                valid=False,
                errors=[f"Delta {delta_id} not found"],
                warnings=[],
                info=[]
            )
        
        errors = []
        warnings = []
        
        # 检查 delta 内容的有效性
        if not delta.summary:
            warnings.append("Delta has no summary")
        
        if not delta.chapter_number:
            warnings.append("Delta has no chapter number")
        
        # TODO: 检查 content_json 的有效性
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            info=[f"Delta from {delta.source_type.value} at chapter {delta.chapter_number}"]
        )
    
    async def validate_character_arc(
        self,
        character_id: int,
        chapter_start: int,
        chapter_end: int
    ) -> ValidationResult:
        """验证角色 Arc 的连贯性"""
        errors = []
        warnings = []
        info = []
        
        # 获取角色节点
        result = await self.db.execute(
            select(WorldNode).where(
                WorldNode.id == character_id,
                WorldNode.node_type == WorldNodeType.CHARACTER
            )
        )
        character = result.scalar_one_or_none()
        
        if not character:
            return ValidationResult(
                valid=False,
                errors=[f"Character {character_id} not found"],
                warnings=[],
                info=[]
            )
        
        # 获取角色在章节范围内的状态变化
        # TODO: 实现状态变化分析
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            info=info
        )
    
    async def _find_orphan_nodes(self, project_id: int) -> list[int]:
        """查找没有连接的孤立节点"""
        # 查找所有节点
        nodes_result = await self.db.execute(
            select(WorldNode.id).where(WorldNode.project_id == project_id)
        )
        all_nodes = set(nodes_result.scalars().all())
        
        # 查找所有作为 source 或 target 的节点
        edges_result = await self.db.execute(
            select(WorldEdge.source_id, WorldEdge.target_id)
            .where(WorldEdge.project_id == project_id)
        )
        connected_nodes = set()
        for source_id, target_id in edges_result.all():
            connected_nodes.add(source_id)
            connected_nodes.add(target_id)
        
        return list(all_nodes - connected_nodes)
    
    async def _find_invalid_references(self, project_id: int) -> list[str]:
        """查找无效引用"""
        invalid = []
        
        # 检查边的 source/target 是否有效
        edges_result = await self.db.execute(
            select(WorldEdge).where(WorldEdge.project_id == project_id)
        )
        for edge in edges_result.scalars():
            nodes_result = await self.db.execute(
                select(WorldNode.id).where(WorldNode.id.in_([edge.source_id, edge.target_id]))
            )
            valid_ids = set(nodes_result.scalars().all())
            
            if edge.source_id not in valid_ids:
                invalid.append(f"Edge {edge.id}: invalid source_id {edge.source_id}")
            if edge.target_id not in valid_ids:
                invalid.append(f"Edge {edge.id}: invalid target_id {edge.target_id}")
        
        return invalid
    
    async def _find_edge_conflicts(self, project_id: int) -> list[str]:
        """查找边冲突（如重复边）"""
        conflicts = []
        
        # 查找相同起点和终点的多条边
        from sqlalchemy import func
        
        result = await self.db.execute(
            select(
                WorldEdge.from_node_id,
                WorldEdge.to_node_id,
                func.count(WorldEdge.id).label('count')
            )
            .where(WorldEdge.project_id == project_id)
            .group_by(WorldEdge.from_node_id, WorldEdge.to_node_id)
            .having(func.count(WorldEdge.id) > 1)
        )
        
        for from_id, to_id, count in result.all():
            conflicts.append(f"Multiple edges between {from_id} and {to_id}: {count}")
        
        return conflicts
    
    async def _check_state_consistency(self, project_id: int) -> list[str]:
        """检查状态一致性"""
        issues = []
        
        # 检查角色状态的有效性
        result = await self.db.execute(
            select(WorldNode).where(
                WorldNode.project_id == project_id,
                WorldNode.node_type == WorldNodeType.CHARACTER
            )
        )
        
        for character in result.scalars():
            if character.state_json:
                state = character.state_json
                
                # 检查必填状态字段
                if "health" in state and (not isinstance(state["health"], (int, float)) or state["health"] < 0):
                    issues.append(f"Character {character.id}: invalid health value")
                
                if "alive" in state and not isinstance(state["alive"], bool):
                    issues.append(f"Character {character.id}: alive must be boolean")
        
        return issues
    
    async def _check_required_fields(self, project_id: int) -> list[str]:
        """检查必填字段"""
        missing = []
        
        result = await self.db.execute(
            select(WorldNode).where(WorldNode.project_id == project_id)
        )
        
        for node in result.scalars():
            if not node.name:
                missing.append(f"Node {node.id}: missing name")
            if not node.node_type:
                missing.append(f"Node {node.id}: missing node_type")
        
        return missing
