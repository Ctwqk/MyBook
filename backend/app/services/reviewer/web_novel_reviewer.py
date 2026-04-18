"""Web Novel Experience Reviewer - v2.7 新增

网络小说体验审查器：
- 评估章节的读者体验质量
- 检查奖励节拍（reward beat）是否到位
- 评估沉浸感和进度标记
- 生成修复指令
"""
from typing import Any, Optional
from pydantic import BaseModel, Field

from app.services.reviewer.v2_7_experience_overlay import (
    RewardBeatTag,
    RewardCategory,
    RepairInstruction,
    ReviewVerdictV3,
    ImmersionAnchor,
    ProgressMarker,
)


class WebNovelExperienceReviewOutput(BaseModel):
    """网文体验审查输出"""
    # 体验评分
    engagement_score: float = Field(ge=0, le=1)
    pacing_score: float = Field(ge=0, le=1)
    emotional_impact_score: float = Field(ge=0, le=1)
    satisfaction_score: float = Field(ge=0, le=1)
    
    # 奖励标签分析
    delivered_reward_tags: list[RewardBeatTag] = Field(default_factory=list)
    missing_reward_tags: list[RewardBeatTag] = Field(default_factory=list)
    
    # 问题列表
    experience_issues: list[dict] = Field(default_factory=list)
    
    # 修复建议
    repair_suggestions: list[str] = Field(default_factory=list)
    
    # 证据引用
    evidence_refs: list[str] = Field(default_factory=list)
    
    # 沉浸锚点评估
    immersion_anchor_evaluation: dict[str, Any] = Field(default_factory=dict)
    
    # 进度标记评估
    progress_marker_evaluation: dict[str, Any] = Field(default_factory=dict)


