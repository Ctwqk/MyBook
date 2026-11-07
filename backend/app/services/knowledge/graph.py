"""KnowledgeGraph - 知识图谱管理

基于 V4.6 设计文档
"""
from typing import Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class KnowledgeNode:
    """知识节点"""
    id: str
    type: str  # character, location, item, event, concept
    name: str
    properties: dict = field(default_factory=dict)
    aliases: list[str] = field(default_factory=list)
    description: str = ""
    sources: list[str] = field(default_factory=list)  # 章节引用


@dataclass
class KnowledgeEdge:
    """知识边"""
    id: str
    source_id: str
    target_id: str
    relation: str  # related_to, part_of, causes, influenced_by, etc.
    properties: dict = field(default_factory=dict)
    weight: float = 1.0


@dataclass
class KnowledgeGraph:
    """知识图谱"""
    nodes: dict[str, KnowledgeNode] = field(default_factory=dict)
    edges: dict[str, KnowledgeEdge] = field(default_factory=dict)
    node_index: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))  # type -> node_ids
    link_index: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))  # name -> node_ids
    
    def add_node(self, node: KnowledgeNode) -> None:
        """添加节点"""
        self.nodes[node.id] = node
        self.node_index[node.type].append(node.id)
        self.link_index[node.name.lower()].append(node.id)
        for alias in node.aliases:
            self.link_index[alias.lower()].append(node.id)
    
    def add_edge(self, edge: KnowledgeEdge) -> None:
        """添加边"""
        self.edges[edge.id] = edge
    
    def get_node(self, node_id: str) -> Optional[KnowledgeNode]:
        """获取节点"""
        return self.nodes.get(node_id)
    
    def get_node_by_name(self, name: str) -> Optional[KnowledgeNode]:
        """通过名称查找节点"""
        node_ids = self.link_index.get(name.lower(), [])
        if node_ids:
            return self.nodes.get(node_ids[0])
        return None
    
    def get_nodes_by_type(self, node_type: str) -> list[KnowledgeNode]:
        """获取指定类型的所有节点"""
        node_ids = self.node_index.get(node_type, [])
        return [self.nodes[nid] for nid in node_ids if nid in self.nodes]
    
    def get_neighbors(self, node_id: str) -> list[tuple[KnowledgeNode, KnowledgeEdge]]:
        """获取邻居节点"""
        neighbors = []
        for edge in self.edges.values():
            if edge.source_id == node_id:
                target = self.nodes.get(edge.target_id)
                if target:
                    neighbors.append((target, edge))
            elif edge.target_id == node_id:
                source = self.nodes.get(edge.source_id)
                if source:
                    neighbors.append((source, edge))
        return neighbors
    
    def get_subgraph(
        self,
        center_id: str,
        depth: int = 1
    ) -> "KnowledgeGraph":
        """获取以某节点为中心的子图"""
        subgraph = KnowledgeGraph()
        
        def add_with_depth(node_id: str, current_depth: int):
            if current_depth > depth:
                return
            
            node = self.nodes.get(node_id)
            if not node:
                return
            
            subgraph.add_node(node)
            
            for neighbor, edge in self.get_neighbors(node_id):
                subgraph.add_node(neighbor)
                subgraph.add_edge(edge)
                add_with_depth(neighbor.id, current_depth + 1)
        
        add_with_depth(center_id, 0)
        return subgraph
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "nodes": [
                {
                    "id": n.id,
                    "type": n.type,
                    "name": n.name,
                    "properties": n.properties,
                    "aliases": n.aliases,
                    "description": n.description,
                    "sources": n.sources
                }
                for n in self.nodes.values()
            ],
            "edges": [
                {
                    "id": e.id,
                    "source_id": e.source_id,
                    "target_id": e.target_id,
                    "relation": e.relation,
                    "properties": e.properties,
                    "weight": e.weight
                }
                for e in self.edges.values()
            ]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "KnowledgeGraph":
        """从字典创建"""
        graph = cls()
        
        for node_data in data.get("nodes", []):
            node = KnowledgeNode(
                id=node_data["id"],
                type=node_data["type"],
                name=node_data["name"],
                properties=node_data.get("properties", {}),
                aliases=node_data.get("aliases", []),
                description=node_data.get("description", ""),
                sources=node_data.get("sources", [])
            )
            graph.add_node(node)
        
        for edge_data in data.get("edges", []):
            edge = KnowledgeEdge(
                id=edge_data["id"],
                source_id=edge_data["source_id"],
                target_id=edge_data["target_id"],
                relation=edge_data["relation"],
                properties=edge_data.get("properties", {}),
                weight=edge_data.get("weight", 1.0)
            )
            graph.add_edge(edge)
        
        return graph
    
    def merge(self, other: "KnowledgeGraph") -> None:
        """合并另一个图谱"""
        for node in other.nodes.values():
            if node.id not in self.nodes:
                self.add_node(node)
        
        for edge in other.edges.values():
            if edge.id not in self.edges:
                self.add_edge(edge)
    
    def find_path(
        self,
        source_id: str,
        target_id: str,
        max_length: int = 5
    ) -> list[list[str]]:
        """查找两点间的所有路径"""
        paths = []
        
        def dfs(current: str, target: str, path: list[str], visited: set[str]):
            if len(path) > max_length:
                return
            
            if current == target:
                paths.append(path.copy())
                return
            
            for neighbor, _ in self.get_neighbors(current):
                if neighbor.id not in visited:
                    visited.add(neighbor.id)
                    path.append(neighbor.id)
                    dfs(neighbor.id, target, path, visited)
                    path.pop()
                    visited.remove(neighbor.id)
        
        dfs(source_id, target_id, [source_id], {source_id})
        return paths