# apps/evidence/adapters/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass


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
        timeout: int = 60,
    ) -> AdapterResult:
        raise NotImplementedError

    @classmethod
    def for_claude(cls, model_id: str = "claude-sonnet-4-6") -> "ModelAdapter":
        from apps.evidence.adapters.anthropic import AnthropicAdapter
        return AnthropicAdapter(model_id)