class WebNovelExperienceReviewer:
    """网络小说体验审查器 - v2.7"""
    
    def __init__(self, llm_provider=None):
        self.llm = llm_provider
    
    async def review_chapter_experience(
        self,
        chapter_text: str,
        chapter_no: int,
        planned_experience: dict[str, Any],
        context: Optional[dict[str, Any]] = None
    ) -> WebNovelExperienceReviewOutput:
        """
        审查章节的读者体验
        
        Args:
            chapter_text: 章节正文
            chapter_no: 章节号
            planned_experience: 计划的体验内容
            context: 额外上下文
            
        Returns:
            WebNovelExperienceReviewOutput: 体验审查结果
        """
        # 构建审查提示
        prompt = self._build_experience_review_prompt(
            chapter_text, chapter_no, planned_experience, context
        )
        
        if self.llm:
            response = await self.llm.generate(prompt, system_prompt=self._get_system_prompt())
            content = self._clean_response(response.content)
            return self._parse_review_output(content)
        
        # 无 LLM 时返回默认结果
        return self._default_review_output()
    
    def _get_system_prompt(self) -> str:
        return """你是一个专业的网络小说体验评估师。
        
你的任务是评估章节的读者体验质量，特别关注：
1. 奖励节拍（reward beat）是否到位
2. 沉浸感是否足够
3. 进度标记是否清晰
4. 读者是否获得满足感

请严格按照 JSON 格式输出评估结果。"""
    
    def _build_experience_review_prompt(
        self,
        chapter_text: str,
        chapter_no: int,
        planned_experience: dict[str, Any],
        context: Optional[dict[str, Any]]
    ) -> str:
        planned_tags = planned_experience.get("planned_reward_tags", [])
        immersion_anchors = planned_experience.get("immersion_anchors", [])
        progress_markers = planned_experience.get("progress_markers", [])
        
        return f"""请评估第{chapter_no}章的读者体验质量。

【章节正文】（部分）
{chapter_text[:3000]}

【计划的奖励标签】
{', '.join([tag.value if hasattr(tag, 'value') else str(tag) for tag in planned_tags]) if planned_tags else '无'}

【计划的沉浸锚点】
{'; '.join([a.get('description', '') for a in immersion_anchors]) if immersion_anchors else '无'}

【计划的进度标记】
{'; '.join([p.get('title', '') for p in progress_markers]) if progress_markers else '无'}

请分析本章实际提供的奖励标签，评估缺失的体验元素，并给出修复建议。

请以 JSON 格式输出：
{{
    "engagement_score": 0.0-1.0,
    "pacing_score": 0.0-1.0,
    "emotional_impact_score": 0.0-1.0,
    "satisfaction_score": 0.0-1.0,
    "delivered_reward_tags": ["tag1", "tag2"],
    "missing_reward_tags": ["tag3"],
    "experience_issues": [
        {{"issue": "描述", "severity": "high/medium/low", "location": "位置"}}
    ],
    "repair_suggestions": ["建议1", "建议2"],
    "evidence_refs": ["引用1", "引用2"],
    "immersion_anchor_evaluation": {{"found": [], "missing": []}},
    "progress_marker_evaluation": {{"delivered": [], "missing": []}}
}}"""
    
    def _clean_response(self, content: str) -> str:
        """清理 LLM 输出"""
        import re
        # 移除思考标签
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
        content = re.sub(r'<thinking>.*?</thinking>', '', content, flags=re.DOTALL)
        return content.strip()
    
    def _parse_review_output(self, content: str) -> WebNovelExperienceReviewOutput:
        """解析审查输出"""
        import json
        import re
        
        try:
            # 尝试提取 JSON
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                data = json.loads(json_match.group(0))
                
                # 转换奖励标签
                delivered_tags = []
                for tag_str in data.get("delivered_reward_tags", []):
                    try:
                        delivered_tags.append(RewardBeatTag(tag_str))
                    except ValueError:
                        pass
                
                missing_tags = []
                for tag_str in data.get("missing_reward_tags", []):
                    try:
                        missing_tags.append(RewardBeatTag(tag_str))
                    except ValueError:
                        pass
                
                return WebNovelExperienceReviewOutput(
                    engagement_score=data.get("engagement_score", 0.5),
                    pacing_score=data.get("pacing_score", 0.5),
                    emotional_impact_score=data.get("emotional_impact_score", 0.5),
                    satisfaction_score=data.get("satisfaction_score", 0.5),
                    delivered_reward_tags=delivered_tags,
                    missing_reward_tags=missing_tags,
                    experience_issues=data.get("experience_issues", []),
                    repair_suggestions=data.get("repair_suggestions", []),
                    evidence_refs=data.get("evidence_refs", []),
                    immersion_anchor_evaluation=data.get("immersion_anchor_evaluation", {}),
                    progress_marker_evaluation=data.get("progress_marker_evaluation", {})
                )
        except (json.JSONDecodeError, KeyError):
            pass
        
        return self._default_review_output()
    
    def _default_review_output(self) -> WebNovelExperienceReviewOutput:
        """默认审查输出"""
        return WebNovelExperienceReviewOutput(
            engagement_score=0.5,
            pacing_score=0.5,
            emotional_impact_score=0.5,
            satisfaction_score=0.5,
            delivered_reward_tags=[],
            missing_reward_tags=[],
            experience_issues=[],
            repair_suggestions=[],
            evidence_refs=[]
        )
    
    def generate_repair_instruction(
        self,
        review_output: WebNovelExperienceReviewOutput,
        failure_type: str,
        repair_scope: str
    ) -> RepairInstruction:
        """
        根据审查输出生成修复指令
        
        Args:
            review_output: 审查输出
            failure_type: 失败类型
            repair_scope: 修复范围 (scene/band/arc)
            
        Returns:
            RepairInstruction: 修复指令
        """
        must_fix = []
        must_preserve = []
        
        # 从问题中提取必须修复项
        for issue in review_output.experience_issues:
            if issue.get("severity") in ["high", "critical"]:
                must_fix.append(issue.get("issue", ""))
        
        # 保留已实现的奖励标签
        for tag in review_output.delivered_reward_tags:
            must_preserve.append(f"reward_beat:{tag.value if hasattr(tag, 'value') else str(tag)}")
        
        # 构建设计补丁
        design_patch = {
            "suggested_reward_tags": [
                tag.value if hasattr(tag, 'value') else str(tag) 
                for tag in review_output.missing_reward_tags
            ],
            "repair_suggestions": review_output.repair_suggestions,
            "experience_scores": {
                "engagement": review_output.engagement_score,
                "pacing": review_output.pacing_score,
                "emotional_impact": review_output.emotional_impact_score,
                "satisfaction": review_output.satisfaction_score
            }
        }
        
        return RepairInstruction(
            repair_scope=repair_scope,
            failure_type=failure_type,
            must_fix=must_fix,
            must_preserve=must_preserve,
            design_patch=design_patch,
            evidence_refs=review_output.evidence_refs,
            priority=3 if len(must_fix) > 3 else 2
        )
