"""Historical Review Hub - v2.7 新增

历史审查中心：
整合 ContinuityChecker、WebNovelExperienceReviewer 和可选的 lint 适配器
"""
from typing import Any, Optional
from datetime import datetime

from app.services.reviewer.v2_7_experience_overlay import (
    ReviewVerdictV3,
    RepairInstruction,
    ChapterExperiencePlan,
)
from app.services.reviewer.web_novel_reviewer import (
    WebNovelExperienceReviewer,
    WebNovelExperienceReviewOutput,
)


class ContinuityChecker:
    """连续性检查器"""
    
    def __init__(self, llm_provider=None):
        self.llm = llm_provider
    
    async def check_consistency(
        self,
        chapter_text: str,
        chapter_no: int,
        context: dict[str, Any]
    ) -> dict[str, Any]:
        """
        检查章节连续性
        
        Args:
            chapter_text: 章节正文
            chapter_no: 章节号
            context: 上下文信息
            
        Returns:
            dict: 连续性检查结果
        """
        # TODO: 实现完整的连续性检查
        # 目前返回基本结果
        return {
            "consistent": True,
            "issues": [],
            "warnings": []
        }


class LintAdapter:
    """Lint 适配器基类"""
    
    def __init__(self, name: str):
        self.name = name
        self.available = False
    
    async def run(self, text: str) -> dict[str, Any]:
        """运行 lint 检查"""
        return {"available": False, "issues": []}


class ValeAdapter(LintAdapter):
    """Vale lint 适配器"""
    
    def __init__(self):
        super().__init__("vale")
        # 检查 Vale 是否可用
        import shutil
        self.available = shutil.which("vale") is not None


class TextlintAdapter(LintAdapter):
    """Textlint 适配器"""
    
    def __init__(self):
        super().__init__("textlint")
        import shutil
        self.available = shutil.which("textlint") is not None


class LanguageToolAdapter(LintAdapter):
    """LanguageTool 适配器"""
    
    def __init__(self):
        super().__init__("languagetool")
        # LanguageTool 可能需要网络访问
        self.available = True  # 假设可用


class ReviewdogStyleAdapter(LintAdapter):
    """Reviewdog 风格适配器"""
    
    def __init__(self):
        super().__init__("reviewdog")
        import shutil
        self.available = shutil.which("reviewdog") is not None


