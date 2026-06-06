# llm_eval_harness/apps/evals/adapters/gemini.py
import logging
import os
import time

from apps.evals.adapters.base import AdapterResult, ModelAdapter

logger = logging.getLogger(__name__)


class GeminiAdapter(ModelAdapter):
    def __init__(self, model_id: str) -> None:
        self.model_id = model_id
        import google.generativeai as genai
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))
        self._genai = genai

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
                model = self._genai.GenerativeModel(
                    model_name=self.model_id,
                    system_instruction=system_prompt,
                )
                response = model.generate_content(
                    user_prompt,
                    generation_config=self._genai.types.GenerationConfig(
                        max_output_tokens=max_tokens,
                    ),
                    request_options={"timeout": timeout},
                )
                latency_ms = int((time.monotonic() - start) * 1000)
                output = response.text if hasattr(response, "text") and response.text else ""
                token_count = None
                if hasattr(response, "usage_metadata") and response.usage_metadata:
                    token_count = getattr(response.usage_metadata, "total_token_count", None)
                return AdapterResult(output=output, latency_ms=latency_ms, token_count=token_count)

            except Exception as exc:
                exc_str = str(exc)
                is_rate_limit = (
                    "429" in exc_str
                    or "quota" in exc_str.lower()
                    or "resource_exhausted" in exc_str.lower()
                    or "rate" in exc_str.lower()
                )
                # Also catch google.api_core ResourceExhausted if importable
                try:
                    from google.api_core.exceptions import ResourceExhausted
                    if isinstance(exc, ResourceExhausted):
                        is_rate_limit = True
                except ImportError:
                    pass

                if is_rate_limit and attempt == 0:
                    logger.warning("Gemini rate limit on %s, retrying after 2s", self.model_id)
                    time.sleep(2)
                    continue

                logger.error("GeminiAdapter.complete failed [%s]: %s", self.model_id, exc)
                return AdapterResult(output="", latency_ms=0, error=exc_str)

        return AdapterResult(output="", latency_ms=0, error="Unknown error in GeminiAdapter")
