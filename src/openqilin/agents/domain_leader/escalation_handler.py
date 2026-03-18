"""EscalationHandler — PM calls DL; DL produces DomainLeaderResponse; PM synthesises channel reply.

Usage by ProjectManager:
    handler = EscalationHandler(dl_agent)
    response = handler.escalate(project_id=..., message=..., task_id=..., trace_id=...)
    # PM uses response.advisory_text to synthesise channel reply
    # If response.domain_outcome == "domain_risk_escalation": PM escalates to CWO
"""

from __future__ import annotations

from openqilin.agents.domain_leader.agent import DomainLeaderAgent
from openqilin.agents.domain_leader.models import DomainLeaderRequest, DomainLeaderResponse


class EscalationHandler:
    """Bridges ProjectManager escalation calls to the DomainLeaderAgent.

    PM is responsible for:
    - Sending the escalation request.
    - Synthesising the channel reply from ``DomainLeaderResponse.advisory_text``.
    - Further escalating to CWO when ``domain_outcome == "domain_risk_escalation"``.

    DL never writes to the Discord channel directly.
    """

    def __init__(self, domain_leader: DomainLeaderAgent) -> None:
        self._dl = domain_leader

    def escalate(
        self,
        *,
        project_id: str,
        message: str,
        trace_id: str,
        task_id: str | None = None,
        requesting_agent: str = "project_manager",
    ) -> DomainLeaderResponse:
        """Escalate PM request to DL. Returns DL domain response for PM synthesis."""
        request = DomainLeaderRequest(
            project_id=project_id,
            message=message,
            requesting_agent=requesting_agent,
            trace_id=trace_id,
            task_id=task_id,
        )
        return self._dl.handle_escalation(request)
