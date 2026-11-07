"""BookStateRuntime - 世界状态运行时

核心数据结构：
- ObjectiveWorldGraph: 世界节点和边
- Snapshot: 快照（as-of chapter 查询）

职责：
- 从 DB 加载当前世界状态
- Replay deltas 获取历史状态
- 提供查询接口
"""
from typing import Optional, Any
from dataclasses import dataclass, field
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.world_nodes import WorldNode, WorldNodeType
from app.models.world_edges import WorldEdge, EdgeType
from app.models.graph_deltas import GraphDelta, DeltaType
from app.services.book_state.repository import BookStateRepository


@dataclass
class ObjectiveWorldGraph:
    """客观世界图"""
    nodes_by_id: dict[int, WorldNode] = field(default_factory=dict)
    states_by_node_id: dict[int, dict] = field(default_factory=dict)
    edges_by_id: dict[int, WorldEdge] = field(default_factory=dict)
    outgoing_edges: dict[int, list[int]] = field(default_factory=dict)  # node_id -> list of edge_ids
    incoming_edges: dict[int, list[int]] = field(default_factory=dict)  # node_id -> list of edge_ids
    
    def get_node(self, node_id: int) -> Optional[WorldNode]:
        return self.nodes_by_id.get(node_id)
    
    def get_outgoing_edges(self, node_id: int) -> list[WorldEdge]:
        edge_ids = self.outgoing_edges.get(node_id, [])
        return [self.edges_by_id[eid] for eid in edge_ids if eid in self.edges_by_id]
    
    def get_incoming_edges(self, node_id: int) -> list[WorldEdge]:
        edge_ids = self.incoming_edges.get(node_id, [])
        return [self.edges_by_id[eid] for eid in edge_ids if eid in self.edges_by_id]
    
    def get_neighbors(self, node_id: int, edge_type: Optional[EdgeType] = None) -> list[tuple[WorldNode, WorldEdge]]:
        """获取邻居节点"""
        result = []
        for edge in self.get_outgoing_edges(node_id):
            if edge_type and edge.edge_type != edge_type:
                continue
            neighbor = self.nodes_by_id.get(edge.target_id)
            if neighbor:
                result.append((neighbor, edge))
        return result


@dataclass
class BookStateSnapshot:
    """世界状态快照"""
    project_id: int
    as_of_chapter: int
    as_of_story_time: Optional[str]
    world_graph: ObjectiveWorldGraph
    built_at: str


