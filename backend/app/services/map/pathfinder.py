"""PathFinder - Dijkstra 路径计算

基于 Scheme C 设计文档的 Dijkstra 算法实现
支持多权重路径搜索
"""
import heapq
from dataclasses import dataclass, field
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.map_nodes import MapNode, MapNodeType
from app.models.map_edges import MapEdge, MapEdgeType


@dataclass
class PathResult:
    """路径计算结果"""
    found: bool
    path: list[int]  # node_ids
    total_distance: float = 0.0
    total_travel_time: float = 0.0
    total_cost: float = 0.0
    total_risk: float = 0.0
    total_narrative: float = 0.0
    edges: list[MapEdge] = field(default_factory=list)
    blocked_nodes: list[int] = field(default_factory=list)
    blocked_edges: list[int] = field(default_factory=list)


@dataclass
class PathConfig:
    """路径搜索配置"""
    weight_type: str = "distance"  # distance, time, cost, risk, narrative, composite
    composite_weights: dict = field(default_factory=lambda: {
        "distance": 1.0,
        "travel_time": 0.5,
        "cost": 0.3,
        "risk": 2.0,
        "narrative": 1.5
    })
    max_risk: float = 10.0  # 风险上限
    allow_blocked: bool = False  # 是否允许经过阻塞路径
    prefer_known: bool = True  # 是否优先已知路线


