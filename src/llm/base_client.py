"""Abstract base class for LLM clients."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Standardised response from any LLM provider."""
    content: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    finish_reason: str | None = None
    raw: dict | None = None


class BaseLLMClient(ABC):
    """Abstract LLM client interface.

    All LLM providers implement this interface so the router
    can dispatch to any of them interchangeably.
    """

    provider: str = "base"

    def __init__(self, api_key: str, model: str, max_tokens: int = 4096, temperature: float = 0.3):
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

    @abstractmethod
    def complete(self, prompt: str, system: str = "") -> LLMResponse:
        """Send a completion request and return a standardised response."""
        ...

    @abstractmethod
    def complete_structured(self, prompt: str, system: str = "", schema: dict | None = None) -> LLMResponse:
        """Request structured (JSON) output from the model."""
        ...

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost in USD based on token counts. Override per provider."""
        return 0.0
