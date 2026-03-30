"""世界设定模型"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class WorldSetting(Base):
    __tablename__ = "world_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False)  # 类别：地理、政治、历史、魔法等
    name: Mapped[str] = mapped_column(String(200), nullable=False)       # 设定名称
    content: Mapped[str] = mapped_column(Text, nullable=True)            # 设定内容
    importance: Mapped[int] = mapped_column(Integer, default=1)          # 重要性 1-5
    mutable_flag: Mapped[bool] = mapped_column(Boolean, default=False)    # 是否可变
    
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
    project: Mapped["Project"] = relationship("Project", back_populates="world_settings")


from app.models.project import Project
