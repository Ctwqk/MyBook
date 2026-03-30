"""Anthropic Claude Provider"""
import httpx
from typing import Any, Optional

from ..base import LLMProvider, LLMResponse


class AnthropicProvider(LLMProvider):
    """Anthropic Claude API Provider"""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-5-sonnet-20241022",
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ):
        super().__init__(model, temperature, max_tokens)
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            base_url="https://api.anthropic.com",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            timeout=120.0,
        )

    async def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> LLMResponse:
        """生成文本"""
        messages = [{"role": "user", "content": prompt}]
        return await self.chat(messages, system_prompt=system_prompt, **kwargs)

    async def generate_structured(
        self,
        prompt: str,
        system_prompt: Optional[str],
        response_schema: dict[str, Any],
        **kwargs
    ) -> dict[str, Any]:
        """生成结构化输出"""
        messages = [{"role": "user", "content": prompt}]
        response = await self._post("/v1/messages", {
            "model": self.model,
            "messages": messages,
            "system": system_prompt,
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
        })

        content = response["content"][0]["text"]
        return {"content": content}

    async def chat(self, messages: list[dict[str, str]], system_prompt: Optional[str] = None, **kwargs) -> LLMResponse:
        """对话模式"""
        # 将 OpenAI 格式转换为 Anthropic 格式
        anthropic_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                anthropic_messages.append({
                    "role": "user" if msg["role"] == "user" else "assistant",
                    "content": msg["content"]
                })

        data = {
            "model": self.model,
            "messages": anthropic_messages,
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
        }
        
        if system_prompt:
            data["system"] = system_prompt

        response = await self._post("/v1/messages", data)

        return LLMResponse(
            content=response["content"][0]["text"],
            model=response.get("model", self.model),
            usage={
                "input_tokens": response.get("usage", {}).get("input_tokens", 0),
                "output_tokens": response.get("usage", {}).get("output_tokens", 0),
            },
            raw_response=response,
        )

    async def _post(self, endpoint: str, data: dict) -> dict:
        """发送 POST 请求"""
        response = await self.client.post(endpoint, json=data)
        response.raise_for_status()
        return response.json()

    async def close(self):
        """关闭连接"""
        await self.client.aclose()
