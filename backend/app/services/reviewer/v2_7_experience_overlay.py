"""Reader Experience Overlay - v2.7 新增

包含：
- ReaderPromise: 读者承诺
- ArcPayoffMap: Arc 回报图
- BandDelightSchedule: Band 愉悦时刻表
- ChapterExperiencePlan: 章节体验计划
- RewardBeatTag: 奖励节拍标签
- ImmersionAnchor: 沉浸锚点
- ProgressMarker: 进度标记
"""
from datetime import datetime
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field


# ========================================
# 奖励类别枚举
# ========================================

class RewardCategory(str, Enum):
    """奖励类别"""
    POWER = "power"           # 力量/实力提升
    SOCIAL = "social"         # 社交/关系发展
    JUSTICE = "justice"       # 正义/复仇/公平
    MYSTERY = "mystery"       # 谜题/悬疑揭示
    EMOTION = "emotion"       # 情感/浪漫/感动


class RewardBeatTag(str, Enum):
    """奖励节拍标签"""
    # Power 类
    POWER_GAIN = "power_gain"                 # 获得力量
    POWER_DISPLAY = "power_display"           # 力量展示
    POWER_REVELATION = "power_revelation"     # 力量揭示
    POWER_LIMIT_BREAK = "power_limit_break"  # 突破极限
    
    # Social 类
    ALLY_GAIN = "ally_gain"                   # 获得盟友
    ALLY_LOSS = "ally_loss"                   # 失去盟友
    RELATIONSHIP_DEVELOP = "relationship_develop"  # 关系发展
    BETRAYAL_REVEAL = "betrayal_reveal"       # 背叛揭露
    
    # Justice 类
    ENEMY_PUNISHMENT = "enemy_punishment"     # 敌人受罚
    INJUSTICE_REDRESS = "injustice_redress"  # 不公纠正
    HEROIC_ACT = "heroic_act"                # 英勇行为
    
    # Mystery 类
    CLUE_DISCOVERY = "clue_discovery"         # 线索发现
    TRUTH_REVEAL = "truth_reveal"            # 真相揭示
    PLOT_TWIST = "plot_twist"                # 剧情反转
    
    # Emotion 类
    HEARTWARMING = "heartwarming"            # 暖心时刻
    SAD_MOMENT = "sad_moment"                # 悲伤时刻
    TENSION_RELEASE = "tension_release"      # 紧张释放
    ROMANTIC_MOMENT = "romantic_moment"      # 浪漫时刻


# ========================================
# Reader Experience 核心类型
# ========================================

class ImmersionAnchor(BaseModel):
    """沉浸锚点 - 增强读者沉浸感的关键元素"""
    anchor_type: str  # sensory/emotional/visual/auditory
    description: str
    placement: str  # scene_start/scene_mid/scene_end/chapter_start/chapter_end
    intensity: float = Field(ge=0, le=1)  # 0-1 强度


class ProgressMarker(BaseModel):
    """进度标记 - 标记角色/世界的关键进展"""
    marker_type: str  # character_arc/world_state/relationship/plot
    title: str
    description: str
    chapter_no: int
    importance: str = "medium"  # low/medium/high/critical


class ReaderPromise(BaseModel):
    """读者承诺 - 小说对读者的核心承诺"""
    promise_type: str  # power_fantasy/social_drama/mystery_reveal/emotional_journey
    core_promise: str
    delivery_expectation: str  # early_mid/late_mid/end/climax
    
    # 承诺兑现追踪
    delivery_status: str = "pending"  # pending/partial/fulfilled
    delivery_chapter: Optional[int] = None
    
    # 读者期待曲线
    anticipation_curve: list[dict] = Field(default_factory=list)
    
    # 元数据
    created_at: datetime = Field(default_factory=datetime.now)


class ArcPayoffItem(BaseModel):
    """Arc 回报项"""
    payoff_type: str  # mystery/revelation/confrontation/resolution
    title: str
    description: str
    setup_chapters: list[int]  # 铺陈章节
    target_chapter: int  # 目标章节
    payoff_strength: str = "medium"  # low/medium/high
    
    # 兑现状态
    status: str = "setup"  # setup/teased/promised/delivered
    delivered_chapter: Optional[int] = None


class ArcPayoffMap(BaseModel):
    """Arc 回报图 - 追踪每个 Arc 的所有回报承诺"""
    arc_no: int
    arc_title: str
    
    # 回报项列表
    payoffs: list[ArcPayoffItem] = Field(default_factory=list)
    
    # 回报密度分析
    payoff_density: str = "balanced"  # sparse/balanced/dense
    climax_payoff_count: int = 0
    
    # 元数据
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class BandDelightItem(BaseModel):
    """Band 愉悦项 - 轻量级回报"""
    item_type: str  # humor/witty_dialogue/character_moment/small_victory
    title: str
    description: str
    target_chapter: int
    
    # 效果强度
    delight_strength: str = "light"  # light/medium/strong
    surprise_factor: float = Field(ge=0, le=1)


