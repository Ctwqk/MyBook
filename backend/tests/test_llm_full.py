"""完整的 LLM Provider 测试"""
import pytest
from unittest.mock import MagicMock, AsyncMock
import json

from app.llm.base import LLMProvider, LLMResponse
from app.llm.mock import MockLLMProvider


class TestLLMResponse:
    """LLM Response 测试"""
    
    def test_create_response(self):
        """测试创建响应"""
        response = LLMResponse(
            content="测试响应内容",
            model="gpt-4",
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total": 150}
        )
        
        assert response.content == "测试响应内容"
        assert response.model == "gpt-4"
        assert response.usage["total"] == 150
    
    def test_response_with_raw(self):
        """测试带原始响应的响应"""
        response = LLMResponse(
            content="内容",
            model="mock",
            usage={"total": 100},
            raw_response={"mock": True, "id": "test_123"}
        )
        
        assert response.raw_response is not None
        assert response.raw_response["id"] == "test_123"


class TestLLMProviderInterface:
    """LLM Provider 接口测试"""
    
    def test_provider_base_class(self):
        """测试 Provider 基类"""
        # LLMProvider 是抽象类，不能直接实例化
        assert hasattr(LLMProvider, 'generate')
        assert hasattr(LLMProvider, 'generate_structured')
        assert hasattr(LLMProvider, 'chat')
        assert hasattr(LLMProvider, 'get_config')
    
    def test_provider_get_config(self):
        """测试获取配置"""
        class TestProvider(LLMProvider):
            async def generate(self, prompt, system_prompt=None, **kwargs):
                return LLMResponse(content="", model="", usage={})
            
            async def generate_structured(self, prompt, system_prompt, response_schema, **kwargs):
                return {}
            
            async def chat(self, messages, **kwargs):
                return LLMResponse(content="", model="", usage={})
        
        provider = TestProvider(model="test-model", temperature=0.8, max_tokens=2000)
        config = provider.get_config()
        
        assert config["model"] == "test-model"
        assert config["temperature"] == 0.8
        assert config["max_tokens"] == 2000


class TestMockLLMProvider:
    """Mock LLM Provider 测试"""
    
    @pytest.mark.asyncio
    async def test_generate_basic(self):
        """测试基本生成"""
        provider = MockLLMProvider()
        
        response = await provider.generate(
            prompt="测试 prompt",
            system_prompt="你是一个作家"
        )
        
        assert isinstance(response, LLMResponse)
        assert response.content is not None
        assert len(response.content) > 0
        assert response.model == "mock-gpt-4"
    
    @pytest.mark.asyncio
    async def test_generate_with_custom_model(self):
        """测试自定义模型"""
        provider = MockLLMProvider(model="custom-model")
        
        response = await provider.generate("test")
        
        assert response.model == "custom-model"
    
    @pytest.mark.asyncio
    async def test_call_count(self):
        """测试调用计数"""
        provider = MockLLMProvider()
        
        assert provider.call_count == 0
        
        await provider.generate("test1")
        assert provider.call_count == 1
        
        await provider.generate("test2")
        assert provider.call_count == 2
    
    @pytest.mark.asyncio
    async def test_generate_structured(self):
        """测试结构化生成"""
        provider = MockLLMProvider()
        
        response = await provider.generate_structured(
            prompt="生成角色信息",
            system_prompt="生成 JSON",
            response_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "integer"}
                }
            }
        )
        
        assert isinstance(response, dict)
    
    @pytest.mark.asyncio
    async def test_chat(self):
        """测试对话"""
        provider = MockLLMProvider()
        
        messages = [
            {"role": "system", "content": "你是作家"},
            {"role": "user", "content": "写一个故事"}
        ]
        
        response = await provider.chat(messages)
        
        assert isinstance(response, LLMResponse)
        assert len(response.content) > 0
    
    @pytest.mark.asyncio
    async def test_mock_outline_response(self):
        """测试模拟大纲响应"""
        provider = MockLLMProvider()
        
        response = await provider.generate(
            prompt="生成第1章大纲",
            system_prompt="你是章节策划"
        )
        
        # 确认响应包含章节相关内容
        assert "第" in response.content or "章节" in response.content or "outline" in response.content.lower()
    
    @pytest.mark.asyncio
    async def test_mock_character_response(self):
        """测试模拟角色响应"""
        provider = MockLLMProvider()
        
        response = await provider.generate(
            prompt="生成角色卡",
            system_prompt="你是角色设计师"
        )
        
        assert len(response.content) > 0
    
    @pytest.mark.asyncio
    async def test_mock_review_response(self):
        """测试模拟审查响应"""
        provider = MockLLMProvider()
        
        response = await provider.generate(
            prompt="审查章节",
            system_prompt="你是编辑"
        )
        
        assert len(response.content) > 0


