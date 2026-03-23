from __future__ import annotations

from unittest.mock import MagicMock, patch

from openqilin.llm_gateway.embedding_service import GeminiEmbeddingService
from openqilin.task_orchestrator.dispatch.llm_dispatch import LocalConversationStore


def _mock_client(*, status_code: int, payload: object) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = payload
    client = MagicMock()
    client.post.return_value = response
    client_manager = MagicMock()
    client_manager.__enter__.return_value = client
    client_manager.__exit__.return_value = False
    return client_manager


def test_gemini_embedding_service_returns_none_on_http_error() -> None:
    service = GeminiEmbeddingService(api_key="test-key")

    with patch(
        "openqilin.llm_gateway.embedding_service.httpx.Client",
        return_value=_mock_client(status_code=503, payload={"error": {"message": "unavailable"}}),
    ):
        assert service.embed("hello world") is None


def test_gemini_embedding_service_returns_none_on_wrong_dim() -> None:
    service = GeminiEmbeddingService(api_key="test-key")

    with patch(
        "openqilin.llm_gateway.embedding_service.httpx.Client",
        return_value=_mock_client(status_code=200, payload={"embedding": {"values": [0.1, 0.2]}}),
    ):
        assert service.embed("hello world") is None


def test_gemini_embedding_service_returns_none_on_empty_text() -> None:
    service = GeminiEmbeddingService(api_key="test-key")

    assert service.embed("   ") is None


def test_local_conversation_store_find_relevant_windows_returns_empty() -> None:
    store = LocalConversationStore(max_turns=40)

    assert store.find_relevant_windows("scope", (0.1,) * 768) == ()


def test_local_conversation_store_fetch_channel_summary_returns_none() -> None:
    store = LocalConversationStore(max_turns=40)

    assert store.fetch_channel_summary("other-scope") is None
