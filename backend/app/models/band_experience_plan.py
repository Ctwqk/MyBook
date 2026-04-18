"""Band Experience Plan Model - v2.7 新增

Band 体验计划表
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class BandExperiencePlan(Base):
    """Band 体验计划 - v2.7
    
    存储 Band 级别的愉悦时刻表
    """
    __tablename__ = "band_experience_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # 项目和 Arc 标识
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    arc_no: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Band 标识
    band_no: Mapped[int] = mapped_column(Integer, nullable=False)
    band_name: Mapped[str] = mapped_column(String(200), nullable=True)
    
    # 章节范围
    start_chapter: Mapped[int] = mapped_column(Integer, nullable=False)
    end_chapter: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # 愉悦时刻表 JSON
    delight_schedule_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 分布统计
    delight_per_chapter_avg: Mapped[float] = mapped_column(
        JSON, default=0.0
    )
    distribution: Mapped[str] = mapped_column(
        String(20), default="regular"  # front_loaded/regular/back_loaded
    )
    
    # 状态
    is_active: Mapped[bool] = mapped_column(default=True)
    
    # 时间戳
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
    project: Mapped["Project"] = relationship("Project", back_populates="band_experience_plans")


# Forward references
from app.models.project import Project
