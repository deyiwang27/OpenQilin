"""Issues #161/#164 unit tests for llm_calls_total wiring."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from openqilin.agents.project_manager.agent import ProjectManagerAgent
from openqilin.agents.project_manager.artifact_writer import PMProjectArtifactWriter
from openqilin.agents.project_manager.models import ProjectManagerRequest
from openqilin.agents.secretary.agent import SecretaryAgent
from openqilin.agents.secretary.models import SecretaryRequest
from openqilin.control_plane.grammar.models import ChatContext, IntentClass
from openqilin.observability.testing.stubs import InMemoryMetricRecorder


def _served_response(text: str = "advisory") -> SimpleNamespace:
    return SimpleNamespace(decision="served", generated_text=text)


def _denied_response() -> SimpleNamespace:
    return SimpleNamespace(decision="denied", generated_text=None)


def _secretary_request(intent: IntentClass = IntentClass.DISCUSSION) -> SecretaryRequest:
    return SecretaryRequest(
        message="Hello",
        intent=intent,
        context=ChatContext(chat_class="general", channel_id="ch-1", project_id=None),
        trace_id="trace-sec-1",
    )


def _project_manager_request() -> ProjectManagerRequest:
    return ProjectManagerRequest(
        project_id="proj-001",
        message="What is the status?",
        intent="DISCUSSION",
        context={},
        trace_id="trace-pm-1",
    )


def _project_manager_agent(
    *,
    llm: MagicMock,
    metric_recorder: InMemoryMetricRecorder | None = None,
) -> ProjectManagerAgent:
    data_access = SimpleNamespace(get_project_snapshot=lambda _project_id: None)
    project_artifact_repo = SimpleNamespace()
    return ProjectManagerAgent(
        llm_gateway=llm,
        artifact_writer=MagicMock(spec=PMProjectArtifactWriter),
        data_access=data_access,  # type: ignore[arg-type]
        domain_leader_agent=MagicMock(),
        task_dispatch_service=MagicMock(),
        project_artifact_repo=project_artifact_repo,
        metric_recorder=metric_recorder,
    )


def test_secretary_increments_llm_calls_total() -> None:
    llm = MagicMock()
    llm.complete.return_value = _served_response()
    recorder = InMemoryMetricRecorder()
    agent = SecretaryAgent(llm_gateway=llm, metric_recorder=recorder)

    agent.handle(_secretary_request())

    assert (
        recorder.get_counter_value(
            "llm_calls_total",
            labels={"purpose": "secretary_response"},
        )
        == 1
    )


def test_secretary_increments_on_each_call() -> None:
    llm = MagicMock()
    llm.complete.return_value = _served_response()
    recorder = InMemoryMetricRecorder()
    agent = SecretaryAgent(llm_gateway=llm, metric_recorder=recorder)

    agent.handle(_secretary_request())
    agent.handle(_secretary_request())

    assert (
        recorder.get_counter_value(
            "llm_calls_total",
            labels={"purpose": "secretary_response"},
        )
        == 2
    )


def test_secretary_increments_even_on_denied_response() -> None:
    llm = MagicMock()
    llm.complete.return_value = _denied_response()
    recorder = InMemoryMetricRecorder()
    agent = SecretaryAgent(llm_gateway=llm, metric_recorder=recorder)

    agent.handle(_secretary_request())

    assert (
        recorder.get_counter_value(
            "llm_calls_total",
            labels={"purpose": "secretary_response"},
        )
        == 1
    )


def test_secretary_no_recorder_no_error() -> None:
    llm = MagicMock()
    llm.complete.return_value = _served_response()
    agent = SecretaryAgent(llm_gateway=llm)

    agent.handle(_secretary_request())


def test_pm_increments_llm_calls_total() -> None:
    llm = MagicMock()
    llm.complete.return_value = _served_response("Status: all good.")
    recorder = InMemoryMetricRecorder()
    agent = _project_manager_agent(llm=llm, metric_recorder=recorder)

    agent.handle(_project_manager_request())

    assert (
        recorder.get_counter_value(
            "llm_calls_total",
            labels={"purpose": "pm_response"},
        )
        == 1
    )


def test_pm_no_recorder_no_error() -> None:
    llm = MagicMock()
    llm.complete.return_value = _served_response("Status: all good.")
    agent = _project_manager_agent(llm=llm)

    agent.handle(_project_manager_request())
