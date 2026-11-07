"""Map Edges Model - Scheme C 地图边

MapEdge 类型：
- road: 道路
- path: 小径
- river: 河流
- sea_route: 海上路线
- flight_route: 飞行路线
- tunnel: 隧道
- portal: 传送门
- rail: 铁路
- border_crossing: 边境通道
- hidden_route: 隐藏路线
- mountain_pass: 山路
- space_route: 太空路线
- world_gate: 世界之门
"""
import enum
from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text, func, JSON, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class MapEdgeType(str, enum.Enum):
    ROAD = "road"                 # 道路
    PATH = "path"                 # 小径
    RIVER = "river"               # 河流
    SEA_ROUTE = "sea_route"       # 海上路线
    FLIGHT_ROUTE = "flight_route" # 飞行路线
    TUNNEL = "tunnel"             # 隧道
    PORTAL = "portal"            # 传送门
    RAIL = "rail"                 # 铁路
    BORDER_CROSSING = "border_crossing"  # 边境通道
    HIDDEN_ROUTE = "hidden_route"  # 隐藏路线
    MOUNTAIN_PASS = "mountain_pass"  # 山路
    SPACE_ROUTE = "space_route"    # 太空路线
    WORLD_GATE = "world_gate"     # 世界之门


class MapEdge(Base):
    __tablename__ = "map_edges"
    __table_args__ = (
        Index("ix_map_edges_project", "project_id"),
        Index("ix_map_edges_from_node", "from_node_id"),
        Index("ix_map_edges_to_node", "to_node_id"),
        Index("ix_map_edges_subworld", "subworld_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    
    # 所属 subworld
    subworld_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("sub_worlds.id", ondelete="CASCADE"), nullable=True
    )
    
    # 边两端
    from_node_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("map_nodes.id", ondelete="CASCADE"), nullable=False
    )
    to_node_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("map_nodes.id", ondelete="CASCADE"), nullable=False
    )
    
    # 边类型
    edge_type: Mapped[MapEdgeType] = mapped_column(Enum(MapEdgeType), nullable=False)
    
    # 方向性
    bidirectional: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # 权重（用于路径计算）
    distance: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    travel_time: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)  # 小时
    travel_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    risk_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)  # 0-10
    narrative_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    
    # 状态
    status: Mapped[str] = mapped_column(String(50), default="open", nullable=False)  # open/blocked/hidden
    discovered_by_default: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    visibility_default: Mapped[str] = mapped_column(String(50), default="public", nullable=False)
    
    # 访问控制
    access_rule_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # 元数据
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<MapEdge(id={self.id}, type={self.edge_type}, {self.from_node_id}->{self.to_node_id})>"


# Forward reference
from app.models.project import Project
from app.models.map_nodes import MapNode