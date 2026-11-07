"""BookState Repository - 数据访问层

职责：
- WorldNode CRUD
- WorldEdge CRUD
- GraphDelta append
- Snapshot 查询
"""
from typing import Optional
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.world_nodes import WorldNode, WorldNodeType
from app.models.world_edges import WorldEdge, EdgeType
from app.models.graph_deltas import GraphDelta, DeltaType


class BookStateRepository:
    """BookState 数据访问层"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ========== WorldNode ==========
    
    async def get_node(self, node_id: int) -> Optional[WorldNode]:
        """获取节点"""
        result = await self.db.execute(
            select(WorldNode).where(WorldNode.id == node_id)
        )
        return result.scalar_one_or_none()
    
    async def get_nodes_by_project(
        self,
        project_id: int,
        node_type: Optional[WorldNodeType] = None,
        is_active: bool = True
    ) -> list[WorldNode]:
        """获取项目的所有节点"""
        query = select(WorldNode).where(WorldNode.project_id == project_id)
        
        if node_type:
            query = query.where(WorldNode.node_type == node_type)
        if is_active is not None:
            query = query.where(WorldNode.is_active == is_active)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_nodes_by_ids(self, node_ids: list[int]) -> list[WorldNode]:
        """批量获取节点"""
        if not node_ids:
            return []
        result = await self.db.execute(
            select(WorldNode).where(WorldNode.id.in_(node_ids))
        )
        return list(result.scalars().all())
    
    async def create_node(self, node: WorldNode) -> WorldNode:
        """创建节点"""
        self.db.add(node)
        await self.db.flush()
        await self.db.refresh(node)
        return node
    
    async def update_node(self, node: WorldNode) -> WorldNode:
        """更新节点"""
        await self.db.flush()
        await self.db.refresh(node)
        return node
    
    async def delete_node(self, node: WorldNode) -> None:
        """删除节点"""
        await self.db.delete(node)
        await self.db.flush()
    
    # ========== WorldEdge ==========
    
    async def get_edge(self, edge_id: int) -> Optional[WorldEdge]:
        """获取边"""
        result = await self.db.execute(
            select(WorldEdge).where(WorldEdge.id == edge_id)
        )
        return result.scalar_one_or_none()
    
    async def get_edges_by_project(
        self,
        project_id: int,
        edge_type: Optional[EdgeType] = None,
        is_active: bool = True
    ) -> list[WorldEdge]:
        """获取项目的所有边"""
        query = select(WorldEdge).where(WorldEdge.project_id == project_id)
        
        if edge_type:
            query = query.where(WorldEdge.edge_type == edge_type)
        if is_active is not None:
            query = query.where(WorldEdge.is_active == is_active)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_edges_by_node(
        self,
        node_id: int,
        direction: str = "outgoing"  # outgoing / incoming / both
    ) -> list[WorldEdge]:
        """获取与节点相关的边"""
        query = select(WorldEdge)
        
        if direction == "outgoing":
            query = query.where(WorldEdge.source_id == node_id)
        elif direction == "incoming":
            query = query.where(WorldEdge.target_id == node_id)
        else:  # both
            query = query.where(or_(
                WorldEdge.source_id == node_id,
                WorldEdge.target_id == node_id
            ))
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def create_edge(self, edge: WorldEdge) -> WorldEdge:
        """创建边"""
        self.db.add(edge)
        await self.db.flush()
        await self.db.refresh(edge)
        return edge
    
    async def update_edge(self, edge: WorldEdge) -> WorldEdge:
        """更新边"""
        await self.db.flush()
        await self.db.refresh(edge)
        return edge
    
    async def delete_edge(self, edge: WorldEdge) -> None:
        """删除边"""
        await self.db.delete(edge)
        await self.db.flush()
    
    # ========== GraphDelta ==========
    
    async def get_delta(self, delta_id: int) -> Optional[GraphDelta]:
        """获取增量"""
        result = await self.db.execute(
            select(GraphDelta).where(GraphDelta.id == delta_id)
        )
        return result.scalar_one_or_none()
    
    async def get_deltas_by_project(
        self,
        project_id: int,
        up_to_chapter: Optional[int] = None,
        delta_type: Optional[DeltaType] = None,
        is_committed: bool = True
    ) -> list[GraphDelta]:
        """获取项目的所有增量"""
        query = select(GraphDelta).where(GraphDelta.project_id == project_id)
        
        if up_to_chapter:
            query = query.where(
                or_(
                    GraphDelta.chapter_number == None,
                    GraphDelta.chapter_number <= up_to_chapter
                )
            )
        if delta_type:
            query = query.where(GraphDelta.delta_type == delta_type)
        if is_committed is not None:
            query = query.where(GraphDelta.is_committed == is_committed)
        
        query = query.order_by(GraphDelta.created_at)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def create_delta(self, delta: GraphDelta) -> GraphDelta:
        """创建增量"""
        self.db.add(delta)
        await self.db.flush()
        await self.db.refresh(delta)
        return delta
    
    async def commit_delta(self, delta: GraphDelta) -> GraphDelta:
        """提交增量"""
        delta.is_committed = True
        await self.db.flush()
        await self.db.refresh(delta)
        return delta
    
    async def revert_delta(
        self,
        delta: GraphDelta,
        reverted_by_delta_id: int
    ) -> GraphDelta:
        """回滚增量"""
        delta.is_reverted = True
        delta.reverted_by_delta_id = reverted_by_delta_id
        await self.db.flush()
        await self.db.refresh(delta)
        return delta
    
    # ========== 批量操作 ==========
    
    async def batch_create_nodes(self, nodes: list[WorldNode]) -> list[WorldNode]:
        """批量创建节点"""
        self.db.add_all(nodes)
        await self.db.flush()
        for node in nodes:
            await self.db.refresh(node)
        return nodes
    
    async def batch_create_edges(self, edges: list[WorldEdge]) -> list[WorldEdge]:
        """批量创建边"""
        self.db.add_all(edges)
        await self.db.flush()
        for edge in edges:
            await self.db.refresh(edge)
        return edges