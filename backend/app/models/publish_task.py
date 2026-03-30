"""发布任务模型"""
import enum
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class PublishStatus(str, enum.Enum):
    PENDING = "pending"           # 待处理
    PREPARING = "preparing"       # 准备中
    SUBMITTING = "submitting"     # 提交中
    SUCCESS = "success"           # 成功
    FAILED = "failed"             # 失败
    CANCELLED = "cancelled"       # 已取消


class PublishMode(str, enum.Enum):
    DRAFT = "draft"               # 存草稿
    IMMEDIATE = "immediate"      # 立即发布


class PublishErrorCode(str, enum.Enum):
    SESSION_EXPIRED = "SESSION_EXPIRED"
    BOOK_NOT_BOUND = "BOOK_NOT_BOUND"
    NETWORK_ERROR = "NETWORK_ERROR"
    PLATFORM_VALIDATION_ERROR = "PLATFORM_VALIDATION_ERROR"
    DUPLICATE_SUBMISSION = "DUPLICATE_SUBMISSION"
    PLATFORM_LAYOUT_CHANGED = "PLATFORM_LAYOUT_CHANGED"
    CONTENT_FORMAT_ERROR = "CONTENT_FORMAT_ERROR"
    RISK_CONTROL_BLOCKED = "RISK_CONTROL_BLOCKED"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class PublishTask(Base):
    __tablename__ = "publish_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    chapter_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False
    )
    platform: Mapped[str] = mapped_column(String(100), nullable=False)  # 平台标识
    account_id: Mapped[str] = mapped_column(String(100), nullable=True)  # 平台账户ID
    remote_book_id: Mapped[str] = mapped_column(String(100), nullable=True)  # 远程书籍ID
    
    mode: Mapped[PublishMode] = mapped_column(
        Enum(PublishMode),
        default=PublishMode.DRAFT,
        nullable=False
    )
    status: Mapped[PublishStatus] = mapped_column(
        Enum(PublishStatus),
        default=PublishStatus.PENDING,
        nullable=False
    )
    error_code: Mapped[PublishErrorCode] = mapped_column(
        Enum(PublishErrorCode),
        nullable=True
    )
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    
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
    project: Mapped["Project"] = relationship("Project", back_populates="publish_tasks")
    chapter: Mapped["Chapter"] = relationship("Chapter", back_populates="publish_tasks")


from app.models.project import Project
from app.models.chapter import Chapter
