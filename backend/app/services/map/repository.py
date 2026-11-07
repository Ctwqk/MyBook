"""MapRepository - 地图数据访问层

提供地图节点和边的 CRUD 操作
"""
from typing import Optional
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.map_nodes import MapNode, MapNodeType
from app.models.map_edges import MapEdge, MapEdgeType
from app.models.subworld import SubWorld, MapRegion


class MapRepository:
    """地图数据访问层"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ========== SubWorld ==========
    
    async def create_subworld(
        self,
        project_id: int,
        name: str,
        subworld_type: str,
        description: Optional[str] = None,
        is_default: bool = False,
        **kwargs
    ) -> SubWorld:
        """创建子世界"""
        subworld = SubWorld(
            project_id=project_id,
            name=name,
            subworld_type=subworld_type,
            description=description,
            is_default=is_default,
            **kwargs
        )
        self.db.add(subworld)
        await self.db.flush()
        return subworld
    
    async def get_subworld(self, subworld_id: int) -> Optional[SubWorld]:
        """获取子世界"""
        result = await self.db.execute(
            select(SubWorld).where(SubWorld.id == subworld_id)
        )
        return result.scalar_one_or_none()
    
    async def get_subworlds_by_project(self, project_id: int) -> list[SubWorld]:
        """获取项目的所有子世界"""
        result = await self.db.execute(
            select(SubWorld)
            .where(SubWorld.project_id == project_id)
            .order_by(SubWorld.is_default.desc(), SubWorld.name)
        )
        return list(result.scalars().all())
    
    async def get_default_subworld(self, project_id: int) -> Optional[SubWorld]:
        """获取默认子世界"""
        result = await self.db.execute(
            select(SubWorld).where(
                and_(
                    SubWorld.project_id == project_id,
                    SubWorld.is_default == True
                )
            )
        )
        return result.scalar_one_or_none()
    
    # ========== MapRegion ==========
    
    async def create_region(
        self,
        project_id: int,
        subworld_id: int,
        name: str,
        description: Optional[str] = None,
        **kwargs
    ) -> MapRegion:
        """创建地图区域"""
        region = MapRegion(
            project_id=project_id,
            subworld_id=subworld_id,
            name=name,
            description=description,
            **kwargs
        )
        self.db.add(region)
        await self.db.flush()
        return region
    
    async def get_regions_by_subworld(self, subworld_id: int) -> list[MapRegion]:
        """获取子世界的所有区域"""
        result = await self.db.execute(
            select(MapRegion)
            .where(MapRegion.subworld_id == subworld_id)
            .order_by(MapRegion.name)
        )
        return list(result.scalars().all())
    
    # ========== MapNode ==========
    
    async def create_node(
        self,
        project_id: int,
        name: str,
        node_type: MapNodeType,
        subworld_id: Optional[int] = None,
        region_id: Optional[int] = None,
        **kwargs
    ) -> MapNode:
        """创建地图节点"""
        node = MapNode(
            project_id=project_id,
            name=name,
            node_type=node_type,
            subworld_id=subworld_id,
            region_id=region_id,
            **kwargs
        )
        self.db.add(node)
        await self.db.flush()
        return node
    
    async def get_node(self, node_id: int) -> Optional[MapNode]:
        """获取地图节点"""
        result = await self.db.execute(
            select(MapNode).where(MapNode.id == node_id)
        )
        return result.scalar_one_or_none()
    
    async def get_nodes_by_project(
        self,
        project_id: int,
        node_type: Optional[MapNodeType] = None,
        subworld_id: Optional[int] = None,
        region_id: Optional[int] = None,
        is_active: Optional[bool] = True
    ) -> list[MapNode]:
        """获取项目的地图节点"""
        query = select(MapNode).where(MapNode.project_id == project_id)
        
        if node_type:
            query = query.where(MapNode.node_type == node_type)
        if subworld_id:
            query = query.where(MapNode.subworld_id == subworld_id)
        if region_id:
            query = query.where(MapNode.region_id == region_id)
        if is_active is not None:
            query = query.where(MapNode.is_active == is_active)
        
        query = query.order_by(MapNode.name)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def update_node(self, node_id: int, **kwargs) -> Optional[MapNode]:
        """更新地图节点"""
        node = await self.get_node(node_id)
        if not node:
            return None
        
        for key, value in kwargs.items():
            if hasattr(node, key):
                setattr(node, key, value)
        
        await self.db.flush()
        return node
    
    async def delete_node(self, node_id: int) -> bool:
        """删除地图节点"""
        node = await self.get_node(node_id)
        if not node:
            return False
        
        await self.db.delete(node)
        await self.db.flush()
        return True
    
    # ========== MapEdge ==========
    
    async def create_edge(
        self,
        project_id: int,
        from_node_id: int,
        to_node_id: int,
        edge_type: MapEdgeType,
        subworld_id: Optional[int] = None,
        bidirectional: bool = False,
        **kwargs
    ) -> MapEdge:
        """创建地图边"""
        edge = MapEdge(
            project_id=project_id,
            from_node_id=from_node_id,
            to_node_id=to_node_id,
            edge_type=edge_type,
            subworld_id=subworld_id,
            bidirectional=bidirectional,
            **kwargs
        )
        self.db.add(edge)
        await self.db.flush()
        
        # 如果是双向边，创建反向边
        if bidirectional:
            reverse_edge = MapEdge(
                project_id=project_id,
                from_node_id=to_node_id,
                to_node_id=from_node_id,
                edge_type=edge_type,
                subworld_id=subworld_id,
                bidirectional=False,  # 反向边标记为非双向，避免无限递归
                **kwargs
            )
            self.db.add(reverse_edge)
            await self.db.flush()
        
        return edge
    
    async def get_edge(self, edge_id: int) -> Optional[MapEdge]:
        """获取地图边"""
        result = await self.db.execute(
            select(MapEdge).where(MapEdge.id == edge_id)
        )
        return result.scalar_one_or_none()
    
    async def get_edges_by_project(
        self,
        project_id: int,
        edge_type: Optional[MapEdgeType] = None,
        subworld_id: Optional[int] = None,
        from_node_id: Optional[int] = None,
        to_node_id: Optional[int] = None
    ) -> list[MapEdge]:
        """获取项目的地图边"""
        query = select(MapEdge).where(MapEdge.project_id == project_id)
        
        if edge_type:
            query = query.where(MapEdge.edge_type == edge_type)
        if subworld_id:
            query = query.where(MapEdge.subworld_id == subworld_id)
        if from_node_id:
            query = query.where(MapEdge.from_node_id == from_node_id)
        if to_node_id:
            query = query.where(MapEdge.to_node_id == to_node_id)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_edges_from_node(self, node_id: int) -> list[MapEdge]:
        """获取从指定节点出发的所有边"""
        result = await self.db.execute(
            select(MapEdge).where(MapEdge.from_node_id == node_id)
        )
        return list(result.scalars().all())
    
    async def update_edge(self, edge_id: int, **kwargs) -> Optional[MapEdge]:
        """更新地图边"""
        edge = await self.get_edge(edge_id)
        if not edge:
            return None
        
        for key, value in kwargs.items():
            if hasattr(edge, key):
                setattr(edge, key, value)
        
        await self.db.flush()
        return edge
    
    async def delete_edge(self, edge_id: int) -> bool:
        """删除地图边"""
        edge = await self.get_edge(edge_id)
        if not edge:
            return False
        
        await self.db.delete(edge)
        await self.db.flush()
        return True
    
    # ========== 批量操作 ==========
    
    async def bulk_create_nodes(
        self,
        nodes: list[dict]
    ) -> list[MapNode]:
        """批量创建节点"""
        created = []
        for node_data in nodes:
            node = MapNode(**node_data)
            self.db.add(node)
            created.append(node)
        
        await self.db.flush()
        return created
    
    async def bulk_create_edges(
        self,
        edges: list[dict]
    ) -> list[MapEdge]:
        """批量创建边"""
        created = []
        for edge_data in edges:
            edge = MapEdge(**edge_data)
            self.db.add(edge)
            created.append(edge)
        
        await self.db.flush()
        return created
