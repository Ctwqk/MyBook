"""审查相关 Pydantic schemas"""
from datetime import datetime
from typing import Optional

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
