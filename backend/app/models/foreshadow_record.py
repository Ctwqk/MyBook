"""伏笔记录模型"""
import enum
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func, Enum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class ForeshadowStatus(str, enum.Enum):
    SETUP = "setup"             # 已埋下
    DEVELOPING = "developing"   # 发展中
    RESOLVED = "resolved"       # 已解开
    ABANDONED = "abandoned"     # 已放弃


class ForeshadowRecord(Base):
    __tablename__ = "foreshadow_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    chapter_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)          # 伏笔内容
    related_entities: Mapped[list] = mapped_column(JSON, nullable=True)  # 相关实体
    status: Mapped[ForeshadowStatus] = mapped_column(
        Enum(ForeshadowStatus),
        default=ForeshadowStatus.SETUP,
        nullable=False
    )
    planned_resolution: Mapped[str] = mapped_column(Text, nullable=True)  # 计划如何解开
    
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
    project: Mapped["Project"] = relationship("Project", back_populates="foreshadows")
    chapter: Mapped["Chapter"] = relationship("Chapter", back_populates="foreshadows")


from app.models.project import Project
from app.models.chapter import Chapter