class TestMockLLMStructuredResponses:
    """Mock LLM 结构化响应测试"""
    
    @pytest.mark.asyncio
    async def test_structured_outline_response(self):
        """测试结构化大纲响应"""
        provider = MockLLMProvider()
        
        schema = {
            "type": "object",
            "properties": {
                "chapters": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "chapter_no": {"type": "integer"},
                            "title": {"type": "string"},
                            "outline": {"type": "string"}
                        }
                    }
                }
            }
        }
        
        response = await provider.generate_structured(
            prompt="生成章节大纲",
            system_prompt="生成 JSON",
            response_schema=schema
        )
        
        assert "chapters" in response
    
    @pytest.mark.asyncio
    async def test_structured_character_response(self):
        """测试结构化角色响应"""
        provider = MockLLMProvider()
        
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "role_type": {"type": "string"},
                "profile": {"type": "string"}
            }
        }
        
        response = await provider.generate_structured(
            prompt="生成角色",
            system_prompt="生成 JSON",
            response_schema=schema
        )
        
        assert "name" in response or "result" in response


class TestLLMProviderFactory:
    """LLM Provider 工厂测试"""
    
    def test_factory_returns_mock_by_default(self):
        """测试工厂默认返回 mock"""
        from app.llm.factory import get_llm_provider
        from unittest.mock import patch
        
        # Mock settings
        with patch('app.llm.factory.get_settings') as mock_settings:
            mock_settings.return_value.llm_provider = "mock"
            mock_settings.return_value.default_model = "test"
            mock_settings.return_value.default_temperature = 0.7
            mock_settings.return_value.default_max_tokens = 4096
            
            provider = get_llm_provider("mock")
            
            assert isinstance(provider, MockLLMProvider)
    
    @pytest.mark.asyncio
    async def test_provider_can_generate(self):
        """测试 provider 可以生成"""
        from app.llm.factory import get_llm_provider
        from unittest.mock import patch
        
        with patch('app.llm.factory.get_settings') as mock_settings:
            mock_settings.return_value.llm_provider = "mock"
            mock_settings.return_value.default_model = "test"
            mock_settings.return_value.default_temperature = 0.7
            mock_settings.return_value.default_max_tokens = 4096
            
            provider = get_llm_provider()
            response = await provider.generate("测试")
            
            assert response is not None


class TestLLMUsageTracking:
    """LLM 使用量追踪测试"""
    
    @pytest.mark.asyncio
    async def test_usage_recorded(self):
        """测试使用量被记录"""
        provider = MockLLMProvider()
        
        response = await provider.generate("测试 prompt")
        
        assert "prompt_tokens" in response.usage
        assert "completion_tokens" in response.usage
        assert "total" in response.usage
    
    @pytest.mark.asyncio
    async def test_usage_increases_with_longer_prompt(self):
        """测试更长 prompt 导致更多 token"""
        provider = MockLLMProvider()
        
        short_response = await provider.generate("短")
        long_response = await provider.generate("这是一段很长的内容" * 10)
        
        # 长的输入应该产生更多 usage
        assert long_response.usage["prompt_tokens"] >= short_response.usage["prompt_tokens"]


class TestLLMErrorHandling:
    """LLM 错误处理测试"""
    
    @pytest.mark.asyncio
    async def test_mock_provider_always_succeeds(self):
        """测试 mock provider 总是成功"""
        provider = MockLLMProvider()
        
        # 多次调用都应该成功
        for _ in range(5):
            response = await provider.generate("测试")
            assert response is not None
            assert len(response.content) > 0
