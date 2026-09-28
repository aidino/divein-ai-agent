# Cấu hình đa nhà cung cấp model
"""Module quản lý cấu hình và khởi tạo mô hình ngôn ngữ (LLM)."""

import os
from typing import Literal, cast
from dotenv import load_dotenv
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, SecretStr

# Nạp biến môi trường từ .env
load_dotenv()

ProviderType = Literal[
    "openai",
    "anthropic",
    "gemini",
    "openrouter",
    "deepseek",
    "zai",
    "siliconflow",
]


class AppConfig(BaseModel):
    """Cấu hình toàn cục cho Agent."""

    provider: ProviderType = Field(
        default_factory=lambda: cast(
            ProviderType, os.getenv("AI_PROVIDER", "openai").lower()
        )
    )
    temperature: float = Field(default=0.0, ge=0.0, le=1.0)
    max_tokens: int = Field(default=4096)

    def get_llm(self) -> BaseChatModel:
        """Khởi tạo và trả về LLM client chuẩn hóa của LangChain."""
        p = self.provider

        if p == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            model_name = os.getenv("OPENAI_MODEL", "gpt-4o")
            base_url = os.getenv("OPENAI_BASE_URL")
            if not api_key:
                raise ValueError("Thiếu biến môi trường OPENAI_API_KEY trong .env")
            return ChatOpenAI(
                model=model_name,
                api_key=SecretStr(api_key),
                base_url=base_url,
                temperature=self.temperature,
                max_completion_tokens=self.max_tokens,
                streaming=True,
            )

        elif p == "deepseek":
            api_key = os.getenv("DEEPSEEK_API_KEY")
            base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
            model_name = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
            if not api_key:
                raise ValueError("Thiếu biến môi trường DEEPSEEK_API_KEY trong .env")
            return ChatOpenAI(
                model=model_name,
                api_key=SecretStr(api_key),
                base_url=base_url,
                temperature=self.temperature,
                max_completion_tokens=self.max_tokens,
                streaming=True,
            )

        elif p == "openrouter":
            api_key = os.getenv("OPENROUTER_API_KEY")
            base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
            model_name = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.7-sonnet")
            if not api_key:
                raise ValueError("Thiếu biến môi trường OPENROUTER_API_KEY trong .env")
            return ChatOpenAI(
                model=model_name,
                api_key=SecretStr(api_key),
                base_url=base_url,
                temperature=self.temperature,
                max_completion_tokens=self.max_tokens,
                streaming=True,
            )

        elif p == "zai":
            api_key = os.getenv("ZAI_API_KEY")
            base_url = os.getenv("ZAI_BASE_URL", "https://api.z.ai/api/paas/v4")
            model_name = os.getenv("ZAI_MODEL", "glm-4-plus")
            if not api_key:
                raise ValueError("Thiếu biến môi trường ZAI_API_KEY trong .env")
            return ChatOpenAI(
                model=model_name,
                api_key=SecretStr(api_key),
                base_url=base_url,
                temperature=self.temperature,
                max_completion_tokens=self.max_tokens,
                streaming=True,
            )

        elif p == "siliconflow":
            api_key = os.getenv("SILICONFLOW_API_KEY")
            base_url = os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
            model_name = os.getenv("SILICONFLOW_MODEL", "deepseek-ai/DeepSeek-V3")
            if not api_key:
                raise ValueError("Thiếu biến môi trường SILICONFLOW_API_KEY trong .env")
            return ChatOpenAI(
                model=model_name,
                api_key=SecretStr(api_key),
                base_url=base_url,
                temperature=self.temperature,
                max_completion_tokens=self.max_tokens,
                streaming=True,
            )

        elif p == "gemini":
            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
            base_url = os.getenv(
                "GEMINI_BASE_URL",
                "https://generativelanguage.googleapis.com/v1beta/openai/",
            )
            if not api_key:
                raise ValueError("Thiếu biến môi trường GEMINI_API_KEY trong .env")
            # Gemini hỗ trợ chuẩn OpenAI-compatible endpoint hoàn hảo:
            return ChatOpenAI(
                model=model_name,
                api_key=SecretStr(api_key),
                base_url=base_url,
                temperature=self.temperature,
                max_completion_tokens=self.max_tokens,
                streaming=True,
            )

        elif p == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            model_name = os.getenv("ANTHROPIC_MODEL", "claude-3-7-sonnet-20250219")
            if not api_key:
                raise ValueError("Thiếu biến môi trường ANTHROPIC_API_KEY trong .env")
            try:
                from langchain_anthropic import ChatAnthropic
            except ImportError:
                raise ImportError(
                    "Để dùng Anthropic trực tiếp, bạn cần cài đặt: uv add langchain-anthropic"
                )
            return ChatAnthropic(
                model_name=model_name,
                api_key=SecretStr(api_key),
                temperature=self.temperature,
                max_tokens_to_sample=self.max_tokens,
                streaming=True,
                # timeout/stop là tham số bắt buộc trong chữ ký BaseChatModel 1.x
                timeout=None,
                stop=None,
            )

        else:
            raise NotImplementedError(f"Provider '{self.provider}' chưa được hỗ trợ.")


# Khởi tạo singleton instance
config = AppConfig()
