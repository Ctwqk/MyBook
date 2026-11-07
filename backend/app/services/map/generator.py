"""MapGenerator - 地图生成服务

基于 LLM 生成地图内容
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.map_nodes import MapNode, MapNodeType
from app.models.map_edges import MapEdge, MapEdgeType
from app.models.subworld import SubWorld, MapRegion
from app.services.map.repository import MapRepository


class MapGenerator:
    """地图内容生成器"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = MapRepository(db)
    
    async def generate_subworld(
        self,
        project_id: int,
        name: str,
        subworld_type: str,
        description: Optional[str] = None,
        physics_rules: Optional[dict] = None,
        magic_rules: Optional[dict] = None,
        access_rules: Optional[dict] = None
    ) -> SubWorld:
        """生成子世界"""
        # 检查是否已存在默认子世界
        existing = await self.repo.get_default_subworld(project_id)
        is_default = not existing
        
        return await self.repo.create_subworld(
            project_id=project_id,
            name=name,
            subworld_type=subworld_type,
            description=description,
            is_default=is_default,
            physics_rules=physics_rules,
            magic_rules=magic_rules,
            access_rules=access_rules
        )
    
    async def generate_region(
        self,
        project_id: int,
        subworld_id: int,
        name: str,
        description: Optional[str] = None,
        climate: Optional[str] = None,
        terrain: Optional[str] = None
    ) -> MapRegion:
        """生成地图区域"""
        return await self.repo.create_region(
            project_id=project_id,
            subworld_id=subworld_id,
            name=name,
            description=description,
            climate=climate,
            terrain=terrain
        )
    
    async def generate_node(
        self,
        project_id: int,
        name: str,
        node_type: MapNodeType,
        subworld_id: Optional[int] = None,
        region_id: Optional[int] = None,
        description: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> MapNode:
        """生成地图节点"""
        return await self.repo.create_node(
            project_id=project_id,
            name=name,
            node_type=node_type,
            subworld_id=subworld_id,
            region_id=region_id,
            description=description,
            metadata_json=metadata
        )
    
    async def generate_edge(
        self,
        project_id: int,
        from_node_id: int,
        to_node_id: int,
        edge_type: MapEdgeType,
        subworld_id: Optional[int] = None,
        bidirectional: bool = True,
        distance: float = 1.0,
        travel_time: Optional[float] = None,
        travel_cost: float = 0.0,
        risk_level: float = 0.0,
        narrative_cost: float = 0.0
    ) -> MapEdge:
        """生成地图边"""
        if travel_time is None:
            # 默认：基于距离估算
            travel_time = distance * 8  # 假设每小时行进 8 单位
        
        return await self.repo.create_edge(
            project_id=project_id,
            from_node_id=from_node_id,
            to_node_id=to_node_id,
            edge_type=edge_type,
            subworld_id=subworld_id,
            bidirectional=bidirectional,
            distance=distance,
            travel_time=travel_time,
            travel_cost=travel_cost,
            risk_level=risk_level,
            narrative_cost=narrative_cost
        )
    
    async def generate_full_map(
        self,
        project_id: int,
        subworld_name: str,
        subworld_type: str = "main_world",
        regions: list[dict] = None,
        nodes: list[dict] = None,
        edges: list[dict] = None
    ) -> dict:
        """
        生成完整地图
        
        Args:
            project_id: 项目 ID
            subworld_name: 子世界名称
            subworld_type: 子世界类型
            regions: 区域列表 [{"name": "...", "description": "..."}]
            nodes: 节点列表 [{"name": "...", "type": "...", "region": "..."}]
            edges: 边列表 [{"from": "...", "to": "...", "type": "...", "distance": 1.0}]
        
        Returns:
            {"subworld": SubWorld, "regions": [...], "nodes": [...], "edges": [...]}
        """
        # 1. 创建子世界
        subworld = await self.generate_subworld(
            project_id=project_id,
            name=subworld_name,
            subworld_type=subworld_type
        )
        
        result = {
            "subworld": subworld,
            "regions": [],
            "nodes": [],
            "edges": []
        }
        
        # 2. 创建区域
        region_map = {}  # name -> region
        if regions:
            for region_data in regions:
                region = await self.generate_region(
                    project_id=project_id,
                    subworld_id=subworld.id,
                    name=region_data["name"],
                    description=region_data.get("description"),
                    climate=region_data.get("climate"),
                    terrain=region_data.get("terrain")
                )
                region_map[region.name] = region
                result["regions"].append(region)
        
        # 3. 创建节点
        node_map = {}  # name -> node
        if nodes:
            for node_data in nodes:
                node_type_str = node_data.get("type", "site")
                try:
                    node_type = MapNodeType(node_type_str)
                except ValueError:
                    node_type = MapNodeType.SITE
                
                region_id = None
                if node_data.get("region") and node_data["region"] in region_map:
                    region_id = region_map[node_data["region"]].id
                
                node = await self.generate_node(
                    project_id=project_id,
                    name=node_data["name"],
                    node_type=node_type,
                    subworld_id=subworld.id,
                    region_id=region_id,
                    description=node_data.get("description"),
                    metadata=node_data.get("metadata")
                )
                node_map[node.name] = node
                result["nodes"].append(node)
        
        # 4. 创建边
        if edges:
            for edge_data in edges:
                from_name = edge_data["from"]
                to_name = edge_data["to"]
                
                if from_name not in node_map or to_name not in node_map:
                    continue
                
                edge_type_str = edge_data.get("type", "path")
                try:
                    edge_type = MapEdgeType(edge_type_str)
                except ValueError:
                    edge_type = MapEdgeType.PATH
                
                edge = await self.generate_edge(
                    project_id=project_id,
                    from_node_id=node_map[from_name].id,
                    to_node_id=node_map[to_name].id,
                    edge_type=edge_type,
                    subworld_id=subworld.id,
                    bidirectional=edge_data.get("bidirectional", True),
                    distance=edge_data.get("distance", 1.0),
                    travel_time=edge_data.get("travel_time"),
                    travel_cost=edge_data.get("travel_cost", 0.0),
                    risk_level=edge_data.get("risk_level", 0.0),
                    narrative_cost=edge_data.get("narrative_cost", 0.0)
                )
                result["edges"].append(edge)
        
        return result
    
    async def update_node_from_llm(
        self,
        node_id: int,
        llm_description: str
    ) -> Optional[MapNode]:
        """根据 LLM 生成的内容更新节点"""
        # 解析 LLM 返回的描述，更新节点属性
        # TODO: 集成 LLM 解析逻辑
        return await self.repo.update_node(
            node_id,
            description=llm_description
        )
    
    async def suggest_connections(
        self,
        node_id: int,
        max_distance: float = 10.0
    ) -> list[dict]:
        """
        根据 LLM 建议节点连接
        
        TODO: 集成 LLM 分析逻辑
        - 分析节点特征
        - 建议可能的连接位置
        - 推荐边的类型
        """
        node = await self.repo.get_node(node_id)
        if not node:
            return []
        
        # TODO: LLM 分析
        suggestions = []
        
        return suggestions