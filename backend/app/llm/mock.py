"""Mock LLM Provider - 用于测试和开发"""
import json
from typing import Any, Optional

from app.llm.base import LLMProvider, LLMResponse


class MockLLMProvider(LLMProvider):
    """Mock LLM Provider 实现"""

    def __init__(self, model: str = "mock-gpt-4", temperature: float = 0.7, max_tokens: int = 4096):
        super().__init__(model, temperature, max_tokens)
        self.call_count = 0

    async def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> LLMResponse:
        """Mock 生成"""
        self.call_count += 1
        
        # 构建模拟响应
        content = self._generate_mock_response(prompt, system_prompt)
        
        return LLMResponse(
            content=content,
            model=self.model,
            usage={"prompt_tokens": len(prompt) // 4, "completion_tokens": len(content) // 4, "total": (len(prompt) + len(content)) // 4},
            raw_response={"mock": True, "call_number": self.call_count}
        )

    async def generate_structured(
        self,
        prompt: str,
        system_prompt: Optional[str],
        response_schema: dict[str, Any],
        **kwargs
    ) -> dict[str, Any]:
        """Mock 结构化生成"""
        self.call_count += 1
        
        # 尝试解析预期的 JSON 结构
        mock_response = self._generate_mock_structured_response(prompt, response_schema)
        
        return mock_response

    async def chat(self, messages: list[dict[str, str]], **kwargs) -> LLMResponse:
        """Mock 对话"""
        self.call_count += 1
        
        # 简单拼接消息作为响应
        content = "我收到了你的消息。这是 Mock LLM 的回复。"
        
        return LLMResponse(
            content=content,
            model=self.model,
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total": 150},
            raw_response={"mock": True, "call_number": self.call_count}
        )

    def _generate_mock_response(self, prompt: str, system_prompt: Optional[str]) -> str:
        """生成模拟响应"""
        # 根据 prompt 关键词生成不同响应
        prompt_lower = prompt.lower()
        
        if "outline" in prompt_lower or "大纲" in prompt_lower:
            return self._mock_outline_response()
        elif "character" in prompt_lower or "角色" in prompt_lower:
            return self._mock_character_response()
        elif "story bible" in prompt_lower or "故事圣经" in prompt_lower:
            return self._mock_story_bible_response()
        elif "summary" in prompt_lower or "摘要" in prompt_lower:
            return self._mock_summary_response()
        elif "review" in prompt_lower or "审查" in prompt_lower:
            return self._mock_review_response()
        else:
            return self._mock_chapter_response()

    def _mock_outline_response(self) -> str:
        """模拟大纲响应"""
        return """## 第1章大纲
**标题**: 命运的相遇
**钩子**: 主角在古老的图书馆中发现了一本神秘的书籍

### 情节要点:
1. 主角林逸是一个普通的大学生
2. 在图书馆打工时偶然发现了一本发光的古籍
3. 古籍中的文字开始流入他的意识
4. 一个神秘的声音在呼唤他

### 伏笔:
- 古籍的封面有一个奇怪的符号
- 图书馆似乎隐藏着什么秘密

---

## 第2章大纲
**标题**: 觉醒之路
**钩子**: 觉醒的力量伴随着危险而来"""
    
    def _mock_character_response(self) -> str:
        """模拟角色响应"""
        return """## 主角角色卡

**姓名**: 林逸
**角色类型**: 主角

### 基本信息:
- **性格**: 沉稳内敛，富有好奇心
- **动机**: 寻找自己身世的真相
- **秘密**: 体内封印着古老的力量

### 关系网:
- 导师: 陈老 - 神秘的图书馆管理员
- 伙伴: 小青 - 附身于古籍的精灵
- 对手: 黑影组织

### 当前状态:
- 位置: 东海大学图书馆
- 情绪: 困惑但充满期待
- 能力: 刚刚觉醒，力量微弱"""
    
    def _mock_story_bible_response(self) -> str:
        """模拟故事圣经响应"""
        return """# 故事圣经 - 《觉醒者》

## 基本信息
- **类型**: 都市异能/玄幻
- **基调**: 神秘、热血、成长
- **主题**: 觉醒与成长

## 一句话概述
一个普通大学生意外获得古老力量，在追寻身世真相的过程中揭开世界的神秘面纱。

## 世界观概述
现代都市中存在一个隐藏的修炼世界。千年前的上古大战后，世界被分为表里两层。表世界是普通人生活的现代都市，里世界则是修炼者和神秘力量的领域。

## 核心冲突
- 表世界与里世界的平衡
- 主角身世之谜
- 黑影组织的阴谋"""
    
    def _mock_summary_response(self) -> str:
        """模拟摘要响应"""
        return """## 章节摘要

**主要事件**:
1. 林逸在图书馆发现神秘古籍
2. 古籍激活，林逸开始觉醒
3. 遇到导师陈老
4. 了解到里世界的存在

**角色状态变化**:
- 林逸: 从普通人 → 觉醒者
- 能力值: 0 → 1

**伏笔更新**:
- 新增: 古籍的来源之谜
- 发展: 黑影组织的存在"""
    
    def _mock_review_response(self) -> str:
        """模拟审查响应"""
        return """## 章节审查报告

**评分**: 7.5/10

**优点**:
- 开篇钩子设置得当
- 场景描写细腻
- 角色性格鲜明

**问题**:
1. [中等] 第3段节奏稍慢，建议精简
2. [低] 对话略显生硬，需要更口语化
3. [低] 部分描写重复

**总体评价**:
章节整体质量良好，故事推进自然。建议在后续修改中关注对话的自然度和节奏把控。"""
    
    def _mock_chapter_response(self) -> str:
        """模拟章节正文响应"""
        return """林逸从未想过，一个普通的夜晚会改变他的一生。

那天，他在东海大学图书馆做兼职，整理归还的书籍。深夜的图书馆异常安静，只有他翻动书页的声音。

突然，一本古籍从书架深处散发出微弱的光芒。

那光芒纯净而古老，仿佛穿越了无尽的岁月。林逸下意识地伸出手，指尖触碰到书皮的瞬间，一股温热的力量涌入他的身体。

"终于...等到了..."

一个苍老而神秘的声音在他脑海中响起。

林逸猛地后退一步，环顾四周，却发现图书馆里空无一人。那个声音再次响起，这次更加清晰：

"不要害怕，年轻人。我是这本书的守护者。而你，即将成为觉醒者..."

窗外，夜色深沉。东海大学图书馆的某个角落，一场命运的相遇正在展开。"""
    
    def _generate_mock_structured_response(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        """生成模拟结构化响应"""
        schema_str = json.dumps(schema)
        
        # 简单的 mock 结构化数据
        if "outlines" in schema_str or "chapters" in schema_str:
            return {
                "chapters": [
                    {
                        "chapter_no": 1,
                        "title": "命运的相遇",
                        "outline": "主角在图书馆发现神秘古籍...",
                        "hook": "发光的古籍..."
                    },
                    {
                        "chapter_no": 2,
                        "title": "觉醒之路",
                        "outline": "林逸开始觉醒...",
                        "hook": "觉醒的力量..."
                    }
                ]
            }
        elif "character" in schema_str or "角色" in schema_str:
            return {
                "name": "林逸",
                "role_type": "protagonist",
                "profile": "普通大学生...",
                "personality": "沉稳、好奇...",
                "motivation": "寻找身世真相",
                "secrets": "体内封印力量",
                "relationships": {}
            }
        elif "summary" in schema_str or "摘要" in schema_str:
            return {
                "summary": "本章主要讲述...",
                "key_events": ["事件1", "事件2"],
                "state_changes": {},
                "foreshadow_changes": []
            }
        else:
            return {"result": "Mock structured response"}
