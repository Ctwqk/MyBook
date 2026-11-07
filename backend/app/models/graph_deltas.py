"""Graph Deltas Model - BookState Append-only Delta Ledger

Delta 类型：
- world_state: 世界状态变更
- map_state: 地图状态变更
- cognition: 认知层变更
- narrative_control: 叙事控制变更
- repair: 修复操作
- retcon_block: 回滚阻断

Patch 操作：
- create: 创建
- set: 设置
- merge: 合并
- append: 追加
- remove: 移除
- replace: 替换
- deactivate: 停用
"""
import enum
from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text, func, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class DeltaType(str, enum.Enum):
    WORLD_STATE = "world_state"
    MAP_STATE = "map_state"
    COGNITION = "cognition"
    NARRATIVE_CONTROL = "narrative_control"
    REPAIR = "repair"
    RETCON_BLOCK = "retcon_block"


class SourceType(str, enum.Enum):
    WRITER = "writer"
    REVIEWER = "reviewer"
    COMPILER = "compiler"
    MIGRATION = "migration"
    MANUAL = "manual"
    LEGACY_IMPORT = "legacy_import"


class GraphDelta(Base):
    __tablename__ = "graph_deltas"
    __table_args__ = (
        Index("ix_graph_deltas_project_chapter", "project_id", "chapter_number"),
        Index("ix_graph_deltas_project_type", "project_id", "delta_type"),
        Index("ix_graph_deltas_project_time", "project_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    
    # 章节信息
    chapter_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    story_time: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # 故事时间描述
    
    # Delta 元信息
    delta_type: Mapped[DeltaType] = mapped_column(Enum(DeltaType), nullable=False)
    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType), nullable=False)
    source_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # 来源ID
    world_line_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # 所属世界线
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 变更摘要
    
    # Patches（结构化 JSON）
    # 包含 node_patches, edge_patches, fact_patches, map_patches, cognition_patches, narrative_patches
    node_patches: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    edge_patches: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    fact_patches: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    map_patches: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    cognition_patches: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    narrative_patches: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    
    # 证据引用
    evidence_refs: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list
    
    # 元数据
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # 状态
    is_committed: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_reverted: Mapped[bool] = mapped_column(default=False, nullable=False)
    reverted_by_delta_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project")

    def __repr__(self) -> str:
        return f"<GraphDelta(id={self.id}, type={self.delta_type}, chapter={self.chapter_number})>"


class NodePatchOp(str, enum.Enum):
    CREATE = "create"
    SET = "set"
    MERGE = "merge"
    APPEND = "append"
    REMOVE = "remove"
    REPLACE = "replace"
    DEACTIVATE = "deactivate"


class EdgePatchOp(str, enum.Enum):
    CREATE = "create"
    SET = "set"
    REMOVE = "remove"
    REPLACE = "replace"
    DEACTIVATE = "deactivate"


# Forward reference
from app.models.project import Project