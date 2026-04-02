"""Writer Service - v2.3 Scene 模式 + 错误恢复

支持：
- 单章单次生成（阶段 0.5）
- 分 scene 生成 + stitch（正式阶段）
- 结构化输出
- 错误恢复策略
"""
import asyncio
import json
import re
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.base import LLMProvider
from app.llm.mock import MockLLMProvider
from app.models.chapter import Chapter, ChapterStatus
from app.repositories.chapter import ChapterRepository
from app.services.memory.service import MemoryService
from app.services.orchestrator.schemas import (
    ScenePlan,
    SceneOutput,
    WriterOutput,
    WriterGenerationRequest,
    RetryPolicy,
    OperationMode,
)
from app.schemas.chapter import (
    GenerateChapterRequest,
    ContinueChapterRequest,
    RewriteChapterRequest,
    PatchChapterRequest,
)
from app.schemas.memory import ContextPackRequest
from app.services.writer.prompts import (
    CHAPTER_GENERATION_PROMPT,
    CHAPTER_CONTINUATION_PROMPT,
    CHAPTER_REWRITE_PROMPT,
    CHAPTER_PATCH_PROMPT,
    SCENE_BREAKDOWN_PROMPT,
    SCENE_GENERATION_PROMPT,
    SCENE_STITCH_PROMPT,
    STRUCTURED_EXTRACTION_PROMPT,
    FALLBACK_EXTRACTION_PROMPT,
    WRITER_REPAIR_PROMPT,
)


