"""Policy evaluation-input normalization."""

from __future__ import annotations

from openqilin.data_access.repositories.runtime_state import TaskRecord
from openqilin.policy_runtime_integration.models import PolicyEvaluationInput


def normalize_policy_input(task: TaskRecord) -> PolicyEvaluationInput:
    """Normalize admitted task into policy-runtime input shape."""

    return PolicyEvaluationInput(
        task_id=task.task_id,
        request_id=task.request_id,
        trace_id=task.trace_id,
        principal_id=task.principal_id,
        principal_role=task.principal_role,
        trust_domain=task.trust_domain,
        connector=task.connector,
        action=task.command,
        target=task.target,
        args=task.args,
        project_id=task.project_id,
    )
