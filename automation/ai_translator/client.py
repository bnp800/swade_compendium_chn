"""DeepSeek v4 API client for SWADE translation.

Uses HTTP API directly to avoid dependency issues.
Handles rate limiting, retries, and concurrent request management.
"""
import json
import os
import time
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# Try to import httpx, fall back to urllib
try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

import urllib.request
import urllib.error


class DeepSeekClient:
    """Client for DeepSeek v4 translation API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-chat",
        max_retries: int = 3,
        timeout: float = 120.0,
    ):
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError(
                "DeepSeek API key not found. Set DEEPSEEK_API_KEY env var."
            )
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.max_retries = max_retries
        self.timeout = timeout

    def _http_post(self, endpoint: str, payload: dict) -> dict:
        """Make HTTP POST request to DeepSeek API."""
        url = f"{self.base_url}{endpoint}"
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        if HAS_HTTPX:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, content=data, headers=headers)
                if resp.status_code >= 400:
                    raise Exception(f"HTTP {resp.status_code}: {resp.text[:500]}")
                return resp.json()
        else:
            req = urllib.request.Request(url, data=data, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", errors="replace")
                raise Exception(f"HTTP {e.code}: {body[:500]}")
            except Exception as e:
                raise Exception(f"Request failed: {e}")

    def translate(
        self,
        text: str,
        system_prompt: str,
        context: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> Optional[str]:
        """Translate a single text segment."""
        messages = [{"role": "system", "content": system_prompt}]
        user_msg = text
        if context:
            user_msg = f"Context: {context}\n\nText:\n{user_msg}"
        messages.append({"role": "user", "content": user_msg})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": 0.9,
            "stream": False,
        }

        for attempt in range(self.max_retries):
            try:
                resp = self._http_post("/v1/chat/completions", payload)
                content = resp["choices"][0]["message"]["content"]
                return content.strip() if content else None
            except Exception as e:
                msg = str(e)
                if "429" in msg or "rate" in msg.lower():
                    wait = (2 ** attempt) * 5
                    logger.warning("Rate limited, waiting %ds...", wait)
                    time.sleep(wait)
                elif "503" in msg or "502" in msg:
                    wait = (2 ** attempt) * 3
                    logger.warning("Server error, waiting %ds...", wait)
                    time.sleep(wait)
                else:
                    logger.error("API error (attempt %d): %s", attempt + 1, e)
                    if attempt < self.max_retries - 1:
                        time.sleep(2 ** attempt)
                    else:
                        return None
        return None


def create_client_from_env() -> DeepSeekClient:
    """Create a DeepSeekClient from environment variables."""
    return DeepSeekClient(
        api_key=os.environ.get("DEEPSEEK_API_KEY"),
        base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        model=os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
    )
