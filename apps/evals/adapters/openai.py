# llm_eval_harness/apps/evals/adapters/openai.py
import logging
import os
import time

from apps.evals.adapters.base import AdapterResult, ModelAdapter

logger = logging.getLogger(__name__)


class OpenAIAdapter(ModelAdapter):
    def __init__(
        self,
        model_id: str,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.model_id = model_id
        from openai import OpenAI
        import openai as _openai
        self._openai = _openai
        self._client = OpenAI(
            api_key=api_key or os.environ.get("OPENAI_API_KEY", ""),
            base_url=base_url,
        )

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1024,
        timeout: int = 30,
    ) -> AdapterResult:
        for attempt in range(2):
            try:
                start = time.monotonic()
                response = self._client.chat.completions.create(
                    model=self.model_id,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    max_tokens=max_tokens,
                    timeout=timeout,
                )
                latency_ms = int((time.monotonic() - start) * 1000)
                output = ""
                if response.choices:
                    output = response.choices[0].message.content or ""
                token_count = response.usage.total_tokens if response.usage else None
                return AdapterResult(output=output, latency_ms=latency_ms, token_count=token_count)

            except self._openai.RateLimitError:
                if attempt == 0:
                    logger.warning("OpenAI rate limit on %s, retrying after 2s", self.model_id)
                    time.sleep(2)
                    continue
                return AdapterResult(
                    output="",
                    latency_ms=0,
                    error="OpenAI rate limit exceeded after retry",
                )
            except Exception as exc:
                logger.error("OpenAIAdapter.complete failed [%s]: %s", self.model_id, exc)
                return AdapterResult(output="", latency_ms=0, error=str(exc))

        return AdapterResult(output="", latency_ms=0, error="Unknown error in OpenAIAdapter")


class OpenAICompatAdapter(OpenAIAdapter):
    """Wraps any OpenAI-compatible endpoint (Ollama, vLLM, LM Studio, etc.)."""

    def __init__(self, model_id: str) -> None:
        base_url = os.environ.get("OPENAI_COMPAT_BASE_URL", "http://localhost:11434/v1")
        super().__init__(model_id, base_url=base_url, api_key="none")
