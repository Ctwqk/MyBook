"""LLM Provider 测试"""
import pytest
from app.llm.base import LLMProvider, LLMResponse
from app.llm.mock import MockLLMProvider


class TestMockLLMProvider:
    """Mock LLM Provider 测试"""
    
    @pytest.mark.asyncio
    async def test_generate(self):
        """测试生成"""
        provider = MockLLMProvider()
        
        response = await provider.generate(
            prompt="写一个关于觉醒的故事开头",
            system_prompt="你是一个小说作家"
        )
        
        assert isinstance(response, LLMResponse)
        assert response.content is not None
        assert len(response.content) > 0
        assert response.model == "mock-gpt-4"
    
    @pytest.mark.asyncio
    async def test_generate_structured(self):
        """测试结构化生成"""
        provider = MockLLMProvider()
        
        response = await provider.generate_structured(
            prompt="生成3个角色",
            system_prompt="生成角色信息",
            response_schema={
                "type": "object",
                "properties": {
                    "characters": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "role": {"type": "string"}
                            }
                        }
                    }
                }
            }
        )
        
        assert isinstance(response, dict)
        assert "characters" in response
    
    @pytest.mark.asyncio
    async def test_chat(self):
        """测试对话"""
        provider = MockLLMProvider()
        
        messages = [
            {"role": "system", "content": "你是一个小说作家"},
            {"role": "user", "content": "写一个故事开头"}
        ]
        
        response = await provider.chat(messages)
        
        assert isinstance(response, LLMResponse)
        assert response.content is not None
    
    @pytest.mark.asyncio
    async def test_call_count(self):
        """测试调用计数"""
        provider = MockLLMProvider()
        
        await provider.generate("test1")
        await provider.generate("test2")
        await provider.generate("test3")
        
        assert provider.call_count == 3