class HistoricalReviewHub:
    """历史审查中心 - v2.7
    
    整合多种审查器：
    - ContinuityChecker: 连续性检查
    - WebNovelExperienceReviewer: 网文体验审查
    - Lint 适配器: 风格检查（可选）
    """
    
    def __init__(
        self,
        llm_provider=None,
        enable_lint: bool = False,
        lint_adapters: Optional[list[str]] = None
    ):
        self.llm = llm_provider
        
        # 初始化审查器
        self.continuity_checker = ContinuityChecker(llm_provider)
        self.wner = WebNovelExperienceReviewer(llm_provider)
        
        # 初始化 lint 适配器
        self.lint_adapters: dict[str, LintAdapter] = {}
        if enable_lint:
            self._init_lint_adapters(lint_adapters or ["vale", "textlint"])
    
    def _init_lint_adapters(self, adapter_names: list[str]):
        """初始化 lint 适配器"""
        adapter_map = {
            "vale": ValeAdapter,
            "textlint": TextlintAdapter,
            "languagetool": LanguageToolAdapter,
            "reviewdog": ReviewdogStyleAdapter
        }
        
        for name in adapter_names:
            if name in adapter_map:
                adapter = adapter_map[name]()
                self.lint_adapters[name] = adapter
    
    async def review_chapter(
        self,
        chapter_text: str,
        chapter_no: int,
        chapter_id: int,
        context: dict[str, Any],
        planned_experience: Optional[dict[str, Any]] = None,
        previous_verdict: Optional[ReviewVerdictV3] = None
    ) -> ReviewVerdictV3:
        """
        完整的章节审查
        
        Args:
            chapter_text: 章节正文
            chapter_no: 章节号
            chapter_id: 章节 ID
            context: 上下文信息
            planned_experience: 计划的体验内容
            previous_verdict: 上一次审查结果（用于重写后审查）
            
        Returns:
            ReviewVerdictV3: 综合审查结果
        """
        all_issues = []
        all_scores = {
            "consistency": 1.0,
            "pacing": 1.0,
            "hook": 1.0,
            "overall": 1.0
        }
        experience_scores = {
            "engagement": 0.5,
            "pacing": 0.5,
            "emotional_impact": 0.5,
            "reader_satisfaction": 0.5,
            "coherence": 0.5
        }
        
        # 1. 连续性检查
        continuity_result = await self.continuity_checker.check_consistency(
            chapter_text, chapter_no, context
        )
        
        if not continuity_result.get("consistent", True):
            all_issues.extend(continuity_result.get("issues", []))
            all_scores["consistency"] = 0.7
        
        # 2. 体验审查（v2.7 新增）
        experience_output: Optional[WebNovelExperienceReviewOutput] = None
        if planned_experience:
            experience_output = await self.wner.review_chapter_experience(
                chapter_text, chapter_no, planned_experience, context
            )
            
            # 更新体验评分
            experience_scores["engagement"] = experience_output.engagement_score
            experience_scores["pacing"] = experience_output.pacing_score
            experience_scores["emotional_impact"] = experience_output.emotional_impact_score
            experience_scores["reader_satisfaction"] = experience_output.satisfaction_score
            
            # 添加体验问题
            all_issues.extend(experience_output.experience_issues)
        
        # 3. Lint 检查（可选）
        lint_issues = []
        for adapter in self.lint_adapters.values():
            if adapter.available:
                lint_result = await adapter.run(chapter_text)
                lint_issues.extend(lint_result.get("issues", []))
        
        if lint_issues:
            all_issues.extend(lint_issues)
            all_scores["overall"] = max(0.5, all_scores["overall"] - 0.1)
        
        # 4. 综合评分
        all_scores["overall"] = min(all_scores.values())
        
        # 5. 确定 verdict
        verdict, verdict_reason = self._determine_verdict(
            all_issues, all_scores, experience_output, previous_verdict
        )
        
        # 6. 生成修复指令（如需要）
        repair_instruction = None
        if verdict == "fail":
            repair_instruction = self._generate_repair_instruction(
                all_issues, experience_output
            )
        
        # 7. 确定推荐动作
        recommended_action = self._determine_recommended_action(verdict, repair_instruction)
        
        # 构建审查摘要
        review_summary = self._build_review_summary(
            all_issues, all_scores, experience_scores
        )
        
        # 收集已实现和计划的奖励标签
        planned_tags = []
        delivered_tags = []
        if planned_experience:
            planned_tags = planned_experience.get("planned_reward_tags", [])
        if experience_output:
            delivered_tags = experience_output.delivered_reward_tags
        
        return ReviewVerdictV3(
            verdict=verdict,
            verdict_reason=verdict_reason,
            recommended_action=recommended_action,
            review_summary=review_summary,
            issues=all_issues,
            planned_reward_tags=planned_tags,
            delivered_reward_tags=delivered_tags,
            experience_scores=experience_scores,
            repair_instruction=repair_instruction,
            scores=all_scores,
            parse_success=True
        )
    
    def _determine_verdict(
        self,
        issues: list[dict],
        scores: dict[str, float],
        experience_output: Optional[WebNovelExperienceReviewOutput],
        previous_verdict: Optional[ReviewVerdictV3]
    ) -> tuple[str, str]:
        """确定审查 verdict"""
        high_severity_count = sum(
            1 for i in issues 
            if i.get("severity") in ["high", "critical"]
        )
        
        # 严重问题或低分
        if high_severity_count >= 3:
            return "fail", f"发现 {high_severity_count} 个严重问题"
        
        if scores.get("overall", 1.0) < 0.6:
            return "fail", f"综合评分过低: {scores['overall']:.2f}"
        
        # 体验问题
        if experience_output:
            if experience_output.satisfaction_score < 0.4:
                return "fail", f"读者满意度过低: {experience_output.satisfaction_score:.2f}"
            if len(experience_output.missing_reward_tags) >= 3:
                return "fail", f"缺少 {len(experience_output.missing_reward_tags)} 个奖励标签"
        
        # 警告级别
        medium_severity_count = sum(
            1 for i in issues 
            if i.get("severity") == "medium"
        )
        
        if medium_severity_count >= 5:
            return "warn", f"发现 {medium_severity_count} 个中等问题"
        
        if scores.get("overall", 1.0) < 0.8:
            return "warn", f"综合评分偏低: {scores['overall']:.2f}"
        
        # 通过
        return "pass", "章节通过审查"
    
    def _generate_repair_instruction(
        self,
        issues: list[dict],
        experience_output: Optional[WebNovelExperienceReviewOutput]
    ) -> RepairInstruction:
        """生成修复指令"""
        must_fix = []
        evidence_refs = []
        
        for issue in issues:
            if issue.get("severity") in ["high", "critical"]:
                must_fix.append(issue.get("description", issue.get("issue", "")))
                if issue.get("location"):
                    evidence_refs.append(f"{issue.get('location')}: {issue.get('description', '')}")
        
        # 从体验输出中提取修复建议
        repair_suggestions = []
        if experience_output:
            repair_suggestions = experience_output.repair_suggestions
            evidence_refs.extend(experience_output.evidence_refs)
        
        # 确定修复范围
        repair_scope = "scene"
        if len(must_fix) > 10:
            repair_scope = "band"
        if len(must_fix) > 20:
            repair_scope = "arc"
        
        # 确定失败类型
        failure_type = "consistency"
        if experience_output:
            if experience_output.satisfaction_score < 0.3:
                failure_type = "emotional_impact"
            elif len(experience_output.missing_reward_tags) > 0:
                failure_type = "reward_beat"
        
        return RepairInstruction(
            repair_scope=repair_scope,
            failure_type=failure_type,
            must_fix=must_fix[:20],  # 限制数量
            must_preserve=[],
            design_patch={"suggestions": repair_suggestions},
            evidence_refs=evidence_refs[:10],
            priority=3 if len(must_fix) > 5 else 2
        )
    
    def _determine_recommended_action(
        self,
        verdict: str,
        repair_instruction: Optional[RepairInstruction]
    ) -> str:
        """确定推荐动作"""
        if verdict == "pass":
            return "accept"
        elif verdict == "warn":
            return "accept_with_warning"
        elif verdict == "fail" and repair_instruction:
            scope = repair_instruction.repair_scope
            if scope == "scene":
                return "rewrite"
            else:
                return "repair"
        return "stop"
    
    def _build_review_summary(
        self,
        issues: list[dict],
        scores: dict[str, float],
        experience_scores: dict[str, float]
    ) -> str:
        """构建审查摘要"""
        summary_parts = []
        
        # 问题摘要
        high_count = sum(1 for i in issues if i.get("severity") == "high")
        medium_count = sum(1 for i in issues if i.get("severity") == "medium")
        low_count = sum(1 for i in issues if i.get("severity") == "low")
        
        if issues:
            summary_parts.append(f"发现问题: 高{high_count}个, 中{medium_count}个, 低{low_count}个")
        
        # 评分摘要
        summary_parts.append(f"综合评分: {scores.get('overall', 0):.2f}")
        
        # 体验摘要
        summary_parts.append(
            f"读者体验: 参与度{experience_scores.get('engagement', 0):.2f}, "
            f"情感冲击{experience_scores.get('emotional_impact', 0):.2f}, "
            f"满意度{experience_scores.get('reader_satisfaction', 0):.2f}"
        )
        
        return "; ".join(summary_parts)
