"""审查相关 Pydantic schemas"""
from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, Field

from app.models.review_note import IssueType, Severity


class ReviewIssue(BaseModel):
    """审查问题"""
    issue_type: IssueType
    severity: Severity
    description: str
    location: Optional[str] = None
    fix_suggestion: Optional[str] = None


class ReviewVerdict(BaseModel):
    """审查判决"""
    approved: bool
    score: float = Field(ge=0, le=10)
    issues: list[ReviewIssue] = []
    summary: str
    strengths: list[str] = []


class ReviewRequest(BaseModel):
    """审查请求"""
    check_types: Optional[list[str]] = None  # 可指定检查类型
    # consistency, outline_completion, pacing, hook


class ReviewNoteResponse(BaseModel):
    """审查记录响应"""
    id: int
    chapter_id: int
    issue_type: str
    severity: str
    description: str
    fix_suggestion: Optional[str] = None
    created_at: datetime
    # v2.7 新增字段
    forced_accept_applied: bool = False
    override_reason: Optional[str] = None
    rewrite_attempt_count: int = 0

    model_config = {"from_attributes": True}


class ReviewResponse(BaseModel):
    """审查响应"""
    chapter_id: int
    verdict: ReviewVerdict
    review_notes: list[ReviewNoteResponse] = []


class PartialReviewRequest(BaseModel):
    """部分审查请求"""
    segment_text: str
    segment_location: Optional[str] = None
    check_types: Optional[list[str]] = None


class RewriteInstructionsResponse(BaseModel):
    """重写指令响应"""
    chapter_id: int
    instructions: str
    prioritized_fixes: list[str] = []


# ========================================
# v2.7 新增 schemas
# ========================================

class RepairInstructionSchema(BaseModel):
    """修复指令 schema"""
    repair_scope: str  # scene/band/arc
    failure_type: str
    must_fix: list[str] = Field(default_factory=list)
    must_preserve: list[str] = Field(default_factory=list)
    design_patch: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[str] = Field(default_factory=list)
    priority: int = 1


class RewriteAttemptResponse(BaseModel):
    """重写尝试响应"""
    id: int
    project_id: int
    chapter_id: int
    chapter_number: int
    attempt_no: int
    repair_scope: str
    result_verdict: Optional[str] = None
    forced_accept_applied: bool = False
    repair_instruction_summary: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ExperienceScoresSchema(BaseModel):
    """体验评分 schema"""
    engagement: float = 0.5
    pacing: float = 0.5
    emotional_impact: float = 0.5
    reader_satisfaction: float = 0.5
    coherence: float = 0.5


class ReviewVerdictV3Response(BaseModel):
    """v2.7 扩展审查响应"""
    verdict: str
    verdict_reason: str
    recommended_action: Optional[str] = None
    review_summary: str = ""
    issues: list[dict] = Field(default_factory=list)
    planned_reward_tags: list[str] = Field(default_factory=list)
    delivered_reward_tags: list[str] = Field(default_factory=list)
    experience_scores: ExperienceScoresSchema = Field(default_factory=ExperienceScoresSchema)
    repair_instruction: Optional[RepairInstructionSchema] = None
    force_accept_recommended: bool = False
    forced_accept_applied: bool = False
    override_reason: Optional[str] = None
    scores: dict[str, float] = Field(default_factory=dict)
    rewrite_attempt_count: int = 0
