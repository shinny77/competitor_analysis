"""OpenAI GPT-4 LLM client."""

from __future__ import annotations

import openai

from .base_client import BaseLLMClient, LLMResponse

# Pricing per 1M tokens
PRICING = {
    "gpt-4o": {"input": 2.50, "output": 10.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.0, "output": 30.0},
}

DEFAULT_MODEL = "gpt-4o"


class OpenAIClient(BaseLLMClient):
    """OpenAI GPT client."""

    provider = "openai"

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL, max_tokens: int = 4096, temperature: float = 0.3):
        super().__init__(api_key, model, max_tokens, temperature)
        self.client = openai.OpenAI(api_key=api_key)

    def complete(self, prompt: str, system: str = "") -> LLMResponse:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )

        choice = resp.choices[0]
        content = choice.message.content or ""
        input_tok = resp.usage.prompt_tokens if resp.usage else 0
        output_tok = resp.usage.completion_tokens if resp.usage else 0

        return LLMResponse(
            content=content,
            model=self.model,
            provider=self.provider,
            input_tokens=input_tok,
            output_tokens=output_tok,
            total_tokens=input_tok + output_tok,
            cost_usd=self._estimate_cost(input_tok, output_tok),
            finish_reason=choice.finish_reason,
        )

    def complete_structured(self, prompt: str, system: str = "", schema: dict | None = None) -> LLMResponse:
        json_instruction = "Respond with valid JSON only. No markdown fences, no explanation."
        if schema:
            import json
            json_instruction += f"\n\nExpected JSON schema:\n{json.dumps(schema, indent=2)}"

        full_system = f"{system}\n\n{json_instruction}" if system else json_instruction

        messages = [
            {"role": "system", "content": full_system},
            {"role": "user", "content": prompt},
        ]

        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            response_format={"type": "json_object"},
        )

        choice = resp.choices[0]
        content = choice.message.content or ""
        input_tok = resp.usage.prompt_tokens if resp.usage else 0
        output_tok = resp.usage.completion_tokens if resp.usage else 0

        return LLMResponse(
            content=content,
            model=self.model,
            provider=self.provider,
            input_tokens=input_tok,
            output_tokens=output_tok,
            total_tokens=input_tok + output_tok,
            cost_usd=self._estimate_cost(input_tok, output_tok),
            finish_reason=choice.finish_reason,
        )

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        prices = PRICING.get(self.model, {"input": 2.50, "output": 10.0})
        return (input_tokens * prices["input"] + output_tokens * prices["output"]) / 1_000_000
