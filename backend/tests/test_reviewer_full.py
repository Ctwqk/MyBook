"""完整的 Reviewer Service 测试"""
import pytest
from pydantic import BaseModel

from app.models.review_note import IssueType, Severity
from app.schemas.review import (
    ReviewIssue,
    ReviewVerdict,
    ReviewRequest,
    ReviewResponse,
    PartialReviewRequest,
    RewriteInstructionsResponse,
)


class TestReviewSchemas:
    """Review Schemas 测试"""
    
    def test_review_issue_full(self):
        """测试完整审查问题"""
        issue = ReviewIssue(
            issue_type=IssueType.CONSISTENCY,
            severity=Severity.HIGH,
            description="角色性格前后不一致",
            location="第3段",
            fix_suggestion="统一调整为沉稳内敛"
        )
        
        assert issue.issue_type == IssueType.CONSISTENCY
        assert issue.severity == Severity.HIGH
        assert issue.location == "第3段"
    
    def test_review_issue_minimal(self):
        """测试最小审查问题"""
        issue = ReviewIssue(
            issue_type=IssueType.PACING,
            severity=Severity.LOW,
            description="节奏稍慢"
        )
        
        assert issue.location is None
        assert issue.fix_suggestion is None
    
    def test_review_verdict_approved(self):
        """测试审查通过判决"""
        verdict = ReviewVerdict(
            approved=True,
            score=9.0,
            issues=[],
            summary="章节质量优秀",
            strengths=["文笔流畅", "情节紧凑", "人物鲜明"]
        )
        
        assert verdict.approved is True
        assert verdict.score == 9.0
        assert len(verdict.issues) == 0
        assert len(verdict.strengths) == 3
    
    def test_review_verdict_with_issues(self):
        """测试带问题的审查判决"""
        issues = [
            ReviewIssue(
                issue_type=IssueType.PACING,
                severity=Severity.MEDIUM,
                description="节奏问题"
            ),
            ReviewIssue(
                issue_type=IssueType.DIALOGUE,
                severity=Severity.LOW,
                description="对话生硬"
            )
        ]
        
        verdict = ReviewVerdict(
            approved=True,
            score=7.5,
            issues=issues,
            summary="有小问题但整体良好"
        )
        
        assert verdict.approved is True
        assert len(verdict.issues) == 2
        assert verdict.issues[0].severity == Severity.MEDIUM
    
    def test_review_verdict_rejected(self):
        """测试审查未通过判决"""
        verdict = ReviewVerdict(
            approved=False,
            score=4.0,
            issues=[
                ReviewIssue(
                    issue_type=IssueType.CONSISTENCY,
                    severity=Severity.CRITICAL,
                    description="严重一致性问题"
                )
            ],
            summary="存在严重问题，需要大幅修改"
        )
        
        assert verdict.approved is False
        assert verdict.score == 4.0
    
    def test_review_request_defaults(self):
        """测试审查请求默认值"""
        request = ReviewRequest()
        
        assert request.check_types is None
    
    def test_review_request_specific(self):
        """测试指定检查类型的审查请求"""
        request = ReviewRequest(
            check_types=["consistency", "pacing", "hook"]
        )
        
        assert len(request.check_types) == 3
        assert "consistency" in request.check_types
    
    def test_partial_review_request(self):
        """测试部分审查请求"""
        request = PartialReviewRequest(
            segment_text="要审查的段落内容...",
            segment_location="第5段 3-5行",
            check_types=["pacing", "dialogue"]
        )
        
        assert "第5段" in request.segment_location
        assert len(request.check_types) == 2
    
    def test_rewrite_instructions_response(self):
        """测试重写指令响应"""
        response = RewriteInstructionsResponse(
            chapter_id=1,
            instructions="1. 改善对话 2. 精简旁白",
            prioritized_fixes=[
                "对话不自然",
                "节奏过慢",
                "环境描写不足"
            ]
        )
        
        assert response.chapter_id == 1
        assert len(response.prioritized_fixes) == 3


class TestReviewIssueTypes:
    """审查问题类型测试"""
    
    def test_all_issue_types(self):
        """测试所有问题类型"""
        expected_types = [
            "consistency",
            "plot_hole",
            "pacing",
            "character",
            "dialogue",
            "description",
            "hook",
            "other"
        ]
        
        for type_str in expected_types:
            assert hasattr(IssueType, type_str.upper())
    
    def test_issue_type_values(self):
        """测试问题类型值"""
        assert IssueType.CONSISTENCY == "consistency"
        assert IssueType.PLOT_HOLE == "plot_hole"
        assert IssueType.PACING == "pacing"
        assert IssueType.HOOK == "hook"


