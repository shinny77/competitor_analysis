"""Google Gemini LLM client."""

from __future__ import annotations

import google.generativeai as genai

from .base_client import BaseLLMClient, LLMResponse

# Pricing per 1M tokens
PRICING = {
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
}

DEFAULT_MODEL = "gemini-2.0-flash"


class GeminiClient(BaseLLMClient):
    """Google Gemini client."""

    provider = "gemini"

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL, max_tokens: int = 4096, temperature: float = 0.3):
        super().__init__(api_key, model, max_tokens, temperature)
        genai.configure(api_key=api_key)
        self.model_instance = genai.GenerativeModel(model)

    def complete(self, prompt: str, system: str = "") -> LLMResponse:
        full_prompt = f"{system}\n\n{prompt}" if system else prompt

        config = genai.types.GenerationConfig(
            max_output_tokens=self.max_tokens,
            temperature=self.temperature,
        )

        resp = self.model_instance.generate_content(full_prompt, generation_config=config)

        content = resp.text if resp.text else ""
        # Gemini token counts from usage_metadata
        input_tok = getattr(resp.usage_metadata, "prompt_token_count", 0) or 0
        output_tok = getattr(resp.usage_metadata, "candidates_token_count", 0) or 0

        return LLMResponse(
            content=content,
            model=self.model,
            provider=self.provider,
            input_tokens=input_tok,
            output_tokens=output_tok,
            total_tokens=input_tok + output_tok,
            cost_usd=self._estimate_cost(input_tok, output_tok),
        )

    def complete_structured(self, prompt: str, system: str = "", schema: dict | None = None) -> LLMResponse:
        json_instruction = "Respond with valid JSON only. No markdown fences, no explanation."
        if schema:
            import json
            json_instruction += f"\n\nExpected JSON schema:\n{json.dumps(schema, indent=2)}"

        full_system = f"{system}\n\n{json_instruction}" if system else json_instruction
        return self.complete(prompt, system=full_system)

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        prices = PRICING.get(self.model, {"input": 0.10, "output": 0.40})
        return (input_tokens * prices["input"] + output_tokens * prices["output"]) / 1_000_000
