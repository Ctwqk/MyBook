"""审查记录模型"""
import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Boolean, func, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class IssueType(str, enum.Enum):
    CONSISTENCY = "consistency"       # 一致性问题
    PLOT_HOLE = "plot_hole"           # 剧情漏洞
    PACING = "pacing"                 # 节奏问题
    CHARACTER = "character"           # 角色问题
    DIALOGUE = "dialogue"             # 对话问题
    DESCRIPTION = "description"       # 描述问题
    HOOK = "hook"                     # 钩子问题
    OTHER = "other"                    # 其他


class Severity(str, enum.Enum):
    LOW = "low"       # 低
    MEDIUM = "medium" # 中
    HIGH = "high"     # 高
    CRITICAL = "critical"  # 严重


class ReviewNote(Base):
    __tablename__ = "review_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    chapter_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False
    )
    issue_type: Mapped[IssueType] = mapped_column(
        Enum(IssueType),
        default=IssueType.OTHER,
        nullable=False
    )
    severity: Mapped[Severity] = mapped_column(
        Enum(Severity),
        default=Severity.MEDIUM,
        nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)     # 问题描述
    fix_suggestion: Mapped[str] = mapped_column(Text, nullable=True)    # 修复建议
    
    # v2.7: 强制接受标记
    forced_accept_applied: Mapped[bool] = mapped_column(default=False)
    
    # v2.7: 覆盖原因
    override_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # v2.7: 重写尝试次数
    rewrite_attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="review_notes")
    chapter: Mapped["Chapter"] = relationship("Chapter", back_populates="review_notes")


from app.models.project import Project
from app.models.chapter import Chapter
