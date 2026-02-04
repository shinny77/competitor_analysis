"""JSON checkpoint save/load/list for pipeline state persistence."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..utils.logger import get_logger

log = get_logger(__name__)


class CheckpointManager:
    """Manages pipeline checkpoints for resume capability.

    Checkpoints are JSON files that capture the state at each pipeline
    stage, allowing interrupted runs to resume from the last successful
    stage rather than starting over.
    """

    def __init__(self, checkpoint_dir: str = "checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def save(self, stage: str, data: dict[str, Any], project_name: str = "default") -> Path:
        """Save a checkpoint for a pipeline stage.

        Args:
            stage: Pipeline stage name (e.g. 'research_efm', 'analysis').
            data: Arbitrary JSON-serializable state to save.
            project_name: Project identifier for namespacing.

        Returns:
            Path to the saved checkpoint file.
        """
        checkpoint = {
            "stage": stage,
            "project": project_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }

        filename = f"{project_name}_{stage}.json"
        path = self.checkpoint_dir / filename

        with open(path, "w") as f:
            json.dump(checkpoint, f, indent=2, default=str)

        log.info(f"Checkpoint saved: {path}")
        return path

    def load(self, stage: str, project_name: str = "default") -> dict[str, Any] | None:
        """Load a checkpoint for a pipeline stage.

        Returns:
            The checkpoint data dict, or None if not found.
        """
        filename = f"{project_name}_{stage}.json"
        path = self.checkpoint_dir / filename

        if not path.exists():
            log.info(f"No checkpoint found for {stage}")
            return None

        with open(path) as f:
            checkpoint = json.load(f)

        log.info(f"Checkpoint loaded: {path} (saved {checkpoint.get('timestamp', 'unknown')})")
        return checkpoint.get("data")

    def exists(self, stage: str, project_name: str = "default") -> bool:
        """Check if a checkpoint exists for a stage."""
        filename = f"{project_name}_{stage}.json"
        return (self.checkpoint_dir / filename).exists()

    def list_checkpoints(self, project_name: str | None = None) -> list[dict[str, Any]]:
        """List all available checkpoints, optionally filtered by project.

        Returns:
            List of checkpoint metadata dicts.
        """
        results = []
        for path in sorted(self.checkpoint_dir.glob("*.json")):
            try:
                with open(path) as f:
                    cp = json.load(f)
                meta = {
                    "file": path.name,
                    "stage": cp.get("stage", "unknown"),
                    "project": cp.get("project", "unknown"),
                    "timestamp": cp.get("timestamp", "unknown"),
                }
                if project_name is None or meta["project"] == project_name:
                    results.append(meta)
            except (json.JSONDecodeError, KeyError):
                log.warning(f"Skipping invalid checkpoint: {path}")
        return results

    def delete(self, stage: str, project_name: str = "default") -> bool:
        """Delete a specific checkpoint."""
        filename = f"{project_name}_{stage}.json"
        path = self.checkpoint_dir / filename
        if path.exists():
            path.unlink()
            log.info(f"Checkpoint deleted: {path}")
            return True
        return False

    def clear(self, project_name: str | None = None):
        """Clear all checkpoints, optionally for a specific project only."""
        for path in self.checkpoint_dir.glob("*.json"):
            if project_name:
                try:
                    with open(path) as f:
                        cp = json.load(f)
                    if cp.get("project") != project_name:
                        continue
                except (json.JSONDecodeError, KeyError):
                    pass
            path.unlink()
            log.info(f"Checkpoint cleared: {path}")
