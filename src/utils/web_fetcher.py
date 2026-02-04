"""URL fetching with retry, timeout, and content extraction."""

from __future__ import annotations

import time
from typing import Any

import requests
from bs4 import BeautifulSoup

from .logger import get_logger

log = get_logger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}


class WebFetcher:
    """Fetch and extract content from web pages with retry logic."""

    def __init__(
        self,
        timeout: int = 30,
        max_retries: int = 3,
        backoff_base: float = 2.0,
        headers: dict[str, str] | None = None,
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.session = requests.Session()
        self.session.headers.update(headers or DEFAULT_HEADERS)

    def fetch(self, url: str) -> dict[str, Any]:
        """Fetch a URL and return structured result.

        Returns:
            Dict with keys: url, status, html, text, title, error
        """
        result: dict[str, Any] = {"url": url, "status": None, "html": None, "text": None, "title": None, "error": None}

        for attempt in range(self.max_retries):
            try:
                resp = self.session.get(url, timeout=self.timeout, allow_redirects=True)
                result["status"] = resp.status_code

                if resp.status_code == 200:
                    result["html"] = resp.text
                    soup = BeautifulSoup(resp.text, "html.parser")

                    # Remove scripts and styles
                    for tag in soup(["script", "style", "nav", "footer", "header"]):
                        tag.decompose()

                    result["text"] = soup.get_text(separator="\n", strip=True)
                    title_tag = soup.find("title")
                    result["title"] = title_tag.get_text(strip=True) if title_tag else None
                    return result

                if resp.status_code >= 500:
                    log.warning(f"Server error {resp.status_code} for {url}, attempt {attempt + 1}")
                else:
                    result["error"] = f"HTTP {resp.status_code}"
                    return result

            except requests.exceptions.Timeout:
                result["error"] = "timeout"
                log.warning(f"Timeout for {url}, attempt {attempt + 1}")
            except requests.exceptions.ConnectionError as e:
                result["error"] = f"connection_error: {e}"
                log.warning(f"Connection error for {url}, attempt {attempt + 1}")
            except Exception as e:
                result["error"] = str(e)
                log.error(f"Unexpected error fetching {url}: {e}")
                return result

            if attempt < self.max_retries - 1:
                wait = self.backoff_base ** attempt
                time.sleep(wait)

        return result

    def fetch_text(self, url: str) -> str | None:
        """Fetch a URL and return just the extracted text."""
        result = self.fetch(url)
        return result["text"]

    def fetch_multiple(self, urls: list[str]) -> list[dict[str, Any]]:
        """Fetch multiple URLs sequentially."""
        return [self.fetch(url) for url in urls]
