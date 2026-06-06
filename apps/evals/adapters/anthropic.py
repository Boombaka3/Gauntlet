# llm_eval_harness/apps/evals/adapters/anthropic.py
import logging
import os
import time

from apps.evals.adapters.base import AdapterResult, ModelAdapter

logger = logging.getLogger(__name__)


class AnthropicAdapter(ModelAdapter):
    def __init__(self, model_id: str) -> None:
        self.model_id = model_id
        import anthropic as _anthropic
        self._anthropic = _anthropic
        self._client = _anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
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
                response = self._client.messages.create(
                    model=self.model_id,
                    max_tokens=max_tokens,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                    timeout=timeout,
                )
                latency_ms = int((time.monotonic() - start) * 1000)
                output = response.content[0].text if response.content else ""
                token_count = None
                if response.usage:
                    token_count = response.usage.input_tokens + response.usage.output_tokens
                return AdapterResult(output=output, latency_ms=latency_ms, token_count=token_count)

            except self._anthropic.RateLimitError:
                if attempt == 0:
                    logger.warning("Anthropic rate limit on %s, retrying after 2s", self.model_id)
                    time.sleep(2)
                    continue
                return AdapterResult(
                    output="",
                    latency_ms=0,
                    error="Anthropic rate limit exceeded after retry",
                )
            except Exception as exc:
                logger.error("AnthropicAdapter.complete failed [%s]: %s", self.model_id, exc)
                return AdapterResult(output="", latency_ms=0, error=str(exc))

        return AdapterResult(output="", latency_ms=0, error="Unknown error in AnthropicAdapter")
