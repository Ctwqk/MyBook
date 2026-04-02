"""Arc Envelope Service Tests - v2.4

测试三层决定机制：
1. Layer 1: 百分比 + 上下限计算基础 target
2. Layer 2: 按全书总长度分档调整 range
3. Layer 3: Provisional 预演
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.arc_envelope.service import (
    ArcEnvelopeService,
    ArcTierConfig,
    ARC_TIER_CONFIGS,
    Layer1Result,
    Layer2Result,
)
from app.services.arc_envelope import ArcTier


class TestArcTierDetermination:
    """测试分档确定逻辑"""

    def test_short_tier(self):
        """短长篇（1-150 章）"""
        service = ArcEnvelopeService(MagicMock())
        
        assert service._determine_tier(1) == ArcTier.SHORT
        assert service._determine_tier(100) == ArcTier.SHORT
        assert service._determine_tier(150) == ArcTier.SHORT

    def test_medium_tier(self):
        """中长篇（151-400 章）"""
        service = ArcEnvelopeService(MagicMock())
        
        assert service._determine_tier(151) == ArcTier.MEDIUM
        assert service._determine_tier(300) == ArcTier.MEDIUM
        assert service._determine_tier(400) == ArcTier.MEDIUM

    def test_long_tier(self):
        """长连载（401-800 章）"""
        service = ArcEnvelopeService(MagicMock())
        
        assert service._determine_tier(401) == ArcTier.LONG
        assert service._determine_tier(600) == ArcTier.LONG
        assert service._determine_tier(800) == ArcTier.LONG

    def test_ultra_long_tier(self):
        """超长连载（801+ 章）"""
        service = ArcEnvelopeService(MagicMock())
        
        assert service._determine_tier(801) == ArcTier.ULTRA_LONG
        assert service._determine_tier(1000) == ArcTier.ULTRA_LONG
        assert service._determine_tier(2000) == ArcTier.ULTRA_LONG


class TestLayer1Calculation:
    """测试 Layer 1 计算"""

    @pytest.mark.asyncio
    async def test_layer1_basic_calculation(self):
        """测试基础计算"""
        service = ArcEnvelopeService(MagicMock())
        
        result = await service._compute_layer1(arc_no=1, total_chapters=100)
        
        assert isinstance(result, Layer1Result)
        assert result.base_ratio == 0.15
        # 100 * 0.15 = 15
        assert result.base_target_size == 15
        # soft range 70%-130%
        assert result.base_soft_min == 10  # 15 * 0.70 ≈ 10
        assert result.base_soft_max == 19  # 15 * 1.30 ≈ 19

    @pytest.mark.asyncio
    async def test_layer1_large_project(self):
        """测试大型项目"""
        service = ArcEnvelopeService(MagicMock())
        
        result = await service._compute_layer1(arc_no=1, total_chapters=1000)
        
        assert result.base_target_size == 150  # 1000 * 0.15 = 150


class TestLayer2Calculation:
    """测试 Layer 2 计算 - 分档调整"""

    @pytest.mark.asyncio
    async def test_layer2_short_tier(self):
        """短长篇分档"""
        service = ArcEnvelopeService(MagicMock())
        layer1 = Layer1Result(
            base_ratio=0.15,
            base_target_size=15,
            base_soft_min=10,
            base_soft_max=19
        )
        
        result = await service._compute_layer2(total_chapters=100, layer1=layer1)
        
        assert isinstance(result, Layer2Result)
        assert result.tier == ArcTier.SHORT
        
        # 100 * 0.18 = 18
        # clamp(18, 12, 24) = 18
        assert result.arc_target == 18
        # soft range 75%-125%
        assert result.soft_min == 13  # 18 * 0.75 = 13.5 → 14 (clamped)
        assert result.soft_max == 22  # 18 * 1.25 = 22.5 → 23 (clamped)

    @pytest.mark.asyncio
    async def test_layer2_medium_tier(self):
        """中长篇分档"""
        service = ArcEnvelopeService(MagicMock())
        layer1 = Layer1Result(
            base_ratio=0.15,
            base_target_size=30,
            base_soft_min=21,
            base_soft_max=39
        )
        
        result = await service._compute_layer2(total_chapters=300, layer1=layer1)
        
        assert result.tier == ArcTier.MEDIUM
        # 300 * 0.15 = 45
        # clamp(45, 16, 30) = 30 (capped at max)
        assert result.arc_target == 30

    @pytest.mark.asyncio
    async def test_layer2_long_tier(self):
        """长连载分档"""
        service = ArcEnvelopeService(MagicMock())
        layer1 = Layer1Result(
            base_ratio=0.15,
            base_target_size=60,
            base_soft_min=42,
            base_soft_max=78
        )
        
        result = await service._compute_layer2(total_chapters=600, layer1=layer1)
        
        assert result.tier == ArcTier.LONG
        # 600 * 0.10 = 60
        # clamp(60, 20, 40) = 40 (capped at max)
        assert result.arc_target == 40
        # soft range 55%-170%
        assert result.soft_min == 22  # 40 * 0.55 = 22
        assert result.soft_max == 40  # 40 * 1.70 = 68 (clamped at max 40)

    @pytest.mark.asyncio
    async def test_layer2_ultra_long_tier(self):
        """超长连载分档"""
        service = ArcEnvelopeService(MagicMock())
        layer1 = Layer1Result(
            base_ratio=0.15,
            base_target_size=80,
            base_soft_min=56,
            base_soft_max=104
        )
        
        result = await service._compute_layer2(total_chapters=1000, layer1=layer1)
        
        assert result.tier == ArcTier.ULTRA_LONG
        # 1000 * 0.08 = 80
        # clamp(80, 24, 48) = 48 (capped at max)
        assert result.arc_target == 48
        # soft range 50%-200%
        assert result.soft_min == 24  # 48 * 0.50 = 24
        assert result.soft_max == 48  # 48 * 2.00 = 96 (clamped at max 48)


class TestArcTierConfigs:
    """测试分档配置"""

    def test_short_tier_config(self):
        """短长篇配置"""
        config = ARC_TIER_CONFIGS[ArcTier.SHORT]
        
        assert config.ratio == 0.18
        assert config.min_size == 12
        assert config.max_size == 24
        assert config.soft_min_mult == 0.75
        assert config.soft_max_mult == 1.25

    def test_medium_tier_config(self):
        """中长篇配置"""
        config = ARC_TIER_CONFIGS[ArcTier.MEDIUM]
        
        assert config.ratio == 0.15
        assert config.min_size == 16
        assert config.max_size == 30
        assert config.soft_min_mult == 0.65
        assert config.soft_max_mult == 1.50

    def test_long_tier_config(self):
        """长连载配置"""
        config = ARC_TIER_CONFIGS[ArcTier.LONG]
        
        assert config.ratio == 0.10
        assert config.min_size == 20
        assert config.max_size == 40
        assert config.soft_min_mult == 0.55
        assert config.soft_max_mult == 1.70

    def test_ultra_long_tier_config(self):
        """超长连载配置"""
        config = ARC_TIER_CONFIGS[ArcTier.ULTRA_LONG]
        
        assert config.ratio == 0.08
        assert config.min_size == 24
        assert config.max_size == 48
        assert config.soft_min_mult == 0.50
        assert config.soft_max_mult == 2.00


class TestClampFunction:
    """测试 clamp 辅助函数"""

    def test_clamp_within_bounds(self):
        """值在范围内"""
        service = ArcEnvelopeService(MagicMock())
        
        result = service._clamp(10, 5, 20)
        assert result == 10

    def test_clamp_below_min(self):
        """值低于最小值"""
        service = ArcEnvelopeService(MagicMock())
        
        result = service._clamp(3, 5, 20)
        assert result == 5

    def test_clamp_above_max(self):
        """值高于最大值"""
        service = ArcEnvelopeService(MagicMock())
        
        result = service._clamp(25, 5, 20)
        assert result == 20


class TestDetailedBandAndFrozenZone:
    """测试 detailed band 和 frozen zone 计算"""

    @pytest.mark.asyncio
    async def test_detailed_band_calculation(self):
        """测试 detailed band 计算"""
        service = ArcEnvelopeService(MagicMock())
        layer1 = Layer1Result(
            base_ratio=0.15,
            base_target_size=18,
            base_soft_min=12,
            base_soft_max=23
        )
        layer2 = Layer2Result(
            tier=ArcTier.SHORT,
            tier_config=ARC_TIER_CONFIGS[ArcTier.SHORT],
            arc_target=18,
            soft_min=13,
            soft_max=23
        )
        
        # Mock LLM analysis
        service._analyze_arc_structure = AsyncMock(return_value={
            "recommendation": "keep",
            "evidence": "Test",
            "expansion_signals": [],
            "compression_signals": [],
            "confidence": 0.5
        })
        
        result = await service._provisional_simulation(
            project_id=1, arc_no=1, layer1=layer1, layer2=layer2
        )
        
        # detailed_band = clamp(round(18 * 0.40), 4, 12) = clamp(7, 4, 12) = 7
        assert result.detailed_band_size == 7

    @pytest.mark.asyncio
    async def test_frozen_zone_calculation(self):
        """测试 frozen zone 计算"""
        service = ArcEnvelopeService(MagicMock())
        layer1 = Layer1Result(
            base_ratio=0.15,
            base_target_size=18,
            base_soft_min=12,
            base_soft_max=23
        )
        layer2 = Layer2Result(
            tier=ArcTier.SHORT,
            tier_config=ARC_TIER_CONFIGS[ArcTier.SHORT],
            arc_target=18,
            soft_min=13,
            soft_max=23
        )
        
        service._analyze_arc_structure = AsyncMock(return_value={
            "recommendation": "keep",
            "evidence": "Test",
            "expansion_signals": [],
            "compression_signals": [],
            "confidence": 0.5
        })
        
        result = await service._provisional_simulation(
            project_id=1, arc_no=1, layer1=layer1, layer2=layer2
        )
        
        # frozen_zone = clamp(round(7 * 0.35), 2, 4) = clamp(2, 2, 4) = 2
        assert result.frozen_zone_size == 2


class Test100ChaptersAnd1000Chapters:
    """测试 100 章和 1000 章的典型场景"""

    @pytest.mark.asyncio
    async def test_100_chapters_short_tier(self):
        """100 章项目 - 短长篇"""
        service = ArcEnvelopeService(MagicMock())
        
        result = await service.compute_arc_envelope(
            project_id=1,
            arc_no=1,
            total_chapters=100
        )
        
        assert result.layer2.tier == ArcTier.SHORT
        # 100 * 0.18 = 18
        # clamp(18, 12, 24) = 18
        assert result.layer2.arc_target == 18
        # soft range: 75%-125%
        assert 13 <= result.layer2.soft_min <= 14
        assert 22 <= result.layer2.soft_max <= 23

    @pytest.mark.asyncio
    async def test_1000_chapters_ultra_long_tier(self):
        """1000 章项目 - 超长连载"""
        service = ArcEnvelopeService(MagicMock())
        
        result = await service.compute_arc_envelope(
            project_id=1,
            arc_no=1,
            total_chapters=1000
        )
        
        assert result.layer2.tier == ArcTier.ULTRA_LONG
        # 1000 * 0.08 = 80
        # clamp(80, 24, 48) = 48
        assert result.layer2.arc_target == 48
        # soft range: 50%-200%
        assert 24 <= result.layer2.soft_min <= 25
        assert 48 <= result.layer2.soft_max <= 96


class TestLayer3ProvisionalSimulation:
    """测试 Layer 3 Provisional 预演"""

    @pytest.mark.asyncio
    async def test_expand_recommendation(self):
        """测试扩张建议"""
        service = ArcEnvelopeService(MagicMock())
        layer1 = Layer1Result(
            base_ratio=0.15,
            base_target_size=20,
            base_soft_min=14,
            base_soft_max=26
        )
        layer2 = Layer2Result(
            tier=ArcTier.MEDIUM,
            tier_config=ARC_TIER_CONFIGS[ArcTier.MEDIUM],
            arc_target=25,
            soft_min=16,
            soft_max=30
        )
        
        service._analyze_arc_structure = AsyncMock(return_value={
            "recommendation": "expand",
            "evidence": "Main climax not reached",
            "expansion_signals": ["主高潮尚未到来", "关键thread仍在升温"],
            "compression_signals": [],
            "confidence": 0.7
        })
        
        result = await service._provisional_simulation(
            project_id=1, arc_no=1, layer1=layer1, layer2=layer2
        )
        
        assert result.recommendation.value == "expand"
        # 25 * 1.15 = 28.75 → 29 (但不超过 max 30)
        assert 25 <= result.resolved_target_size <= 30
        assert result.confidence == 0.7

    @pytest.mark.asyncio
    async def test_compress_recommendation(self):
        """测试压缩建议"""
        service = ArcEnvelopeService(MagicMock())
        layer1 = Layer1Result(
            base_ratio=0.15,
            base_target_size=20,
            base_soft_min=14,
            base_soft_max=26
        )
        layer2 = Layer2Result(
            tier=ArcTier.MEDIUM,
            tier_config=ARC_TIER_CONFIGS[ArcTier.MEDIUM],
            arc_target=25,
            soft_min=16,
            soft_max=30
        )
        
        service._analyze_arc_structure = AsyncMock(return_value={
            "recommendation": "compress",
            "evidence": "Main problem solved",
            "expansion_signals": [],
            "compression_signals": ["主问题已解", "高潮已过"],
            "confidence": 0.6
        })
        
        result = await service._provisional_simulation(
            project_id=1, arc_no=1, layer1=layer1, layer2=layer2
        )
        
        assert result.recommendation.value == "compress"
        # 25 * 0.85 = 21.25 → 21
        assert 16 <= result.resolved_target_size <= 25

    @pytest.mark.asyncio
    async def test_keep_recommendation(self):
        """测试保持建议"""
        service = ArcEnvelopeService(MagicMock())
        layer1 = Layer1Result(
            base_ratio=0.15,
            base_target_size=20,
            base_soft_min=14,
            base_soft_max=26
        )
        layer2 = Layer2Result(
            tier=ArcTier.MEDIUM,
            tier_config=ARC_TIER_CONFIGS[ArcTier.MEDIUM],
            arc_target=25,
            soft_min=16,
            soft_max=30
        )
        
        service._analyze_arc_structure = AsyncMock(return_value={
            "recommendation": "keep",
            "evidence": "Arc structure is balanced",
            "expansion_signals": [],
            "compression_signals": [],
            "confidence": 0.5
        })
        
        result = await service._provisional_simulation(
            project_id=1, arc_no=1, layer1=layer1, layer2=layer2
        )
        
        assert result.recommendation.value == "keep"
        assert result.resolved_target_size == 25


class TestAdjustArcEnvelope:
    """测试运行时调整 arc envelope"""

    @pytest.mark.asyncio
    async def test_adjust_expand(self):
        """测试扩张调整"""
        service = ArcEnvelopeService(MagicMock())
        
        # Mock existing envelope
        mock_envelope = MagicMock()
        mock_envelope.resolved_target_size = 20
        mock_envelope.source_policy_tier = "medium"
        
        service._get_envelope = AsyncMock(return_value=mock_envelope)
        service.db.flush = AsyncMock()
        
        result = await service.adjust_arc_envelope(
            project_id=1,
            arc_no=1,
            adjustment="expand"
        )
        
        # 20 * 1.15 = 23
        assert result.resolved_target_size == 23

    @pytest.mark.asyncio
    async def test_adjust_compress(self):
        """测试压缩调整"""
        service = ArcEnvelopeService(MagicMock())
        
        mock_envelope = MagicMock()
        mock_envelope.resolved_target_size = 20
        mock_envelope.source_policy_tier = "medium"
        
        service._get_envelope = AsyncMock(return_value=mock_envelope)
        service.db.flush = AsyncMock()
        
        result = await service.adjust_arc_envelope(
            project_id=1,
            arc_no=1,
            adjustment="compress"
        )
        
        # 20 * 0.85 = 17
        assert result.resolved_target_size == 17


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
