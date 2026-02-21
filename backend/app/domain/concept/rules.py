"""Business rules for the Concept domain — enforces the lifecycle state machine."""
from __future__ import annotations
from app.domain.common.result import Result

# Valid status values
VALID_STATUSES = {"DRAFT", "REVIEW", "APPROVED", "PUBLISHED"}

# The only allowed forward transitions (no reversal)
ALLOWED_TRANSITIONS: dict[str, str] = {
    "DRAFT": "REVIEW",
    "REVIEW": "APPROVED",
    "APPROVED": "PUBLISHED",
}

# Which roles can make which transitions
TRANSITION_ROLES: dict[str, set[str]] = {
    "REVIEW": {"author", "admin"},
    "APPROVED": {"reviewer", "admin"},
    "PUBLISHED": {"approver", "admin"},
}


def validate_status_transition(current_status: str, new_status: str, user_role: str = "admin") -> Result[str]:
    """
    Enforces DRAFT → REVIEW → APPROVED → PUBLISHED.
    Returns Result.ok(new_status) or Result.fail(reason).
    """
    if new_status not in VALID_STATUSES:
        return Result.fail(f"'{new_status}' is not a valid status. Must be one of {VALID_STATUSES}.")

    expected_next = ALLOWED_TRANSITIONS.get(current_status)
    if expected_next is None:
        return Result.fail(f"Concept is already in terminal status '{current_status}'. No further transitions allowed.")

    if new_status != expected_next:
        return Result.fail(
            f"Invalid transition: '{current_status}' → '{new_status}'. "
            f"Only '{current_status}' → '{expected_next}' is allowed."
        )

    allowed_roles = TRANSITION_ROLES.get(new_status, set())
    if user_role not in allowed_roles:
        return Result.fail(
            f"Role '{user_role}' cannot transition to '{new_status}'. "
            f"Required roles: {sorted(allowed_roles)}."
        )

    return Result.ok(new_status)


def validate_concept_content(data: dict) -> Result[dict]:
    """Validates that a concept has the minimum required fields."""
    name = (data.get("name") or "").strip()
    if not name:
        return Result.fail("Concept 'name' is required and cannot be empty.")
    return Result.ok(data)
