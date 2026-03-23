"""Embedding service protocol and Gemini implementation."""

from __future__ import annotations

from typing import Protocol

import httpx


class EmbeddingServiceProtocol(Protocol):
    """Contract for vector embedding generation."""

    def embed(self, text: str) -> tuple[float, ...] | None:
        """Return a float embedding for ``text``, or None on failure."""


class GeminiEmbeddingService:
    """Embedding via Gemini embedContent API."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        model: str = "text-embedding-004",
        timeout: float = 5.0,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout

    def embed(self, text: str) -> tuple[float, ...] | None:
        """Call Gemini embedContent and return the embedding, or None on failure."""
        if not text.strip():
            return None
        url = f"{self._base_url}/models/{self._model}:embedContent?key={self._api_key}"
        body = {
            "model": f"models/{self._model}",
            "content": {"parts": [{"text": text[:2048]}]},
        }
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(url, json=body)
            if response.status_code != 200:
                return None
            data = response.json()
            values = data.get("embedding", {}).get("values")
            if not isinstance(values, list) or len(values) != 768:
                return None
            return tuple(float(value) for value in values)
        except Exception:
            return None
