"""Task-to-LLM routing table.

Routes each pipeline task to the appropriate LLM provider based on
the LLM routing config. Manages client instantiation and provides
a single interface for all LLM calls.
"""

from __future__ import annotations

import os
from typing import Any

from ..config import LLMConfig, LLMRoutingConfig, resolve_api_key
from .base_client import BaseLLMClient, LLMResponse
from .claude_client import ClaudeClient
from .openai_client import OpenAIClient
from .gemini_client import GeminiClient
from .grok_client import GrokClient
from .cost_tracker import CostTracker

PROVIDER_MAP: dict[str, type[BaseLLMClient]] = {
    "claude": ClaudeClient,
    "anthropic": ClaudeClient,
    "openai": OpenAIClient,
    "gpt": OpenAIClient,
    "gemini": GeminiClient,
    "google": GeminiClient,
    "grok": GrokClient,
    "xai": GrokClient,
}


class LLMRouter:
    """Routes pipeline tasks to the correct LLM provider.

    Maintains a pool of instantiated clients and tracks costs
    across all calls.
    """

    def __init__(self, config: LLMRoutingConfig, cost_tracker: CostTracker | None = None):
        self.config = config
        self.cost_tracker = cost_tracker or CostTracker()
        self._clients: dict[str, BaseLLMClient] = {}

    def _get_client(self, llm_config: LLMConfig) -> BaseLLMClient:
        """Get or create a client for the given config."""
        key = f"{llm_config.provider}:{llm_config.model}"
        if key not in self._clients:
            api_key = resolve_api_key(llm_config.api_key_env)
            cls = PROVIDER_MAP.get(llm_config.provider)
            if not cls:
                raise ValueError(f"Unknown LLM provider: {llm_config.provider}")
            self._clients[key] = cls(
                api_key=api_key,
                model=llm_config.model,
                max_tokens=llm_config.max_tokens,
                temperature=llm_config.temperature,
            )
        return self._clients[key]

    def _get_task_config(self, task: str) -> LLMConfig:
        """Resolve a task name to its LLM config."""
        config = getattr(self.config, task, None)
        if config is None:
            raise ValueError(f"Unknown task in routing config: {task}")
        return config

    def call(self, task: str, prompt: str, system: str = "") -> LLMResponse:
        """Route a task to the appropriate LLM and return the response.

        Args:
            task: Task name matching a field in LLMRoutingConfig
                  (e.g. 'content_extraction', 'profile_drafting')
            prompt: The user prompt to send.
            system: Optional system prompt.
        """
        llm_config = self._get_task_config(task)
        client = self._get_client(llm_config)
        response = client.complete(prompt, system=system)
        self.cost_tracker.log_call(task, response)
        return response

    def call_structured(self, task: str, prompt: str, system: str = "", schema: dict | None = None) -> LLMResponse:
        """Route a task expecting structured JSON output."""
        llm_config = self._get_task_config(task)
        client = self._get_client(llm_config)
        response = client.complete_structured(prompt, system=system, schema=schema)
        self.cost_tracker.log_call(task, response)
        return response

    def test_provider(self, provider: str, api_key: str, model: str | None = None) -> LLMResponse:
        """Test a specific provider with a simple prompt. Used by CLI test-llm."""
        cls = PROVIDER_MAP.get(provider)
        if not cls:
            raise ValueError(f"Unknown provider: {provider}")
        default_model = model or getattr(cls, "DEFAULT_MODEL", None) or "default"
        client = cls(api_key=api_key, model=default_model, max_tokens=100, temperature=0.0)
        return client.complete("Say 'OK' if you can hear me. One word only.")
