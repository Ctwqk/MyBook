"""Personality Models - 人物性格系统

基于 V4.7/V4.8 设计文档
"""
import enum
from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text, func, JSON, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class TraitCategory(str, enum.Enum):
    """特质类别"""
    BIG_FIVE = "big_five"         # 大五人格
    MORAL = "moral"              # 道德特质
    SOCIAL = "social"            # 社会特质
    COGNITIVE = "cognitive"      # 认知特质
    EMOTIONAL = "emotional"      # 情感特质
    BEHAVIORAL = "behavioral"    # 行为特质
    MOTIVATION = "motivation"    # 动机特质


class TraitType(str, enum.Enum):
    """具体特质类型"""
    # Big Five
    OPENNESS = "openness"              # 开放性
    CONSCIENTIOUSNESS = "conscientiousness"  # 尽责性
    EXTRAVERSION = "extraversion"      # 外向性
    AGREEABLENESS = "agreeableness"     # 宜人性
    NEUROTICISM = "neuroticism"        # 神经质
    
    # Moral
    HONESTY = "honesty"                # 诚实
    LOYALTY = "loyalty"                # 忠诚
    JUSTICE = "justice"                # 正义
    MERCY = "mercy"                    # 仁慈
    WISDOM = "wisdom"                  # 智慧
    
    # Social
    LEADERSHIP = "leadership"          # 领导力
    EMPATHY = "empathy"                # 同理心
    MANIPULATION = "manipulation"       # 操控
    AUTHORITY = "authority"             # 权威
    
    # Cognitive
    CURIOSITY = "curiosity"            # 好奇心
    RATIONALITY = "rationality"         # 理性
    INTUITION = "intuition"             # 直觉
    CREATIVITY = "creativity"           # 创造力
    
    # Emotional
    COURAGE = "courage"                # 勇气
    FEAR = "fear"                      # 恐惧
    ANGER = "anger"                    # 愤怒
    COMPASSION = "compassion"           # 同情
    
    # Behavioral
    IMPULSIVITY = "impulsivity"        # 冲动
    PATIENCE = "patience"              # 耐心
    FLEXIBILITY = "flexibility"         # 灵活
    PERSISTENCE = "persistence"         # 坚持
    
    # Motivation
    POWER = "power"                    # 权力
    ACHIEVEMENT = "achievement"        # 成就
    AFFILIATION = "affiliation"        # 归属
    SELF_DIRECTION = "self_direction"  # 自主


class PersonalityLoadout(Base):
    """Personality Loadout - 性格配置单
    
    一个角色的完整性格配置，包含：
    - 核心特质（从 V4.8）
    - 大五分数
    - 动机
    - 行为倾向
    """
    __tablename__ = "personality_loadouts"
    __table_args__ = (
        Index("ix_personality_loadouts_character", "character_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    character_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    
    # 名字和版本
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # 大五人格分数 (0-100)
    big_five_openness: Mapped[float] = mapped_column(Float, default=50.0, nullable=False)
    big_five_conscientiousness: Mapped[float] = mapped_column(Float, default=50.0, nullable=False)
    big_five_extraversion: Mapped[float] = mapped_column(Float, default=50.0, nullable=False)
    big_five_agreeableness: Mapped[float] = mapped_column(Float, default=50.0, nullable=False)
    big_five_neuroticism: Mapped[float] = mapped_column(Float, default=50.0, nullable=False)
    
    # 核心特质 JSON
    core_traits: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # 格式: [{"type": "loyalty", "strength": 0.8, "description": "..."}]
    
    # 行为倾向
    behavioral_tendencies: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # 格式: {"aggression": 0.3, "risk_taking": 0.7, ...}
    
    # 心理模型
    psychological_model: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # 格式: {"fears": [...], "desires": [...], "secrets": [...], "habits": [...]}
    
    # 元数据
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)  # manual/llm/derived
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<PersonalityLoadout(id={self.id}, character_id={self.character_id}, name={self.name})>"


class PersonalityTraitInstance(Base):
    """Personality Trait Instance - 特质实例
    
    记录角色在特定上下文中展现的特质
    """
    __tablename__ = "personality_trait_instances"
    __table_args__ = (
        Index("ix_trait_instances_character", "character_id"),
        Index("ix_trait_instances_chapter", "chapter_number"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    character_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    
    # 特质信息
    trait_type: Mapped[TraitType] = mapped_column(Enum(TraitType), nullable=False)
    trait_category: Mapped[TraitCategory] = mapped_column(Enum(TraitCategory), nullable=False)
    strength: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)  # 0-1
    
    # 上下文
    chapter_number: Mapped[int] = mapped_column(Integer, nullable=True)
    context: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # 触发上下文
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<PersonalityTraitInstance(id={self.id}, char={self.character_id}, trait={self.trait_type})>"


class PersonalityEvolution(Base):
    """Personality Evolution - 性格演变记录
    
    记录角色性格的变化历史
    """
    __tablename__ = "personality_evolutions"
    __table_args__ = (
        Index("ix_personality_evolutions_character", "character_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    character_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    
    # 变化信息
    trait_type: Mapped[Optional[TraitType]] = mapped_column(Enum(TraitType), nullable=True)
    change_type: Mapped[str] = mapped_column(String(50), nullable=False)  # increase/decrease/emerged/faded
    
    # 变化前后
    before_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    after_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # 原因
    trigger_chapter: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    trigger_event: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 元数据
    source: Mapped[str] = mapped_column(String(50), default="llm", nullable=False)
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<PersonalityEvolution(id={self.id}, char={self.character_id}, change={self.change_type})>"