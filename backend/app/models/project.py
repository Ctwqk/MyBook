"""项目模型"""
import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class ProjectStatus(str, enum.Enum):
    DRAFT = "draft"           # 草稿
    PLANNING = "planning"     # 规划中
    WRITING = "writing"       # 写作中
    REVIEWING = "reviewing"   # 审查中
    PUBLISHED = "published"   # 已发布
    ARCHIVED = "archived"     # 已归档


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    genre: Mapped[str] = mapped_column(String(100), nullable=True)
    style: Mapped[str] = mapped_column(String(100), nullable=True)
    premise: Mapped[str] = mapped_column(Text, nullable=True)
    target_length: Mapped[int] = mapped_column(Integer, nullable=True)  # 目标字数
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus),
        default=ProjectStatus.DRAFT,
        nullable=False
    )
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
    characters: Mapped[list["Character"]] = relationship(
        "Character", back_populates="project", cascade="all, delete-orphan"
    )
    world_settings: Mapped[list["WorldSetting"]] = relationship(
        "WorldSetting", back_populates="project", cascade="all, delete-orphan"
    )
    volumes: Mapped[list["Volume"]] = relationship(
        "Volume", back_populates="project", cascade="all, delete-orphan"
    )
    chapters: Mapped[list["Chapter"]] = relationship(
        "Chapter", back_populates="project", cascade="all, delete-orphan"
    )
    story_bible: Mapped[Optional["StoryBible"]] = relationship(
        "StoryBible", back_populates="project", uselist=False, cascade="all, delete-orphan"
    )
    foreshadows: Mapped[list["ForeshadowRecord"]] = relationship(
        "ForeshadowRecord", back_populates="project", cascade="all, delete-orphan"
    )
    review_notes: Mapped[list["ReviewNote"]] = relationship(
        "ReviewNote", back_populates="project", cascade="all, delete-orphan"
    )
    publish_tasks: Mapped[list["PublishTask"]] = relationship(
        "PublishTask", back_populates="project", cascade="all, delete-orphan"
    )


# Forward reference for type hints
from app.models.character import Character
from app.models.world_setting import WorldSetting
from app.models.volume import Volume
from app.models.chapter import Chapter
from app.models.story_bible import StoryBible
from app.models.foreshadow_record import ForeshadowRecord
from app.models.review_note import ReviewNote
from app.models.publish_task import PublishTask
