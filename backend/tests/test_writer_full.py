"""完整的 Writer Service 测试"""
import pytest
from pydantic import BaseModel

from app.schemas.chapter import (
    GenerateChapterRequest,
    ContinueChapterRequest,
    RewriteChapterRequest,
    PatchChapterRequest,
)


class TestWriterSchemas:
    """Writer Schemas 测试"""
    
    def test_generate_request_full(self):
        """测试完整生成请求"""
        request = GenerateChapterRequest(
            outline="自定义章节大纲",
            context_pack_id=1,
            style_hints="保持紧张节奏"
        )
        
        assert request.outline == "自定义章节大纲"
        assert request.context_pack_id == 1
        assert request.style_hints == "保持紧张节奏"
    
    def test_generate_request_minimal(self):
        """测试最小生成请求"""
        request = GenerateChapterRequest()
        
        assert request.outline is None
        assert request.style_hints is None
    
    def test_continue_request_full(self):
        """测试完整续写请求"""
        request = ContinueChapterRequest(
            last_paragraph="上一段的最后内容...",
            target_word_count=5000
        )
        
        assert request.last_paragraph == "上一段的最后内容..."
        assert request.target_word_count == 5000
    
    def test_continue_request_defaults(self):
        """测试续写请求默认值"""
        request = ContinueChapterRequest()
        
        assert request.last_paragraph is None
        assert request.target_word_count == 3000
    
    def test_rewrite_request(self):
        """测试重写请求"""
        request = RewriteChapterRequest(
            rewrite_instructions="改善对话自然度，减少旁白"
        )
        
        assert "对话" in request.rewrite_instructions
    
    def test_patch_request(self):
        """测试修补请求"""
        request = PatchChapterRequest(
            segment_id="seg_001",
            segment_content="需要修补的原段落内容",
            patch_instructions="让这段更紧张"
        )
        
        assert request.segment_id == "seg_001"
        assert "紧张" in request.patch_instructions


class TestWriterPrompts:
    """Writer Prompts 测试"""
    
    def test_chapter_generation_prompt_format(self):
        """测试章节生成 prompt 格式"""
        from app.services.writer.prompts import CHAPTER_GENERATION_PROMPT
        
        prompt = CHAPTER_GENERATION_PROMPT.format(
            chapter_no=1,
            title="第一章",
            outline="章节大纲",
            context="上下文",
            style_hints="风格提示"
        )
        
        assert "第 1 章" in prompt
        assert "章节大纲" in prompt
        assert "上下文" in prompt
    
    def test_continuation_prompt_format(self):
        """测试续写 prompt 格式"""
        from app.services.writer.prompts import CHAPTER_CONTINUATION_PROMPT
        
        prompt = CHAPTER_CONTINUATION_PROMPT.format(
            chapter_no=2,
            existing_text="已有内容...",
            last_paragraph="最后一段",
            context="上下文",
            target_word_count=3000
        )
        
        assert "已有内容" in prompt
        assert "3000" in prompt
    
    def test_rewrite_prompt_format(self):
        """测试重写 prompt 格式"""
        from app.services.writer.prompts import CHAPTER_REWRITE_PROMPT
        
        prompt = CHAPTER_REWRITE_PROMPT.format(
            chapter_no=1,
            existing_text="原内容",
            rewrite_instructions="修改指令",
            context="上下文"
        )
        
        assert "原内容" in prompt
        assert "修改指令" in prompt
    
    def test_patch_prompt_format(self):
        """测试修补 prompt 格式"""
        from app.services.writer.prompts import CHAPTER_PATCH_PROMPT
        
        prompt = CHAPTER_PATCH_PROMPT.format(
            chapter_no=1,
            existing_text="全文内容",
            segment_id="seg_1",
            segment_content="要修补的段落",
            patch_instructions="修改说明"
        )
        
        assert "seg_1" in prompt
        assert "要修补的段落" in prompt
    
    def test_extraction_prompt_format(self):
        """测试提取 prompt 格式"""
        from app.services.writer.prompts import CHAPTER_EXTRACTION_PROMPT
        
        prompt = CHAPTER_EXTRACTION_PROMPT.format(
            chapter_no=1,
            text="章节内容..."
        )
        
        assert "第 1 章" in prompt
        assert "章节内容" in prompt


class TestWriterPromptsStructure:
    """Writer Prompts 结构测试"""
    
    def test_all_prompts_exist(self):
        """测试所有 writer prompts 存在"""
        from app.services.writer import prompts
        
        assert hasattr(prompts, 'CHAPTER_GENERATION_PROMPT')
        assert hasattr(prompts, 'CHAPTER_CONTINUATION_PROMPT')
        assert hasattr(prompts, 'CHAPTER_REWRITE_PROMPT')
        assert hasattr(prompts, 'CHAPTER_PATCH_PROMPT')
        assert hasattr(prompts, 'CHAPTER_EXTRACTION_PROMPT')
    
    def test_prompts_contain_placeholders(self):
        """测试 prompts 包含必要占位符"""
        from app.services.writer.prompts import (
            CHAPTER_GENERATION_PROMPT,
            CHAPTER_CONTINUATION_PROMPT,
            CHAPTER_REWRITE_PROMPT,
        )
        
        assert "{chapter_no}" in CHAPTER_GENERATION_PROMPT
        assert "{existing_text}" in CHAPTER_CONTINUATION_PROMPT
        assert "{rewrite_instructions}" in CHAPTER_REWRITE_PROMPT
    
    def test_prompts_not_empty(self):
        """测试 prompts 内容不为空"""
        from app.services.writer.prompts import (
            CHAPTER_GENERATION_PROMPT,
            CHAPTER_CONTINUATION_PROMPT,
            CHAPTER_REWRITE_PROMPT,
            CHAPTER_PATCH_PROMPT,
            CHAPTER_EXTRACTION_PROMPT,
        )
        
        for prompt in [
            CHAPTER_GENERATION_PROMPT,
            CHAPTER_CONTINUATION_PROMPT,
            CHAPTER_REWRITE_PROMPT,
            CHAPTER_PATCH_PROMPT,
            CHAPTER_EXTRACTION_PROMPT,
        ]:
            assert len(prompt) > 50  # 至少 50 字符


class TestChapterGenerationFlow:
    """章节生成流程测试"""
    
    def test_generation_with_custom_outline(self):
        """测试使用自定义大纲生成"""
        request = GenerateChapterRequest(
            outline="1. 开场 2. 冲突 3. 高潮 4. 结尾"
        )
        
        assert len(request.outline) > 0
    
    def test_generation_without_outline(self):
        """测试不提供大纲"""
        request = GenerateChapterRequest()
        
        assert request.outline is None
    
    def test_continuation_with_target_length(self):
        """测试指定目标字数续写"""
        request = ContinueChapterRequest(target_word_count=8000)
        
        assert request.target_word_count == 8000
    
    def test_rewrite_with_focused_instructions(self):
        """测试针对性重写指令"""
        instructions = [
            "改善对话自然度",
            "增加环境描写",
            "加快节奏"
        ]
        
        request = RewriteChapterRequest(
            rewrite_instructions="; ".join(instructions)
        )
        
        assert "对话" in request.rewrite_instructions
