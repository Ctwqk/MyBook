"""LLM Provider 工厂"""
from typing import Optional

from ..core.config import get_settings
from .base import LLMProvider
from .mock import MockLLMProvider as MockProvider
from .providers import (
    OpenAIProvider,
    AnthropicProvider,
    OllamaProvider,
    SiliconFlowProvider,
    DeepSeekProvider,
    ZhipuProvider,
)


def create_llm_provider(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    **kwargs
) -> LLMProvider:
    """
    创建 LLM Provider 实例
    
    Args:
        provider: Provider 类型 (mock/openai/anthropic/ollama/siliconflow/deepseek/zhipu)
        model: 指定的模型名称 (可选，会覆盖默认配置)
        **kwargs: 其他参数
    
    Returns:
        LLMProvider 实例
    """
    settings = get_settings()
    provider = provider or settings.llm_provider
    
    # 创建对应的 Provider
    if provider == "mock":
        return MockProvider(model=model or "mock-gpt4")
    
    elif provider == "openai":
        return OpenAIProvider(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=model or settings.openai_model,
            temperature=kwargs.get("temperature", settings.openai_temperature),
            max_tokens=kwargs.get("max_tokens", settings.openai_max_tokens),
        )
    
    elif provider == "anthropic":
        return AnthropicProvider(
            api_key=settings.anthropic_api_key,
            model=model or settings.anthropic_model,
            temperature=kwargs.get("temperature", settings.anthropic_temperature),
            max_tokens=kwargs.get("max_tokens", settings.anthropic_max_tokens),
        )
    
    elif provider == "ollama":
        return OllamaProvider(
            base_url=settings.ollama_base_url,
            model=model or settings.ollama_model,
            temperature=kwargs.get("temperature", settings.ollama_temperature),
            max_tokens=kwargs.get("max_tokens", settings.ollama_max_tokens),
        )
    
    elif provider == "siliconflow":
        return SiliconFlowProvider(
            api_key=settings.siliconflow_api_key,
            base_url=settings.siliconflow_base_url,
            model=model or settings.siliconflow_model,
            temperature=kwargs.get("temperature", settings.siliconflow_temperature),
            max_tokens=kwargs.get("max_tokens", settings.siliconflow_max_tokens),
        )
    
    elif provider == "deepseek":
        return DeepSeekProvider(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            model=model or settings.deepseek_model,
            temperature=kwargs.get("temperature", settings.deepseek_temperature),
            max_tokens=kwargs.get("max_tokens", settings.deepseek_max_tokens),
        )
    
    elif provider == "zhipu":
        return ZhipuProvider(
            api_key=settings.zhipu_api_key,
            base_url=settings.zhipu_base_url,
            model=model or settings.zhipu_model,
            temperature=kwargs.get("temperature", settings.zhipu_temperature),
            max_tokens=kwargs.get("max_tokens", settings.zhipu_max_tokens),
        )
    
    else:
        # 默认返回 Mock
        return MockProvider(model=model or "mock-gpt4")


def create_module_provider(module: str, **kwargs) -> LLMProvider:
    """
    根据模块创建对应的 Provider
    
    Args:
        module: 模块名 (planner/writer/reviewer)
        **kwargs: 其他参数
    
    Returns:
        LLMProvider 实例
    """
    settings = get_settings()
    
    # 获取模块对应的模型配置
    if module == "planner":
        model = settings.planner_model
    elif module == "writer":
        model = settings.writer_model
    elif module == "reviewer":
        model = settings.reviewer_model
    else:
        model = None
    
    return create_llm_provider(model=model, **kwargs)
