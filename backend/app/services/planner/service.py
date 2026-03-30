"""Planner Service - 规划服务"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.base import LLMProvider
from app.llm.mock import MockLLMProvider
from app.models.project import Project
from app.models.story_bible import StoryBible
from app.models.character import Character
from app.models.volume import Volume
from app.models.chapter import Chapter, ChapterStatus
from app.services.planner.schemas import (
    PremiseAnalysis,
    StoryBibleDraft,
    CharacterCard,
    ArcPlan,
    ChapterOutline,
)
from app.repositories.project import ProjectRepository
from app.repositories.chapter import ChapterRepository
from app.services.planner.prompts import (
    PREMISE_ANALYSIS_PROMPT,
    STORY_BIBLE_PROMPT,
    CHARACTER_CARD_PROMPT,
    ARC_PLAN_PROMPT,
    CHAPTER_OUTLINE_PROMPT,
)


class PlannerService:
    """规划服务"""

    def __init__(self, db: AsyncSession, llm_provider: Optional[LLMProvider] = None):
        self.db = db
        self.llm = llm_provider or MockLLMProvider()
        self.project_repo = ProjectRepository(db)
        self.chapter_repo = ChapterRepository(db)

    async def parse_premise(self, premise: str) -> PremiseAnalysis:
        """
        解析 premise
        
        Args:
            premise: 用户输入的想法/剧情
            
        Returns:
            PremiseAnalysis: 解析后的结构化分析
        """
        system_prompt = """你是一个专业的小说策划助手。你需要分析用户提供的想法或剧情简述，
        提取出核心元素并结构化输出。"""
        
        prompt = PREMISE_ANALYSIS_PROMPT.format(premise=premise)
        response = await self.llm.generate(prompt, system_prompt)
        
        # TODO: 解析 LLM 返回的结构化数据
        # 暂时返回模拟数据
        return PremiseAnalysis(
            genre="都市异能",
            theme="成长与觉醒",
            tone="热血、神秘",
            target_audience="年轻读者",
            key_elements=["主角", "神秘力量", "成长历程"],
            potential_conflicts=["正邪对立", "身世之谜"]
        )

    async def bootstrap_story(
        self,
        project_id: int,
        premise: str,
        genre: Optional[str] = None,
        style: Optional[str] = None
    ) -> StoryBibleDraft:
        """
        引导故事 - 生成 Story Bible 初稿
        
        Args:
            project_id: 项目 ID
            premise: 剧情简述
            genre: 类型
            style: 风格
            
        Returns:
            StoryBibleDraft: Story Bible 初稿
        """
        project = await self.project_repo.get(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        # 构建 prompt
        system_prompt = """你是一个专业的小说世界观设计师。你的任务是根据用户提供的想法，
        创建一个完整的故事圣经（Story Bible）。包括世界观、主题、角色设定等核心元素。"""
        
        prompt = STORY_BIBLE_PROMPT.format(
            project_title=project.title,
            premise=premise,
            genre=genre or project.genre or "通用",
            style=style or project.style or "正常"
        )
        
        response = await self.llm.generate(prompt, system_prompt)
        
        # TODO: 解析结构化输出
        # 创建 StoryBible 记录
        story_bible = StoryBible(
            project_id=project_id,
            title=project.title,
            genre=genre or project.genre,
            logline=premise,
            synopsis=response.content[:2000] if len(response.content) > 2000 else response.content,
        )
        self.db.add(story_bible)
        
        return StoryBibleDraft(
            title=project.title,
            genre=genre or project.genre or "通用",
            theme="待定义",
            logline=premise,
            synopsis=response.content[:1000],
            world_overview="待填充",
            narrative_structure={}
        )

    async def generate_character_cards(
        self,
        project_id: int,
        count: int = 3
    ) -> list[CharacterCard]:
        """
        生成角色卡
        
        Args:
            project_id: 项目 ID
            count: 生成数量
            
        Returns:
            list[CharacterCard]: 角色卡列表
        """
        # 获取项目信息
        project = await self.project_repo.get(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        # TODO: 获取 story bible 和 premise
        
        system_prompt = """你是一个专业的小说角色设计师。你的任务是根据故事背景，
        创建有血有肉的角色。确保角色有清晰的动机、性格特点和发展空间。"""
        
        prompt = CHARACTER_CARD_PROMPT.format(
            project_title=project.title,
            premise=project.premise or "待定义",
            count=count
        )
        
        response = await self.llm.generate(prompt, system_prompt)
        
        # TODO: 解析结构化输出并创建 Character 记录
        # 暂时返回模拟数据
        mock_cards = []
        for i in range(count):
            card = CharacterCard(
                name=f"角色{i+1}",
                role_type="supporting" if i > 0 else "protagonist",
                profile=f"这是角色{i+1}的简介",
                personality="性格待填充",
                motivation="动机待填充",
                secrets="秘密待填充",
                relationships={}
            )
            mock_cards.append(card)
            
            # 创建数据库记录
            character = Character(
                project_id=project_id,
                name=card.name,
                role_type=card.role_type,
                profile=card.profile,
                personality=card.personality,
                motivation=card.motivation,
                secrets=card.secrets,
                relationships=card.relationships
            )
            self.db.add(character)
        
        return mock_cards

    async def generate_arc_plan(
        self,
        project_id: int,
        total_arcs: int = 3,
        target_chapters_per_arc: int = 30
    ) -> ArcPlan:
        """
        生成卷/弧线规划
        
        Args:
            project_id: 项目 ID
            total_arcs: 总弧线数
            target_chapters_per_arc: 每弧线目标章节数
            
        Returns:
            ArcPlan: 弧线规划
        """
        project = await self.project_repo.get(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        system_prompt = """你是一个专业的小说结构策划师。你的任务是将长篇故事分解为若干个弧线（arc），
        每个弧线有明确的目标、冲突和高潮。确保弧线之间有递进关系。"""
        
        prompt = ARC_PLAN_PROMPT.format(
            project_title=project.title,
            premise=project.premise or "待定义",
            total_arcs=total_arcs,
            target_chapters_per_arc=target_chapters_per_arc
        )
        
        response = await self.llm.generate(prompt, system_prompt)
        
        # TODO: 解析结构化输出并创建 Volume 记录
        volumes = []
        for i in range(total_arcs):
            volume = Volume(
                project_id=project_id,
                volume_no=i + 1,
                title=f"第{i+1}卷",
                goal=f"第{i+1}卷目标",
                conflict=f"第{i+1}卷冲突",
                expected_chapter_count=target_chapters_per_arc,
                summary=f"第{i+1}卷摘要"
            )
            self.db.add(volume)
            volumes.append(volume)
        
        return ArcPlan(
            total_arcs=total_arcs,
            volumes=[v for v in volumes]
        )

    async def generate_chapter_outlines(
        self,
        project_id: int,
        volume_id: Optional[int] = None,
        count: int = 10,
        existing_outlines: Optional[list[str]] = None
    ) -> list[ChapterOutline]:
        """
        生成章节大纲
        
        Args:
            project_id: 项目 ID
            volume_id: 卷 ID（可选）
            count: 生成数量
            existing_outlines: 已有大纲摘要
            
        Returns:
            list[ChapterOutline]: 章节大纲列表
        """
        project = await self.project_repo.get(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        # 获取当前最大章节号
        next_chapter_no = await self.chapter_repo.get_next_chapter_no(project_id)
        
        system_prompt = """你是一个专业的小说章节策划师。你的任务是根据已有的故事大纲，
        为每个章节创建详细的章节大纲，包括起承转合、关键情节点和章节钩子。"""
        
        prompt = CHAPTER_OUTLINE_PROMPT.format(
            project_title=project.title,
            premise=project.premise or "待定义",
            volume_id=volume_id,
            count=count,
            start_chapter_no=next_chapter_no,
            existing_outlines="\n".join(existing_outlines) if existing_outlines else "暂无"
        )
        
        response = await self.llm.generate(prompt, system_prompt)
        
        # TODO: 解析结构化输出并创建 Chapter 记录
        outlines = []
        for i in range(count):
            outline = ChapterOutline(
                chapter_no=next_chapter_no + i,
                title=f"第{next_chapter_no + i}章",
                outline=f"章节大纲内容",
                hook=f"章节钩子",
                key_events=[]
            )
            outlines.append(outline)
            
            # 创建数据库记录
            chapter = Chapter(
                project_id=project_id,
                volume_id=volume_id,
                chapter_no=outline.chapter_no,
                title=outline.title,
                outline=outline.outline,
                hook=outline.hook,
                status=ChapterStatus.OUTLINE
            )
            self.db.add(chapter)
        
        return outlines

    async def revise_outline(
        self,
        chapter_id: int,
        revision_notes: str
    ) -> ChapterOutline:
        """
        修订章节大纲
        
        Args:
            chapter_id: 章节 ID
            revision_notes: 修订笔记
            
        Returns:
            ChapterOutline: 修订后的大纲
        """
        chapter = await self.chapter_repo.get(chapter_id)
        if not chapter:
            raise ValueError(f"Chapter {chapter_id} not found")
        
        # TODO: 调用 LLM 进行修订
        # 暂时返回当前大纲
        return ChapterOutline(
            chapter_no=chapter.chapter_no,
            title=chapter.title or f"第{chapter.chapter_no}章",
            outline=chapter.outline or "待填充",
            hook=chapter.hook or "待填充",
            key_events=[]
        )
