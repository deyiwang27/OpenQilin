"""Grammar layer command parser: /oq <verb> [target] [args...] → CommandEnvelope."""

from __future__ import annotations

import shlex

from openqilin.control_plane.grammar.models import CommandEnvelope, GrammarParseError

_COMMAND_PREFIX = "/oq"

# Verb catalog per OwnerInteractionGrammar.md §5
_KNOWN_VERBS: frozenset[str] = frozenset(
    {
        "project",
        "ask",
        "status",
        "escalate",
        "approve",
        "deny",
        "doctor",
        "discord",
        "governance",
    }
)


class CommandParser:
    """Parse compact /oq command syntax into a CommandEnvelope."""

    def parse(self, raw_input: str) -> CommandEnvelope:
        """Parse raw /oq command string into CommandEnvelope.

        Raises GrammarParseError on unrecognized verb or malformed input.
        """
        stripped = raw_input.strip()
        if not stripped.startswith(_COMMAND_PREFIX):
            raise GrammarParseError(
                code="GRAM-005",
                message=(f"input is not a compact command (must start with {_COMMAND_PREFIX!r})"),
                details={"raw_input": raw_input[:256]},
            )

        try:
            tokens = shlex.split(stripped)
        except ValueError as exc:
            raise GrammarParseError(
                code="GRAM-005",
                message=f"malformed command syntax: {exc}",
                details={"raw_input": raw_input[:256]},
            ) from exc

        # tokens[0] == "/oq", tokens[1] == verb
        if len(tokens) < 2:
            raise GrammarParseError(
                code="GRAM-005",
                message="compact command requires a verb: /oq <verb> [target] [args]",
                details={"raw_input": raw_input[:256]},
            )

        verb = tokens[1].lower()
        if verb not in _KNOWN_VERBS:
            raise GrammarParseError(
                code="GRAM-005",
                message=(f"unrecognized verb {verb!r}; supported: {sorted(_KNOWN_VERBS)}"),
                details={"verb": verb, "raw_input": raw_input[:256]},
            )

        remainder = tokens[2:]
        target: str | None = remainder[0] if remainder else None
        args = remainder[1:] if len(remainder) > 1 else []

        return CommandEnvelope(
            verb=verb,
            target=target,
            args=args,
            raw_input=raw_input,
        )
