"""SubWorld Model - Scheme C 子世界

SubWorld 是世界图谱的最高层级划分，用于：
- 分离主世界与异世界/副本
- 管理位面/维度
- 支持多场景地图
"""
import enum
from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text, func, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class SubWorldType(str, enum.Enum):
    MAIN_WORLD = "main_world"       # 主世界
    PARALLEL_WORLD = "parallel_world"  # 平行世界
    DIMENSION = "dimension"          # 异次元/位面
    DUNGEON = "dungeon"            # 地下城/副本
    DREAM_WORLD = "dream_world"     # 梦境世界
    VIRTUAL_SPACE = "virtual_space"  # 虚拟空间
    HEAVEN = "heaven"              # 天界/神域
    HELL = "hell"                  # 地狱
    AFTERLIFE = "afterlife"        # 死后世界
    MEMORY_SPACE = "memory_space"  # 记忆空间


class SubWorld(Base):
    __tablename__ = "sub_worlds"
    __table_args__ = (
        Index("ix_sub_worlds_project", "project_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    
    # 子世界信息
    subworld_type: Mapped[SubWorldType] = mapped_column(Enum(SubWorldType), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 空间规则
    physics_rules: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # 重力、时间流速等
    magic_rules: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)   # 魔法规则
    access_rules: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)   # 进入条件
    
    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # 主世界标记
    
    # 层级关系
    parent_subworld_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("sub_worlds.id", ondelete="SET NULL"), nullable=True
    )
    
    # 元数据
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # 关系
    map_nodes = relationship("MapNode", back_populates="subworld", cascade="all, delete-orphan")
    map_edges = relationship("MapEdge", cascade="all, delete-orphan")
    map_regions = relationship("MapRegion", back_populates="subworld", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<SubWorld(id={self.id}, name={self.name}, type={self.subworld_type})>"


class MapRegion(Base):
    """Map Region - 地图区域
    
    位于 SubWorld 下一级，用于组织地图节点
    """
    __tablename__ = "map_regions"
    __table_args__ = (
        Index("ix_map_regions_subworld", "subworld_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    
    # 所属子世界
    subworld_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sub_worlds.id", ondelete="CASCADE"), nullable=False
    )
    
    # 区域信息
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    climate: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # 气候类型
    terrain: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # 地形
    
    # 层级关系
    parent_region_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("map_regions.id", ondelete="SET NULL"), nullable=True
    )
    
    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # 元数据
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # 关系
    subworld = relationship("SubWorld", back_populates="map_regions")
    map_nodes = relationship("MapNode", back_populates="region")

    def __repr__(self) -> str:
        return f"<MapRegion(id={self.id}, name={self.name})>"