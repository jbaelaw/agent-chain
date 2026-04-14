"""Async Anthropic backend using httpx.AsyncClient."""

from __future__ import annotations

import os

import httpx

from .async_base import AsyncLLMBackend


class AsyncAnthropicBackend(AsyncLLMBackend):

    def __init__(
        self,
        *,
        model: str = "claude-sonnet-4-20250514",
        api_key: str | None = None,
        base_url: str = "https://api.anthropic.com/v1",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        timeout: float = 60.0,
    ) -> None:
        self._model = model
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self._base_url = base_url.rstrip("/")
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._timeout = timeout

    @property
    def name(self) -> str:
        return f"anthropic/{self._model}"

    async def agenerate(self, prompt: str, system_prompt: str = "") -> str:
        if not self._api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")

        body: dict = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            body["system"] = system_prompt

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}/messages",
                headers={
                    "x-api-key": self._api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=self._timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["content"][0]["text"]
