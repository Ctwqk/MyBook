"""Writer Service - 写作服务"""
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.base import LLMProvider
from app.llm.mock import MockLLMProvider
from app.models.chapter import Chapter, ChapterStatus
from app.models.character_state import CharacterState
from app.schemas.chapter import (
    GenerateChapterRequest,
    ContinueChapterRequest,
    RewriteChapterRequest,
    PatchChapterRequest,
)
from app.schemas.memory import ContextPackRequest
from app.repositories.chapter import ChapterRepository
from app.services.memory.service import MemoryService
from app.services.writer.prompts import (
    CHAPTER_GENERATION_PROMPT,
    CHAPTER_CONTINUATION_PROMPT,
    CHAPTER_REWRITE_PROMPT,
    CHAPTER_PATCH_PROMPT,
    CHAPTER_EXTRACTION_PROMPT,
)


class WriterService:
    """写作服务"""

    def __init__(
        self,
        db: AsyncSession,
        llm_provider: Optional[LLMProvider] = None
    ):
        self.db = db
        self.llm = llm_provider or MockLLMProvider()
        self.chapter_repo = ChapterRepository(db)
        self.memory_service = MemoryService(db)

    async def generate_chapter(
        self,
        project_id: int,
        chapter_id: int,
        request: GenerateChapterRequest
    ) -> dict[str, Any]:
        """
        生成章节正文
        
        Args:
            project_id: 项目 ID
            chapter_id: 章节 ID
            request: 生成请求
            
        Returns:
            dict: 包含正文和提取信息的字典
        """
        # 获取章节信息
        chapter = await self.chapter_repo.get(chapter_id)
        if not chapter:
            raise ValueError(f"Chapter {chapter_id} not found")
        
        # 构建上下文包
        context_request = ContextPackRequest(
            chapter_id=chapter_id,
            include_story_bible=True,
            include_character_states=True,
            include_recent_chapters=3,
            include_foreshadows=True
        )
        context_pack = await self.memory_service.build_context_pack(project_id, context_request)
        
        # 构建 prompt
        outline = request.outline or chapter.outline or ""
        system_prompt = """你是一个专业的小说写作助手。你的任务是根据章节大纲和上下文，
        创作引人入胜的小说章节。注意保持文笔流畅，情节紧凑，人物鲜活。"""
        
        prompt = CHAPTER_GENERATION_PROMPT.format(
            chapter_no=chapter.chapter_no,
            title=chapter.title or f"第{chapter.chapter_no}章",
            outline=outline,
            context=context_pack.formatted_context,
            style_hints=request.style_hints or ""
        )
        
        # 调用 LLM 生成
        response = await self.llm.generate(prompt, system_prompt)
        text = response.content
        
        # 更新章节
        word_count = len(text) // 2  # 粗略估算中文字数
        chapter.text = text
        chapter.word_count = word_count
        chapter.status = ChapterStatus.DRAFT
        
        await self.db.flush()
        await self.db.refresh(chapter)
        
        # 提取摘要和状态变化
        extracted = await self._extract_chapter_data(text, chapter.chapter_no)
        
        return {
            "chapter": chapter,
            "text": text,
            "word_count": word_count,
            "summary": extracted.get("summary"),
            "state_changes": extracted.get("state_changes", []),
            "foreshadow_changes": extracted.get("foreshadow_changes", [])
        }

    async def continue_chapter(
        self,
        project_id: int,
        chapter_id: int,
        request: ContinueChapterRequest
    ) -> dict[str, Any]:
        """
        续写章节
        
        Args:
            project_id: 项目 ID
            chapter_id: 章节 ID
            request: 续写请求
            
        Returns:
            dict: 包含续写内容的字典
        """
        chapter = await self.chapter_repo.get(chapter_id)
        if not chapter:
            raise ValueError(f"Chapter {chapter_id} not found")
        
        # 获取上下文
        context_request = ContextPackRequest(
            chapter_id=chapter_id,
            include_story_bible=True,
            include_character_states=True,
            include_recent_chapters=1,
            include_foreshadows=True
        )
        context_pack = await self.memory_service.build_context_pack(project_id, context_request)
        
        # 确定续写起点
        last_content = request.last_paragraph or chapter.text[-500:] if chapter.text else ""
        
        system_prompt = """你是一个专业的小说写作助手。你的任务是在已有内容的基础上，
        继续创作小说内容，保持文风一致，情节连贯。"""
        
        prompt = CHAPTER_CONTINUATION_PROMPT.format(
            chapter_no=chapter.chapter_no,
            existing_text=chapter.text or "",
            last_paragraph=last_content,
            context=context_pack.formatted_context,
            target_word_count=request.target_word_count
        )
        
        response = await self.llm.generate(prompt, system_prompt)
        continuation = response.content
        
        # 更新章节
        new_text = (chapter.text or "") + "\n\n" + continuation
        chapter.text = new_text
        chapter.word_count = len(new_text) // 2
        chapter.status = ChapterStatus.WRITING
        
        await self.db.flush()
        await self.db.refresh(chapter)
        
        return {
            "chapter": chapter,
            "continuation": continuation,
            "new_word_count": chapter.word_count
        }

    async def rewrite_chapter(
        self,
        project_id: int,
        chapter_id: int,
        request: RewriteChapterRequest
    ) -> dict[str, Any]:
        """
        重写章节
        
        Args:
            project_id: 项目 ID
            chapter_id: 章节 ID
            request: 重写请求
            
        Returns:
            dict: 包含重写内容的字典
        """
        chapter = await self.chapter_repo.get(chapter_id)
        if not chapter:
            raise ValueError(f"Chapter {chapter_id} not found")
        
        # 获取上下文
        context_request = ContextPackRequest(
            chapter_id=chapter_id,
            include_story_bible=True,
            include_character_states=True,
            include_recent_chapters=2,
            include_foreshadows=True
        )
        context_pack = await self.memory_service.build_context_pack(project_id, context_request)
        
        system_prompt = """你是一个专业的小说编辑。你的任务是按照给定的修改指令，
        重写小说章节，保持核心情节不变，但改进指定的问题。"""
        
        prompt = CHAPTER_REWRITE_PROMPT.format(
            chapter_no=chapter.chapter_no,
            existing_text=chapter.text or "",
            rewrite_instructions=request.rewrite_instructions,
            context=context_pack.formatted_context
        )
        
        response = await self.llm.generate(prompt, system_prompt)
        rewritten = response.content
        
        # 更新章节
        chapter.text = rewritten
        chapter.word_count = len(rewritten) // 2
        
        await self.db.flush()
        await self.db.refresh(chapter)
        
        return {
            "chapter": chapter,
            "rewritten_text": rewritten,
            "word_count": chapter.word_count
        }

    async def patch_chapter_segment(
        self,
        project_id: int,
        chapter_id: int,
        request: PatchChapterRequest
    ) -> dict[str, Any]:
        """
        修补章节段落
        
        Args:
            project_id: 项目 ID
            chapter_id: 章节 ID
            request: 修补请求
            
        Returns:
            dict: 包含修补后内容的字典
        """
        chapter = await self.chapter_repo.get(chapter_id)
        if not chapter:
            raise ValueError(f"Chapter {chapter_id} not found")
        
        system_prompt = """你是一个专业的小说编辑。你的任务是修补小说中的特定段落，
        按照修改指令进行局部修改，保持整体风格一致。"""
        
        prompt = CHAPTER_PATCH_PROMPT.format(
            chapter_no=chapter.chapter_no,
            existing_text=chapter.text or "",
            segment_id=request.segment_id,
            segment_content=request.segment_content,
            patch_instructions=request.patch_instructions
        )
        
        response = await self.llm.generate(prompt, system_prompt)
        patched = response.content
        
        # 替换原段落
        if chapter.text and request.segment_content in chapter.text:
            new_text = chapter.text.replace(request.segment_content, patched)
        else:
            new_text = patched
        
        chapter.text = new_text
        chapter.word_count = len(new_text) // 2
        
        await self.db.flush()
        await self.db.refresh(chapter)
        
        return {
            "chapter": chapter,
            "patched_segment": patched,
            "new_word_count": chapter.word_count
        }

    async def _extract_chapter_data(
        self,
        text: str,
        chapter_no: int
    ) -> dict[str, Any]:
        """提取章节数据：摘要、状态变化、伏笔变化"""
        system_prompt = """你是一个专业的小说分析助手。请分析小说章节内容，
        提取以下信息：摘要、状态变化、伏笔变化。请以结构化格式输出。"""
        
        prompt = CHAPTER_EXTRACTION_PROMPT.format(
            chapter_no=chapter_no,
            text=text[:3000]  # 限制文本长度
        )
        
        response = await self.llm.generate(prompt, system_prompt)
        
        # TODO: 解析结构化输出
        # 暂时返回模拟数据
        return {
            "summary": f"第{chapter_no}章主要讲述了...",
            "state_changes": [],
            "foreshadow_changes": []
        }
