"""Chapter Rewrite Attempt Model - v2.7 新增

章节重写尝试记录表
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, JSON, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class ChapterRewriteAttempt(Base):
    """章节重写尝试记录 - v2.7
    
    追踪每次重写尝试：
    - 触发重写的审查 ID
    - 修复范围 (scene/band/arc)
    - 设计补丁
    - 源草稿和结果草稿
    - 最终 verdict
    - 强制接受标记
    """
    __tablename__ = "chapter_rewrite_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # 项目和章节标识
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    chapter_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False
    )
    chapter_number: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # 尝试编号（1-3）
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # 触发重写的审查 ID
    trigger_review_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("review_notes.id"), nullable=True
    )
    
    # 修复范围
    repair_scope: Mapped[str] = mapped_column(String(20), nullable=False)  # scene/band/arc
    
    # 设计补丁 JSON
    design_patch_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 源草稿 ID（重写前的草稿）
    source_draft_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # 结果草稿 ID（重写后的草稿）
    result_draft_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # 结果 verdict
    result_verdict: Mapped[str] = mapped_column(String(20), nullable=True)  # pass/warn/fail
    
    # 强制接受标记
    forced_accept_applied: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # 修复指令摘要（用于调试）
    repair_instruction_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="rewrite_attempts")
    chapter: Mapped["Chapter"] = relationship("Chapter", back_populates="rewrite_attempts")
    trigger_review: Mapped[Optional["ReviewNote"]] = relationship(
        "ReviewNote", foreign_keys=[trigger_review_id]
    )


# Forward references
from app.models.project import Project
from app.models.chapter import Chapter
from app.models.review_note import ReviewNote
