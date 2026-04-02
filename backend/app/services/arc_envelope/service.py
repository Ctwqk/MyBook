"""Arc Envelope Service - v2.4 三层决定机制 + Provisional 预演

核心功能：
1. Layer 1: 百分比 + 上下限计算基础 target
2. Layer 2: 按全书总长度分档调整 range
3. Layer 3: 每个 arc 单独做 Provisional 预演确定最终 envelope

这替代了 v2.3 中固定章节数的 arc 规划方式。
"""
import json
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.llm.base import LLMProvider
from app.repositories.project import ProjectRepository
from app.models.arc_envelope import (
    ArcEnvelope, ArcStructureDraft, ArcEnvelopeAnalysis,
    ProvisionalPromotionRecord, ArcTier, ArcRecommendation, ArcPhase
)


# ========================================
# Layer 配置 - 按总长度分档
# ========================================

@dataclass
class ArcTierConfig:
    """Arc 分档配置"""
    ratio: float              # 百分比
    min_size: int            # 最小章节数
    max_size: int            # 最大章节数
    soft_min_mult: float     # 软下限乘数
    soft_max_mult: float     # 软上限乘数
    tier_name: str           # 分档名称


# 按总长度分档的配置
ARC_TIER_CONFIGS: dict[ArcTier, ArcTierConfig] = {
    # 短长篇（1-150 章）
    ArcTier.SHORT: ArcTierConfig(
        ratio=0.18,
        min_size=12,
        max_size=24,
        soft_min_mult=0.75,
        soft_max_mult=1.25,
        tier_name="short"
    ),
    # 中长篇（151-400 章）
    ArcTier.MEDIUM: ArcTierConfig(
        ratio=0.15,
        min_size=16,
        max_size=30,
        soft_min_mult=0.65,
        soft_max_mult=1.50,
        tier_name="medium"
    ),
    # 长连载（401-800 章）
    ArcTier.LONG: ArcTierConfig(
        ratio=0.10,
        min_size=20,
        max_size=40,
        soft_min_mult=0.55,
        soft_max_mult=1.70,
        tier_name="long"
    ),
    # 超长连载（801+ 章）
    ArcTier.ULTRA_LONG: ArcTierConfig(
        ratio=0.08,
        min_size=24,
        max_size=48,
        soft_min_mult=0.50,
        soft_max_mult=2.00,
        tier_name="ultra_long"
    ),
}


@dataclass
class Layer1Result:
    """Layer 1 计算结果"""
    base_ratio: float
    base_target_size: int
    base_soft_min: int
    base_soft_max: int


@dataclass
class Layer2Result:
    """Layer 2 计算结果"""
    tier: ArcTier
    tier_config: ArcTierConfig
    arc_target: int
    soft_min: int
    soft_max: int


@dataclass
class Layer3Result:
    """Layer 3 Provisional 预演结果"""
    recommendation: ArcRecommendation
    resolved_target_size: int
    resolved_soft_min: int
    resolved_soft_max: int
    detailed_band_size: int
    frozen_zone_size: int
    confidence: float
    evidence: str
    expansion_signals: list[str] = field(default_factory=list)
    compression_signals: list[str] = field(default_factory=list)


@dataclass
class ArcEnvelopeResult:
    """完整 Arc Envelope 结果"""
    arc_no: int
    layer1: Layer1Result
    layer2: Layer2Result
    layer3: Layer3Result
    current_projected_size: int
    structure_draft: Optional[dict] = None


# ========================================
# Arc Envelope Service
# ========================================

