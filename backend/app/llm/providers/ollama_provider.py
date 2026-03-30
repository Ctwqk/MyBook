"""Ollama 本地模型 Provider"""
import httpx
from typing import Any, Optional

from ..base import LLMProvider, LLMResponse


class OllamaProvider(LLMProvider):
    """Ollama 本地 LLM Provider"""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.2",
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ):
        super().__init__(model, temperature, max_tokens)
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=300.0,  # Ollama 可能需要更长的超时
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
        """生成结构化输出"""
        # Ollama 不直接支持 JSON mode，在 prompt 中引导输出格式
        enhanced_prompt = f"""{prompt}

请以有效的 JSON 格式返回结果，不要包含其他内容。JSON 格式要求：
{response_schema}"""

        response = await self.generate(enhanced_prompt, system_prompt, **kwargs)
        return {"content": response.content}

    async def chat(self, messages: list[dict[str, str]], **kwargs) -> LLMResponse:
        """对话模式"""
        # 将 OpenAI 格式转换为 Ollama 格式
        ollama_messages = []
        for msg in messages:
            if msg["role"] == "system":
                # Ollama 使用单独的 system 字段
                continue
            ollama_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        # 检查是否有 system prompt
        system_prompt = None
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
                break

        data = {
            "model": self.model,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", self.temperature),
                "num_predict": kwargs.get("max_tokens", self.max_tokens),
            }
        }

        if system_prompt:
            data["system"] = system_prompt

        response = await self._post("/api/chat", data)

        return LLMResponse(
            content=response["message"]["content"],
            model=self.model,
            usage={
                "prompt_tokens": response.get("prompt_eval_count", 0),
                "completion_tokens": response.get("eval_count", 0),
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
