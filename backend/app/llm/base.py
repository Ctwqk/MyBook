"""LLM Provider 抽象层"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class LLMResponse:
    """LLM 响应"""
    content: str
    model: str
    usage: dict[str, int]  # token 使用量
    raw_response: Optional[dict] = None


class LLMProvider(ABC):
    """LLM Provider 抽象基类"""

    def __init__(self, model: str = "default", temperature: float = 0.7, max_tokens: int = 4096):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    @abstractmethod
    async def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> LLMResponse:
        """
        生成文本
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            **kwargs: 其他参数
            
        Returns:
            LLMResponse: 响应对象
        """
        pass

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        system_prompt: Optional[str],
        response_schema: dict[str, Any],
        **kwargs
    ) -> dict[str, Any]:
        """
        生成结构化输出
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            response_schema: 响应格式定义
            **kwargs: 其他参数
            
        Returns:
            dict: 结构化响应
        """
        pass

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        **kwargs
    ) -> LLMResponse:
        """
        对话模式
        
        Args:
            messages: 消息列表 [{"role": "user/assistant/system", "content": "..."}]
            **kwargs: 其他参数
            
        Returns:
            LLMResponse: 响应对象
        """
        pass

    def get_config(self) -> dict[str, Any]:
        """获取当前配置"""
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
