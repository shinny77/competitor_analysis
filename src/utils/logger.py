"""Structured logging for the competitive intelligence pipeline."""

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path


def get_logger(
    name: str,
    level: int = logging.INFO,
    log_file: str | None = None,
) -> logging.Logger:
    """Create a structured logger.

    Args:
        name: Logger name (typically module name).
        level: Logging level.
        log_file: Optional file path for persistent logs.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(level)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(fmt)
    logger.addHandler(console)

    # File handler (optional)
    if log_file:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(str(path))
        fh.setLevel(level)
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    return logger


class PipelineLogger:
    """Structured logger that tracks pipeline events with context."""

    def __init__(self, project_name: str, log_dir: str = "output/logs"):
        self.project_name = project_name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        log_file = self.log_dir / f"{project_name}_{ts}.log"

        self.logger = get_logger(
            f"pipeline.{project_name}",
            log_file=str(log_file),
        )
        self.events: list[dict] = []

    def event(self, stage: str, action: str, detail: str = "", **kwargs):
        """Log a pipeline event with structured metadata."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "project": self.project_name,
            "stage": stage,
            "action": action,
            "detail": detail,
            **kwargs,
        }
        self.events.append(entry)
        extra = " ".join(f"{k}={v}" for k, v in kwargs.items())
        self.logger.info(f"[{stage}] {action}: {detail} {extra}".strip())

    def error(self, stage: str, action: str, detail: str = "", **kwargs):
        """Log a pipeline error."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "project": self.project_name,
            "stage": stage,
            "action": action,
            "detail": detail,
            "level": "error",
            **kwargs,
        }
        self.events.append(entry)
        extra = " ".join(f"{k}={v}" for k, v in kwargs.items())
        self.logger.error(f"[{stage}] {action}: {detail} {extra}".strip())
