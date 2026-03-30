"""角色模型"""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class CharacterRoleType(str):
    PROTAGONIST = "protagonist"       # 主角
    SUPPORTING = "supporting"         # 配角
    ANTAGONIST = "antagonist"         # 反派
    MINOR = "minor"                   # 次要角色


class Character(Base):
    __tablename__ = "characters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    role_type: Mapped[str] = mapped_column(String(50), default=CharacterRoleType.SUPPORTING)
    
    # 基本信息
    profile: Mapped[Optional[str]] = mapped_column(Text, nullable=True)         # 人物小传
    personality: Mapped[Optional[str]] = mapped_column(Text, nullable=True)     # 性格特点
    motivation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)      # 动机/目标
    secrets: Mapped[Optional[str]] = mapped_column(Text, nullable=True)         # 秘密
    relationships: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)   # 人物关系
    
    # 状态
    current_state: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # 当前状态
    power_level: Mapped[Optional[int]] = mapped_column(Integer, nullable=True) # 能力等级
    tags: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)      # 标签
    
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
    project: Mapped["Project"] = relationship("Project", back_populates="characters")
    states: Mapped[list["CharacterState"]] = relationship(
        "CharacterState", back_populates="character", cascade="all, delete-orphan"
    )


from app.models.project import Project
from app.models.character_state import CharacterState