class TestReviewSeverity:
    """审查严重级别测试"""
    
    def test_all_severity_levels(self):
        """测试所有严重级别"""
        assert Severity.LOW == "low"
        assert Severity.MEDIUM == "medium"
        assert Severity.HIGH == "high"
        assert Severity.CRITICAL == "critical"
    
    def test_severity_order(self):
        """测试严重级别排序"""
        severity_values = {
            Severity.LOW: 1,
            Severity.MEDIUM: 2,
            Severity.HIGH: 3,
            Severity.CRITICAL: 4
        }
        
        assert severity_values[Severity.CRITICAL] > severity_values[Severity.HIGH]
        assert severity_values[Severity.HIGH] > severity_values[Severity.MEDIUM]
        assert severity_values[Severity.MEDIUM] > severity_values[Severity.LOW]


class TestReviewPrompts:
    """Review Prompts 测试"""
    
    def test_chapter_review_prompt_format(self):
        """测试章节审查 prompt 格式"""
        from app.services.reviewer.prompts import CHAPTER_REVIEW_PROMPT
        
        prompt = CHAPTER_REVIEW_PROMPT.format(
            chapter_no=1,
            title="第一章",
            text="章节正文...",
            outline="章节大纲",
            context="上下文",
            check_types="consistency, pacing, hook"
        )
        
        assert "第 1 章" in prompt
        assert "consistency, pacing, hook" in prompt
    
    def test_partial_review_prompt_format(self):
        """测试部分审查 prompt 格式"""
        from app.services.reviewer.prompts import PARTIAL_REVIEW_PROMPT
        
        prompt = PARTIAL_REVIEW_PROMPT.format(
            segment_text="段落内容",
            segment_location="第5段",
            check_types="pacing, dialogue"
        )
        
        assert "段落内容" in prompt
        assert "第5段" in prompt
    
    def test_rewrite_instructions_prompt_format(self):
        """测试重写指令 prompt 格式"""
        from app.services.reviewer.prompts import REWRITE_INSTRUCTIONS_PROMPT
        
        prompt = REWRITE_INSTRUCTIONS_PROMPT.format(
            chapter_no=1,
            issues="1. 问题1\n2. 问题2",
            existing_text="现有内容..."
        )
        
        assert "第 1 章" in prompt
        assert "问题1" in prompt


class TestReviewPromptsStructure:
    """Review Prompts 结构测试"""
    
    def test_all_prompts_exist(self):
        """测试所有 reviewer prompts 存在"""
        from app.services.reviewer import prompts
        
        assert hasattr(prompts, 'CHAPTER_REVIEW_PROMPT')
        assert hasattr(prompts, 'PARTIAL_REVIEW_PROMPT')
        assert hasattr(prompts, 'REWRITE_INSTRUCTIONS_PROMPT')
    
    def test_prompts_not_empty(self):
        """测试 prompts 内容不为空"""
        from app.services.reviewer.prompts import (
            CHAPTER_REVIEW_PROMPT,
            PARTIAL_REVIEW_PROMPT,
            REWRITE_INSTRUCTIONS_PROMPT,
        )
        
        for prompt in [CHAPTER_REVIEW_PROMPT, PARTIAL_REVIEW_PROMPT, REWRITE_INSTRUCTIONS_PROMPT]:
            assert len(prompt) > 30


class TestReviewWorkflow:
    """审查工作流测试"""
    
    def test_review_with_all_checks(self):
        """测试全项审查"""
        request = ReviewRequest(
            check_types=["consistency", "pacing", "hook", "character"]
        )
        
        assert len(request.check_types) == 4
    
    def test_review_with_single_check(self):
        """测试单项审查"""
        request = ReviewRequest(check_types=["consistency"])
        
        assert request.check_types == ["consistency"]
    
    def test_verdict_scoring(self):
        """测试评分系统"""
        # 优秀
        excellent = ReviewVerdict(approved=True, score=9.5, issues=[], summary="优秀")
        assert excellent.score >= 9.0
        
        # 良好
        good = ReviewVerdict(approved=True, score=7.5, issues=[], summary="良好")
        assert 7.0 <= good.score < 9.0
        
        # 及格
        pass_score = ReviewVerdict(approved=True, score=6.0, issues=[], summary="及格")
        assert 6.0 <= pass_score.score < 7.0
        
        # 不及格
        fail = ReviewVerdict(approved=False, score=4.0, issues=[], summary="不及格")
        assert fail.score < 6.0