class BandDelightSchedule(BaseModel):
    """Band 愉悦时刻表 - 追踪每个 Band 的愉悦点分布"""
    band_no: int
    band_name: str
    arc_no: int
    
    # 愉悦项
    delights: list[BandDelightItem] = Field(default_factory=list)
    
    # 分布统计
    delight_per_chapter_avg: float = 0.0
    chapter_range: tuple[int, int] = (0, 0)  # (start_chapter, end_chapter)
    
    # 分布均匀性
    distribution: str = "regular"  # front_loaded/regular/back_loaded
    
    # 元数据
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class SceneExperienceMetadata(BaseModel):
    """场景体验元数据 - 增强 ScenePlan"""
    # v2.7 新增字段
    reward_beat_tag: Optional[RewardBeatTag] = None
    reward_category: Optional[RewardCategory] = None
    immersion_anchors: list[ImmersionAnchor] = Field(default_factory=list)
    progress_markers: list[ProgressMarker] = Field(default_factory=list)
    
    # 体验强度
    emotional_intensity: float = Field(ge=0, le=1, default=0.5)
    pacing_tempo: str = "medium"  # slow/medium/fast/climactic
    
    # 读者满足感预测
    satisfaction_prediction: float = Field(ge=0, le=1, default=0.5)


class ChapterExperiencePlan(BaseModel):
    """章节体验计划 - v2.7"""
    chapter_id: int
    chapter_no: int
    
    # 章节级别的奖励承诺
    planned_reward_tags: list[RewardBeatTag] = Field(default_factory=list)
    reward_categories: list[RewardCategory] = Field(default_factory=list)
    
    # 实际兑现
    delivered_reward_tags: list[RewardBeatTag] = Field(default_factory=list)
    delivered_categories: list[RewardCategory] = Field(default_factory=list)
    
    # 体验评分预测
    experience_scores: dict[str, float] = Field(default_factory=lambda: {
        "engagement": 0.5,
        "pacing": 0.5,
        "emotional_impact": 0.5,
        "reader_satisfaction": 0.5,
        "coherence": 0.5
    })
    
    # 沉浸锚点
    immersion_anchors: list[ImmersionAnchor] = Field(default_factory=list)
    
    # 进度标记
    progress_markers: list[ProgressMarker] = Field(default_factory=list)
    
    # 场景级体验
    scene_experiences: list[SceneExperienceMetadata] = Field(default_factory=list)
    
    # 章节钩子与悬念
    chapter_hook: Optional[str] = None
    chapter_cliffhanger: Optional[str] = None
    
    # 元数据
    plan_type: str = "initial"  # initial/revised
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# ========================================
# 修复指令结构 - v2.7
# ========================================

class RepairInstruction(BaseModel):
    """修复指令 - v2.7 新增"""
    repair_scope: str  # scene/band/arc
    failure_type: str  # consistency/pacing/reward_beat/emotional_impact/coherence
    
    # 必须修复
    must_fix: list[str] = Field(default_factory=list)
    
    # 必须保留
    must_preserve: list[str] = Field(default_factory=list)
    
    # 设计补丁
    design_patch: dict[str, Any] = Field(default_factory=dict)
    
    # 证据引用
    evidence_refs: list[str] = Field(default_factory=list)
    
    # 优先级
    priority: int = 1  # 1-5, 越高越优先


# ========================================
# 扩展 ReviewVerdict - v2.7
# ========================================

class ReviewVerdictV3(BaseModel):
    """审查判决 - v2.7 扩展版
    
    兼容旧版，同时包含：
    - recommended_action: 推荐动作
    - review_summary: 审查摘要
    - planned/delivered_reward_tags: 奖励标签
    - experience_scores: 体验评分
    - repair_instruction: 修复指令
    - force_accept_recommended: 是否建议强制接受
    """
    # 核心判定（保持兼容）
    verdict: str = "pass"  # pass/warn/fail
    verdict_reason: str = ""
    
    # v2.7 新增
    recommended_action: Optional[str] = None  # accept/accept_with_warning/repair/rewrite/stop
    
    # 审查摘要
    review_summary: str = ""
    
    # 问题列表
    issues: list[dict] = Field(default_factory=list)
    
    # 奖励标签追踪
    planned_reward_tags: list[RewardBeatTag] = Field(default_factory=list)
    delivered_reward_tags: list[RewardBeatTag] = Field(default_factory=list)
    
    # 体验评分
    experience_scores: dict[str, float] = Field(default_factory=lambda: {
        "engagement": 0.5,
        "pacing": 0.5,
        "emotional_impact": 0.5,
        "reader_satisfaction": 0.5,
        "coherence": 0.5
    })
    
    # 修复指令（当 verdict == fail 时必须提供）
    repair_instruction: Optional[RepairInstruction] = None
    
    # 强制接受标记
    force_accept_recommended: bool = False
    
    # patch/rewrite instructions（保持兼容）
    patch_instructions: Optional[str] = None
    rewrite_instructions: Optional[str] = None
    
    # 评分（保持兼容）
    scores: dict[str, float] = Field(default_factory=lambda: {
        "consistency": 1.0,
        "pacing": 1.0,
        "hook": 1.0,
        "overall": 1.0
    })
    
    # 错误恢复
    parse_success: bool = True
    parse_error: Optional[str] = None
    
    # 元数据
    created_at: datetime = Field(default_factory=datetime.now)
    forced_accept_applied: bool = False
    override_reason: Optional[str] = None
