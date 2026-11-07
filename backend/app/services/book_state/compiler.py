"""GraphDeltaCompiler - 增量编译器

职责：
- 应用 patch 到 world_nodes / world_edges
- 检测冲突（old_value 校验）
- 生成 committed GraphDelta
"""
from typing import Optional, Any
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.models.world_nodes import WorldNode, WorldNodeType
from app.models.world_edges import WorldEdge, EdgeType, EdgeFamily
from app.models.graph_deltas import GraphDelta, DeltaType, SourceType, NodePatchOp, EdgePatchOp
from app.services.book_state.repository import BookStateRepository


@dataclass
class PatchResult:
    """Patch 执行结果"""
    success: bool
    patch_index: int
    patch: dict
    error: Optional[str] = None
    applied: bool = False


@dataclass
class CompileResult:
    """编译结果"""
    success: bool
    delta: Optional[GraphDelta]
    patch_results: list[PatchResult]
    errors: list[str]
    
    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0


class GraphDeltaCompiler:
    """GraphDelta 编译器"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = BookStateRepository(db)
    
    async def compile(
        self,
        project_id: int,
        chapter_number: Optional[int],
        node_patches: list[dict],
        edge_patches: list[dict],
        source_type: SourceType = SourceType.WRITER,
        source_id: Optional[str] = None,
        summary: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> CompileResult:
        """
        编译 patches 并生成 GraphDelta
        
        Args:
            project_id: 项目ID
            chapter_number: 章节号
            node_patches: 节点 patches
            edge_patches: 边 patches
            source_type: 来源类型
            source_id: 来源ID
            summary: 变更摘要
            metadata: 额外元数据
        
        Returns:
            CompileResult: 编译结果
        """
        patch_results: list[PatchResult] = []
        errors: list[str] = []
        
        # 1. 验证和准备 patches
        validated_node_patches = []
        validated_edge_patches = []
        
        for i, patch in enumerate(node_patches):
            result = await self._validate_node_patch(patch, project_id)
            result.patch_index = i
            patch_results.append(result)
            if result.success:
                validated_node_patches.append(result.patch)
            else:
                errors.append(f"Node patch {i}: {result.error}")
        
        for i, patch in enumerate(edge_patches):
            result = await self._validate_edge_patch(patch, project_id)
            result.patch_index = len(node_patches) + i
            patch_results.append(result)
            if result.success:
                validated_edge_patches.append(result.patch)
            else:
                errors.append(f"Edge patch {i}: {result.error}")
        
        # 2. 如果有错误但可以容忍（warning），仍然允许继续
        # 如果有致命错误（critical），阻止提交
        critical_errors = [e for e in errors if "CRITICAL" in e.upper() or "BLOCK" in e.upper()]
        if critical_errors:
            return CompileResult(
                success=False,
                delta=None,
                patch_results=patch_results,
                errors=critical_errors
            )
        
        # 3. 创建 GraphDelta
        delta = GraphDelta(
            project_id=project_id,
            chapter_number=chapter_number,
            delta_type=DeltaType.WORLD_STATE,
            source_type=source_type,
            source_id=source_id,
            summary=summary or self._generate_summary(node_patches, edge_patches),
            node_patches=validated_node_patches,
            edge_patches=validated_edge_patches,
            metadata_json=metadata,
            is_committed=True  # 直接提交（后续可加入 ReviewGate）
        )
        
        await self.repo.create_delta(delta)
        
        # 4. 应用 patches
        for patch_result in patch_results:
            if patch_result.success and patch_result.applied:
                continue  # 已经应用
            
            if patch_result.patch.get("patch_type") == "node":
                await self._apply_node_patch(patch_result.patch)
            elif patch_result.patch.get("patch_type") == "edge":
                await self._apply_edge_patch(patch_result.patch)
        
        return CompileResult(
            success=True,
            delta=delta,
            patch_results=patch_results,
            errors=errors
        )
    
    async def _validate_node_patch(self, patch: dict, project_id: int) -> PatchResult:
        """验证节点 patch"""
        op = patch.get("op")
        node_id = patch.get("node_id")
        node_type = patch.get("node_type")
        field_path = patch.get("field_path")
        new_value = patch.get("new_value")
        old_value = patch.get("old_value")
        
        try:
            op_enum = NodePatchOp(op)
        except ValueError:
            return PatchResult(
                success=False,
                patch_index=0,
                patch=patch,
                error=f"Unknown op: {op}"
            )
        
        # CREATE 操作验证
        if op_enum == NodePatchOp.CREATE:
            if not node_type:
                return PatchResult(
                    success=False,
                    patch_index=0,
                    patch=patch,
                    error="CREATE requires node_type"
                )
            try:
                WorldNodeType(node_type)
            except ValueError:
                return PatchResult(
                    success=False,
                    patch_index=0,
                    patch=patch,
                    error=f"Unknown node_type: {node_type}"
                )
            
            patch["patch_type"] = "node"
            patch["applied"] = True
            return PatchResult(success=True, patch_index=0, patch=patch, applied=True)
        
        # 其他操作需要 node_id
        if not node_id:
            return PatchResult(
                success=False,
                patch_index=0,
                patch=patch,
                error="Operation requires node_id"
            )
        
        # 验证 node 存在
        node = await self.repo.get_node(node_id)
        if not node:
            return PatchResult(
                success=False,
                patch_index=0,
                patch=patch,
                error=f"Node {node_id} not found"
            )
        
        # 验证 project 匹配
        if node.project_id != project_id:
            return PatchResult(
                success=False,
                patch_index=0,
                patch=patch,
                error=f"Node {node_id} belongs to different project"
            )
        
        # 验证 old_value 匹配（用于 SET/MERGE/REPLACE 操作）
        if old_value is not None and field_path:
            current_value = self._get_nested_field(node, field_path)
            if current_value != old_value:
                return PatchResult(
                    success=False,
                    patch_index=0,
                    patch=patch,
                    error=f"old_value mismatch: expected {old_value}, got {current_value}"
                )
        
        patch["patch_type"] = "node"
        patch["applied"] = True
        return PatchResult(success=True, patch_index=0, patch=patch, applied=True)
    
    async def _validate_edge_patch(self, patch: dict, project_id: int) -> PatchResult:
        """验证边 patch"""
        op = patch.get("op")
        edge_id = patch.get("edge_id")
        source_id = patch.get("source_id")
        target_id = patch.get("target_id")
        edge_type = patch.get("edge_type")
        
        try:
            op_enum = EdgePatchOp(op)
        except ValueError:
            return PatchResult(
                success=False,
                patch_index=0,
                patch=patch,
                error=f"Unknown edge op: {op}"
            )
        
        # CREATE 操作验证
        if op_enum == EdgePatchOp.CREATE:
            if not all([source_id, target_id, edge_type]):
                return PatchResult(
                    success=False,
                    patch_index=0,
                    patch=patch,
                    error="CREATE requires source_id, target_id, edge_type"
                )
            
            # 验证 edge_type
            try:
                EdgeType(edge_type)
            except ValueError:
                return PatchResult(
                    success=False,
                    patch_index=0,
                    patch=patch,
                    error=f"Unknown edge_type: {edge_type}"
                )
            
            # 验证 source 和 target 存在
            source = await self.repo.get_node(source_id)
            target = await self.repo.get_node(target_id)
            if not source or not target:
                return PatchResult(
                    success=False,
                    patch_index=0,
                    patch=patch,
                    error="Source or target node not found"
                )
            
            patch["patch_type"] = "edge"
            patch["applied"] = True
            return PatchResult(success=True, patch_index=0, patch=patch, applied=True)
        
        # 其他操作需要 edge_id
        if not edge_id:
            return PatchResult(
                success=False,
                patch_index=0,
                patch=patch,
                error="Operation requires edge_id"
            )
        
        # 验证 edge 存在
        edge = await self.repo.get_edge(edge_id)
        if not edge:
            return PatchResult(
                success=False,
                patch_index=0,
                patch=patch,
                error=f"Edge {edge_id} not found"
            )
        
        patch["patch_type"] = "edge"
        patch["applied"] = True
        return PatchResult(success=True, patch_index=0, patch=patch, applied=True)
    
    async def _apply_node_patch(self, patch: dict) -> None:
        """应用节点 patch"""
        op = patch.get("op")
        node_id = patch.get("node_id")
        node_type = patch.get("node_type")
        name = patch.get("name")
        field_path = patch.get("field_path")
        new_value = patch.get("new_value")
        
        if op == NodePatchOp.CREATE.value:
            node = WorldNode(
                project_id=patch.get("project_id"),
                node_type=WorldNodeType(node_type),
                name=name,
                description=patch.get("description"),
                profile_json=patch.get("profile_json"),
                state_json=patch.get("state_json"),
                created_at_chapter=patch.get("created_at_chapter")
            )
            await self.repo.create_node(node)
        else:
            node = await self.repo.get_node(node_id)
            if not node:
                return
            
            if op == NodePatchOp.SET.value and field_path:
                self._set_nested_field(node, field_path, new_value)
            elif op == NodePatchOp.MERGE.value and field_path:
                current = self._get_nested_field(node, field_path) or {}
                if isinstance(current, dict):
                    current.update(new_value)
                    self._set_nested_field(node, field_path, current)
            elif op == NodePatchOp.DEACTIVATE.value:
                node.is_active = False
                if patch.get("retired_at_chapter"):
                    node.retired_at_chapter = patch.get("retired_at_chapter")
            
            await self.repo.update_node(node)
    
    async def _apply_edge_patch(self, patch: dict) -> None:
        """应用边 patch"""
        op = patch.get("op")
        edge_id = patch.get("edge_id")
        source_id = patch.get("source_id")
        target_id = patch.get("target_id")
        edge_type = patch.get("edge_type")
        
        if op == EdgePatchOp.CREATE.value:
            edge = WorldEdge(
                project_id=patch.get("project_id"),
                source_id=source_id,
                target_id=target_id,
                edge_type=EdgeType(edge_type),
                edge_family=self._infer_edge_family(EdgeType(edge_type)),
                weight=patch.get("weight", 1.0),
                confidence=patch.get("confidence", 1.0),
                established_at_chapter=patch.get("established_at_chapter")
            )
            await self.repo.create_edge(edge)
        else:
            edge = await self.repo.get_edge(edge_id)
            if not edge:
                return
            
            if op == EdgePatchOp.SET.value:
                for key in ["weight", "confidence", "state"]:
                    if key in patch:
                        setattr(edge, key, patch[key])
            elif op == EdgePatchOp.DEACTIVATE.value:
                edge.is_active = False
                if patch.get("ended_at_chapter"):
                    edge.ended_at_chapter = patch.get("ended_at_chapter")
            
            await self.repo.update_edge(edge)
    
    def _get_nested_field(self, obj: Any, field_path: str) -> Any:
        """获取嵌套字段值"""
        parts = field_path.split(".")
        value = obj
        for part in parts:
            if hasattr(value, part):
                value = getattr(value, part)
            elif isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        return value
    
    def _set_nested_field(self, obj: Any, field_path: str, value: Any) -> None:
        """设置嵌套字段值"""
        parts = field_path.split(".")
        target = obj
        for part in parts[:-1]:
            if hasattr(target, part):
                target = getattr(target, part)
            elif isinstance(target, dict):
                target = target.get(part)
            else:
                return
        
        final_part = parts[-1]
        if hasattr(target, final_part):
            setattr(target, final_part, value)
        elif isinstance(target, dict):
            target[final_part] = value
    
    def _infer_edge_family(self, edge_type: EdgeType) -> EdgeFamily:
        """推断边类型"""
        family_mapping = {
            # Organization
            EdgeType.MEMBER_OF: EdgeFamily.ORGANIZATION,
            EdgeType.LEADER_OF: EdgeFamily.ORGANIZATION,
            EdgeType.SUBORDINATE_TO: EdgeFamily.ORGANIZATION,
            EdgeType.BRANCH_OF: EdgeFamily.ORGANIZATION,
            EdgeType.PART_OF: EdgeFamily.ORGANIZATION,
            # Possession
            EdgeType.OWNS: EdgeFamily.POSSESSION,
            EdgeType.POSSESSES: EdgeFamily.POSSESSION,
            EdgeType.EQUIPPED_WITH: EdgeFamily.POSSESSION,
            EdgeType.BOUND_TO: EdgeFamily.POSSESSION,
            EdgeType.CREATED_BY: EdgeFamily.POSSESSION,
            EdgeType.GRANTS_ABILITY: EdgeFamily.POSSESSION,
            # Social
            EdgeType.FAMILY_OF: EdgeFamily.SOCIAL,
            EdgeType.ALLY_OF: EdgeFamily.SOCIAL,
            EdgeType.ENEMY_OF: EdgeFamily.SOCIAL,
            EdgeType.MENTOR_OF: EdgeFamily.SOCIAL,
            EdgeType.ROMANTIC_WITH: EdgeFamily.SOCIAL,
            EdgeType.TRUSTS: EdgeFamily.SOCIAL,
            EdgeType.DISTRUSTS: EdgeFamily.SOCIAL,
            EdgeType.OWES_DEBT_TO: EdgeFamily.SOCIAL,
            # 默认
        }
        return family_mapping.get(edge_type, EdgeFamily.SOCIAL)
    
    def _generate_summary(self, node_patches: list, edge_patches: list) -> str:
        """生成变更摘要"""
        node_ops = {}
        edge_ops = {}
        
        for patch in node_patches:
            op = patch.get("op", "unknown")
            node_ops[op] = node_ops.get(op, 0) + 1
        
        for patch in edge_patches:
            op = patch.get("op", "unknown")
            edge_ops[op] = edge_ops.get(op, 0) + 1
        
        parts = []
        if node_ops:
            parts.append(f"{len(node_patches)} node patches")
        if edge_ops:
            parts.append(f"{len(edge_patches)} edge patches")
        
        return "; ".join(parts) if parts else "No changes"