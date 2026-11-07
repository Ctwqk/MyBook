"""PersonalityEngine - 性格管理引擎

基于 V4.7/V4.8 设计文档
"""
from dataclasses import dataclass
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.personality import (
    PersonalityLoadout, 
    PersonalityTraitInstance, 
    PersonalityEvolution,
    TraitType,
    TraitCategory
)


@dataclass
class PersonalitySummary:
    """性格摘要"""
    character_id: int
    big_five: dict
    core_traits: list[dict]
    behavioral_tendencies: dict
    psychological_model: dict


class PersonalityEngine:
    """性格管理引擎"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_loadout(
        self,
        character_id: int,
        name: str,
        big_five: Optional[dict] = None,
        core_traits: Optional[list[dict]] = None,
        behavioral_tendencies: Optional[dict] = None,
        psychological_model: Optional[dict] = None,
        source: str = "manual"
    ) -> PersonalityLoadout:
        """创建性格配置"""
        loadout = PersonalityLoadout(
            character_id=character_id,
            name=name,
            big_five_openness=big_five.get("openness", 50.0) if big_five else 50.0,
            big_five_conscientiousness=big_five.get("conscientiousness", 50.0) if big_five else 50.0,
            big_five_extraversion=big_five.get("extraversion", 50.0) if big_five else 50.0,
            big_five_agreeableness=big_five.get("agreeableness", 50.0) if big_five else 50.0,
            big_five_neuroticism=big_five.get("neuroticism", 50.0) if big_five else 50.0,
            core_traits=core_traits,
            behavioral_tendencies=behavioral_tendencies,
            psychological_model=psychological_model,
            source=source
        )
        self.db.add(loadout)
        await self.db.flush()
        return loadout
    
    async def get_loadout(self, character_id: int) -> Optional[PersonalityLoadout]:
        """获取角色性格配置"""
        result = await self.db.execute(
            select(PersonalityLoadout).where(
                PersonalityLoadout.character_id == character_id,
                PersonalityLoadout.is_active == True
            )
        )
        return result.scalar_one_or_none()
    
    async def update_loadout(
        self,
        character_id: int,
        **kwargs
    ) -> Optional[PersonalityLoadout]:
        """更新性格配置"""
        loadout = await self.get_loadout(character_id)
        if not loadout:
            return None
        
        # 如果更新了分数，需要记录版本
        if any(k in kwargs for k in ["big_five_openness", "big_five_conscientiousness", 
                                       "big_five_extraversion", "big_five_agreeableness",
                                       "big_five_neuroticism", "core_traits"]):
            loadout.version += 1
        
        for key, value in kwargs.items():
            if hasattr(loadout, key):
                setattr(loadout, key, value)
        
        await self.db.flush()
        return loadout
    
    async def derive_from_text(
        self,
        character_id: int,
        description: str
    ) -> PersonalityLoadout:
        """
        从角色描述 LLM 提取性格
        
        TODO: 集成 LLM 解析
        """
        # TODO: 调用 LLM 解析角色描述
        return await self.create_loadout(
            character_id=character_id,
            name=f"Derived from description",
            source="llm"
        )
    
    async def record_trait_instance(
        self,
        character_id: int,
        trait_type: TraitType,
        strength: float,
        chapter_number: Optional[int] = None,
        context: Optional[str] = None,
        description: Optional[str] = None
    ) -> PersonalityTraitInstance:
        """记录特质实例"""
        # 确定特质类别
        category = self._get_trait_category(trait_type)
        
        instance = PersonalityTraitInstance(
            character_id=character_id,
            trait_type=trait_type,
            trait_category=category,
            strength=strength,
            chapter_number=chapter_number,
            context=context,
            description=description
        )
        self.db.add(instance)
        await self.db.flush()
        return instance
    
    def _get_trait_category(self, trait_type: TraitType) -> TraitCategory:
        """获取特质类别"""
        mapping = {
            TraitType.OPENNESS: TraitCategory.BIG_FIVE,
            TraitType.CONSCIENTIOUSNESS: TraitCategory.BIG_FIVE,
            TraitType.EXTRAVERSION: TraitCategory.BIG_FIVE,
            TraitType.AGREEABLENESS: TraitCategory.BIG_FIVE,
            TraitType.NEUROTICISM: TraitCategory.BIG_FIVE,
            TraitType.HONESTY: TraitCategory.MORAL,
            TraitType.LOYALTY: TraitCategory.MORAL,
            TraitType.JUSTICE: TraitCategory.MORAL,
            TraitType.MERCY: TraitCategory.MORAL,
            TraitType.WISDOM: TraitCategory.MORAL,
            TraitType.LEADERSHIP: TraitCategory.SOCIAL,
            TraitType.EMPATHY: TraitCategory.SOCIAL,
            TraitType.MANIPULATION: TraitCategory.SOCIAL,
            TraitType.AUTHORITY: TraitCategory.SOCIAL,
            TraitType.CURIOSITY: TraitCategory.COGNITIVE,
            TraitType.RATIONALITY: TraitCategory.COGNITIVE,
            TraitType.INTUITION: TraitCategory.COGNITIVE,
            TraitType.CREATIVITY: TraitCategory.COGNITIVE,
            TraitType.COURAGE: TraitCategory.EMOTIONAL,
            TraitType.FEAR: TraitCategory.EMOTIONAL,
            TraitType.ANGER: TraitCategory.EMOTIONAL,
            TraitType.COMPASSION: TraitCategory.EMOTIONAL,
            TraitType.IMPULSIVITY: TraitCategory.BEHAVIORAL,
            TraitType.PATIENCE: TraitCategory.BEHAVIORAL,
            TraitType.FLEXIBILITY: TraitCategory.BEHAVIORAL,
            TraitType.PERSISTENCE: TraitCategory.BEHAVIORAL,
            TraitType.POWER: TraitCategory.MOTIVATION,
            TraitType.ACHIEVEMENT: TraitCategory.MOTIVATION,
            TraitType.AFFILIATION: TraitCategory.MOTIVATION,
            TraitType.SELF_DIRECTION: TraitCategory.MOTIVATION,
        }
        return mapping.get(trait_type, TraitCategory.BEHAVIORAL)
    
    async def record_evolution(
        self,
        character_id: int,
        trait_type: TraitType,
        change_type: str,
        before_value: Optional[float] = None,
        after_value: Optional[float] = None,
        trigger_chapter: Optional[int] = None,
        trigger_event: Optional[str] = None,
        explanation: Optional[str] = None
    ) -> PersonalityEvolution:
        """记录性格变化"""
        evolution = PersonalityEvolution(
            character_id=character_id,
            trait_type=trait_type,
            change_type=change_type,
            before_value=before_value,
            after_value=after_value,
            trigger_chapter=trigger_chapter,
            trigger_event=trigger_event,
            explanation=explanation
        )
        self.db.add(evolution)
        await self.db.flush()
        return evolution
    
    async def get_evolution_history(
        self,
        character_id: int,
        limit: int = 20
    ) -> list[PersonalityEvolution]:
        """获取性格变化历史"""
        result = await self.db.execute(
            select(PersonalityEvolution)
            .where(PersonalityEvolution.character_id == character_id)
            .order_by(PersonalityEvolution.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_summary(self, character_id: int) -> Optional[PersonalitySummary]:
        """获取性格摘要"""
        loadout = await self.get_loadout(character_id)
        if not loadout:
            return None
        
        return PersonalitySummary(
            character_id=character_id,
            big_five={
                "openness": loadout.big_five_openness,
                "conscientiousness": loadout.big_five_conscientiousness,
                "extraversion": loadout.big_five_extraversion,
                "agreeableness": loadout.big_five_agreeableness,
                "neuroticism": loadout.big_five_neuroticism
            },
            core_traits=loadout.core_traits or [],
            behavioral_tendencies=loadout.behavioral_tendencies or {},
            psychological_model=loadout.psychological_model or {}
        )
    
    async def check_consistency(
        self,
        character_id: int,
        action: str
    ) -> dict:
        """
        检查行为是否符合性格
        
        TODO: 实现一致性检查
        - 分析动作
        - 对比性格配置
        - 返回一致性评分
        """
        loadout = await self.get_loadout(character_id)
        if not loadout:
            return {"consistent": True, "score": 1.0, "notes": "No loadout found"}
        
        # TODO: 实现实际检查逻辑
        return {
            "consistent": True,
            "score": 1.0,
            "notes": "Placeholder - integrate with LLM"
        }