class PathFinder:
    """Dijkstra 路径计算器"""
    
    def __init__(self, db: AsyncSession, project_id: int):
        self.db = db
        self.project_id = project_id
        self._nodes: dict[int, MapNode] = {}
        self._edges: dict[int, list[MapEdge]] = {}  # node_id -> outgoing edges
    
    async def load_graph(self, subworld_id: Optional[int] = None) -> None:
        """加载图数据"""
        # 加载节点
        query = select(MapNode).where(
            MapNode.project_id == self.project_id,
            MapNode.is_active == True
        )
        if subworld_id:
            query = query.where(MapNode.subworld_id == subworld_id)
        
        result = await self.db.execute(query)
        for node in result.scalars():
            self._nodes[node.id] = node
            self._edges[node.id] = []
        
        # 加载边
        edge_query = select(MapEdge).where(
            MapEdge.project_id == self.project_id
        )
        if subworld_id:
            edge_query = edge_query.where(MapEdge.subworld_id == subworld_id)
        
        edge_result = await self.db.execute(edge_query)
        for edge in edge_result.scalars():
            if edge.from_node_id in self._edges:
                self._edges[edge.from_node_id].append(edge)
    
    def _get_weight(self, edge: MapEdge, config: PathConfig) -> float:
        """计算边的权重"""
        if config.weight_type == "distance":
            return edge.distance
        elif config.weight_type == "time":
            return edge.travel_time
        elif config.weight_type == "cost":
            return edge.travel_cost
        elif config.weight_type == "risk":
            return edge.risk_level
        elif config.weight_type == "narrative":
            return edge.narrative_cost
        elif config.weight_type == "composite":
            return (
                config.composite_weights["distance"] * edge.distance +
                config.composite_weights["travel_time"] * edge.travel_time +
                config.composite_weights["cost"] * edge.travel_cost +
                config.composite_weights["risk"] * edge.risk_level +
                config.composite_weights["narrative"] * edge.narrative_cost
            )
        return edge.distance
    
    def _is_accessible(self, edge: MapEdge, node: MapNode, config: PathConfig) -> bool:
        """检查边是否可通行"""
        if node.status == "blocked":
            return config.allow_blocked
        if edge.status == "blocked":
            return config.allow_blocked
        if config.max_risk and edge.risk_level > config.max_risk:
            return False
        return True
    
    async def find_path(
        self,
        from_node_id: int,
        to_node_id: int,
        config: Optional[PathConfig] = None
    ) -> PathResult:
        """
        使用 Dijkstra 算法找最短路径
        
        Args:
            from_node_id: 起始节点
            to_node_id: 目标节点
            config: 搜索配置
        
        Returns:
            PathResult: 路径结果
        """
        if config is None:
            config = PathConfig()
        
        if not self._nodes:
            await self.load_graph()
        
        if from_node_id not in self._nodes or to_node_id not in self._nodes:
            return PathResult(found=False, path=[])
        
        # Dijkstra
        distances: dict[int, float] = {from_node_id: 0}
        previous: dict[int, tuple[int, MapEdge]] = {}  # node_id -> (prev_node_id, edge)
        priority_queue: list[tuple[float, int]] = [(0, from_node_id)]
        visited: set[int] = set()
        blocked_edges: list[int] = []
        blocked_nodes: list[int] = []
        
        while priority_queue:
            current_dist, current_node = heapq.heappop(priority_queue)
            
            if current_node in visited:
                continue
            visited.add(current_node)
            
            if current_node == to_node_id:
                break
            
            current_node_obj = self._nodes[current_node]
            
            for edge in self._edges.get(current_node, []):
                neighbor = edge.to_node_id
                
                if neighbor in visited:
                    continue
                
                if neighbor not in self._nodes:
                    continue
                
                neighbor_node = self._nodes[neighbor]
                
                # 检查可通行性
                if not self._is_accessible(edge, neighbor_node, config):
                    if edge.status == "blocked" and edge.id not in blocked_edges:
                        blocked_edges.append(edge.id)
                    if neighbor_node.status == "blocked" and neighbor not in blocked_nodes:
                        blocked_nodes.append(neighbor)
                    continue
                
                weight = self._get_weight(edge, config)
                new_dist = current_dist + weight
                
                if neighbor not in distances or new_dist < distances[neighbor]:
                    distances[neighbor] = new_dist
                    previous[neighbor] = (current_node, edge)
                    heapq.heappush(priority_queue, (new_dist, neighbor))
        
        # 重建路径
        if to_node_id not in previous and to_node_id != from_node_id:
            return PathResult(
                found=False,
                path=[],
                blocked_nodes=blocked_nodes,
                blocked_edges=blocked_edges
            )
        
        path: list[int] = []
        edges: list[MapEdge] = []
        current = to_node_id
        
        while current in previous:
            prev_node, edge = previous[current]
            path.append(current)
            edges.append(edge)
            current = prev_node
        path.append(from_node_id)
        path.reverse()
        edges.reverse()
        
        # 计算总权重
        result = PathResult(
            found=True,
            path=path,
            edges=edges,
            blocked_nodes=blocked_nodes,
            blocked_edges=blocked_edges
        )
        
        for edge in edges:
            result.total_distance += edge.distance
            result.total_travel_time += edge.travel_time
            result.total_cost += edge.travel_cost
            result.total_risk += edge.risk_level
            result.total_narrative += edge.narrative_cost
        
        return result
    
    async def find_all_reachable(
        self,
        from_node_id: int,
        max_distance: float = 100.0,
        config: Optional[PathConfig] = None
    ) -> dict[int, float]:
        """
        找到从起点可达的所有节点及其最短距离
        
        Args:
            from_node_id: 起始节点
            max_distance: 最大距离限制
            config: 搜索配置
        
        Returns:
            dict[node_id, distance]
        """
        if config is None:
            config = PathConfig()
        
        if not self._nodes:
            await self.load_graph()
        
        if from_node_id not in self._nodes:
            return {}
        
        distances: dict[int, float] = {from_node_id: 0}
        priority_queue: list[tuple[float, int]] = [(0, from_node_id)]
        visited: set[int] = set()
        
        while priority_queue:
            current_dist, current_node = heapq.heappop(priority_queue)
            
            if current_node in visited:
                continue
            visited.add(current_node)
            
            if current_dist > max_distance:
                continue
            
            for edge in self._edges.get(current_node, []):
                neighbor = edge.to_node_id
                
                if neighbor in visited:
                    continue
                
                if neighbor not in self._nodes:
                    continue
                
                neighbor_node = self._nodes[neighbor]
                
                if not self._is_accessible(edge, neighbor_node, config):
                    continue
                
                weight = self._get_weight(edge, config)
                new_dist = current_dist + weight
                
                if new_dist <= max_distance:
                    if neighbor not in distances or new_dist < distances[neighbor]:
                        distances[neighbor] = new_dist
                        heapq.heappush(priority_queue, (new_dist, neighbor))
        
        return distances
