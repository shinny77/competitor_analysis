"""Shared utilities for logging, web fetching, and helpers."""

from .logger import get_logger
from .web_fetcher import WebFetcher

__all__ = ["get_logger", "WebFetcher"]