class BookStateRuntime:
    """BookState 运行时"""
    
    def __init__(self, db: AsyncSession, project_id: int):
        self.db = db
        self.project_id = project_id
        self.repo = BookStateRepository(db)
        
        # 当前状态
        self.world_graph: Optional[ObjectiveWorldGraph] = None
        self.current_chapter: Optional[int] = None
    
    async def load_current_state(self) -> ObjectiveWorldGraph:
        """加载当前世界状态"""
        # 加载所有活跃节点
        nodes = await self.repo.get_nodes_by_project(self.project_id, is_active=True)
        
        # 加载所有活跃边
        edges = await self.repo.get_edges_by_project(self.project_id, is_active=True)
        
        # 构建世界图
        graph = ObjectiveWorldGraph()
        
        for node in nodes:
            graph.nodes_by_id[node.id] = node
            graph.states_by_node_id[node.id] = node.state_json or {}
            graph.outgoing_edges[node.id] = []
            graph.incoming_edges[node.id] = []
        
        for edge in edges:
            graph.edges_by_id[edge.id] = edge
            if edge.source_id in graph.outgoing_edges:
                graph.outgoing_edges[edge.source_id].append(edge.id)
            if edge.target_id in graph.incoming_edges:
                graph.incoming_edges[edge.target_id].append(edge.id)
        
        self.world_graph = graph
        return graph
    
    async def get_snapshot(self, up_to_chapter: int) -> BookStateSnapshot:
        """
        获取指定章节的世界状态快照
        
        通过 replay 增量账本获取历史状态
        """
        # 1. 找到 <= up_to_chapter 的最近快照
        # TODO: 实现 snapshot 表的查询
        
        # 2. 加载基础状态（当前实现使用当前状态作为基础）
        base_graph = await self.load_current_state()
        
        # 3. 获取需要 replay 的 deltas
        deltas = await self.repo.get_deltas_by_project(
            self.project_id,
            up_to_chapter=up_to_chapter,
            is_committed=True
        )
        
        # 4. Replay deltas（简化版：实际需要按时间/章节顺序 replay）
        # 当前实现只处理 commit 状态
        for delta in deltas:
            if delta.chapter_number and delta.chapter_number <= up_to_chapter:
                await self._replay_delta(base_graph, delta)
        
        return BookStateSnapshot(
            project_id=self.project_id,
            as_of_chapter=up_to_chapter,
            as_of_story_time=None,
            world_graph=base_graph,
            built_at=None  # TODO: 填充实际时间
        )
    
    async def _replay_delta(self, graph: ObjectiveWorldGraph, delta: GraphDelta) -> None:
        """Replay 单个增量"""
        # 处理 node patches
        for patch in (delta.node_patches or []):
            await self._replay_node_patch(graph, patch)
        
        # 处理 edge patches
        for patch in (delta.edge_patches or []):
            await self._replay_edge_patch(graph, patch)
    
    async def _replay_node_patch(self, graph: ObjectiveWorldGraph, patch: dict) -> None:
        """Replay 节点 patch"""
        op = patch.get("op")
        node_id = patch.get("node_id")
        field_path = patch.get("field_path")
        new_value = patch.get("new_value")
        
        if op == "create":
            # 创建新节点（需要额外加载完整数据）
            node = await self.repo.get_node(node_id)
            if node:
                graph.nodes_by_id[node.id] = node
                graph.states_by_node_id[node.id] = node.state_json or {}
                graph.outgoing_edges[node.id] = []
                graph.incoming_edges[node.id] = []
        
        elif op == "set" and node_id and field_path:
            node = graph.nodes_by_id.get(node_id)
            if node and hasattr(node, field_path):
                setattr(node, field_path, new_value)
        
        elif op == "deactivate" and node_id:
            node = graph.nodes_by_id.get(node_id)
            if node:
                node.is_active = False
                node.retired_at_chapter = patch.get("retired_at_chapter")
    
    async def _replay_edge_patch(self, graph: ObjectiveWorldGraph, patch: dict) -> None:
        """Replay 边 patch"""
        op = patch.get("op")
        edge_id = patch.get("edge_id")
        
        if op == "create":
            edge = await self.repo.get_edge(edge_id)
            if edge:
                graph.edges_by_id[edge.id] = edge
                if edge.source_id in graph.outgoing_edges:
                    graph.outgoing_edges[edge.source_id].append(edge.id)
                if edge.target_id in graph.incoming_edges:
                    graph.incoming_edges[edge.target_id].append(edge.id)
        
        elif op == "deactivate" and edge_id:
            edge = graph.edges_by_id.get(edge_id)
            if edge:
                edge.is_active = False
                edge.ended_at_chapter = patch.get("ended_at_chapter")
    
    # ========== 便捷查询方法 ==========
    
    async def get_character_node(self, character_name: str) -> Optional[WorldNode]:
        """获取角色节点"""
        if not self.world_graph:
            await self.load_current_state()
        
        for node in self.world_graph.nodes_by_id.values():
            if node.node_type == WorldNodeType.CHARACTER and node.name == character_name:
                return node
        return None
    
    async def get_character_location(self, character_node_id: int) -> Optional[int]:
        """获取角色当前位置（location_id）"""
        if not self.world_graph:
            await self.load_current_state()
        
        node = self.world_graph.nodes_by_id.get(character_node_id)
        if not node:
            return None
        
        state = graph.states_by_node_id.get(character_node_id, {})
        return state.get("location_id")
    
    async def get_relationships(
        self,
        node_id: int,
        relationship_types: Optional[list[EdgeType]] = None
    ) -> list[tuple[WorldNode, WorldEdge]]:
        """获取节点的所有关系"""
        if not self.world_graph:
            await self.load_current_state()
        
        result = []
        for edge in self.world_graph.get_outgoing_edges(node_id):
            if relationship_types and edge.edge_type not in relationship_types:
                continue
            neighbor = self.world_graph.nodes_by_id.get(edge.target_id)
            if neighbor:
                result.append((neighbor, edge))
        return result
    
    async def get_all_characters(self) -> list[WorldNode]:
        """获取所有角色"""
        if not self.world_graph:
            await self.load_current_state()
        
        return [
            node for node in self.world_graph.nodes_by_id.values()
            if node.node_type == WorldNodeType.CHARACTER and node.is_active
        ]
    
    async def get_node_count(self) -> int:
        """获取节点总数"""
        if not self.world_graph:
            await self.load_current_state()
        return len(self.world_graph.nodes_by_id)
    
    async def get_edge_count(self) -> int:
        """获取边总数"""
        if not self.world_graph:
            await self.load_current_state()
        return len(self.world_graph.edges_by_id)