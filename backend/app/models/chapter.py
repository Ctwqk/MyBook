"""章节模型"""
import enum
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class ChapterStatus(str, enum.Enum):
    OUTLINE = "outline"       # 只有大纲
    DRAFT = "draft"           # 草稿
    WRITING = "writing"       # 写作中
    REVIEWING = "reviewing"   # 审查中
    APPROVED = "approved"     # 已通过
    PUBLISHED = "published"   # 已发布


class Chapter(Base):
    __tablename__ = "chapters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    volume_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("volumes.id", ondelete="SET NULL"), nullable=True
    )
    chapter_no: Mapped[int] = mapped_column(Integer, nullable=False)     # 章节号
    title: Mapped[str] = mapped_column(String(200), nullable=True)       # 章节标题
    outline: Mapped[str] = mapped_column(Text, nullable=True)            # 章节大纲
    text: Mapped[str] = mapped_column(Text, nullable=True)               # 章节正文
    summary: Mapped[str] = mapped_column(Text, nullable=True)            # 章节摘要
    hook: Mapped[str] = mapped_column(Text, nullable=True)              # 章节钩子
    status: Mapped[ChapterStatus] = mapped_column(
        Enum(ChapterStatus),
        default=ChapterStatus.OUTLINE,
        nullable=False
    )
    word_count: Mapped[int] = mapped_column(Integer, default=0)         # 字数
    
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
    project: Mapped["Project"] = relationship("Project", back_populates="chapters")
    volume: Mapped["Volume"] = relationship("Volume", back_populates="chapters")
    memories: Mapped[list["ChapterMemory"]] = relationship(
        "ChapterMemory", back_populates="chapter", cascade="all, delete-orphan"
    )
    review_notes: Mapped[list["ReviewNote"]] = relationship(
        "ReviewNote", back_populates="chapter", cascade="all, delete-orphan"
    )
    foreshadows: Mapped[list["ForeshadowRecord"]] = relationship(
        "ForeshadowRecord", back_populates="chapter", cascade="all, delete-orphan"
    )
    publish_tasks: Mapped[list["PublishTask"]] = relationship(
        "PublishTask", back_populates="chapter", cascade="all, delete-orphan"
    )


from app.models.project import Project
from app.models.volume import Volume
from app.models.chapter_memory import ChapterMemory
from app.models.review_note import ReviewNote
from app.models.foreshadow_record import ForeshadowRecord
from app.models.publish_task import PublishTask
