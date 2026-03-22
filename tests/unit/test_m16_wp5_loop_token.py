"""M16-WP5 unit tests for loop-token discipline and classifier cache behavior."""

from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from openqilin.control_plane.grammar.intent_classifier import IntentClassifier
from openqilin.control_plane.grammar.models import ChatContext, GrammarParseError, IntentClass
from openqilin.observability.metrics.recorder import OTelMetricRecorder
from openqilin.observability.testing.stubs import InMemoryMetricRecorder
from openqilin.task_orchestrator.loop_control import LoopState, check_and_increment_hop


def _context(*, channel_id: str) -> ChatContext:
    return ChatContext(chat_class="project", channel_id=channel_id, project_id="proj-001")


def _served_response(intent: str = "discussion") -> SimpleNamespace:
    return SimpleNamespace(decision="served", generated_text=intent)


def test_cache_hit_skips_llm_call() -> None:
    llm_gateway = MagicMock()
    llm_gateway.complete.return_value = _served_response("discussion")
    classifier = IntentClassifier(llm_gateway=llm_gateway)

    ctx = _context(channel_id="ch-1")
    assert classifier.classify("status update please", ctx) == IntentClass.DISCUSSION
    assert classifier.classify("status update please", ctx) == IntentClass.DISCUSSION
    assert llm_gateway.complete.call_count == 1


def test_cache_miss_different_channel() -> None:
    llm_gateway = MagicMock()
    llm_gateway.complete.return_value = _served_response("discussion")
    classifier = IntentClassifier(llm_gateway=llm_gateway)

    classifier.classify("same text", _context(channel_id="ch-1"))
    classifier.classify("same text", _context(channel_id="ch-2"))

    assert llm_gateway.complete.call_count == 2


def test_cache_miss_different_message() -> None:
    llm_gateway = MagicMock()
    llm_gateway.complete.return_value = _served_response("discussion")
    classifier = IntentClassifier(llm_gateway=llm_gateway)

    ctx = _context(channel_id="ch-1")
    classifier.classify("first message", ctx)
    classifier.classify("second message", ctx)

    assert llm_gateway.complete.call_count == 2


def test_cache_expired_calls_llm_again() -> None:
    llm_gateway = MagicMock()
    llm_gateway.complete.return_value = _served_response("discussion")
    classifier = IntentClassifier(llm_gateway=llm_gateway)

    message = "re-evaluate this"
    ctx = _context(channel_id="ch-1")
    key = (message[:1000], ctx.channel_id)
    classifier._cache[key] = (IntentClass.QUERY, time.monotonic() - 61.0)

    classifier.classify(message, ctx)

    assert llm_gateway.complete.call_count == 1


def test_mutation_not_cached() -> None:
    llm_gateway = MagicMock()
    llm_gateway.complete.return_value = _served_response("mutation")
    classifier = IntentClassifier(llm_gateway=llm_gateway)

    with pytest.raises(GrammarParseError) as exc_info:
        classifier.classify("delete project alpha", _context(channel_id="ch-1"))

    assert exc_info.value.code == "GRAM-004"
    assert classifier._cache == {}


def test_llm_unavailable_not_cached() -> None:
    llm_gateway = MagicMock()
    llm_gateway.complete.return_value = SimpleNamespace(decision="denied", generated_text=None)
    classifier = IntentClassifier(llm_gateway=llm_gateway)

    outcome = classifier.classify("status update please", _context(channel_id="ch-1"))

    assert outcome == IntentClass.DISCUSSION
    assert classifier._cache == {}


def test_metric_incremented_on_cache_miss() -> None:
    llm_gateway = MagicMock()
    llm_gateway.complete.return_value = _served_response("query")
    metric_recorder = InMemoryMetricRecorder()
    classifier = IntentClassifier(llm_gateway=llm_gateway, metric_recorder=metric_recorder)

    classifier.classify("what is the budget", _context(channel_id="ch-1"))

    assert (
        metric_recorder.get_counter_value(
            "llm_calls_total",
            labels={"purpose": "intent_classification"},
        )
        == 1
    )


def test_no_metric_on_cache_hit() -> None:
    llm_gateway = MagicMock()
    llm_gateway.complete.return_value = _served_response("discussion")
    metric_recorder = InMemoryMetricRecorder()
    classifier = IntentClassifier(llm_gateway=llm_gateway, metric_recorder=metric_recorder)

    ctx = _context(channel_id="ch-1")
    classifier.classify("repeat message", ctx)
    classifier.classify("repeat message", ctx)

    assert (
        metric_recorder.get_counter_value(
            "llm_calls_total",
            labels={"purpose": "intent_classification"},
        )
        == 1
    )


def test_no_metric_on_llm_unavailable() -> None:
    llm_gateway = MagicMock()
    llm_gateway.complete.return_value = SimpleNamespace(decision="denied", generated_text=None)
    metric_recorder = InMemoryMetricRecorder()
    classifier = IntentClassifier(llm_gateway=llm_gateway, metric_recorder=metric_recorder)

    classifier.classify("classification fallback", _context(channel_id="ch-1"))

    assert (
        metric_recorder.get_counter_value(
            "llm_calls_total",
            labels={"purpose": "intent_classification"},
        )
        == 0
    )


def test_loop_state_per_task_isolation() -> None:
    loop_state_a = LoopState()
    loop_state_b = LoopState()

    check_and_increment_hop(loop_state_a)

    assert loop_state_a.hop_count == 1
    assert loop_state_b.hop_count == 0


def test_otel_metric_recorder_no_exception() -> None:
    recorder = OTelMetricRecorder()
    recorder.increment_counter("test_counter", labels={"k": "v"})
