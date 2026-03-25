"""Deterministic keyword-to-agent advisory routing authority table."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

TOPIC_ROUTING_TABLE: dict[str, frozenset[str]] = {
    "auditor": frozenset(
        {
            "budget",
            "spend",
            "spending",
            "compliance",
            "violation",
            "audit",
            "trail",
            "financial",
            "expenditure",
            "cost",
            "overrun",
            "breach",
            "governance breach",
        }
    ),
    "cso": frozenset(
        {
            "strategic",
            "strategy",
            "portfolio",
            "alignment",
            "cross-project",
            "opportunity",
            "conflict",
            "risk",
            "roadmap",
        }
    ),
    "project_manager": frozenset(
        {
            "task",
            "assignment",
            "blocked",
            "milestone",
            "progress",
            "execution plan",
            "sprint",
            "backlog",
        }
    ),
    "cwo": frozenset(
        {
            "charter",
            "workforce",
            "initialization",
            "specialist",
            "workforce plan",
            "role binding",
            "agent activation",
        }
    ),
    "ceo": frozenset(
        {
            "approve",
            "directive",
            "executive",
            "authorize",
            "escalation",
            "final decision",
        }
    ),
    "administrator": frozenset(
        {
            "infrastructure",
            "infra",
            "document policy",
            "retention",
            "quarantine",
            "integrity",
            "hash",
            "system health",
            "health check",
            "policy enforcement",
            "agent health",
        }
    ),
}


@dataclass(frozen=True, slots=True)
class RoutingDecision:
    agent_role: str
    confidence: Literal["high", "low"]
    matched_keywords: list[str] = field(default_factory=list)


class AdvisoryTopicRouter:
    """Classify free-text messages to institutional agent roles by keyword matching."""

    def classify(self, text: str) -> RoutingDecision | None:
        """Classify text against TOPIC_ROUTING_TABLE.

        Matching is substring-based on lowercased text.
        Returns None if no keyword matches, or if two roles tie on keyword count.
        Returns RoutingDecision(confidence="high") when one role wins.
        """

        normalized_text = text.lower()
        matches: list[tuple[str, int, list[str]]] = []

        for role, keywords in TOPIC_ROUTING_TABLE.items():
            matched_keywords = [keyword for keyword in keywords if keyword in normalized_text]
            if matched_keywords:
                matches.append((role, len(matched_keywords), matched_keywords))

        if not matches:
            return None

        if len(matches) == 1:
            role, _count, matched_keywords = matches[0]
            return RoutingDecision(
                agent_role=role,
                confidence="high",
                matched_keywords=matched_keywords,
            )

        max_count = max(count for _role, count, _keywords in matches)
        winners = [
            (role, matched_keywords)
            for role, count, matched_keywords in matches
            if count == max_count
        ]
        if len(winners) != 1:
            return None

        role, matched_keywords = winners[0]
        return RoutingDecision(
            agent_role=role,
            confidence="high",
            matched_keywords=matched_keywords,
        )
