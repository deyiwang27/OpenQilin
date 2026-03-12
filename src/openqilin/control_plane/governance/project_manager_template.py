"""Project Manager template contract validation for mandatory operations."""

from __future__ import annotations

from dataclasses import dataclass

MANDATORY_PROJECT_MANAGER_OPERATIONS = (
    "milestone_planning",
    "task_decomposition",
    "task_assignment",
    "progress_reporting",
)

_OPERATION_TOKEN_RULES: dict[str, tuple[str, ...]] = {
    "milestone_planning": ("milestone", "plan"),
    "task_decomposition": ("decompos", "task"),
    "task_assignment": ("assign", "task"),
    "progress_reporting": ("progress", "report"),
}


@dataclass(frozen=True, slots=True)
class ProjectManagerTemplateValidationResult:
    """Validated Project Manager mandatory operation contract."""

    mandatory_operations: tuple[str, ...]


class ProjectManagerTemplateError(ValueError):
    """Raised when Project Manager template misses mandatory operations."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def validate_project_manager_template(system_prompt: str) -> ProjectManagerTemplateValidationResult:
    """Validate required Project Manager operations from system prompt text."""

    normalized_prompt = system_prompt.strip().lower()
    if not normalized_prompt:
        raise ProjectManagerTemplateError(
            code="project_manager_template_invalid",
            message="project manager template prompt must not be blank",
        )

    missing_operations = []
    for operation, required_tokens in _OPERATION_TOKEN_RULES.items():
        if not all(token in normalized_prompt for token in required_tokens):
            missing_operations.append(operation)

    if missing_operations:
        raise ProjectManagerTemplateError(
            code="project_manager_template_missing_operations",
            message=(
                "project manager template missing mandatory operations: "
                + ", ".join(missing_operations)
            ),
        )

    return ProjectManagerTemplateValidationResult(
        mandatory_operations=MANDATORY_PROJECT_MANAGER_OPERATIONS
    )
