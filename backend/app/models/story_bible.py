"""故事圣经模型"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class StoryBible(Base):
    __tablename__ = "story_bibles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    
    # 故事核心
    title: Mapped[str] = mapped_column(Text, nullable=True)            # 标题
    genre: Mapped[str] = mapped_column(Text, nullable=True)             # 类型
    theme: Mapped[str] = mapped_column(Text, nullable=True)            # 主题
    logline: Mapped[str] = mapped_column(Text, nullable=True)          # 一句话概述
    synopsis: Mapped[str] = mapped_column(Text, nullable=True)          # 故事大纲
    tone: Mapped[str] = mapped_column(Text, nullable=True)              # 基调
    target_audience: Mapped[str] = mapped_column(Text, nullable=True)   # 目标读者
    
    # 世界观
    world_overview: Mapped[str] = mapped_column(Text, nullable=True)    # 世界概述
    world_rules: Mapped[list] = mapped_column(JSON, nullable=True)       # 世界规则
    magic_system: Mapped[str] = mapped_column(Text, nullable=True)      # 魔法/能力系统
    
    # 叙事结构
    narrative_structure: Mapped[dict] = mapped_column(JSON, nullable=True)  # 叙事结构
    key_plot_points: Mapped[list] = mapped_column(JSON, nullable=True)     # 关键情节点
    
    # 元数据
    meta_data: Mapped[dict] = mapped_column(JSON, nullable=True)        # 其他元数据
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="story_bible")


from app.models.project import Project
