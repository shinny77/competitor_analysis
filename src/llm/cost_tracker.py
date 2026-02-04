"""Per-call cost logging and budget management."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..utils.logger import get_logger

log = get_logger(__name__)


@dataclass
class CostEntry:
    """A single LLM call cost record."""
    timestamp: str
    task: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float


class CostTracker:
    """Tracks LLM costs across the pipeline and enforces budget caps."""

    def __init__(self, budget_usd: float = 20.0, alert_pcts: list[int] | None = None):
        self.budget_usd = budget_usd
        self.alert_pcts = alert_pcts or [50, 75]
        self.entries: list[CostEntry] = []
        self._alerted: set[int] = set()

    @property
    def total_cost(self) -> float:
        return sum(e.cost_usd for e in self.entries)

    @property
    def budget_remaining(self) -> float:
        return max(0.0, self.budget_usd - self.total_cost)

    @property
    def budget_pct_used(self) -> float:
        if self.budget_usd <= 0:
            return 100.0
        return (self.total_cost / self.budget_usd) * 100

    def log_call(self, task: str, response: Any) -> CostEntry:
        """Log a completed LLM call from an LLMResponse."""
        entry = CostEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            task=task,
            provider=response.provider,
            model=response.model,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            cost_usd=response.cost_usd,
        )
        self.entries.append(entry)
        self._check_budget()
        return entry

    def _check_budget(self):
        """Check budget thresholds and log warnings."""
        pct = self.budget_pct_used
        for threshold in self.alert_pcts:
            if pct >= threshold and threshold not in self._alerted:
                self._alerted.add(threshold)
                log.warning(
                    f"Budget alert: {pct:.1f}% used "
                    f"(${self.total_cost:.4f} / ${self.budget_usd:.2f})"
                )

        if pct >= 100:
            raise BudgetExceededError(
                f"Budget exceeded: ${self.total_cost:.4f} >= ${self.budget_usd:.2f}"
            )

    def summary(self) -> dict[str, Any]:
        """Return a cost summary breakdown."""
        by_provider: dict[str, float] = {}
        by_task: dict[str, float] = {}
        total_input = 0
        total_output = 0

        for e in self.entries:
            by_provider[e.provider] = by_provider.get(e.provider, 0) + e.cost_usd
            by_task[e.task] = by_task.get(e.task, 0) + e.cost_usd
            total_input += e.input_tokens
            total_output += e.output_tokens

        return {
            "total_cost_usd": round(self.total_cost, 6),
            "budget_usd": self.budget_usd,
            "budget_pct_used": round(self.budget_pct_used, 1),
            "total_calls": len(self.entries),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "by_provider": by_provider,
            "by_task": by_task,
        }

    def save(self, path: str | Path):
        """Save cost log to JSON."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "summary": self.summary(),
            "entries": [
                {
                    "timestamp": e.timestamp,
                    "task": e.task,
                    "provider": e.provider,
                    "model": e.model,
                    "input_tokens": e.input_tokens,
                    "output_tokens": e.output_tokens,
                    "cost_usd": e.cost_usd,
                }
                for e in self.entries
            ],
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def load(self, path: str | Path):
        """Load cost log from JSON."""
        path = Path(path)
        if not path.exists():
            return
        with open(path) as f:
            data = json.load(f)
        for e in data.get("entries", []):
            self.entries.append(CostEntry(**e))


class BudgetExceededError(Exception):
    """Raised when the LLM cost budget is exceeded."""
    pass
