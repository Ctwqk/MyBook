"""Planner Service - 规划服务"""
import re
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.base import LLMProvider
from app.llm.factory import create_llm_provider
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

    # 清理用正则表达式
    THINKING_PATTERNS = [
        (r'<think>[\s\S]*?</think>', ''),
        (r'<thinking>[\s\S]*?</thinking>', ''),
    ]

    def __init__(self, db: AsyncSession, llm_provider: Optional[LLMProvider] = None):
        self.db = db
        self.llm = llm_provider or create_llm_provider()
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
        
        # 清理 LLM 返回的思考标签
        content = response.content
        content = re.sub(r'<think>[\s\S]*?</think>', '', content)
        content = re.sub(r'<thinking>[\s\S]*?</thinking>', '', content)
        
        # TODO: 解析结构化输出
        # 创建 StoryBible 记录
        story_bible = StoryBible(
            project_id=project_id,
            title=project.title,
            genre=genre or project.genre,
            logline=premise,
            synopsis=content,
        )
        self.db.add(story_bible)
        
        return StoryBibleDraft(
            title=project.title,
            genre=genre or project.genre or "通用",
            theme="待定义",
            logline=premise,
            synopsis=content[:1000],
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
            volume_id=volume_id or "",
            count=count,
            start_chapter_no=next_chapter_no,
            end_chapter_no=next_chapter_no + count - 1,
            existing_outlines="\n".join(existing_outlines) if existing_outlines else "暂无"
        )
        
        response = await self.llm.generate(prompt, system_prompt)
        
        # 解析 LLM 返回的大纲内容
        outlines = self._parse_chapter_outlines(response.content, next_chapter_no, count)
        
        for outline in outlines:
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

    def _parse_chapter_outlines(
        self,
        content: str,
        start_chapter_no: int,
        count: int
    ) -> list[ChapterOutline]:
        """
        解析 LLM 返回的章节大纲内容
        
        Args:
            content: LLM 返回的原始文本
            start_chapter_no: 起始章节号
            count: 需要解析的大纲数量
            
        Returns:
            list[ChapterOutline]: 解析后的大纲列表
        """
        outlines = []
        
        # 过滤掉 MiniMax 的各种思考标签
        content = re.sub(r'<reasoning>.*?</reasoning>', '', content, flags=re.DOTALL)
        content = re.sub(r'<reflection>.*?</reflection>', '', content, flags=re.DOTALL)
        content = re.sub(r'<thinking>.*?</thinking>', '', content, flags=re.DOTALL)
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
        # 也过滤 XML 风格的思考标签
        content = re.sub(r'<.*?>.*?<\/.*?>', '', content, flags=re.DOTALL)
        
        # 尝试解析 JSON 格式
        try:
            import json
            # 提取 JSON 数组
            json_match = re.search(r'\[\s*\{.*\}\s*\]', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                json_str = re.sub(r',\s*\]', ']', json_str)
                data = json.loads(json_str)
                for i, item in enumerate(data[:count]):
                    outline = ChapterOutline(
                        chapter_no=start_chapter_no + i,
                        title=item.get('title', f"第{start_chapter_no + i}章"),
                        outline=item.get('outline', ''),
                        hook=item.get('hook', ''),
                        key_events=item.get('key_events', [])
                    )
                    outlines.append(outline)
                return outlines[:count]
        except (json.JSONDecodeError, KeyError):
            pass
        
        # 尝试按简化格式解析（章节X：\n起：xxx\n承：xxx...）
        simple_pattern = r'章节(\d+)[:：]\s*起[:：]\s*([^\n]+)\s*承[:：]\s*([^\n]+)\s*转[:：]\s*([^\n]+)\s*合[:：]\s*([^\n]+)\s*钩子[:：]\s*([^\n]+)'
        simple_matches = re.findall(simple_pattern, content)
        if simple_matches and len(simple_matches) >= count:
            for i, match in enumerate(simple_matches[:count]):
                chapter_num = int(match[0])
                outline_text = f"起：{match[1]}\n承：{match[2]}\n转：{match[3]}\n合：{match[4]}"
                outline = ChapterOutline(
                    chapter_no=start_chapter_no + i,
                    title=f"第{start_chapter_no + i}章",
                    outline=outline_text,
                    hook=match[5],
                    key_events=[]
                )
                outlines.append(outline)
            if outlines:
                return outlines[:count]
        
        # 尝试按 Markdown 章节标题分割
        section_patterns = [
            r'(?:^|\n)(#{1,3}\s*)?(?:第(\d+)章|章节标题)[^\n]*\n+(.*?)(?=\n#{1,3}\s*(?:第\d+章|章节标题)|$)',
            r'(?:^|\n)#{1,3}\s*📖\s*[^\n]+\n+(.*?)(?=\n#{1,3}\s*📖|$)',
        ]
        
        sections = []
        for pattern in section_patterns:
            matches = re.findall(pattern, content, re.DOTALL)
            if matches:
                for match in matches:
                    if len(match) == 2 and match[0]:
                        sections.append((match[0], match[1]))
                    elif len(match) == 1:
                        sections.append((None, match[0]))
        
        if sections and len(sections) >= count:
            for i, (chapter_num, section_content) in enumerate(sections[:count]):
                actual_chapter_no = start_chapter_no + i
                title_match = re.search(r'《([^》]+)》|「([^」]+)」|标题[：:]\s*([^\n]+)', section_content)
                title = f"第{actual_chapter_no}章"
                if title_match:
                    title = title_match.group(1) or title_match.group(2) or title_match.group(3)
                    title = title.strip()
                
                outline = ChapterOutline(
                    chapter_no=actual_chapter_no,
                    title=title,
                    outline=section_content.strip()[:500],
                    hook=self._extract_hook(section_content),
                    key_events=[]
                )
                outlines.append(outline)
            if outlines:
                return outlines[:count]
        
        # 尝试按章节分割内容（备用）
        chapter_patterns = [
            r'第(\d+)章[：:]\s*([^\n]+)',
            r'##\s*第(\d+)章[：:]*\s*([^\n]+)',
            r'\*\*第(\d+)章\*\*[：:]*\s*([^\n]+)',
        ]
        
        chapters_found = []
        for pattern in chapter_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                chapter_no = int(match[0])
                title = match[1].strip() if len(match) > 1 else f"第{chapter_no}章"
                chapters_found.append((chapter_no, title))
        
        # 如果找不到格式化的章节，尝试按段落分割
        if not chapters_found:
            # 将内容分成 count 个部分
            paragraphs = content.split('\n\n')
            paragraphs = [p.strip() for p in paragraphs if p.strip()]
            
            for i in range(min(count, len(paragraphs))):
                chapter_no = start_chapter_no + i
                para = paragraphs[i] if i < len(paragraphs) else ""
                
                # 尝试从段落中提取标题
                first_line = para.split('\n')[0] if '\n' in para else para[:50]
                title = first_line.strip('#*【】[]').strip()
                if len(title) > 30:
                    title = title[:30] + "..."
                
                # 提取大纲内容（去掉标题行）
                outline_content = para
                if '\n' in para:
                    lines = para.split('\n')
                    outline_content = '\n'.join(lines[1:]) if len(lines) > 1 else para
                
                outline = ChapterOutline(
                    chapter_no=chapter_no,
                    title=title or f"第{chapter_no}章",
                    outline=outline_content[:500] if len(outline_content) > 500 else outline_content,
                    hook=self._extract_hook(outline_content),
                    key_events=[]
                )
                outlines.append(outline)
        else:
            # 使用找到的章节信息
            for i, (chapter_no, title) in enumerate(chapters_found[:count]):
                actual_chapter_no = start_chapter_no + i
                
                # 提取该章节的大纲内容
                section_start = content.find(f'{chapter_no}章')
                if section_start == -1:
                    section_start = content.find(f'**第{chapter_no}章**')
                if section_start == -1:
                    section_start = content.find(f'## 第{chapter_no}章')
                
                section_end = len(content)
                for j in range(i + 1, len(chapters_found)):
                    next_chapter_start = content.find(f'{chapters_found[j][0]}章')
                    if next_chapter_start != -1 and next_chapter_start > section_start:
                        section_end = next_chapter_start
                        break
                
                section_content = content[section_start:section_end] if section_start < section_end else content[section_start:section_start+500]
                
                outline = ChapterOutline(
                    chapter_no=actual_chapter_no,
                    title=title,
                    outline=section_content[:500],
                    hook=self._extract_hook(section_content),
                    key_events=[]
                )
                outlines.append(outline)
        
        # 如果解析失败或数量不足，填充默认数据
        while len(outlines) < count:
            i = len(outlines)
            outline = ChapterOutline(
                chapter_no=start_chapter_no + i,
                title=f"第{start_chapter_no + i}章",
                outline=f"章节大纲内容（LLM生成）",
                hook="章节钩子",
                key_events=[]
            )
            outlines.append(outline)
        
        return outlines[:count]

    def _extract_hook(self, content: str) -> str:
        """从内容中提取钩子/悬念"""
        hook_patterns = [
            r'钩子[：:]\s*([^\n]+)',
            r'悬念[：:]\s*([^\n]+)',
            r'结尾[：:]\s*([^\n]+)',
        ]
        
        for pattern in hook_patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(1).strip()
        
        # 如果找不到，返回最后一句
        sentences = content.split('。')
        if len(sentences) > 1:
            return sentences[-2].strip() + "。" if sentences[-2] else ""
        
        return ""

    # ==================== v2.6: Replan Project ====================
    
    async def replan_project(
        self,
        project_id: int,
        arc_signals: Optional[dict] = None,
        pacing_signals: Optional[dict] = None
    ) -> dict:
        """
        重规划项目 - v2.6 新增
        
        当以下情况触发时调用：
        - 连续多章审查失败
        - Arc完成或重大转折
        - 人工触发重规划
        
        Args:
            project_id: 项目ID
            arc_signals: Arc Director信号 (包含confusion_signals, pacing_signals, character_heat_signals等)
            pacing_signals: Pacing Strategist信号
        
        Returns:
            重规划结果
        """
        project = await self.project_repo.get(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        # 构建重规划提示
        replan_context = []
        
        if arc_signals:
            # 分析Arc Director信号
            confusion = arc_signals.get("confusion_signals", [])
            character_heat = arc_signals.get("character_heat_signals", [])
            risk_signals = arc_signals.get("risk_signals", [])
            trend_views = arc_signals.get("trend_views", [])
            
            if confusion:
                replan_context.append(f"读者困惑点: {len(confusion)}个")
            if character_heat:
                replan_context.append(f"角色热度变化: {len(character_heat)}个")
            if risk_signals:
                replan_context.append(f"风险信号: {len(risk_signals)}个")
            if trend_views:
                # 分析趋势
                rising = [v for v in trend_views if v.get("trend_type") == "rising"]
                falling = [v for v in trend_views if v.get("trend_type") == "falling"]
                replan_context.append(f"上升趋势: {len(rising)}个, 下降趋势: {len(falling)}个")
        
        if pacing_signals:
            # 分析Pacing信号
            immediate = pacing_signals.get("immediate_signals", [])
            recent = pacing_signals.get("recent_signals", [])
            
            if immediate:
                replan_context.append(f"即时节奏问题: {len(immediate)}个")
            if recent:
                replan_context.append(f"近期节奏反馈: {len(recent)}个")
        
        # 获取当前Story Bible
        story_bible = await self.get_story_bible(project_id)
        
        # 构建重规划prompt
        system_prompt = """你是一个专业的小说策划编辑。你的任务是分析读者反馈信号，
        对故事计划进行调整优化。"""
        
        prompt = f"""基于以下读者反馈信号，对故事计划进行重规划：

当前反馈信号：
{chr(10).join(replan_context) if replan_context else "无显著信号"}

当前Story Bible摘要：
- 主题: {getattr(story_bible, 'theme', 'N/A')}
- 类型: {getattr(story_bible, 'genre', 'N/A')}

请分析并给出重规划建议：
1. 是否需要调整Arc结构？
2. 是否需要加强/削弱某些角色线？
3. 节奏优化建议
4. 其他调整

请以JSON格式输出建议。
"""
        
        try:
            response = await self.llm.generate(prompt, system_prompt)
            content = self._clean_text(response.content)
            
            # 尝试解析JSON
            import json
            import re
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                suggestions = json.loads(json_match.group(0))
            else:
                suggestions = {"raw_suggestions": content[:1000]}
        except Exception as e:
            suggestions = {"error": str(e), "raw_suggestions": ""}
        
        return {
            "project_id": project_id,
            "replan_signals": replan_context,
            "suggestions": suggestions,
            "replan_type": "signal_driven" if (arc_signals or pacing_signals) else "manual"
        }
