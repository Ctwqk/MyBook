"""Memory Service - 记忆服务"""
from typing import Optional, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.story_bible import StoryBible
from app.models.character import Character
from app.models.character_state import CharacterState
from app.models.chapter import Chapter
from app.models.chapter_memory import ChapterMemory
from app.models.foreshadow_record import ForeshadowRecord, ForeshadowStatus
from app.models.review_note import ReviewNote
from app.schemas.memory import (
    StoryBibleResponse,
    ContextPackRequest,
    ContextPackResponse,
    ForeshadowRecordCreate,
)
from app.repositories.chapter import ChapterRepository


class MemoryService:
    """记忆服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.chapter_repo = ChapterRepository(db)

    # ==================== Story Bible ====================
    
    async def get_story_bible(self, project_id: int) -> Optional[StoryBible]:
        """获取 Story Bible"""
        result = await self.db.execute(
            select(StoryBible).where(StoryBible.project_id == project_id)
        )
        return result.scalar_one_or_none()

    async def update_story_bible(
        self,
        project_id: int,
        updates: dict[str, Any]
    ) -> StoryBible:
        """更新 Story Bible"""
        story_bible = await self.get_story_bible(project_id)
        if not story_bible:
            story_bible = StoryBible(project_id=project_id)
            self.db.add(story_bible)
        
        for key, value in updates.items():
            if hasattr(story_bible, key):
                setattr(story_bible, key, value)
        
        await self.db.flush()
        await self.db.refresh(story_bible)
        return story_bible

    # ==================== Characters ====================
    
    async def get_characters(self, project_id: int) -> list[Character]:
        """获取项目角色列表"""
        result = await self.db.execute(
            select(Character).where(Character.project_id == project_id)
        )
        return list(result.scalars().all())

    async def create_character(
        self,
        project_id: int,
        data: dict[str, Any]
    ) -> Character:
        """创建角色"""
        character = Character(
            project_id=project_id,
            name=data.get("name"),
            role_type=data.get("role_type", "supporting"),
            profile=data.get("profile"),
            personality=data.get("personality"),
            motivation=data.get("motivation"),
            secrets=data.get("secrets"),
            relationships=data.get("relationships"),
            current_state=data.get("current_state"),
            power_level=data.get("power_level"),
            tags=data.get("tags"),
        )
        self.db.add(character)
        await self.db.flush()
        await self.db.refresh(character)
        return character

    # ==================== Character States ====================
    
    async def get_character_states(
        self,
        project_id: int,
        character_id: Optional[int] = None
    ) -> list[CharacterState]:
        """获取角色状态"""
        query = select(CharacterState).where(CharacterState.project_id == project_id)
        if character_id:
            query = query.where(CharacterState.character_id == character_id)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_character_states(
        self,
        project_id: int,
        character_id: int,
        state_data: dict[str, Any]
    ) -> CharacterState:
        """更新角色状态"""
        # 查找现有状态
        result = await self.db.execute(
            select(CharacterState)
            .where(
                CharacterState.project_id == project_id,
                CharacterState.character_id == character_id
            )
            .order_by(CharacterState.updated_at.desc())
        )
        state = result.scalar_one_or_none()
        
        if not state:
            state = CharacterState(
                project_id=project_id,
                character_id=character_id
            )
            self.db.add(state)
        
        for key, value in state_data.items():
            if hasattr(state, key):
                setattr(state, key, value)
        
        await self.db.flush()
        await self.db.refresh(state)
        return state

    # ==================== Chapter Memory ====================
    
    async def save_chapter_memory(
        self,
        project_id: int,
        chapter_id: int,
        memory_data: dict[str, Any]
    ) -> ChapterMemory:
        """保存章节记忆"""
        memory = ChapterMemory(
            project_id=project_id,
            chapter_id=chapter_id,
            summary=memory_data.get("summary"),
            key_events=memory_data.get("key_events"),
            new_world_details=memory_data.get("new_world_details"),
            foreshadow_changes=memory_data.get("foreshadow_changes")
        )
        self.db.add(memory)
        await self.db.flush()
        await self.db.refresh(memory)
        return memory

    async def get_chapter_memory(
        self,
        project_id: int,
        chapter_id: int
    ) -> Optional[ChapterMemory]:
        """获取章节记忆"""
        result = await self.db.execute(
            select(ChapterMemory)
            .where(
                ChapterMemory.project_id == project_id,
                ChapterMemory.chapter_id == chapter_id
            )
        )
        return result.scalar_one_or_none()

    async def get_chapter_memories(
        self,
        project_id: int,
        limit: int = 5
    ) -> list[ChapterMemory]:
        """获取最近的章节记忆"""
        result = await self.db.execute(
            select(ChapterMemory)
            .where(ChapterMemory.project_id == project_id)
            .order_by(ChapterMemory.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    # ==================== Foreshadow ====================
    
    async def record_foreshadow(
        self,
        project_id: int,
        chapter_id: int,
        content: str,
        related_entities: Optional[list[str]] = None,
        planned_resolution: Optional[str] = None
    ) -> ForeshadowRecord:
        """记录伏笔"""
        foreshadow = ForeshadowRecord(
            project_id=project_id,
            chapter_id=chapter_id,
            content=content,
            related_entities=related_entities,
            planned_resolution=planned_resolution,
            status=ForeshadowStatus.SETUP
        )
        self.db.add(foreshadow)
        await self.db.flush()
        await self.db.refresh(foreshadow)
        return foreshadow

    async def resolve_foreshadow(
        self,
        foreshadow_id: int
    ) -> ForeshadowRecord:
        """解决伏笔"""
        result = await self.db.execute(
            select(ForeshadowRecord).where(ForeshadowRecord.id == foreshadow_id)
        )
        foreshadow = result.scalar_one_or_none()
        if not foreshadow:
            raise ValueError(f"Foreshadow {foreshadow_id} not found")
        
        foreshadow.status = ForeshadowStatus.RESOLVED
        await self.db.flush()
        await self.db.refresh(foreshadow)
        return foreshadow

    async def get_active_foreshadows(
        self,
        project_id: int
    ) -> list[ForeshadowRecord]:
        """获取活跃伏笔"""
        result = await self.db.execute(
            select(ForeshadowRecord)
            .where(
                ForeshadowRecord.project_id == project_id,
                ForeshadowRecord.status.in_([ForeshadowStatus.SETUP, ForeshadowStatus.DEVELOPING])
            )
        )
        return list(result.scalars().all())

    # ==================== Review Notes ====================
    
    async def record_review_note(
        self,
        project_id: int,
        chapter_id: int,
        issue_type: str,
        severity: str,
        description: str,
        fix_suggestion: Optional[str] = None
    ) -> ReviewNote:
        """记录审查笔记"""
        note = ReviewNote(
            project_id=project_id,
            chapter_id=chapter_id,
            issue_type=issue_type,
            severity=severity,
            description=description,
            fix_suggestion=fix_suggestion
        )
        self.db.add(note)
        await self.db.flush()
        await self.db.refresh(note)
        return note

    async def get_pending_reviews(
        self,
        project_id: int
    ) -> list[ReviewNote]:
        """获取待处理审查"""
        result = await self.db.execute(
            select(ReviewNote)
            .where(ReviewNote.project_id == project_id)
            .order_by(ReviewNote.created_at.desc())
        )
        return list(result.scalars().all())

    # ==================== Context Pack ====================
    
    async def build_context_pack(
        self,
        project_id: int,
        request: ContextPackRequest
    ) -> ContextPackResponse:
        """构建上下文包"""
        context_parts = []
        
        # 1. Story Bible
        story_bible = None
        if request.include_story_bible:
            story_bible = await self.get_story_bible(project_id)
            if story_bible:
                context_parts.append(f"【故事背景】\n{story_bible.synopsis or story_bible.world_overview or '暂无'}")
        
        # 2. Character States
        character_states = []
        if request.include_character_states:
            states = await self.get_character_states(project_id)
            character_states = [
                {
                    "character_id": s.character_id,
                    "location": s.location,
                    "goal": s.goal,
                    "emotional_state": s.emotional_state,
                    "last_event": s.last_event
                }
                for s in states
            ]
            if states:
                context_parts.append("【角色状态】")
                for s in states:
                    context_parts.append(f"- {s.character_id}: {s.location or '未知'}, {s.goal or '无目标'}")
        
        # 3. Recent Chapters
        recent_chapters = []
        if request.include_recent_chapters > 0:
            chapters = await self.chapter_repo.get_recent_chapters(project_id, request.include_recent_chapters)
            recent_chapters = [
                {
                    "chapter_no": c.chapter_no,
                    "title": c.title,
                    "summary": c.summary
                }
                for c in chapters
            ]
            if chapters:
                context_parts.append("【最近章节】")
                for c in reversed(chapters):
                    context_parts.append(f"第{c.chapter_no}章: {c.summary or c.outline or '暂无摘要'}")
        
        # 4. Foreshadows
        foreshadows = []
        if request.include_foreshadows:
            active = await self.get_active_foreshadows(project_id)
            foreshadows = [
                {
                    "id": f.id,
                    "content": f.content,
                    "status": f.status.value
                }
                for f in active
            ]
            if active:
                context_parts.append("【伏笔】")
                for f in active:
                    context_parts.append(f"- {f.content}")
        
        # 5. Pending Reviews
        pending_reviews = []
        if request.include_pending_reviews:
            notes = await self.get_pending_reviews(project_id)
            pending_reviews = [
                {
                    "chapter_id": n.chapter_id,
                    "issue_type": n.issue_type.value,
                    "description": n.description
                }
                for n in notes
            ]
        
        # 格式化上下文
        formatted_context = "\n\n".join(context_parts) if context_parts else "暂无上下文"
        
        return ContextPackResponse(
            story_bible=StoryBibleResponse.model_validate(story_bible) if story_bible else None,
            character_states=character_states,
            recent_chapters=recent_chapters,
            foreshadows=foreshadows,
            pending_reviews=pending_reviews,
            formatted_context=formatted_context
        )

    # ==================== Search ====================
    
    async def search_memory(
        self,
        project_id: int,
        query: str,
        search_type: str = "all"
    ) -> list[dict[str, Any]]:
        """
        搜索记忆
        
        Note: 第一版使用简单文本搜索，后续可集成 pgvector/Qdrant
        """
        results = []
        
        if search_type in ["all", "bible"]:
            # 搜索 Story Bible
            bible = await self.get_story_bible(project_id)
            if bible:
                bible_text = " ".join([
                    bible.title or "",
                    bible.synopsis or "",
                    bible.world_overview or "",
                    bible.theme or ""
                ])
                if query.lower() in bible_text.lower():
                    results.append({
                        "type": "story_bible",
                        "content": bible.synopsis or bible.world_overview,
                        "relevance": 0.8
                    })
        
        if search_type in ["all", "chapter"]:
            # 搜索章节
            chapters = await self.chapter_repo.get_by_project(project_id, limit=50)
            for ch in chapters:
                search_text = " ".join([
                    ch.title or "",
                    ch.outline or "",
                    ch.summary or ""
                ])
                if query.lower() in search_text.lower():
                    results.append({
                        "type": "chapter",
                        "chapter_id": ch.id,
                        "chapter_no": ch.chapter_no,
                        "content": ch.summary or ch.outline,
                        "relevance": 0.7
                    })
        
        return results
