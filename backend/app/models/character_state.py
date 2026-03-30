"""角色状态模型"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class CharacterState(Base):
    __tablename__ = "character_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    character_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    
    # 状态快照
    location: Mapped[str] = mapped_column(String(200), nullable=True)          # 当前位置
    goal: Mapped[str] = mapped_column(Text, nullable=True)                      # 当前目标
    emotional_state: Mapped[str] = mapped_column(String(100), nullable=True)    # 情绪状态
    power_level: Mapped[int] = mapped_column(Integer, nullable=True)           # 能力等级
    relationship_state: Mapped[dict] = mapped_column(JSON, nullable=True)       # 关系状态
    last_event: Mapped[str] = mapped_column(Text, nullable=True)               # 最后事件
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project")
    character: Mapped["Character"] = relationship("Character", back_populates="states")


from app.models.project import Project
from app.models.character import Character