class WriterService:
    """写作服务 - v2.3"""

    # 清理正则
    THINKING_PATTERNS = [
        (r'<reasoning>.*?</reasoning>', ''),
        (r'<reflection>.*?</reflection>', ''),
        (r'<thinking>.*?</thinking>', ''),
        (r'<[\s\S]*?<\/[\s\S]*?>', ''),
    ]

    def __init__(
        self,
        db: AsyncSession,
        llm_provider: Optional[LLMProvider] = None,
        operation_mode: OperationMode = OperationMode.CHECKPOINT,
        retry_policy: Optional[RetryPolicy] = None
    ):
        self.db = db
        self.llm = llm_provider or MockLLMProvider()
        self.chapter_repo = ChapterRepository(db)
        self.memory_service = MemoryService(db)
        
        # v2.3 配置
        self.operation_mode = operation_mode
        self.retry_policy = retry_policy or RetryPolicy()

    # ==================== 主入口 ====================

    async def generate_chapter(
        self,
        project_id: int,
        chapter_id: int,
        request: WriterGenerationRequest
    ) -> WriterOutput:
        """
        生成章节 - v2.3 主入口
        
        根据配置选择：
        - scene 模式：分 scene 生成 + stitch
        - 单章模式：直接生成
        """
        # 获取章节信息
        chapter = await self.chapter_repo.get(chapter_id)
        if not chapter:
            raise ValueError(f"Chapter {chapter_id} not found")
        
        # 获取上下文
        context_pack = await self.memory_service.build_context_pack(
            project_id,
            ContextPackRequest(
                chapter_id=chapter_id,
                include_story_bible=True,
                include_character_states=True,
                include_recent_chapters=3,
                include_foreshadows=True
            )
        )
        
        # 选择生成模式
        if request.use_scene_mode:
            return await self._generate_with_scenes(
                project_id, chapter, request, context_pack
            )
        else:
            return await self._generate_single_pass(
                project_id, chapter, request, context_pack
            )

    # ==================== Scene 模式 ====================

    async def _generate_with_scenes(
        self,
        project_id: int,
        chapter: Chapter,
        request: WriterGenerationRequest,
        context_pack: Any
    ) -> WriterOutput:
        """分 scene 生成 + stitch"""
        scene_count = request.scene_count or 2
        
        # Step 1: Scene Breakdown
        scene_plans = await self._breakdown_scenes(
            chapter, request, context_pack, scene_count
        )
        
        # Step 2: 逐个生成 scenes
        scene_outputs = []
        previous_ending = ""
        
        for i, plan in enumerate(scene_plans):
            scene_output = await self._generate_single_scene(
                project_id, chapter, plan, context_pack,
                previous_ending, i == 0
            )
            scene_outputs.append(scene_output)
            previous_ending = scene_output.text_blob[-200:] if scene_output.text_blob else ""
        
        # Step 3: Scene Stitch
        stitched_text = await self._stitch_scenes(
            chapter, scene_outputs, context_pack
        )
        
        # Step 4: Structured Extraction
        extracted = await self._extract_structured_info(stitched_text, chapter.chapter_no)
        
        # 更新章节
        word_count = len(stitched_text) // 2
        chapter.text = stitched_text
        chapter.word_count = word_count
        chapter.status = ChapterStatus.DRAFT
        await self.db.flush()
        
        # 构建 WriterOutput
        return WriterOutput(
            project_id=project_id,
            chapter_id=chapter.id,
            draft_blob=stitched_text,
            scene_outputs=scene_outputs,
            use_scene_mode=True,
            chapter_summary=extracted.get("chapter_summary", ""),
            event_candidates=extracted.get("event_candidates", []),
            state_change_candidates=extracted.get("state_change_candidates", []),
            thread_beat_candidates=extracted.get("thread_beat_candidates", []),
            lore_candidates=extracted.get("lore_candidates", []),
            timeline_hints=extracted.get("timeline_hints", []),
            generation_meta={
                "scene_count": scene_count,
                "mode": "scene"
            }
        )

    async def _breakdown_scenes(
        self,
        chapter: Chapter,
        request: WriterGenerationRequest,
        context_pack: Any,
        scene_count: int
    ) -> list[ScenePlan]:
        """将章节拆分成 scenes"""
        system_prompt = """你是一个专业的小说章节策划师。
        你的任务是将章节大纲拆分成多个 scene，每个 scene 有明确的目标。"""
        
        prompt = SCENE_BREAKDOWN_PROMPT.format(
            chapter_no=chapter.chapter_no,
            title=chapter.title or f"第{chapter.chapter_no}章",
            outline=request.outline or chapter.outline or "待定义",
            context=context_pack.formatted_context,
            scene_count=scene_count
        )
        
        response = await self._call_llm_with_retry(prompt, system_prompt)
        content = self._clean_text(response.content)
        
        # 解析 scene plans
        scene_plans = self._parse_scene_plans(content, scene_count)
        
        # 如果解析失败，创建默认 plans
        if not scene_plans:
            scene_plans = self._create_default_scene_plans(chapter.chapter_no, scene_count)
        
        return scene_plans

    async def _generate_single_scene(
        self,
        project_id: int,
        chapter: Chapter,
        scene_plan: ScenePlan,
        context_pack: Any,
        previous_ending: str,
        is_first: bool,
        total_scenes: int = 2,
        target_word_count: int = 3000
    ) -> SceneOutput:
        """生成单个 scene"""
        system_prompt = """你是一个专业的小说写作助手。
        你的任务是创作指定 scene 的正文内容。"""
        
        target_words = target_word_count // total_scenes
        
        prompt = SCENE_GENERATION_PROMPT.format(
            chapter_no=chapter.chapter_no,
            scene_no=scene_plan.scene_no,
            total_scenes=scene_plan.total_scenes,
            scene_objective=scene_plan.scene_objective,
            scene_time_point=scene_plan.scene_time_point or "同时",
            scene_location=scene_plan.scene_location or "待定",
            involved_entities=", ".join(scene_plan.involved_entities) or "待定",
            must_progress_points="\n".join([f"- {p}" for p in scene_plan.must_progress_points]) if scene_plan.must_progress_points else "待定",
            micro_hook=scene_plan.micro_hook or "保持悬念",
            previous_scene_ending=previous_ending or "（首个 scene）",
            target_words=target_words
        )
        
        response = await self._call_llm_with_retry(prompt, system_prompt)
        text = self._clean_text(response.content)
        
        return SceneOutput(
            scene_no=scene_plan.scene_no,
            scene_objective=scene_plan.scene_objective,
            text_blob=text,
            micro_summary=text[:100] + "..." if len(text) > 100 else text
        )

    async def _stitch_scenes(
        self,
        chapter: Chapter,
        scene_outputs: list[SceneOutput],
        context_pack: Any
    ) -> str:
        """合并 scenes 成章节"""
        scenes_text = "\n\n".join([
            f"【Scene {s.scene_no}】\n{s.text_blob}"
            for s in scene_outputs
        ])
        
        system_prompt = """你是一个专业的小说编辑。
        你的任务是将多个 scenes 合并成连贯的章节。"""
        
        prompt = SCENE_STITCH_PROMPT.format(
            scenes=scenes_text,
            scene_count=len(scene_outputs),
            chapter_no=chapter.chapter_no,
            title=chapter.title or f"第{chapter.chapter_no}章",
            outline=chapter.outline or ""
        )
        
        response = await self._call_llm_with_retry(prompt, system_prompt)
        return self._clean_text(response.content)

    # ==================== 单章模式（阶段 0.5） ====================

    async def _generate_single_pass(
        self,
        project_id: int,
        chapter: Chapter,
        request: WriterGenerationRequest,
        context_pack: Any
    ) -> WriterOutput:
        """单章单次生成（阶段 0.5）"""
        system_prompt = """你是一个专业的小说写作助手。
        你的任务是根据章节大纲和上下文，创作引人入胜的小说章节。"""
        
        prompt = CHAPTER_GENERATION_PROMPT.format(
            chapter_no=chapter.chapter_no,
            title=chapter.title or f"第{chapter.chapter_no}章",
            outline=request.outline or chapter.outline or "",
            context=context_pack.formatted_context,
            style_hints=request.style_hints or ""
        )
        
        response = await self._call_llm_with_retry(prompt, system_prompt)
        text = self._clean_text(response.content)
        
        # Structured Extraction
        extracted = await self._extract_structured_info(text, chapter.chapter_no)
        
        # 更新章节
        word_count = len(text) // 2
        chapter.text = text
        chapter.word_count = word_count
        chapter.status = ChapterStatus.DRAFT
        await self.db.flush()
        
        return WriterOutput(
            project_id=project_id,
            chapter_id=chapter.id,
            draft_blob=text,
            use_scene_mode=False,
            chapter_summary=extracted.get("chapter_summary", ""),
            event_candidates=extracted.get("event_candidates", []),
            state_change_candidates=extracted.get("state_change_candidates", []),
            generation_meta={"mode": "single_pass"}
        )

    # ==================== 工具方法 ====================

    async def _call_llm_with_retry(
        self,
        prompt: str,
        system_prompt: str = "",
        max_retries: int = None
    ) -> Any:
        """带重试的 LLM 调用"""
        max_retries = max_retries or self.retry_policy.max_retries
        
        for attempt in range(max_retries + 1):
            try:
                response = await self.llm.generate(prompt, system_prompt)
                if response and response.content:
                    return response
            except Exception as e:
                if attempt == max_retries:
                    raise
                await asyncio.sleep(self.retry_policy.retry_delay_seconds * (attempt + 1))
        
        raise RuntimeError("LLM 调用失败，已达最大重试次数")

    def _clean_text(self, text: str) -> str:
        """清理 LLM 输出"""
        if not text:
            return text
        
        for pattern, replacement in self.THINKING_PATTERNS:
            text = re.sub(pattern, replacement, text, flags=re.DOTALL)
        
        # 清理多余空行
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()

    def _parse_scene_plans(self, content: str, expected_count: int) -> list[ScenePlan]:
        """解析 scene plans"""
        scene_plans = []
        
        # 尝试 JSON 解析
        try:
            # 查找 JSON 数组
            json_match = re.search(r'\[\s*\{.*\}\s*\]', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                for i, item in enumerate(data):
                    scene_plans.append(ScenePlan(
                        scene_no=i + 1,
                        scene_objective=item.get("scene_objective", ""),
                        scene_time_point=item.get("scene_time_point"),
                        scene_location=item.get("scene_location"),
                        involved_entities=item.get("involved_entities", []),
                        must_progress_points=item.get("must_progress_points", []),
                        micro_hook=item.get("micro_hook")
                    ))
                return scene_plans
        except (json.JSONDecodeError, KeyError):
            pass
        
        # 简单文本解析
        scene_blocks = re.split(r'(?:【Scene\s*\d+】|Scene\s*\d+[：:])', content)
        scene_blocks = [b.strip() for b in scene_blocks if b.strip()]
        
        for i, block in enumerate(scene_blocks[:expected_count]):
            lines = block.split('\n')
            title = lines[0] if lines else f"Scene {i+1}"
            
            scene_plans.append(ScenePlan(
                scene_no=i + 1,
                scene_objective=title,
                must_progress_points=[title]
            ))
        
        return scene_plans

    def _create_default_scene_plans(self, chapter_no: int, count: int) -> list[ScenePlan]:
        """创建默认 scene plans"""
        return [
            ScenePlan(
                scene_no=i + 1,
                scene_objective=f"第{i+1}部分",
                must_progress_points=[f"推进情节{i+1}"]
            )
            for i in range(count)
        ]

    async def _extract_structured_info(
        self,
        text: str,
        chapter_no: int
    ) -> dict[str, Any]:
        """提取结构化信息"""
        system_prompt = """你是一个专业的小说分析助手。
        请从章节中提取结构化信息。"""
        
        prompt = STRUCTURED_EXTRACTION_PROMPT.format(
            chapter_text=text[:5000]  # 限制长度
        )
        
        try:
            response = await self.llm.generate(prompt, system_prompt)
            content = self._clean_text(response.content)
            
            # JSON 解析
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                return json.loads(json_match.group(0))
        except Exception:
            pass
        
        # 降级提取
        return await self._fallback_extraction(text, chapter_no)

    async def _fallback_extraction(
        self,
        text: str,
        chapter_no: int
    ) -> dict[str, Any]:
        """降级提取（当 JSON 解析失败时）"""
        prompt = FALLBACK_EXTRACTION_PROMPT.format(
            chapter_text=text[:3000]
        )
        
        try:
            response = await self.llm.generate(prompt, "")
            return {
                "chapter_summary": self._clean_text(response.content)[:100],
                "event_candidates": [],
                "state_change_candidates": [],
                "parse_success": False
            }
        except Exception:
            return {
                "chapter_summary": "",
                "event_candidates": [],
                "state_change_candidates": [],
                "parse_success": False
            }

    # ==================== 兼容旧 API ====================

    async def generate_chapter_legacy(
        self,
        project_id: int,
        chapter_id: int,
        request: GenerateChapterRequest
    ) -> dict[str, Any]:
        """旧 API 兼容"""
        output = await self.generate_chapter(
            project_id,
            chapter_id,
            WriterGenerationRequest(
                chapter_id=chapter_id,
                outline=request.outline,
                use_scene_mode=False,
                target_word_count=request.target_word_count or 3000,
                style_hints=request.style_hints
            )
        )
        
        chapter = await self.chapter_repo.get(chapter_id)
        
        return {
            "chapter": chapter,
            "text": output.draft_blob,
            "word_count": len(output.draft_blob) // 2,
            "summary": output.chapter_summary
        }

    async def continue_chapter(
        self,
        project_id: int,
        chapter_id: int,
        request: ContinueChapterRequest
    ) -> dict[str, Any]:
        """续写章节"""
        chapter = await self.chapter_repo.get(chapter_id)
        if not chapter:
            raise ValueError(f"Chapter {chapter_id} not found")
        
        context_pack = await self.memory_service.build_context_pack(
            project_id,
            ContextPackRequest(
                chapter_id=chapter_id,
                include_story_bible=True,
                include_character_states=True,
                include_recent_chapters=1,
                include_foreshadows=True
            )
        )
        
        system_prompt = """你是一个专业的小说写作助手。
        你的任务是在已有内容的基础上继续创作。"""
        
        prompt = CHAPTER_CONTINUATION_PROMPT.format(
            chapter_no=chapter.chapter_no,
            existing_text=chapter.text or "",
            last_paragraph=request.last_paragraph or (chapter.text[-500:] if chapter.text else ""),
            context=context_pack.formatted_context,
            target_word_count=request.target_word_count
        )
        
        response = await self.llm.generate(prompt, system_prompt)
        continuation = self._clean_text(response.content)
        
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
        """重写章节"""
        chapter = await self.chapter_repo.get(chapter_id)
        if not chapter:
            raise ValueError(f"Chapter {chapter_id} not found")
        
        context_pack = await self.memory_service.build_context_pack(
            project_id,
            ContextPackRequest(
                chapter_id=chapter_id,
                include_story_bible=True,
                include_character_states=True,
                include_recent_chapters=2,
                include_foreshadows=True
            )
        )
        
        system_prompt = """你是一个专业的小说编辑。
        你的任务是按照修改指令重写章节。"""
        
        prompt = CHAPTER_REWRITE_PROMPT.format(
            chapter_no=chapter.chapter_no,
            existing_text=chapter.text or "",
            rewrite_instructions=request.rewrite_instructions,
            context=context_pack.formatted_context
        )
        
        response = await self.llm.generate(prompt, system_prompt)
        rewritten = self._clean_text(response.content)
        
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
        """修补章节段落"""
        chapter = await self.chapter_repo.get(chapter_id)
        if not chapter:
            raise ValueError(f"Chapter {chapter_id} not found")
        
        system_prompt = """你是一个专业的小说编辑。
        你的任务是修补特定段落。"""
        
        prompt = CHAPTER_PATCH_PROMPT.format(
            chapter_no=chapter.chapter_no,
            existing_text=chapter.text or "",
            segment_id=request.segment_id,
            segment_content=request.segment_content,
            patch_instructions=request.patch_instructions
        )
        
        response = await self.llm.generate(prompt, system_prompt)
        patched = self._clean_text(response.content)
        
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
