"""卷/篇章模型"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Volume(Base):
    __tablename__ = "volumes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    volume_no: Mapped[int] = mapped_column(Integer, nullable=False)     # 卷号
    title: Mapped[str] = mapped_column(String(200), nullable=False)      # 卷标题
    goal: Mapped[str] = mapped_column(Text, nullable=True)                # 卷目标
    conflict: Mapped[str] = mapped_column(Text, nullable=True)           # 核心冲突
    expected_chapter_count: Mapped[int] = mapped_column(Integer, default=10)  # 预期章节数
    summary: Mapped[str] = mapped_column(Text, nullable=True)           # 卷摘要
    
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
    project: Mapped["Project"] = relationship("Project", back_populates="volumes")
    chapters: Mapped[list["Chapter"]] = relationship(
        "Chapter", back_populates="volume", cascade="all, delete-orphan"
    )


from app.models.project import Project
from app.models.chapter import Chapter
