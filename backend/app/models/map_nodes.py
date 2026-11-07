"""Map Nodes Model - Scheme C 地图节点

分层地图结构：
SubWorld -> Region -> MapNode -> MapEdge

MapNode 类型：
- settlement: 城市/聚落
- site: 地点
- building: 建筑
- room: 房间
- zone: 区域
- waypoint: 航点
- landmark: 地标
- camp: 营地
- dungeon_room: 地下城房间
"""
import enum
from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text, func, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class MapNodeType(str, enum.Enum):
    SETTLEMENT = "settlement"     # 城市/聚落
    SITE = "site"                 # 地点
    BUILDING = "building"         # 建筑
    ROOM = "room"                # 房间
    ZONE = "zone"                # 区域
    WAYPOINT = "waypoint"        # 航点
    LANDMARK = "landmark"        # 地标
    CAMP = "camp"                # 营地
    DUNGEON_ROOM = "dungeon_room"  # 地下城房间


class MapNode(Base):
    __tablename__ = "map_nodes"
    __table_args__ = (
        Index("ix_map_nodes_subworld", "subworld_id"),
        Index("ix_map_nodes_region", "region_id"),
        Index("ix_map_nodes_type", "node_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    
    # 分层结构
    subworld_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sub_worlds.id", ondelete="CASCADE"), nullable=True
    )
    region_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("map_regions.id", ondelete="SET NULL"), nullable=True
    )
    
    # 节点信息
    node_type: Mapped[MapNodeType] = mapped_column(Enum(MapNodeType), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 空间层级（可选，用于更细粒度表达）
    parent_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("map_nodes.id", ondelete="SET NULL"), nullable=True
    )
    hierarchy_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # e.g., "sub1/region1/node1"
    
    # 状态
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="open", nullable=False)  # open/blocked/hidden
    
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
        return f"<MapNode(id={self.id}, name={self.name}, type={self.node_type})>"


# Forward reference
from app.models.project import Project