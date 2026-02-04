"""Anthropic Claude LLM client."""

from __future__ import annotations

import anthropic

from .base_client import BaseLLMClient, LLMResponse

# Pricing per 1M tokens (as of 2025)
PRICING = {
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
    "claude-opus-4-20250514": {"input": 15.0, "output": 75.0},
    "claude-haiku-3-20250414": {"input": 0.25, "output": 1.25},
}

DEFAULT_MODEL = "claude-sonnet-4-20250514"


class ClaudeClient(BaseLLMClient):
    """Anthropic Claude client."""

    provider = "claude"

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL, max_tokens: int = 4096, temperature: float = 0.3):
        super().__init__(api_key, model, max_tokens, temperature)
        self.client = anthropic.Anthropic(api_key=api_key)

    def complete(self, prompt: str, system: str = "") -> LLMResponse:
        messages = [{"role": "user", "content": prompt}]
        kwargs = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system

        resp = self.client.messages.create(**kwargs)

        content = resp.content[0].text if resp.content else ""
        input_tok = resp.usage.input_tokens
        output_tok = resp.usage.output_tokens

        return LLMResponse(
            content=content,
            model=self.model,
            provider=self.provider,
            input_tokens=input_tok,
            output_tokens=output_tok,
            total_tokens=input_tok + output_tok,
            cost_usd=self._estimate_cost(input_tok, output_tok),
            finish_reason=resp.stop_reason,
        )

    def complete_structured(self, prompt: str, system: str = "", schema: dict | None = None) -> LLMResponse:
        json_instruction = "Respond with valid JSON only. No markdown fences, no explanation."
        if schema:
            import json
            json_instruction += f"\n\nExpected JSON schema:\n{json.dumps(schema, indent=2)}"

        full_system = f"{system}\n\n{json_instruction}" if system else json_instruction
        return self.complete(prompt, system=full_system)

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        prices = PRICING.get(self.model, {"input": 3.0, "output": 15.0})
        return (input_tokens * prices["input"] + output_tokens * prices["output"]) / 1_000_000
