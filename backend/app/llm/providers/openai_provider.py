"""OpenAI 兼容 API Provider"""
import httpx
from typing import Any, Optional

from ..base import LLMProvider, LLMResponse


class OpenAIProvider(LLMProvider):
    """OpenAI 兼容格式的 LLM Provider"""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o",
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ):
        super().__init__(model, temperature, max_tokens)
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=120.0,
        )

    async def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> LLMResponse:
        """生成文本"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        return await self.chat(messages, **kwargs)

    async def generate_structured(
        self,
        prompt: str,
        system_prompt: Optional[str],
        response_schema: dict[str, Any],
        **kwargs
    ) -> dict[str, Any]:
        """生成结构化输出 (使用 JSON Mode)"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self._post("/chat/completions", {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "response_format": {"type": "json_object"},
        })

        content = response["choices"][0]["message"]["content"]
        return {"content": content}

    async def chat(self, messages: list[dict[str, str]], **kwargs) -> LLMResponse:
        """对话模式"""
        response = await self._post("/chat/completions", {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "top_p": kwargs.get("top_p", None),
        })

        return LLMResponse(
            content=response["choices"][0]["message"]["content"],
            model=response.get("model", self.model),
            usage=response.get("usage", {}),
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
