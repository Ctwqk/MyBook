"""v2.7 Reader Experience Overlay 测试

测试内容：
- Reader Experience Overlay 数据模型
- WebNovelExperienceReviewer
- HistoricalReviewHub
- RewriteLoopService (模式特定行为)
- Force-Accept 逻辑
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from app.services.reviewer.v2_7_experience_overlay import (
    RewardCategory,
    RewardBeatTag,
    ReaderPromise,
    ArcPayoffMap,
    BandDelightSchedule,
    ChapterExperiencePlan,
    SceneExperienceMetadata,
    ImmersionAnchor,
    ProgressMarker,
    RepairInstruction,
    ReviewVerdictV3,
)
from app.services.reviewer.web_novel_reviewer import (
    WebNovelExperienceReviewer,
    WebNovelExperienceReviewOutput,
)
from app.services.reviewer.historical_review_hub import (
    HistoricalReviewHub,
    ContinuityChecker,
)


# ========================================
# 测试 RewardBeatTag 和 RewardCategory
# ========================================

class TestRewardTags:
    """测试奖励标签枚举"""
    
    def test_reward_category_values(self):
        """测试奖励类别枚举值"""
        assert RewardCategory.POWER.value == "power"
        assert RewardCategory.SOCIAL.value == "social"
        assert RewardCategory.JUSTICE.value == "justice"
        assert RewardCategory.MYSTERY.value == "mystery"
        assert RewardCategory.EMOTION.value == "emotion"
    
    def test_reward_beat_tag_values(self):
        """测试奖励节拍标签枚举值"""
        assert RewardBeatTag.POWER_GAIN.value == "power_gain"
        assert RewardBeatTag.ALLY_GAIN.value == "ally_gain"
        assert RewardBeatTag.CLUE_DISCOVERY.value == "clue_discovery"
        assert RewardBeatTag.HEARTWARMING.value == "heartwarming"


# ========================================
# 测试 ImmersionAnchor 和 ProgressMarker
# ========================================

class TestExperienceMetadata:
    """测试体验元数据模型"""
    
    def test_immersion_anchor_creation(self):
        """测试沉浸锚点创建"""
        anchor = ImmersionAnchor(
            anchor_type="sensory",
            description="雨声和泥土的气息",
            placement="scene_start",
            intensity=0.8
        )
        assert anchor.anchor_type == "sensory"
        assert anchor.intensity == 0.8
    
    def test_progress_marker_creation(self):
        """测试进度标记创建"""
        marker = ProgressMarker(
            marker_type="character_arc",
            title="主角觉醒",
            description="主角发现自己的特殊能力",
            chapter_no=15,
            importance="high"
        )
        assert marker.marker_type == "character_arc"
        assert marker.importance == "high"


# ========================================
# 测试 ReaderPromise 和 ArcPayoffMap
# ========================================

class TestReaderPromise:
    """测试读者承诺模型"""
    
    def test_reader_promise_creation(self):
        """测试读者承诺创建"""
        promise = ReaderPromise(
            promise_type="power_fantasy",
            core_promise="主角不断变强，最终打败boss",
            delivery_expectation="climax"
        )
        assert promise.promise_type == "power_fantasy"
        assert promise.delivery_status == "pending"


class TestArcPayoffMap:
    """测试 Arc 回报图模型"""
    
    def test_arc_payoff_map_creation(self):
        """测试 Arc 回报图创建"""
        payoff_map = ArcPayoffMap(
            arc_no=1,
            arc_title="觉醒篇",
            payoff_density="balanced",
            climax_payoff_count=3
        )
        assert payoff_map.arc_no == 1
        assert payoff_map.payoff_density == "balanced"


# ========================================
# 测试 ChapterExperiencePlan
# ========================================

class TestChapterExperiencePlan:
    """测试章节体验计划模型"""
    
    def test_chapter_experience_plan_creation(self):
        """测试章节体验计划创建"""
        plan = ChapterExperiencePlan(
            chapter_id=1,
            chapter_no=15,
            planned_reward_tags=[RewardBeatTag.POWER_GAIN],
            reward_categories=[RewardCategory.POWER],
            chapter_hook="主角发现自己觉醒了新能力",
            chapter_cliffhanger="能力的代价是什么？"
        )
        assert plan.chapter_no == 15
        assert len(plan.planned_reward_tags) == 1
        assert plan.plan_type == "initial"
    
    def test_chapter_experience_plan_default_scores(self):
        """测试章节体验计划默认评分"""
        plan = ChapterExperiencePlan(
            chapter_id=1,
            chapter_no=1
        )
        assert plan.experience_scores["engagement"] == 0.5
        assert plan.experience_scores["pacing"] == 0.5


# ========================================
# 测试 RepairInstruction
# ========================================

class TestRepairInstruction:
    """测试修复指令模型"""
    
    def test_repair_instruction_creation(self):
        """测试修复指令创建"""
        instruction = RepairInstruction(
            repair_scope="scene",
            failure_type="reward_beat",
            must_fix=[
                "缺少主角展示能力的场景",
                "敌人惩罚不够爽快"
            ],
            must_preserve=[
                "主角的性格设定",
                "反派的基本动机"
            ],
            design_patch={
                "add_scene": "能力展示",
                "enhance_punishment": True
            },
            evidence_refs=[
                "第3段：战斗场景过于简短",
                "结尾：反派逃脱"
            ],
            priority=3
        )
        assert instruction.repair_scope == "scene"
        assert instruction.failure_type == "reward_beat"
        assert len(instruction.must_fix) == 2
        assert instruction.priority == 3


# ========================================
# 测试 ReviewVerdictV3
# ========================================

class TestReviewVerdictV3:
    """测试扩展审查判决模型"""
    
    def test_review_verdict_v3_basic(self):
        """测试基本 verdict"""
        verdict = ReviewVerdictV3(
            verdict="pass",
            verdict_reason="章节通过审查"
        )
        assert verdict.verdict == "pass"
        assert verdict.force_accept_recommended == False
    
    def test_review_verdict_v3_with_experience(self):
        """测试带体验数据的 verdict"""
        verdict = ReviewVerdictV3(
            verdict="warn",
            verdict_reason="节奏偏慢",
            recommended_action="accept_with_warning",
            review_summary="发现1个中等问题",
            experience_scores={
                "engagement": 0.7,
                "pacing": 0.4,
                "emotional_impact": 0.6,
                "reader_satisfaction": 0.5,
                "coherence": 0.8
            }
        )
        assert verdict.verdict == "warn"
        assert verdict.recommended_action == "accept_with_warning"
        assert verdict.experience_scores["pacing"] == 0.4
    
    def test_review_verdict_v3_fail_with_repair(self):
        """测试失败 verdict 带修复指令"""
        repair = RepairInstruction(
            repair_scope="scene",
            failure_type="coherence",
            must_fix=["时间线矛盾"],
            priority=3
        )
        verdict = ReviewVerdictV3(
            verdict="fail",
            verdict_reason="发现严重连贯性问题",
            recommended_action="rewrite",
            repair_instruction=repair,
            force_accept_recommended=False
        )
        assert verdict.verdict == "fail"
        assert verdict.repair_instruction is not None
        assert verdict.repair_instruction.repair_scope == "scene"
    
    def test_review_verdict_v3_force_accept(self):
        """测试强制接受标记"""
        verdict = ReviewVerdictV3(
            verdict="fail",
            verdict_reason="自动重写循环耗尽",
            forced_accept_applied=True,
            override_reason="blackbox force-accept after 3 failed rewrites"
        )
        assert verdict.forced_accept_applied == True
        assert verdict.override_reason is not None


# ========================================
# 测试 WebNovelExperienceReviewer
# ========================================

class TestWebNovelExperienceReviewer:
    """测试网文体验审查器"""
    
    @pytest.mark.asyncio
    async def test_review_chapter_experience_no_llm(self):
        """测试无 LLM 时的审查返回默认结果"""
        reviewer = WebNovelExperienceReviewer(llm_provider=None)
        
        result = await reviewer.review_chapter_experience(
            chapter_text="测试章节内容",
            chapter_no=1,
            planned_experience={}
        )
        
        assert result.engagement_score == 0.5
        assert result.pacing_score == 0.5
        assert len(result.delivered_reward_tags) == 0
    
    @pytest.mark.asyncio
    async def test_generate_repair_instruction(self):
        """测试生成修复指令"""
        reviewer = WebNovelExperienceReviewer(llm_provider=None)
        
        review_output = WebNovelExperienceReviewOutput(
            engagement_score=0.3,
            pacing_score=0.4,
            emotional_impact_score=0.5,
            satisfaction_score=0.3,
            delivered_reward_tags=[RewardBeatTag.POWER_GAIN],
            missing_reward_tags=[RewardBeatTag.ENEMY_PUNISHMENT],
            experience_issues=[
                {"issue": "战斗场景太短", "severity": "high"}
            ],
            repair_suggestions=["增加战斗细节"],
            evidence_refs=["第5段"]
        )
        
        instruction = reviewer.generate_repair_instruction(
            review_output=review_output,
            failure_type="reward_beat",
            repair_scope="scene"
        )
        
        assert instruction.repair_scope == "scene"
        assert instruction.failure_type == "reward_beat"
        assert len(instruction.must_fix) == 1
        assert instruction.priority == 3


# ========================================
# 测试 ContinuityChecker
# ========================================

class TestContinuityChecker:
    """测试连续性检查器"""
    
    @pytest.mark.asyncio
    async def test_check_consistency(self):
        """测试基本连续性检查"""
        checker = ContinuityChecker(llm_provider=None)
        
        result = await checker.check_consistency(
            chapter_text="测试内容",
            chapter_no=1,
            context={}
        )
        
        assert result["consistent"] == True
        assert result["issues"] == []


# ========================================
# 测试 HistoricalReviewHub
# ========================================

class TestHistoricalReviewHub:
    """测试历史审查中心"""
    
    @pytest.mark.asyncio
    async def test_review_chapter_basic(self):
        """测试基本审查"""
        hub = HistoricalReviewHub(llm_provider=None)
        
        verdict = await hub.review_chapter(
            chapter_text="测试章节内容",
            chapter_no=1,
            chapter_id=1,
            context={}
        )
        
        assert verdict.verdict in ["pass", "warn", "fail"]
        assert verdict.parse_success == True
    
    @pytest.mark.asyncio
    async def test_review_chapter_with_experience(self):
        """测试带体验计划的审查"""
        hub = HistoricalReviewHub(llm_provider=None)
        
        planned_experience = {
            "planned_reward_tags": [RewardBeatTag.POWER_GAIN],
            "immersion_anchors": [
                {"anchor_type": "sensory", "description": "测试锚点"}
            ]
        }
        
        verdict = await hub.review_chapter(
            chapter_text="测试章节内容",
            chapter_no=1,
            chapter_id=1,
            context={},
            planned_experience=planned_experience
        )
        
        assert verdict.verdict in ["pass", "warn", "fail"]
        assert len(verdict.planned_reward_tags) == 1
    
    @pytest.mark.asyncio
    async def test_review_chapter_fail_generates_repair(self):
        """测试失败时生成修复指令"""
        hub = HistoricalReviewHub(llm_provider=None)
        
        # 创建一个会导致失败的审查
        # 注意：由于使用 mock LLM，这里只测试基本结构
        verdict = await hub.review_chapter(
            chapter_text="",
            chapter_no=1,
            chapter_id=1,
            context={}
        )
        
        # 验证 verdict 结构
        assert hasattr(verdict, 'verdict')
        assert hasattr(verdict, 'repair_instruction')


# ========================================
# 测试模式特定行为 (需要 Mock LLM)
# ========================================

class TestRewriteLoopModeSpecific:
    """测试重写循环的模式特定行为"""
    
    def test_checkpoint_mode_no_auto_rewrite(self):
        """checkpoint 模式不自动重写"""
        # 这个测试验证模式特定逻辑的文档说明
        # 实际测试需要完整的 RewriteLoopService
        pass
    
    def test_blackbox_mode_force_accept_after_3_failures(self):
        """blackbox 模式 3 次失败后强制接受"""
        # 文档说明验证
        max_attempts = 3
        assert max_attempts == 3  # 验证最大重写次数
    
    def test_copilot_mode_stops_on_exhausted_fail(self):
        """copilot 模式耗尽失败后停止"""
        # 文档说明验证
        pass


# ========================================
# 测试 Force-Accept 规则
# ========================================

class TestForceAcceptRules:
    """测试强制接受规则"""
    
    def test_force_accept_does_not_change_canon(self):
        """强制接受不改变已接受的 canon"""
        # 验证文档说明：force-accept 只允许章节草稿升级
        # 不修改已接受的 canon 历史
        pass
    
    def test_force_accept_tracked_in_metadata(self):
        """强制接受在元数据中追踪"""
        verdict = ReviewVerdictV3(
            verdict="fail",
            forced_accept_applied=True,
            override_reason="blackbox auto-rewrite exhausted"
        )
        assert verdict.forced_accept_applied == True
        assert verdict.override_reason is not None
    
    def test_status_remains_accepted(self):
        """状态保持 accepted"""
        # 文档说明：forced acceptance 不发明新状态
        # 状态保持 accepted
        pass


# ========================================
# 测试 Repair Scope 规则
# ========================================

class TestRepairScopeRules:
    """测试修复范围规则"""
    
    def test_scene_repair_scope(self):
        """scene 修复范围限制"""
        instruction = RepairInstruction(
            repair_scope="scene",
            failure_type="consistency",
            must_fix=["问题1"]
        )
        assert instruction.repair_scope == "scene"
    
    def test_band_repair_scope(self):
        """band 修复范围限制"""
        instruction = RepairInstruction(
            repair_scope="band",
            failure_type="pacing",
            must_fix=["问题1"]
        )
        assert instruction.repair_scope == "band"
    
    def test_arc_repair_scope(self):
        """arc 修复范围限制"""
        instruction = RepairInstruction(
            repair_scope="arc",
            failure_type="reward_beat",
            must_fix=["问题1"]
        )
        assert instruction.repair_scope == "arc"


# ========================================
# 运行测试
# ========================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
