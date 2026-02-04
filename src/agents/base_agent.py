"""Abstract base agent with run/checkpoint/retry logic.

All pipeline agents (Research, Analyst, Scoring, Output) extend this
base class. It provides:
- Checkpoint-aware execution (skip if already completed)
- Bounded retry with exponential backoff
- Structured logging of agent lifecycle
- Cost tracking integration
"""

from __future__ import annotations

import time
import traceback
from abc import ABC, abstractmethod
from typing import Any

from ..llm.router import LLMRouter
from ..llm.cost_tracker import CostTracker
from ..pipeline.checkpoint import CheckpointManager
from ..utils.logger import PipelineLogger


class BaseAgent(ABC):
    """Abstract base class for pipeline agents.

    Subclasses must implement:
        - agent_name: class attribute identifying the agent
        - execute(): the core agent logic
    """

    agent_name: str = "base"

    def __init__(
        self,
        router: LLMRouter,
        checkpoint_mgr: CheckpointManager,
        logger: PipelineLogger,
        project_name: str,
        max_retries: int = 3,
        backoff_base: float = 2.0,
    ):
        self.router = router
        self.checkpoint_mgr = checkpoint_mgr
        self.logger = logger
        self.project_name = project_name
        self.max_retries = max_retries
        self.backoff_base = backoff_base

    @abstractmethod
    def execute(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Core agent logic. Receives inputs, returns outputs.

        Must be implemented by each concrete agent. Should NOT handle
        retries or checkpointing — that's done by run().
        """
        ...

    def checkpoint_key(self, suffix: str = "") -> str:
        """Generate a checkpoint key for this agent."""
        key = self.agent_name
        if suffix:
            key = f"{key}_{suffix}"
        return key

    def run(self, inputs: dict[str, Any], checkpoint_suffix: str = "") -> dict[str, Any]:
        """Execute the agent with checkpoint awareness and retry logic.

        1. Check if a checkpoint exists — if so, return cached result
        2. Attempt execution up to max_retries times
        3. On success, save checkpoint and return result
        4. On failure after all retries, raise the last exception

        Args:
            inputs: Data passed to execute().
            checkpoint_suffix: Optional suffix for checkpoint key
                               (e.g. competitor name for Research agents).
        """
        ck_key = self.checkpoint_key(checkpoint_suffix)

        # Check for existing checkpoint
        cached = self.checkpoint_mgr.load(ck_key, self.project_name)
        if cached is not None:
            self.logger.event(
                self.agent_name, "checkpoint_hit",
                f"Loaded cached result for {ck_key}",
            )
            return cached

        # Execute with retries
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                self.logger.event(
                    self.agent_name, "start",
                    f"Attempt {attempt}/{self.max_retries}",
                )
                result = self.execute(inputs)
                self.logger.event(
                    self.agent_name, "complete",
                    f"Succeeded on attempt {attempt}",
                )

                # Save checkpoint
                self.checkpoint_mgr.save(ck_key, result, self.project_name)
                return result

            except Exception as e:
                last_error = e
                self.logger.error(
                    self.agent_name, "error",
                    f"Attempt {attempt} failed: {e}",
                    traceback=traceback.format_exc(),
                )
                if attempt < self.max_retries:
                    wait = self.backoff_base ** (attempt - 1)
                    self.logger.event(
                        self.agent_name, "retry",
                        f"Waiting {wait:.1f}s before retry",
                    )
                    time.sleep(wait)

        self.logger.error(
            self.agent_name, "failed",
            f"All {self.max_retries} attempts exhausted",
        )
        raise RuntimeError(
            f"Agent {self.agent_name} failed after {self.max_retries} attempts: {last_error}"
        ) from last_error
