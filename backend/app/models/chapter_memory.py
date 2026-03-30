"""章节记忆模型"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class ChapterMemory(Base):
    __tablename__ = "chapter_memories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    chapter_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False
    )
    summary: Mapped[str] = mapped_column(Text, nullable=True)           # 章节摘要
    key_events: Mapped[list] = mapped_column(JSON, nullable=True)       # 关键事件列表
    new_world_details: Mapped[list] = mapped_column(JSON, nullable=True)  # 新增世界细节
    foreshadow_changes: Mapped[list] = mapped_column(JSON, nullable=True)  # 伏笔变化
    
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
    project: Mapped["Project"] = relationship("Project")
    chapter: Mapped["Chapter"] = relationship("Chapter", back_populates="memories")


from app.models.project import Project
from app.models.chapter import Chapter
