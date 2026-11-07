"""World Edges Model - BookState 世界关系

50种边类型，分8类：
- organization: member_of, leader_of, subordinate_to, branch_of, part_of
- possession: owns, possesses, equipped_with, bound_to, created_by, grants_ability
- control_conflict: controls, governs, claims, occupies, protects, besieges, blockades
- social: family_of, ally_of, enemy_of, mentor_of, romantic_with, trusts, distrusts, owes_debt_to
- capability_rule: has_ability, uses, requires, counters, weak_against, forbidden_by
- event_causal: participates_in, witnesses, causes, prevents, enables, results_in, damages
- fact_evidence: supports, contradicts, evidence_for, proves, disproves
- activity_objective: organizes, hosts, competes_in, rewards, targets, advances_objective
"""
import enum
from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text, func, JSON, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class EdgeType(str, enum.Enum):
    # Organization
    MEMBER_OF = "member_of"
    LEADER_OF = "leader_of"
    SUBORDINATE_TO = "subordinate_to"
    BRANCH_OF = "branch_of"
    PART_OF = "part_of"
    
    # Possession
    OWNS = "owns"
    POSSESSES = "possesses"
    EQUIPPED_WITH = "equipped_with"
    BOUND_TO = "bound_to"
    CREATED_BY = "created_by"
    GRANTS_ABILITY = "grants_ability"
    
    # Control/Conflict
    CONTROLS = "controls"
    GOVERNS = "governs"
    CLAIMS = "claims"
    OCCUPIES = "occupies"
    PROTECTS = "protects"
    BESIEGES = "besieges"
    BLOCKADES = "blockades"
    
    # Social
    FAMILY_OF = "family_of"
    ALLY_OF = "ally_of"
    ENEMY_OF = "enemy_of"
    MENTOR_OF = "mentor_of"
    ROMANTIC_WITH = "romantic_with"
    TRUSTS = "trusts"
    DISTRUSTS = "distrusts"
    OWES_DEBT_TO = "owes_debt_to"
    
    # Capability/Rule
    HAS_ABILITY = "has_ability"
    USES = "uses"
    REQUIRES = "requires"
    COUNTERS = "counters"
    WEAK_AGAINST = "weak_against"
    FORBIDDEN_BY = "forbidden_by"
    
    # Event/Causal
    PARTICIPATES_IN = "participates_in"
    WITNESSES = "witnesses"
    CAUSES = "causes"
    PREVENTS = "prevents"
    ENABLES = "enables"
    RESULTS_IN = "results_in"
    DAMAGES = "damages"
    
    # Fact/Evidence
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    EVIDENCE_FOR = "evidence_for"
    PROVES = "proves"
    DISPROVES = "disproves"
    
    # Activity/Objective
    ORGANIZES = "organizes"
    HOSTS = "hosts"
    COMPETES_IN = "competes_in"
    REWARDS = "rewards"
    TARGETS = "targets"
    ADVANCES_OBJECTIVE = "advances_objective"


class EdgeFamily(str, enum.Enum):
    ORGANIZATION = "organization"
    POSSESSION = "possession"
    CONTROL_CONFLICT = "control_conflict"
    SOCIAL = "social"
    CAPABILITY_RULE = "capability_rule"
    EVENT_CAUSAL = "event_causal"
    FACT_EVIDENCE = "fact_evidence"
    ACTIVITY_OBJECTIVE = "activity_objective"


class Directionality(str, enum.Enum):
    DIRECTED = "directed"      # 有向：source -> target
    BIDIRECTED = "bidirected"  # 双向：source <-> target
    UNDIRECTED = "undirected"  # 无向：source -- target


class WorldEdge(Base):
    __tablename__ = "world_edges"
    __table_args__ = (
        Index("ix_world_edges_project_source", "project_id", "source_id"),
        Index("ix_world_edges_project_target", "project_id", "target_id"),
        Index("ix_world_edges_project_type", "project_id", "edge_type"),
        Index("ix_world_edges_project_active", "project_id", "is_active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    
    # 关系两端
    source_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("world_nodes.id", ondelete="CASCADE"), nullable=False
    )
    target_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("world_nodes.id", ondelete="CASCADE"), nullable=False
    )
    
    # 边类型
    edge_type: Mapped[EdgeType] = mapped_column(Enum(EdgeType), nullable=False)
    edge_family: Mapped[EdgeFamily] = mapped_column(Enum(EdgeFamily), nullable=False)
    directionality: Mapped[Directionality] = mapped_column(
        Enum(Directionality), default=Directionality.DIRECTED, nullable=False
    )
    
    # 权重和置信度
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    
    # 生命周期
    established_at_chapter: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ended_at_chapter: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    
    # 可见性
    visibility_default: Mapped[str] = mapped_column(String(50), default="public", nullable=False)
    
    # 状态和证据
    state: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # active/weakened/broken
    evidence_refs: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project")
    source_node: Mapped["WorldNode"] = relationship(
        "WorldNode", foreign_keys=[source_id], back_populates="outgoing_edges"
    )
    target_node: Mapped["WorldNode"] = relationship(
        "WorldNode", foreign_keys=[target_id], back_populates="incoming_edges"
    )

    def __repr__(self) -> str:
        return f"<WorldEdge(id={self.id}, type={self.edge_type}, {self.source_id}->{self.target_id})>"


# Forward reference
from app.models.project import Project
from app.models.world_nodes import WorldNode