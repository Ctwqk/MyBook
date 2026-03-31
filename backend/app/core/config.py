"""应用配置"""
from functools import lru_cache
from typing import Literal, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/mybook"

    # ==========================
    # LLM Provider 全局配置
    # ==========================
    llm_provider: Literal["mock", "openai", "anthropic", "ollama", "siliconflow", "deepseek", "zhipu", "minimax"] = "mock"

    # ==========================
    # OpenAI 兼容 API
    # ==========================
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o"
    openai_temperature: float = 0.7
    openai_max_tokens: int = 4096

    # ==========================
    # Anthropic Claude
    # ==========================
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-sonnet-20241022"
    anthropic_temperature: float = 0.7
    anthropic_max_tokens: int = 4096

    # ==========================
    # Ollama (本地模型)
    # ==========================
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    ollama_temperature: float = 0.7
    ollama_max_tokens: int = 4096

    # ==========================
    # SiliconFlow (国内 API)
    # ==========================
    siliconflow_api_key: str = ""
    siliconflow_base_url: str = "https://api.siliconflow.cn/v1"
    siliconflow_model: str = "Qwen/Qwen2.5-7B-Instruct"
    siliconflow_temperature: float = 0.7
    siliconflow_max_tokens: int = 4096

    # ==========================
    # DeepSeek
    # ==========================
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"
    deepseek_temperature: float = 0.7
    deepseek_max_tokens: int = 4096

    # ==========================
    # 智谱 AI (GLM)
    # ==========================
    zhipu_api_key: str = ""
    zhipu_base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    zhipu_model: str = "glm-4"
    zhipu_temperature: float = 0.7
    zhipu_max_tokens: int = 4096

    # ==========================
    # MiniMax
    # ==========================
    minimax_api_key: str = ""
    minimax_base_url: str = "https://api.minimaxi.com/v1"
    minimax_model: str = "MiniMax-Text-01"
    minimax_temperature: float = 0.7
    minimax_max_tokens: int = 4096

    # ==========================
    # 各模块默认模型
    # ==========================
    planner_model: str = "gpt-4o"
    writer_model: str = "gpt-4o"
    reviewer_model: str = "gpt-4o-mini"

    # ==========================
    # 生成参数默认值
    # ==========================
    default_temperature: float = 0.7
    default_max_tokens: int = 4096
    default_top_p: float = 0.9

    # ==========================
    # App
    # ==========================
    app_env: Literal["development", "production"] = "development"
    log_level: str = "INFO"

    def get_llm_config(self, provider: Optional[str] = None) -> dict:
        """获取指定 provider 的配置"""
        p = provider or self.llm_provider
        
        configs = {
            "mock": {},
            "openai": {
                "api_key": self.openai_api_key,
                "base_url": self.openai_base_url,
                "model": self.openai_model,
                "temperature": self.openai_temperature,
                "max_tokens": self.openai_max_tokens,
            },
            "anthropic": {
                "api_key": self.anthropic_api_key,
                "model": self.anthropic_model,
                "temperature": self.anthropic_temperature,
                "max_tokens": self.anthropic_max_tokens,
            },
            "ollama": {
                "base_url": self.ollama_base_url,
                "model": self.ollama_model,
                "temperature": self.ollama_temperature,
                "max_tokens": self.ollama_max_tokens,
            },
            "siliconflow": {
                "api_key": self.siliconflow_api_key,
                "base_url": self.siliconflow_base_url,
                "model": self.siliconflow_model,
                "temperature": self.siliconflow_temperature,
                "max_tokens": self.siliconflow_max_tokens,
            },
            "deepseek": {
                "api_key": self.deepseek_api_key,
                "base_url": self.deepseek_base_url,
                "model": self.deepseek_model,
                "temperature": self.deepseek_temperature,
                "max_tokens": self.deepseek_max_tokens,
            },
            "zhipu": {
                "api_key": self.zhipu_api_key,
                "base_url": self.zhipu_base_url,
                "model": self.zhipu_model,
                "temperature": self.zhipu_temperature,
                "max_tokens": self.zhipu_max_tokens,
            },
            "minimax": {
                "api_key": self.minimax_api_key,
                "base_url": self.minimax_base_url,
                "model": self.minimax_model,
                "temperature": self.minimax_temperature,
                "max_tokens": self.minimax_max_tokens,
            },
        }
        return configs.get(p, {})


@lru_cache
def get_settings() -> Settings:
    return Settings()