class ArcEnvelopeService:
    """
    Arc Envelope Service - v2.4
    
    实现三层决定机制：
    1. Layer 1: 百分比 + 上下限计算基础 target
    2. Layer 2: 按全书总长度分档调整 range
    3. Layer 3: 每个 arc 单独做 Provisional 预演
    """

    def __init__(
        self,
        db: AsyncSession,
        llm_provider: Optional[LLMProvider] = None
    ):
        self.db = db
        self.llm = llm_provider
        self.project_repo = ProjectRepository(db)

    # ==================== 核心入口 ====================

    async def compute_arc_envelope(
        self,
        project_id: int,
        arc_no: int,
        total_chapters: Optional[int] = None
    ) -> ArcEnvelopeResult:
        """
        计算单个 arc 的 envelope - 三层决定机制
        
        Args:
            project_id: 项目 ID
            arc_no: Arc 编号（从1开始）
            total_chapters: 全书总章节数（如果为 None，从项目设置获取）
            
        Returns:
            ArcEnvelopeResult: 完整的 arc envelope 结果
        """
        # 获取项目信息
        project = await self.project_repo.get(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        # 确定全书总章节数
        if total_chapters is None:
            total_chapters = project.target_chapters or 100
        
        # Step 1: Layer 1 - 基础 target 计算
        layer1 = await self._compute_layer1(arc_no, total_chapters)
        
        # Step 2: Layer 2 - 分档调整
        layer2 = await self._compute_layer2(total_chapters, layer1)
        
        # Step 3: Layer 3 - Provisional 预演
        layer3 = await self._provisional_simulation(
            project_id, arc_no, layer1, layer2
        )
        
        # 计算当前预测值
        current_projected = layer3.resolved_target_size
        
        return ArcEnvelopeResult(
            arc_no=arc_no,
            layer1=layer1,
            layer2=layer2,
            layer3=layer3,
            current_projected_size=current_projected,
            structure_draft=None  # 会在后续步骤填充
        )

    async def activate_arc(
        self,
        project_id: int,
        arc_no: int
    ) -> ArcEnvelope:
        """
        激活一个 arc - 执行完整的三层决定 + Provisional 预演
        
        Args:
            project_id: 项目 ID
            arc_no: Arc 编号
            
        Returns:
            ArcEnvelope: 持久化的 arc envelope
        """
        # 获取项目信息
        project = await self.project_repo.get(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        total_chapters = project.target_chapters or 100
        
        # 执行三层决定
        result = await self.compute_arc_envelope(project_id, arc_no, total_chapters)
        
        # 检查是否已存在 envelope
        existing = await self._get_envelope(project_id, arc_no)
        
        if existing:
            # 更新现有 envelope
            await self._update_envelope(existing, result)
            envelope = existing
        else:
            # 创建新 envelope
            envelope = await self._create_envelope(project_id, result)
        
        # 生成并保存结构草案
        structure_draft = await self._generate_structure_draft(
            project_id, arc_no, envelope
        )
        
        # 执行 provisional 预演
        await self._run_provisional_simulation(
            project_id, arc_no, envelope, structure_draft
        )
        
        return envelope

    # ==================== Layer 1 ====================

    async def _compute_layer1(
        self,
        arc_no: int,
        total_chapters: int
    ) -> Layer1Result:
        """
        Layer 1: 百分比 + 上下限计算基础 target
        
        公式: base_target_size = clamp(round(total_chapters * ratio), min_size, max_size)
        
        注意：Layer 1 只计算，不应用分档
        """
        # 固定使用 0.15 作为基础百分比
        ratio = 0.15
        
        # 临时使用中等分档的上下限进行 clamp
        temp_min = 10
        temp_max = 50
        
        base_target = self._clamp(
            round(total_chapters * ratio),
            temp_min,
            temp_max
        )
        
        # 临时 soft range
        base_soft_min = self._clamp(
            round(base_target * 0.70),
            temp_min,
            temp_max
        )
        base_soft_max = self._clamp(
            round(base_target * 1.30),
            temp_min,
            temp_max
        )
        
        return Layer1Result(
            base_ratio=ratio,
            base_target_size=base_target,
            base_soft_min=base_soft_min,
            base_soft_max=base_soft_max
        )

    # ==================== Layer 2 ====================

    def _determine_tier(self, total_chapters: int) -> ArcTier:
        """根据总章节数确定分档"""
        if total_chapters <= 150:
            return ArcTier.SHORT
        elif total_chapters <= 400:
            return ArcTier.MEDIUM
        elif total_chapters <= 800:
            return ArcTier.LONG
        else:
            return ArcTier.ULTRA_LONG

    async def _compute_layer2(
        self,
        total_chapters: int,
        layer1: Layer1Result
    ) -> Layer2Result:
        """
        Layer 2: 按全书总长度分档调整
        
        根据分档决定：
        - arc_target（带上下限）
        - soft_min / soft_max（分档相关的 range）
        """
        tier = self._determine_tier(total_chapters)
        config = ARC_TIER_CONFIGS[tier]
        
        # 使用分档的配置计算
        arc_target = self._clamp(
            round(total_chapters * config.ratio),
            config.min_size,
            config.max_size
        )
        
        soft_min = self._clamp(
            round(arc_target * config.soft_min_mult),
            config.min_size,
            config.max_size
        )
        
        soft_max = self._clamp(
            round(arc_target * config.soft_max_mult),
            config.min_size,
            config.max_size
        )
        
        return Layer2Result(
            tier=tier,
            tier_config=config,
            arc_target=arc_target,
            soft_min=soft_min,
            soft_max=soft_max
        )

    # ==================== Layer 3 ====================

    async def _provisional_simulation(
        self,
        project_id: int,
        arc_no: int,
        layer1: Layer1Result,
        layer2: Layer2Result
    ) -> Layer3Result:
        """
        Layer 3: Provisional 预演
        
        这是 v2.4 的关键 - 每个 arc 激活时都要做 provisional 预演
        
        流程：
        1. 生成当前 arc 的中层结构草案
        2. 生成 provisional band（只预演近端章节）
        3. 在 shadow 分支里预演
        4. 做 Arc Envelope Analysis
        5. 确定 resolved envelope
        """
        # 初始使用 layer2 的值
        initial_target = layer2.arc_target
        initial_soft_min = layer2.soft_min
        initial_soft_max = layer2.soft_max
        
        # 如果有 LLM，进行结构草案分析
        if self.llm:
            analysis = await self._analyze_arc_structure(
                project_id, arc_no, initial_target
            )
            
            # 根据分析结果调整
            if analysis["recommendation"] == "expand":
                expansion_factor = 1.15
                resolved_target = min(
                    round(initial_target * expansion_factor),
                    layer2.tier_config.max_size
                )
            elif analysis["recommendation"] == "compress":
                compression_factor = 0.85
                resolved_target = max(
                    round(initial_target * compression_factor),
                    layer2.tier_config.min_size
                )
            else:
                resolved_target = initial_target
        else:
            # 无 LLM 时使用初始值
            resolved_target = initial_target
            analysis = {
                "recommendation": "keep",
                "evidence": "No LLM available, using initial values",
                "expansion_signals": [],
                "compression_signals": [],
                "confidence": 0.3
            }
        
        # 计算 detailed band 和 frozen zone
        detailed_band = self._clamp(
            round(resolved_target * 0.40),
            4, 12
        )
        frozen_zone = self._clamp(
            round(detailed_band * 0.35),
            2, 4
        )
        
        # 计算最终的 soft range
        resolved_soft_min = max(
            layer2.tier_config.min_size,
            round(resolved_target * layer2.tier_config.soft_min_mult)
        )
        resolved_soft_max = min(
            layer2.tier_config.max_size,
            round(resolved_target * layer2.tier_config.soft_max_mult)
        )
        
        return Layer3Result(
            recommendation=ArcRecommendation(analysis["recommendation"]),
            resolved_target_size=resolved_target,
            resolved_soft_min=resolved_soft_min,
            resolved_soft_max=resolved_soft_max,
            detailed_band_size=detailed_band,
            frozen_zone_size=frozen_zone,
            confidence=analysis.get("confidence", 0.5),
            evidence=analysis.get("evidence", ""),
            expansion_signals=analysis.get("expansion_signals", []),
            compression_signals=analysis.get("compression_signals", [])
        )

    async def _analyze_arc_structure(
        self,
        project_id: int,
        arc_no: int,
        initial_target: int
    ) -> dict[str, Any]:
        """
        分析 arc 结构 - LLM 驱动
        
        生成中层结构草案并分析是否需要调整
        """
        system_prompt = """你是一个专业的小说结构分析师。你的任务是分析一个故事弧线的结构，
        判断它应该保持当前目标长度、扩张还是压缩。
        
        分析维度：
        1. 主要矛盾是否复杂
        2. 多线交织程度
        3. 高潮位置
        4. 角色活跃度
        5. 信息密度
        
        输出 JSON 格式：
        {
            "recommendation": "keep/expand/compress",
            "evidence": "分析理由",
            "expansion_signals": ["信号1", ...],
            "compression_signals": ["信号1", ...],
            "confidence": 0.0-1.0
        }
        """
        
        prompt = f"""分析 Arc {arc_no} 的结构：
        初始目标长度：{initial_target} 章
        
        请分析：
        1. 当前 arc 的主要矛盾是什么？
        2. 需要多线交织吗？
        3. 高潮大概应该落在哪里？
        4. 这个 arc 应该扩张还是压缩？
        
        返回 JSON 格式的分析结果。
        """
        
        try:
            response = await self.llm.generate(prompt, system_prompt)
            content = response.content
            
            # 提取 JSON
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
        except Exception:
            pass
        
        # 默认返回 keep
        return {
            "recommendation": "keep",
            "evidence": "Provisional analysis default",
            "expansion_signals": [],
            "compression_signals": [],
            "confidence": 0.3
        }

    # ==================== 辅助方法 ====================

    def _clamp(self, value: int, min_val: int, max_val: int) -> int:
        """Clamp value between min and max"""
        return max(min_val, min(max_val, value))

    async def _get_envelope(
        self,
        project_id: int,
        arc_no: int
    ) -> Optional[ArcEnvelope]:
        """获取现有 envelope"""
        stmt = select(ArcEnvelope).where(
            ArcEnvelope.project_id == project_id,
            ArcEnvelope.arc_no == arc_no
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _create_envelope(
        self,
        project_id: int,
        result: ArcEnvelopeResult
    ) -> ArcEnvelope:
        """创建新的 envelope"""
        envelope = ArcEnvelope(
            project_id=project_id,
            arc_no=result.arc_no,
            base_ratio=result.layer1.base_ratio,
            base_target_size=result.layer1.base_target_size,
            base_soft_min=result.layer1.base_soft_min,
            base_soft_max=result.layer1.base_soft_max,
            source_policy_tier=result.layer2.tier.value,
            total_chapters_at_calculation=0,  # 稍后更新
            resolved_target_size=result.layer3.resolved_target_size,
            resolved_soft_min=result.layer3.resolved_soft_min,
            resolved_soft_max=result.layer3.resolved_soft_max,
            resolved_detailed_band_size=result.layer3.detailed_band_size,
            resolved_frozen_zone_size=result.layer3.frozen_zone_size,
            current_projected_size=result.current_projected_size,
            current_confidence=result.layer3.confidence,
            envelope_status="provisional"
        )
        self.db.add(envelope)
        await self.db.flush()
        return envelope

    async def _update_envelope(
        self,
        envelope: ArcEnvelope,
        result: ArcEnvelopeResult
    ) -> None:
        """更新现有 envelope"""
        envelope.base_ratio = result.layer1.base_ratio
        envelope.base_target_size = result.layer1.base_target_size
        envelope.base_soft_min = result.layer1.base_soft_min
        envelope.base_soft_max = result.layer1.base_soft_max
        envelope.source_policy_tier = result.layer2.tier.value
        envelope.resolved_target_size = result.layer3.resolved_target_size
        envelope.resolved_soft_min = result.layer3.resolved_soft_min
        envelope.resolved_soft_max = result.layer3.resolved_soft_max
        envelope.resolved_detailed_band_size = result.layer3.detailed_band_size
        envelope.resolved_frozen_zone_size = result.layer3.frozen_zone_size
        envelope.current_projected_size = result.current_projected_size
        envelope.current_confidence = result.layer3.confidence
        envelope.envelope_status = "adjusted"

    async def _generate_structure_draft(
        self,
        project_id: int,
        arc_no: int,
        envelope: ArcEnvelope
    ) -> ArcStructureDraft:
        """生成 Arc 中层结构草案"""
        # 检查是否已存在
        stmt = select(ArcStructureDraft).where(
            ArcStructureDraft.envelope_id == envelope.id
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            return existing
        
        # 创建新草案
        draft = ArcStructureDraft(
            envelope_id=envelope.id,
            arc_id=arc_no,
            arc_function="unknown",  # 稍后通过分析确定
            raw_structure="{}"
        )
        self.db.add(draft)
        await self.db.flush()
        return draft

    async def _run_provisional_simulation(
        self,
        project_id: int,
        arc_no: int,
        envelope: ArcEnvelope,
        structure_draft: ArcStructureDraft
    ) -> ArcEnvelopeAnalysis:
        """运行 Provisional 预演并生成分析"""
        # 创建分析记录
        analysis = ArcEnvelopeAnalysis(
            envelope_id=envelope.id,
            arc_id=arc_no,
            based_on_band_id=f"band_{arc_no}_provisional",
            recommendation=envelope.envelope_status or "provisional",
            evidence="Provisional simulation pending",
            expansion_signals=[],
            compression_signals=[],
            suggested_target=envelope.resolved_target_size,
            suggested_soft_min=envelope.resolved_soft_min,
            suggested_soft_max=envelope.resolved_soft_max,
            confidence=envelope.current_confidence,
            is_final=False
        )
        self.db.add(analysis)
        await self.db.flush()
        
        # 更新 envelope 的 latest_analysis_id
        envelope.latest_analysis_id = analysis.id
        
        return analysis

    # ==================== 公开 API ====================

    async def get_arc_envelope(
        self,
        project_id: int,
        arc_no: int
    ) -> Optional[ArcEnvelope]:
        """获取 arc envelope"""
        return await self._get_envelope(project_id, arc_no)

    async def get_project_arcs(
        self,
        project_id: int
    ) -> list[ArcEnvelope]:
        """获取项目的所有 arc envelopes"""
        stmt = select(ArcEnvelope).where(
            ArcEnvelope.project_id == project_id
        ).order_by(ArcEnvelope.arc_no)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def adjust_arc_envelope(
        self,
        project_id: int,
        arc_no: int,
        adjustment: str  # expand/compress/keep
    ) -> ArcEnvelope:
        """
        运行时调整 arc envelope
        
        当检测到 expansion/compression signals 时调用
        """
        envelope = await self._get_envelope(project_id, arc_no)
        if not envelope:
            raise ValueError(f"Arc envelope not found for arc {arc_no}")
        
        tier_name = envelope.source_policy_tier
        tier = ArcTier(tier_name)
        config = ARC_TIER_CONFIGS[tier]
        
        current_target = envelope.resolved_target_size
        
        if adjustment == "expand":
            new_target = min(
                round(current_target * 1.15),
                config.max_size
            )
        elif adjustment == "compress":
            new_target = max(
                round(current_target * 0.85),
                config.min_size
            )
        else:
            new_target = current_target
        
        # 更新 envelope
        envelope.resolved_target_size = new_target
        envelope.resolved_soft_min = max(
            config.min_size,
            round(new_target * config.soft_min_mult)
        )
        envelope.resolved_soft_max = min(
            config.max_size,
            round(new_target * config.soft_max_mult)
        )
        envelope.envelope_status = "adjusted"
        envelope.current_projected_size = new_target
        
        await self.db.flush()
        return envelope

    async def get_tier_for_project(
        self,
        project_id: int
    ) -> ArcTier:
        """获取项目的分档"""
        project = await self.project_repo.get(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        total = project.target_chapters or 100
        return self._determine_tier(total)

    async def preview_all_arcs(
        self,
        project_id: int,
        total_chapters: Optional[int] = None
    ) -> list[dict[str, Any]]:
        """
        预览项目中所有 arc 的 envelope
        
        用于在正式激活前展示预估结果
        """
        project = await self.project_repo.get(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        if total_chapters is None:
            total_chapters = project.target_chapters or 100
        
        tier = self._determine_tier(total_chapters)
        config = ARC_TIER_CONFIGS[tier]
        
        # 计算预估的 arc 数量
        arc_count = max(1, round(total_chapters / config.ratio / 10))
        
        previews = []
        for i in range(1, arc_count + 1):
            result = await self.compute_arc_envelope(project_id, i, total_chapters)
            previews.append({
                "arc_no": result.arc_no,
                "tier": tier.value,
                "base_target": result.layer1.base_target_size,
                "resolved_target": result.layer3.resolved_target_size,
                "soft_range": (result.layer3.resolved_soft_min, result.layer3.resolved_soft_max),
                "detailed_band": result.layer3.detailed_band_size,
                "frozen_zone": result.layer3.frozen_zone_size,
                "recommendation": result.layer3.recommendation.value,
                "confidence": result.layer3.confidence
            })
        
        return previews
