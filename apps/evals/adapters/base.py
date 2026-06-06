# llm_eval_harness/apps/evals/adapters/base.py
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class AdapterResult:
    output: str
    latency_ms: int
    token_count: int | None = None
    error: str | None = None


class ModelAdapter(ABC):
    model_id: str

    @abstractmethod
    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1024,
        timeout: int = 30,
    ) -> AdapterResult:
        raise NotImplementedError

    @classmethod
    def from_model_id(cls, model_id: str) -> "ModelAdapter":
        if model_id.startswith("claude-"):
            from apps.evals.adapters.anthropic import AnthropicAdapter
            return AnthropicAdapter(model_id)
        if model_id.startswith("gpt-") or model_id.startswith("o1") or model_id.startswith("o3"):
            from apps.evals.adapters.openai import OpenAIAdapter
            return OpenAIAdapter(model_id)
        if model_id.startswith("gemini-"):
            from apps.evals.adapters.gemini import GeminiAdapter
            return GeminiAdapter(model_id)
        from apps.evals.adapters.openai import OpenAICompatAdapter
        return OpenAICompatAdapter(model_id)
