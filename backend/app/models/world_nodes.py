"""World Nodes Model - BookState 世界节点

12种节点类型：
- character: 角色
- faction: 势力
- group: 组织
- item: 物品
- resource: 资源
- ability: 能力
- rule: 规则
- activity: 活动
- site_state: 地点状态
- event: 事件
- fact: 事实
- objective: 目标
"""
import enum
from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text, func, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class WorldNodeType(str, enum.Enum):
    CHARACTER = "character"
    FACTION = "faction"
    GROUP = "group"
    ITEM = "item"
    RESOURCE = "resource"
    ABILITY = "ability"
    RULE = "rule"
    ACTIVITY = "activity"
    SITE_STATE = "site_state"
    EVENT = "event"
    FACT = "fact"
    OBJECTIVE = "objective"


class Importance(str, enum.Enum):
    CRITICAL = "critical"    # 核心（主角、关键道具等）
    HIGH = "high"            # 重要（主要配角、重要事件等）
    MEDIUM = "medium"        # 一般（次要角色、局部事件等）
    LOW = "low"              # 边缘（背景角色、提及物品等）


class WorldNode(Base):
    __tablename__ = "world_nodes"
    __table_args__ = (
        Index("ix_world_nodes_project_type", "project_id", "node_type"),
        Index("ix_world_nodes_project_name", "project_id", "name"),
        Index("ix_world_nodes_project_active", "project_id", "is_active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    
    # 基础字段
    node_type: Mapped[WorldNodeType] = mapped_column(
        Enum(WorldNodeType), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    aliases: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    importance: Mapped[Importance] = mapped_column(
        Enum(Importance), default=Importance.MEDIUM, nullable=False
    )
    
    # Profile 和 State（结构化 JSON）
    # profile: 长期属性，不频繁变化
    profile_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # state: 章节/故事时间变化，必须进入 delta ledger
    state_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # metadata: 扩展字段
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # 生命周期
    created_at_chapter: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    retired_at_chapter: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="world_nodes")
    
    # 出边和入边
    outgoing_edges: Mapped[list["WorldEdge"]] = relationship(
        "WorldEdge", foreign_keys="WorldEdge.source_id",
        back_populates="source_node", cascade="all, delete-orphan"
    )
    incoming_edges: Mapped[list["WorldEdge"]] = relationship(
        "WorldEdge", foreign_keys="WorldEdge.target_id",
        back_populates="target_node", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<WorldNode(id={self.id}, type={self.node_type}, name={self.name})>"


# Forward reference
from app.models.project import Project
from app.models.world_edges import WorldEdge