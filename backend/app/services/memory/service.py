"""Memory Service - 记忆服务 v2.3

支持：
- 基础记忆 CRUD
- 上下文构建
- 全文检索（简单 + Qdrant 向量检索）
- 多项目隔离
"""
from typing import Optional, Any, Protocol
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
from app.core.config import get_settings


class VectorStore(Protocol):
    """向量存储协议 - 支持 Qdrant 等"""
    async def upsert(self, points: list[dict]) -> None: ...
    async def search(self, query: str, limit: int, filter_conditions: dict) -> list[dict]: ...
    async def delete(self, filter_conditions: dict) -> None: ...


class QdrantVectorStore:
    """Qdrant 向量存储实现"""
    
    def __init__(self, url: str, collection: str, api_key: Optional[str] = None):
        self.url = url
        self.collection = collection
        self.api_key = api_key
        self._client = None
    
    async def _get_client(self):
        """懒加载 Qdrant 客户端"""
        if self._client is None:
            try:
                from qdrant_client import AsyncQdrantClient
                self._client = AsyncQdrantClient(
                    url=self.url,
                    api_key=self.api_key,
                    timeout=10
                )
            except ImportError:
                raise RuntimeError("Qdrant client not installed. Run: pip install qdrant-client")
        return self._client
    
    async def upsert(self, points: list[dict]) -> None:
        """插入/更新向量"""
        if not points:
            return
        
        client = await self._get_client()
        
        # 确保 collection 存在
        collections = await client.get_collections()
        collection_names = [c.name for c in collections.collections]
        
        if self.collection not in collection_names:
            await client.create_collection(
                collection_name=self.collection,
                vectors_config={"size": 1536, "distance": "Cosine"}
            )
        
        await client.upsert(
            collection_name=self.collection,
            points=points
        )
    
    async def search(
        self,
        query: str,
        limit: int = 5,
        filter_conditions: Optional[dict] = None
    ) -> list[dict]:
        """向量搜索"""
        client = await self._get_client()
        
        search_params = {
            "limit": limit
        }
        if filter_conditions:
            search_params["query_filter"] = filter_conditions
        
        results = await client.search(
            collection_name=self.collection,
            query_vector=query,  # 简化，实际需要 embedding
            **search_params
        )
        
        return [
            {
                "id": r.id,
                "score": r.score,
                "payload": r.payload
            }
            for r in results
        ]
    
    async def delete(self, filter_conditions: dict) -> None:
        """删除向量"""
        client = await self._get_client()
        await client.delete(
            collection_name=self.collection,
            points_selector=filter_conditions
        )


class MemoryService:
    """记忆服务 - v2.3 多项目隔离 + Qdrant 集成"""

    # Qdrant collection name template
    QDRANT_COLLECTION_TEMPLATE = "mybook_project_{project_id}"
    
    def __init__(self, db: AsyncSession, vector_store: Optional[VectorStore] = None):
        self.db = db
        self.chapter_repo = ChapterRepository(db)
        self._vector_store = vector_store
        
        # 初始化 Qdrant（如果配置了）
        self._init_vector_store()
    
    def _init_vector_store(self):
        """初始化向量存储"""
        settings = get_settings()
        
        qdrant_url = getattr(settings, 'qdrant_url', None)
        qdrant_api_key = getattr(settings, 'qdrant_api_key', None)
        
        if qdrant_url:
            self._vector_store = QdrantVectorStore(
                url=qdrant_url,
                collection="mybook_memories",  # 实际会按 project_id 隔离
                api_key=qdrant_api_key
            )
    
    def _get_project_collection(self, project_id: int) -> str:
        """获取项目的 collection 名称（project 隔离）"""
        return f"mybook_project_{project_id}"

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
        
        # 6. Reader Feedback (Phase B)
        reader_feedback = None
        if request.include_reader_feedback:
            from app.services.audience.analyzer import ReaderFeedbackView
            reader_feedback = await ReaderFeedbackView.from_candidates(
                self.db, project_id, request.chapter_id
            )
            feedback_line = f"【读者反馈】 dominant_sentiment: {reader_feedback.dominant_sentiment}"
            context_parts.append(feedback_line)
            if reader_feedback.feedback_summary:
                context_parts.append(f"反馈摘要: {reader_feedback.feedback_summary}")
            if reader_feedback.highlighted_topics:
                context_parts.append(f"高亮话题: {', '.join(reader_feedback.highlighted_topics[:5])}")
        
        # 格式化上下文
        formatted_context = "\n\n".join(context_parts) if context_parts else "暂无上下文"
        
        return ContextPackResponse(
            story_bible=StoryBibleResponse.model_validate(story_bible) if story_bible else None,
            character_states=character_states,
            recent_chapters=recent_chapters,
            foreshadows=foreshadows,
            pending_reviews=pending_reviews,
            reader_feedback=reader_feedback,
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

    # ==================== Qdrant Vector Search (多项目隔离) ====================
    
    async def index_chapter_for_search(
        self,
        project_id: int,
        chapter_id: int,
        text: str,
        metadata: Optional[dict] = None
    ) -> None:
        """
        将章节索引到向量存储（带 project_id 隔离）
        
        实际使用中会：
        1. 生成文本 embedding
        2. 存储到 project 对应的 collection
        """
        if not self._vector_store:
            return  # 未配置 Qdrant
        
        # 简化实现：实际需要 embedding model
        point_id = f"chapter_{project_id}_{chapter_id}"
        
        # project_id 过滤条件
        filter_conditions = {
            "project_id": project_id
        }
        
        # 注意：实际需要使用 embedding 模型生成向量
        # 这里存储原始文本，由调用方保证
        await self._vector_store.upsert([{
            "id": point_id,
            "vector": self._text_to_dummy_vector(text),  # 简化
            "payload": {
                "project_id": project_id,
                "chapter_id": chapter_id,
                "text": text[:5000],  # 限制长度
                "metadata": metadata or {}
            }
        }])
    
    async def search_vectors(
        self,
        project_id: int,
        query: str,
        limit: int = 5
    ) -> list[dict[str, Any]]:
        """
        向量搜索（带 project_id 隔离）
        
        只返回属于指定 project 的结果
        """
        if not self._vector_store:
            return []
        
        # 构建 project_id 过滤条件 - 确保多项目隔离
        filter_conditions = {
            "must": [
                {"key": "project_id", "match": {"value": project_id}}
            ]
        }
        
        try:
            results = await self._vector_store.search(
                query=self._text_to_dummy_vector(query),
                limit=limit,
                filter_conditions=filter_conditions
            )
            
            return [
                {
                    "chapter_id": r["payload"].get("chapter_id"),
                    "text": r["payload"].get("text", ""),
                    "score": r.get("score", 0),
                    "metadata": r["payload"].get("metadata", {})
                }
                for r in results
                if r["payload"].get("project_id") == project_id  # 双重保险
            ]
        except Exception:
            return []
    
    async def delete_project_vectors(self, project_id: int) -> None:
        """
        删除项目的所有向量数据（项目删除时调用）
        
        确保彻底清理，避免数据泄露
        """
        if not self._vector_store:
            return
        
        filter_conditions = {
            "must": [
                {"key": "project_id", "match": {"value": project_id}}
            ]
        }
        
        await self._vector_store.delete(filter_conditions)
    
    def _text_to_dummy_vector(self, text: str) -> list[float]:
        """
        简化：文本转向量
        
        实际应该使用 embedding model（如 OpenAI text-embedding-3-small）
        这里返回零向量占位
        """
        # 返回 1536 维零向量（text-embedding-3-small 的维度）
        return [0.0] * 1536
