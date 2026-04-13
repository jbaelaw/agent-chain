"""Ollama (local LLM) backend."""

from __future__ import annotations

import os

import httpx

from .base import LLMBackend


class OllamaBackend(LLMBackend):
    """Ollama REST API adapter for local models."""

    def __init__(
        self,
        *,
        model: str = "llama3",
        base_url: str | None = None,
        temperature: float = 0.7,
        timeout: float = 120.0,
    ) -> None:
        self._model = model
        self._base_url = (base_url or os.environ.get("OLLAMA_HOST", "http://localhost:11434")).rstrip("/")
        self._temperature = temperature
        self._timeout = timeout

    @property
    def name(self) -> str:
        return f"ollama/{self._model}"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        body: dict = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": self._temperature},
        }
        if system_prompt:
            body["system"] = system_prompt

        resp = httpx.post(
            f"{self._base_url}/api/generate",
            json=body,
            timeout=self._timeout,
        )
        resp.raise_for_status()
        return resp.json()["response"]
